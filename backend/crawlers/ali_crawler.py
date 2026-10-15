# -*- coding: utf-8 -*-
"""
阿里司法拍卖真实采集器 (Alibaba Judicial Auction Live Crawler)
来源: https://sf.taobao.com / https://sf-item.taobao.com
采用 Playwright 实时抓取阿里司法拍卖全国法院上架的真实法拍房、车辆、股权、机械等资产
"""
import asyncio
import re
from datetime import datetime
from typing import List, Tuple, Optional
from playwright.async_api import async_playwright
from sqlalchemy.orm import Session
from backend.models import CourtNotice

import os
from backend.utils import (
    run_async, detect_henan_info, stable_hash, categorize_notice_module,
    is_vehicle_or_equipment_item, parse_price_amount, launch_smart_browser,
    extract_bidding_times, extract_judicial_case_number
)

async def fetch_ali_real_auctions() -> List[dict]:
    results = []
    async with async_playwright() as p:
        user_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ali_profile")
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
            ("https://sf.taobao.com/?order=createTime_desc", "阿里法拍·全国大盘最新")
        ]

        seen_urls = set()
        seen_raw_ids = set()

        warning_reasons = []

        try:
            for target_url, url_type in target_urls:
                try:
                    print(f"[ali_crawler] Accessing {url_type}: {target_url}")
                    await page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(3000)

                    # 风控与验证码拦截特征检测
                    current_url = page.url
                    page_title = await page.title()
                    if any(k in current_url for k in ['punish', 'sec.taobao.com', 'login.taobao.com', 'rgv587']):
                        warning_reasons.append(f"[{url_type}] 触发淘宝风控安全验证重定向: {current_url}")
                        print(f"[ali_crawler] Anti-scraping triggered on {url_type}, aborting remaining pages.")
                        break
                    elif any(k in page_title for k in ['验证码', '安全验证', '登录']):
                        warning_reasons.append(f"[{url_type}] 页面提示安全验证: {page_title}")
                        break

                    # 查询页面上的法拍卡片链接
                    cards = await page.query_selector_all("a[href*='sf_item'], a[href*='sf-item.taobao.com/sf_item']")
                    print(f"[ali_crawler] [{url_type}] Found {len(cards)} sf_item links")
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

                        # 提取卡片文本
                        raw_text = (await card.inner_text()).strip()
                        if not raw_text or len(raw_text) < 6:
                            continue

                        # 提取标的物 ID
                        id_m = re.search(r'sf_item/(\d+)\.htm', clean_url)
                        raw_id = f"ali_{id_m.group(1)}" if id_m else f"ali_{stable_hash(clean_url)}"
                        if raw_id in seen_raw_ids:
                            continue
                        seen_raw_ids.add(raw_id)

                        # 解析标题与价格
                        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
                        title = lines[0] if lines else "阿里司法拍卖标的"

                        starting_price = None
                        eval_price = None
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
                            if "二拍" in line:
                                auction_stage = "二拍"
                            elif "变卖" in line:
                                auction_stage = "变卖"

                        # 彻底过滤排除机动车辆、重型和大型机械设备
                        if is_vehicle_or_equipment_item(title, raw_text):
                            continue

                        # 识别标的物类型（聚焦不动产与债权股权，未能识别的严禁默认归为住宅房产，归为“其他资产”）
                        category = "其他资产"
                        t_clean = re.sub(r'[\u4e00-\u9fa5]{2,30}(?:公司|分公司|支行|行)(?:名下|持有)?', '', title)
                        if any(k in title for k in ["股", "证券", "债券", "债权", "资产包"]):
                            category = "金融债权与股权"
                        elif any(k in title for k in ["地块", "土地", "厂房", "仓库", "工业园"]):
                            category = "工业厂房与土地"
                        elif any(k in t_clean for k in ["房产", "住宅", "商品房", "公寓", "排屋", "大厦", "门面", "商铺", "车位", "车库", "人防车位", "室", "号楼", "单元", "楼房"]):
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

from backend.database import SessionLocal

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

            existing = db.query(CourtNotice).filter(
                CourtNotice.platform == item["platform"],
                CourtNotice.raw_id == item["raw_id"]
            ).first()
            if not existing:
                notice = CourtNotice(
                    platform=item["platform"],
                    raw_id=item["raw_id"],
                    court_name=item["court_name"],
                    case_number=item["case_number"],
                    parties=item["parties"],
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
