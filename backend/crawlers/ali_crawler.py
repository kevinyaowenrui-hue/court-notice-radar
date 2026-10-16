# -*- coding: utf-8 -*-
"""
阿里司法拍卖真实采集器 (Alibaba Judicial Auction Live Crawler)
来源: https://sf.taobao.com / https://sf-item.taobao.com
采用 Playwright 实时抓取阿里司法拍卖全国法院上架的真实法拍房、车辆、股权、机械等资产
"""
import asyncio
import re
import json
import random
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from urllib.parse import quote
from playwright.async_api import async_playwright
from sqlalchemy.orm import Session
from backend.models import CourtNotice

import os
from backend.database import SessionLocal, DATA_DIR
from backend.utils import (
    run_async, detect_henan_info, stable_hash, categorize_notice_module,
    is_vehicle_or_equipment_item, parse_price_amount, launch_smart_browser,
    extract_bidding_times, extract_judicial_case_number, find_existing_notice
)

async def scrape_single_ali_page(
    page, context, target_url: str, url_type: str,
    seen_urls: set, seen_raw_ids: set, warning_reasons: list
) -> List[dict]:
    items = []
    # 防风控平滑等待 2.5 ~ 4.5 秒
    await page.wait_for_timeout(random.randint(2500, 4500))
    print(f"[ali_crawler] Accessing {url_type}: {target_url}")

    for attempt in range(2):
        try:
            await page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)
        except Exception as ge:
            print(f"[ali_crawler] goto note on {url_type} attempt {attempt+1}: {ge}")
            if attempt == 0:
                await asyncio.sleep(random.uniform(2, 4))
                continue
            else:
                return items

        current_url = page.url
        page_title = await page.title()
        is_blocked = any(k in current_url for k in ['punish', 'sec.taobao.com', 'login.taobao.com', 'rgv587']) or any(k in page_title for k in ['验证码', '安全验证', '登录'])
        if is_blocked:
            if attempt == 0:
                print(f"[ali_crawler] [{url_type}] Triggered anti-scraping on attempt 1 ({current_url}), sleeping 3~5s and retrying...")
                await asyncio.sleep(random.uniform(3, 5))
                continue
            else:
                warning_reasons.append(f"[{url_type}] 触发淘宝风控安全验证: {current_url}")
                print(f"[ali_crawler] [{url_type}] Anti-scraping unresolved, skipping this page.")
                return items
        else:
            break

    # 1. 优先定位 <script id="sf-item-list-data" type="text/json">
    json_parsed_success = False
    try:
        script_el = await page.query_selector("script#sf-item-list-data")
        if script_el:
            script_content = await script_el.inner_text()
            if script_content:
                sf_json = json.loads(script_content)
                sf_data = sf_json.get("data", [])
                if isinstance(sf_data, list) and sf_data:
                    print(f"[ali_crawler] [{url_type}] Located sf-item-list-data JSON with {len(sf_data)} items")
                    for d in sf_data:
                        p_id = str(d.get("id") or "")
                        if not p_id:
                            continue
                        raw_id = f"ali_{p_id}"
                        if raw_id in seen_raw_ids:
                            continue
                        seen_raw_ids.add(raw_id)
                        clean_url = f"https://sf-item.taobao.com/sf_item/{p_id}.htm"
                        seen_urls.add(clean_url)

                        title = (d.get("title") or "").strip()
                        if not title or is_vehicle_or_equipment_item(title):
                            continue

                        sp = d.get("initialPrice")
                        ep = d.get("consultPrice")
                        try:
                            sp = float(sp) if sp is not None else None
                        except Exception:
                            sp = None
                        try:
                            ep = float(ep) if ep is not None else None
                        except Exception:
                            ep = None

                        court_name = (d.get("court") or d.get("courtName") or "").strip()
                        if not court_name:
                            cm = re.search(r'^(?:位于)?([\u4e00-\u9fa5]{2,6}(?:省|市|区|县))', title)
                            court_name = f"{cm.group(1)}人民法院" if cm else "人民法院司法拍卖"

                        stage_map = {1: "一拍", 2: "二拍", 3: "变卖", 4: "重新拍卖"}
                        raw_stage = d.get("sellStage")
                        auction_stage = stage_map.get(raw_stage, "一拍")
                        if "变卖" in title:
                            auction_stage = "变卖"
                        elif "二拍" in title:
                            auction_stage = "二拍"

                        b_start, b_end = None, None
                        if d.get("start"):
                            try:
                                b_start = datetime.fromtimestamp(int(d["start"]) / 1000)
                            except Exception:
                                pass
                        if d.get("end"):
                            try:
                                b_end = datetime.fromtimestamp(int(d["end"]) / 1000)
                            except Exception:
                                pass

                        publish_time = None
                        now_time = datetime.now()
                        if b_start:
                            if b_start <= now_time:
                                publish_time = b_start - timedelta(days=7)
                            else:
                                days_adv = 15 if "二拍" in title or "变卖" in title else 30
                                inferred = b_start - timedelta(days=days_adv)
                                days_left = (b_start - now_time).total_seconds() / 86400.0
                                publish_time = inferred if inferred <= now_time else (now_time - timedelta(days=max(1, int(days_adv - days_left))))
                        else:
                            publish_time = now_time

                        category = "其他资产"
                        t_clean = re.sub(r'[\u4e00-\u9fa5]{2,30}(?:公司|分公司|支行|行)(?:名下|持有)?', '', title)
                        if any(k in title for k in ["股", "证券", "债券", "债权", "资产包", "保单", "份额"]):
                            category = "金融债权与股权"
                        elif any(k in title for k in ["地块", "土地", "厂房", "仓库", "工业园", "工业用地", "林权", "矿权", "构筑物"]):
                            category = "工业厂房与土地"
                        elif any(k in t_clean for k in ["房产", "住宅", "商品房", "公寓", "排屋", "大厦", "门面", "商铺", "车位", "车库", "人防车位", "室", "号楼", "单元", "楼房", "写字楼", "别墅"]):
                            category = "住宅/商业房产"

                        desc_text = f"【阿里司法拍卖真实标的】\n标的物：{title}\n当前起拍价：¥{sp:,.2f} 元\n拍卖阶段：{auction_stage}\n处置法院：{court_name}\n详情链接：{clean_url}" if sp else f"{title}\n原站直达：{clean_url}"
                        is_henan, henan_city, henan_tag = detect_henan_info(title=title, content=desc_text, court_name=court_name)
                        case_no = extract_judicial_case_number(f"{title} {desc_text}")
                        sp_clean = round(float(sp), 2) if sp is not None else None
                        ep_clean = round(float(ep), 2) if ep is not None else None
                        if sp_clean is not None and ep_clean is not None and sp_clean == ep_clean:
                            ep_clean = None

                        items.append({
                            "platform": "ali",
                            "raw_id": raw_id,
                            "court_name": court_name,
                            "case_number": case_no,
                            "parties": "",
                            "notice_type": "司法拍卖",
                            "title": title,
                            "content_text": desc_text,
                            "publish_time": publish_time,
                            "source_url": clean_url,
                            "starting_price": sp_clean,
                            "eval_price": ep_clean,
                            "auction_stage": auction_stage,
                            "asset_category": category,
                            "bidding_start": b_start,
                            "bidding_end": b_end,
                            "is_henan": is_henan,
                            "henan_city": henan_city,
                            "henan_tag": henan_tag
                        })
                    json_parsed_success = True
    except Exception as je:
        print(f"[ali_crawler] JSON parse note: {je}")

    # 2. 若 JSON 提取失败或为空，从 DOM 卡片中兜底提取
    if not json_parsed_success or len(items) == 0:
        try:
            cards = await page.query_selector_all("li.sf-item, .pai-item, li[class*='item-']")
            if not cards:
                cards = await page.query_selector_all("a[href*='sf-item.taobao.com/sf_item/']")
            print(f"[ali_crawler] [{url_type}] DOM fallback found {len(cards)} candidate card elements")
            for card in cards:
                try:
                    href = await card.get_attribute("href")
                    if not href:
                        link_el = await card.query_selector("a[href*='sf_item']")
                        if link_el:
                            href = await link_el.get_attribute("href")
                    if not href:
                        continue
                    if href.startswith("//"):
                        href = "https:" + href
                    clean_url = href.split("?")[0]
                    m_id = re.search(r'sf_item/(\d+)', clean_url)
                    if not m_id:
                        m_id = re.search(r'id=(\d+)', href)
                    if not m_id:
                        continue
                    raw_id = f"ali_{m_id.group(1)}"
                    if raw_id in seen_raw_ids or clean_url in seen_urls:
                        continue
                    seen_raw_ids.add(raw_id)
                    seen_urls.add(clean_url)

                    raw_text = (await card.inner_text() or "").strip()
                    lines = [ln.strip() for ln in raw_text.split('\n') if ln.strip()]
                    title = lines[0] if lines else ""
                    for ln in lines:
                        if len(ln) > len(title) and not ln.startswith("¥") and "拍卖" not in ln and "评估" not in ln:
                            title = ln
                            break
                    if not title or is_vehicle_or_equipment_item(title, raw_text):
                        continue

                    starting_price = None
                    eval_price = None
                    for line in lines:
                        if any(k in line for k in ["起拍", "当前价", "变卖价"]):
                            p = parse_price_amount(line)
                            if p is not None:
                                starting_price = p
                        elif "评估" in line:
                            p = parse_price_amount(line)
                            if p is not None:
                                eval_price = p
                        elif "¥" in line and starting_price is None and not any(k in line for k in ["评估", "保证金", "加价"]):
                            p = parse_price_amount(line)
                            if p is not None:
                                starting_price = p

                    auction_stage = "一拍"
                    if "二拍" in raw_text or "二拍" in title:
                        auction_stage = "二拍"
                    elif "变卖" in raw_text or "变卖" in title:
                        auction_stage = "变卖"

                    category = "其他资产"
                    t_clean = re.sub(r'[\u4e00-\u9fa5]{2,30}(?:公司|分公司|支行|行)(?:名下|持有)?', '', title)
                    if any(k in title for k in ["股", "证券", "债券", "债权", "资产包", "保单", "份额"]):
                        category = "金融债权与股权"
                    elif any(k in title for k in ["地块", "土地", "厂房", "仓库", "工业园", "工业用地", "林权", "矿权", "构筑物"]):
                        category = "工业厂房与土地"
                    elif any(k in t_clean for k in ["房产", "住宅", "商品房", "公寓", "排屋", "大厦", "门面", "商铺", "车位", "车库", "人防车位", "室", "号楼", "单元", "楼房", "写字楼", "别墅"]):
                        category = "住宅/商业房产"

                    city_m = re.search(r'^(?:位于)?([\u4e00-\u9fa5]{2,6}(?:省|市|区|县))', title)
                    court_name = f"{city_m.group(1)}人民法院" if city_m else "人民法院司法拍卖"

                    content_text = f"【阿里司法拍卖真实标的】\n标的物：{title}\n当前起拍价：¥{starting_price:,.2f} 元\n拍卖阶段：{auction_stage}\n处置法院：{court_name}\n详情链接：{clean_url}\n{raw_text[:200]}" if starting_price else f"{title}\n原站直达：{clean_url}\n{raw_text[:200]}"

                    b_start, b_end = extract_bidding_times(raw_text)
                    publish_time = None
                    now_time = datetime.now()
                    if b_start:
                        if b_start <= now_time:
                            publish_time = b_start - timedelta(days=7)
                        else:
                            days_adv = 15 if "二拍" in title or "变卖" in title else 30
                            inferred = b_start - timedelta(days=days_adv)
                            days_left = (b_start - now_time).total_seconds() / 86400.0
                            publish_time = inferred if inferred <= now_time else (now_time - timedelta(days=max(1, int(days_adv - days_left))))
                    else:
                        publish_time = now_time

                    is_henan, henan_city, henan_tag = detect_henan_info(title=title, content=content_text, court_name=court_name)
                    case_no = extract_judicial_case_number(f"{title} {raw_text}")
                    sp_clean = round(float(starting_price), 2) if starting_price is not None else None
                    ep_clean = round(float(eval_price), 2) if eval_price is not None else None
                    if sp_clean is not None and ep_clean is not None and sp_clean == ep_clean:
                        ep_clean = None

                    items.append({
                        "platform": "ali",
                        "raw_id": raw_id,
                        "court_name": court_name,
                        "case_number": case_no,
                        "parties": "",
                        "notice_type": "司法拍卖",
                        "title": title,
                        "content_text": content_text,
                        "publish_time": publish_time,
                        "source_url": clean_url,
                        "starting_price": sp_clean,
                        "eval_price": ep_clean,
                        "auction_stage": auction_stage,
                        "asset_category": category,
                        "bidding_start": b_start,
                        "bidding_end": b_end,
                        "is_henan": is_henan,
                        "henan_city": henan_city,
                        "henan_tag": henan_tag
                    })
                except Exception as ce:
                    continue
        except Exception as de:
            print(f"[ali_crawler] DOM query note: {de}")

    return items

async def fetch_ali_real_auctions() -> List[dict]:
    results = []
    async with async_playwright() as p:
        user_data_dir = os.path.join(DATA_DIR, "ali_profile")
        os.makedirs(user_data_dir, exist_ok=True)
        browser = None
        try:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-infobars',
                    '--disable-dev-shm-usage',
                    '--lang=zh-CN'
                ],
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                locale="zh-CN",
                viewport={"width": 1280, "height": 900}
            )
        except Exception as e:
            print(f"[ali_crawler] Persistent context note: {e}, falling back to ephemeral context")
            browser = await launch_smart_browser(p, headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                locale="zh-CN",
                viewport={"width": 1280, "height": 900}
            )

        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = await context.new_page()

        # 先访问主站首页预热会话 Cookie，有效防止直接打开检索页被重定向到惩罚验证页
        try:
            print("[ali_crawler] Warming up session cookies on https://sf.taobao.com...")
            await page.goto("https://sf.taobao.com/", timeout=15000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"[ali_crawler] Warmup notice: {e}")

        # 预载存量已有的阿里标的 raw_id 与 source_url，用于增量早停判断
        known_db_raw_ids = set()
        known_db_urls = set()
        try:
            with SessionLocal() as s:
                rows = s.query(CourtNotice.raw_id, CourtNotice.source_url).filter(CourtNotice.platform == 'ali').all()
                for rid, surl in rows:
                    if rid:
                        known_db_raw_ids.add(rid)
                    if surl:
                        known_db_urls.add(surl.split('?')[0])
        except Exception as e:
            print(f"[ali_crawler] Pre-fetch existing ids note: {e}")

        # 覆盖河南全省 18 地级市 + 重点标的词 + 省级大盘
        henan_18_cities = [
            "郑州", "洛阳", "南阳", "新乡", "商丘", "周口", "驻马店", "信阳",
            "平顶山", "安阳", "开封", "焦作", "许昌", "濮阳", "漯河", "三门峡", "鹤壁", "济源"
        ]
        henan_key_terms = [
            "河南 房产", "河南 土地", "河南 工业", "河南 股权", "河南 债权", "河南 破产"
        ]

        search_tasks = [
            ("https://sf.taobao.com/item_list.htm?province=%BA%D3%C4%CF&order=createTime_desc", "阿里法拍·河南最新", 3),
            ("https://sf.taobao.com/?order=createTime_desc", "阿里法拍·全国大盘最新", 1)
        ]
        for city in henan_18_cities:
            gbk_city = quote(city.encode('gbk'))
            max_p = 3 if city in ["郑州", "洛阳", "南阳", "新乡"] else 2
            search_tasks.append((
                f"https://sf.taobao.com/item_list.htm?q={gbk_city}&order=createTime_desc",
                f"阿里法拍·{city}",
                max_p
            ))
        for kw in henan_key_terms:
            gbk_kw = quote(kw.encode('gbk'))
            search_tasks.append((
                f"https://sf.taobao.com/item_list.htm?q={gbk_kw}&order=createTime_desc",
                f"阿里法拍·{kw}",
                2
            ))

        seen_urls = set()
        seen_raw_ids = set()

        warning_reasons = []

        try:
            for base_url, task_name, max_pages in search_tasks:
                for page_num in range(1, max_pages + 1):
                    target_url = base_url if page_num == 1 else f"{base_url}&page={page_num}"
                    url_type = f"{task_name} (第{page_num}页)"
                    try:
                        page_items = await scrape_single_ali_page(
                            page, context, target_url, url_type,
                            seen_urls, seen_raw_ids, warning_reasons
                        )
                        results.extend(page_items)

                        # 动态增量早停判断：如果当前页解析出的拍品中有 80% 以上在数据库中已存在，则停止该任务后续翻页
                        if page_items:
                            exist_cnt = sum(
                                1 for item in page_items
                                if item["raw_id"] in known_db_raw_ids or item["source_url"].split('?')[0] in known_db_urls
                            )
                            ratio = exist_cnt / len(page_items)
                            print(f"[ali_crawler] [{url_type}] 抓取 {len(page_items)} 件，其中 {exist_cnt} 件已存在于库中 (存量比 {ratio*100:.1f}%)")
                            if ratio >= 0.8:
                                print(f"[ali_crawler] [{task_name}] 存量占比达 {ratio*100:.1f}% >= 80%，触达历史存量边界，早停后续翻页。")
                                break
                        else:
                            print(f"[ali_crawler] [{url_type}] 本页无新增标的，结束后续翻页。")
                            break
                    except Exception as pe:
                        print(f"[ali_crawler] Error on {url_type}: {pe}")
        finally:
            try:
                await page.close()
            except Exception:
                pass
            try:
                await context.close()
            except Exception:
                pass
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
    warning_msg = " ; ".join(warning_reasons) if warning_reasons else None
    return results, warning_msg

def crawl_ali_auctions(db: Optional[Session] = None, max_items: int = 40) -> Tuple[List[CourtNotice], int, Optional[str]]:
    """主入口：执行抓取并存入数据库，返回(新记录, 发现总数, 警告信息)"""
    items, warning_msg = run_async(fetch_ali_real_auctions())
    new_records = []
    seen_db_ids = set()

    close_when_done = False
    if db is None:
        db = SessionLocal()
        close_when_done = True

    try:
        for item in items:
            if item["raw_id"] in seen_db_ids:
                continue
            seen_db_ids.add(item["raw_id"])

            mod_type = categorize_notice_module(item["title"], item["content_text"], item["notice_type"], item["platform"])

            existing = find_existing_notice(db, item["platform"], item["raw_id"], item["title"], item.get("auction_stage"))
            if not existing:
                notice = CourtNotice(
                    platform=item["platform"],
                    raw_id=item["raw_id"],
                    court_name=item["court_name"],
                    case_number=item["case_number"],
                    parties=item.get("parties", ""),
                    notice_type=item["notice_type"],
                    module_type=mod_type,
                    title=item["title"],
                    content_text=item["content_text"],
                    publish_time=item.get("publish_time") or datetime.now(),
                    source_url=item["source_url"],
                    starting_price=item["starting_price"],
                    eval_price=item["eval_price"],
                    auction_stage=item["auction_stage"],
                    asset_category=item["asset_category"],
                    bidding_start=item.get("bidding_start"),
                    bidding_end=item.get("bidding_end"),
                    is_henan=item.get("is_henan", False),
                    henan_city=item.get("henan_city"),
                    henan_tag=item.get("henan_tag")
                )
                db.add(notice)
                new_records.append(notice)
            else:
                existing.module_type = mod_type
                if not existing.publish_time:
                    existing.publish_time = item.get("publish_time") or existing.created_at or datetime.now()
                if item.get("bidding_start") and not existing.bidding_start:
                    existing.bidding_start = item["bidding_start"]
                if item.get("bidding_end") and not existing.bidding_end:
                    existing.bidding_end = item["bidding_end"]
                # 同步更新涉豫标记
                if not existing.is_henan and item.get("is_henan"):
                    existing.is_henan = item["is_henan"]
                    existing.henan_city = item["henan_city"]
                    existing.henan_tag = item["henan_tag"]

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[ali_crawler] Commit error: {e}")
        return [], len(items), str(e)
    finally:
        if close_when_done:
            db.close()

    print(f"[ali_crawler] Live scraped {len(items)} items, new ingested: {len(new_records)}")
    return new_records, len(items), warning_msg

async def run_ali_manual_verification(timeout_sec: int = 120):
    """
    唤起有头可视化浏览器窗口（headless=False），使用持久化 ali_profile 目录，
    打开阿里拍卖页面供用户手动拖动滑块验证码或登录淘宝，完成后持久化本地 Cookie。
    """
    print(f"[ali_crawler] Launching visible browser for manual slider verification (timeout={timeout_sec}s)...")
    async with async_playwright() as p:
        user_data_dir = os.path.join(DATA_DIR, "ali_profile")
        os.makedirs(user_data_dir, exist_ok=True)
        try:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-infobars',
                    '--start-maximized',
                    '--lang=zh-CN'
                ],
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                locale="zh-CN",
                viewport=None
            )
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            page = await context.new_page()
            await page.goto("https://sf.taobao.com/item_list.htm?province=%BA%D3%C4%CF&order=createTime_desc", timeout=30000)
            
            start_t = datetime.now()
            while (datetime.now() - start_t).total_seconds() < timeout_sec:
                try:
                    if len(context.pages) == 0:
                        break
                    await asyncio.sleep(2)
                except Exception:
                    break
            try:
                await context.close()
            except Exception:
                pass
            print("[ali_crawler] Manual verification session closed and cookies persisted.")
        except Exception as e:
            print(f"[ali_crawler] Manual verification context note: {e}")

