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
from datetime import datetime
from typing import List, Tuple, Optional
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

        # 重点覆盖：
        # 1. 阿里司法拍卖河南全省精准检索 (province=%BA%D3%C4%CF 为原生省份参数)
        # 2. 郑州定向检索 (q=%D6%A3%D6%DD 为 GBK 编码“郑州”)
        # 3. 洛阳定向检索 (q=%C2%E5%D1%F4 为 GBK 编码“洛阳”)
        # 4. 阿里司法拍卖全国大盘首页 (最新发布优先)
        target_urls = [
            ("https://sf.taobao.com/item_list.htm?province=%BA%D3%C4%CF&order=createTime_desc", "阿里法拍·河南最新"),
            ("https://sf.taobao.com/item_list.htm?q=%D6%A3%D6%DD&order=createTime_desc", "阿里法拍·郑州重点"),
            ("https://sf.taobao.com/item_list.htm?q=%C2%E5%D1%F4&order=createTime_desc", "阿里法拍·洛阳重点"),
            ("https://sf.taobao.com/item_list.htm?q=%D0%C2%CF%E7&order=createTime_desc", "阿里法拍·新乡重点"),
            ("https://sf.taobao.com/item_list.htm?q=%C4%CF%D1%F4&order=createTime_desc", "阿里法拍·南阳重点"),
            ("https://sf.taobao.com/?order=createTime_desc", "阿里法拍·全国大盘最新")
        ]

        seen_urls = set()
        seen_raw_ids = set()

        warning_reasons = []

        try:
            for target_url, url_type in target_urls:
                try:
                    # 防风控随机平滑等待 3.5 ~ 6 秒
                    await page.wait_for_timeout(random.randint(3500, 6000))
                    print(f"[ali_crawler] Accessing {url_type}: {target_url}")
                    await page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(2500)

                    # 风控与验证码拦截特征检测
                    current_url = page.url
                    page_title = await page.title()
                    if any(k in current_url for k in ['punish', 'sec.taobao.com', 'login.taobao.com', 'rgv587']):
                        warning_reasons.append(f"[{url_type}] 触发淘宝风控安全验证重定向: {current_url}")
                        print(f"[ali_crawler] Anti-scraping triggered on {url_type}, resetting session and continuing next.")
                        try:
                            await context.clear_cookies()
                        except Exception:
                            pass
                        continue
                    elif any(k in page_title for k in ['验证码', '安全验证', '登录']):
                        warning_reasons.append(f"[{url_type}] 页面提示安全验证: {page_title}")
                        continue

                    # 1. 优先定位 <script id="sf-item-list-data" type="text/json"> 节点提取结构化完整数据
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

                                        # 起拍价与评估价（若评估价等于起拍价则置 None）
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
                                        if sp is not None and ep is not None and sp == ep:
                                            ep = None

                                        # 毫秒时间戳转换开拍与结束时间
                                        b_start = None
                                        b_end = None
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

                                        court_name = (d.get("court") or d.get("courtName") or "").strip()
                                        if not court_name:
                                            c_m = re.search(r'([^\s，。、（]{2,15}(?:人民法院|中级法院|基层法院|法庭))', title)
                                            court_name = c_m.group(1) if c_m else "阿里司法拍卖"

                                        case_number = extract_judicial_case_number(title) or ""

                                        stage = "一拍"
                                        st_desc = d.get("statusTitle") or ""
                                        if "二拍" in title or "第二次" in title or "二拍" in st_desc:
                                            stage = "二拍"
                                        elif "变卖" in title or "变卖" in st_desc:
                                            stage = "变卖"
                                        elif "破产" in title:
                                            stage = "破产资产处置"

                                        category = "住宅/商业房产"
                                        if any(k in title for k in ['地块', '土地', '厂房', '仓库', '工业园']):
                                            category = "工业厂房与土地"
                                        elif any(k in title for k in ['股权', '股份', '股票', '债权']):
                                            category = "金融债权与股权"

                                        content_text = (
                                            f"标的物名称：{title}\n"
                                            f"执行/处置法院：{court_name}\n"
                                            f"起拍价：{sp}元\n评估价：{ep}元\n"
                                            f"拍卖阶段：{stage}\n"
                                            f"竞价开始时间：{b_start}\n竞价结束时间：{b_end}\n"
                                            f"详情链接：{clean_url}"
                                        )

                                        is_henan, henan_city, henan_tag = detect_henan_info(title, court_name, content_text)

                                        results.append({
                                            "platform": "ali",
                                            "raw_id": raw_id,
                                            "court_name": court_name,
                                            "case_number": case_number,
                                            "parties": "",
                                            "notice_type": "司法拍卖",
                                            "module_type": "拍卖公告",
                                            "title": title,
                                            "content_text": content_text,
                                            "publish_time": datetime.now(),
                                            "source_url": clean_url,
                                            "starting_price": sp,
                                            "eval_price": ep,
                                            "auction_stage": stage,
                                            "asset_category": category,
                                            "bidding_start": b_start,
                                            "bidding_end": b_end,
                                            "is_henan": is_henan,
                                            "henan_city": henan_city,
                                            "henan_tag": henan_tag
                                        })
                                    json_parsed_success = True
                    except Exception as je:
                        print(f"[ali_crawler] JSON extraction error: {je}")

                    # 2. 若内嵌 JSON 未获取成功，平滑回退至 DOM 节点选择器解析
                    if json_parsed_success:
                        continue

                    # 查询页面上的法拍卡片链接
                    cards = await page.query_selector_all("a[href*='sf_item'], a[href*='sf-item.taobao.com/sf_item']")
                    print(f"[ali_crawler] [{url_type}] DOM fallback: Found {len(cards)} sf_item links")
                    if len(cards) == 0 and not warning_reasons:
                        warning_reasons.append(f"[{url_type}] 页面未发现法拍卡片元素，可能页面结构变更或遭遇防爬限制")

                    for card in cards:
                        href = await card.get_attribute("href")
                        if not href:
                            continue
                        if href.startswith('//'):
                            full_url = f"https:{href}"
                        elif href.startswith('/'):
                            full_url = f"https://sf.taobao.com{href}"
                        else:
                            full_url = href

                        clean_url = full_url.split('?')[0]
                        if clean_url in seen_urls:
                            continue
                        seen_urls.add(clean_url)

                        # 提取卡片文本（优先通过最近的父容器提取，确保包含卡片外部/兄弟节点的起拍价与评估价）
                        raw_text = (await card.inner_text()).strip()
                        container_text = ""
                        try:
                            parent_handle = await card.evaluate_handle(
                                "el => el.closest('li') || el.closest('.sf-item') || el.closest('.item') || el.closest('.item-info') || el.parentElement"
                            )
                            if parent_handle:
                                c_txt = await parent_handle.inner_text()
                                if c_txt:
                                    container_text = c_txt.strip()
                        except Exception:
                            container_text = ""

                        combined_text = container_text if len(container_text) > len(raw_text) else raw_text
                        if not combined_text or len(combined_text) < 6:
                            continue

                        # 提取标的物 ID
                        id_m = re.search(r'sf_item/(\d+)\.htm', clean_url)
                        raw_id = f"ali_{id_m.group(1)}" if id_m else f"ali_{stable_hash(clean_url)}"
                        if raw_id in seen_raw_ids:
                            continue
                        seen_raw_ids.add(raw_id)

                        # 解析标题与价格
                        lines = [l.strip() for l in combined_text.splitlines() if l.strip()]
                        title = lines[0] if lines else "阿里司法拍卖标的"

                        starting_price = None
                        eval_price = None
                        auction_stage = "一拍"
                        if "变卖" in title or "变卖" in combined_text:
                            auction_stage = "变卖"
                        elif any(k in title or k in combined_text for k in ["二拍", "第二次拍卖", "第二次"]):
                            auction_stage = "二拍"
                        elif any(k in title or k in combined_text for k in ["一拍", "第一次拍卖", "第一次"]):
                            auction_stage = "一拍"

                        for line in lines:
                            if "起拍" in line:
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

                        # 彻底过滤排除机动车辆、重型和大型机械设备
                        if is_vehicle_or_equipment_item(title, combined_text):
                            continue

                        # 识别标的物类型：严格映射为前端支持的 4 类枚举（"住宅/商业房产"、"工业厂房与土地"、"金融债权与股权"、"其他资产"）
                        category = "其他资产"
                        t_clean = re.sub(r'[\u4e00-\u9fa5]{2,30}(?:公司|分公司|支行|行)(?:名下|持有)?', '', title)
                        if any(k in title for k in ["股", "证券", "债券", "债权", "资产包", "保单", "份额"]):
                            category = "金融债权与股权"
                        elif any(k in title for k in ["地块", "土地", "厂房", "仓库", "工业园", "工业用地", "林权", "矿权", "构筑物"]):
                            category = "工业厂房与土地"
                        elif any(k in t_clean for k in ["房产", "住宅", "商品房", "公寓", "排屋", "大厦", "门面", "商铺", "车位", "车库", "人防车位", "室", "号楼", "单元", "楼房", "写字楼", "别墅"]):
                            category = "住宅/商业房产"

                        # 尝试从标题中提取涉案城市或法院
                        city_m = re.search(r'^(?:位于)?([\u4e00-\u9fa5]{2,6}(?:省|市|区|县))', title)
                        court_name = f"{city_m.group(1)}人民法院" if city_m else "人民法院司法拍卖"

                        content_text = f"【阿里司法拍卖真实标的】\n标的物：{title}\n当前起拍价：¥{starting_price:,.2f} 元\n拍卖阶段：{auction_stage}\n处置法院：{court_name}\n详情链接：{clean_url}\n{raw_text[:200]}" if starting_price else f"{title}\n原站直达：{clean_url}\n{raw_text[:200]}"

                        # 提取真实发布时间与竞价时间（优先文本中的发布/上架时间；若无显式发布文本，以实时最新上架发现时间为准）
                        b_start, b_end = extract_bidding_times(raw_text)
                        publish_time = None
                        m_pub = re.search(r'(?:发布时间|上架时间|刊登时间|公告时间)[：:\s]*(\d{4}[年\-/]\d{1,2}[月\-/]\d{1,2}日?(?:\s*\d{1,2}:\d{2}(?::\d{2})?)?)', raw_text)
                        if m_pub:
                            try:
                                clean_dt = m_pub.group(1).replace('年', '-').replace('月', '-').replace('日', '')
                                fmt = "%Y-%m-%d %H:%M:%S" if len(clean_dt.strip()) > 16 else ("%Y-%m-%d %H:%M" if len(clean_dt.strip()) > 10 else "%Y-%m-%d")
                                publish_time = datetime.strptime(clean_dt.strip(), fmt)
                            except Exception:
                                pass
                        if not publish_time:
                            publish_time = datetime.now()

                        # 河南智能识别 (属地法院 / 跨域涉豫资产)
                        is_henan, henan_city, henan_tag = detect_henan_info(
                            title=title,
                            content=content_text,
                            court_name=court_name
                        )

                        # 案号提取与价格标准化校验
                        case_no = extract_judicial_case_number(f"{title} {raw_text}")
                        sp_clean = round(float(starting_price), 2) if starting_price is not None else None
                        ep_clean = round(float(eval_price), 2) if eval_price is not None else None
                        if sp_clean is not None and ep_clean is not None and sp_clean == ep_clean:
                            ep_clean = None

                        results.append({
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
                except Exception as e:
                    print(f"[ali_crawler] Error on {url_type}: {e}")
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

