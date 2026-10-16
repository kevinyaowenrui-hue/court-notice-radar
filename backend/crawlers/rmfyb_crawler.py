# -*- coding: utf-8 -*-
"""
《人民法院报》及人民法院公告网真实采集器
来源: https://rmfygg.court.gov.cn/web/rmfyportal/noticeinfo 及 https://www.rmfyb.com/
采用 Playwright 实时渲染与结构化抽取真实全国法院开庭传票、送达裁判文书、执行公告与重整
"""
import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from playwright.async_api import async_playwright
from sqlalchemy.orm import Session
from backend.models import CourtNotice
from backend.utils import (
    launch_smart_browser, extract_judicial_case_number, stable_hash,
    run_async, detect_henan_info, is_promotional_content, categorize_notice_module,
    find_existing_notice
)
import urllib.request
import urllib.parse
import json

def fetch_rmfygg_detail(uuid: str) -> dict:
    """通过官方接口获取人民法院公告网公告正文、案号及刊登日期"""
    url = "https://rmfygg.court.gov.cn/web/rmfyportal/noticedetail?p_p_id=noticedetail_WAR_rmfynoticeDetailportlet&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_resource_id=noticeDetail&p_p_cacheability=cacheLevelPage&p_p_col_id=column-1&p_p_col_count=1"
    data = urllib.parse.urlencode({"_noticedetail_WAR_rmfynoticeDetailportlet_uuid": uuid}).encode('utf-8')
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': f'https://rmfygg.court.gov.cn/web/rmfyportal/noticedetail?paramStr={uuid}'
    }
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            content = (res.get("noticeContent") or "").strip()
            case_no = extract_judicial_case_number(content)
            return {
                "content": content,
                "case_number": case_no,
                "publish_date": res.get("publishDate")
            }
    except Exception:
        return {}

def fetch_rmfyb_static_epaper(target_date: Optional[datetime] = None) -> List[dict]:
    """
    备用通道：抓取《人民法院报》静态数字报（http://rmfyb.chinacourt.org/paper/html/YYYY-MM/DD/node_2.htm 至 node_12.htm）
    当 rmfygg.court.gov.cn 主通道返回 0 条或请求异常时自动触发兜底
    """
    if target_date is None:
        target_date = datetime.now()

    results = []
    seen_urls = set()
    dates_to_try = [target_date - timedelta(days=d) for d in range(5)]

    for dt in dates_to_try:
        found_date_articles = []
        for node_idx in range(2, 13):  # node_2.htm 至 node_12.htm (覆盖《人民法院报》全部公告版面)
            node_url = dt.strftime(f"http://rmfyb.chinacourt.org/paper/html/%Y-%m/%d/node_{node_idx}.htm")
            try:
                req = urllib.request.Request(node_url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
                })
                with urllib.request.urlopen(req, timeout=6) as resp:
                    page_html = resp.read().decode('utf-8', errors='ignore')
                    art_matches = re.findall(r'<a[^>]+href=[\'"]([^\'"]*content_\d+\.htm)[\'"][^>]*>(.*?)</a>', page_html, re.I | re.S)
                    for rel_href, link_text in art_matches:
                        clean_title = re.sub(r'<[^>]+>', '', link_text).strip()
                        if len(clean_title) < 2:
                            continue

                        art_url = urllib.parse.urljoin(node_url, rel_href)
                        if art_url in seen_urls:
                            continue
                        seen_urls.add(art_url)

                        body_text = clean_title
                        try:
                            art_req = urllib.request.Request(art_url, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(art_req, timeout=5) as art_resp:
                                art_html = art_resp.read().decode('utf-8', errors='ignore')
                                b_text = re.sub(r'<script[^>]*>.*?</script>', ' ', art_html, flags=re.S|re.I)
                                b_text = re.sub(r'<style[^>]*>.*?</style>', ' ', b_text, flags=re.S|re.I)
                                b_text = re.sub(r'<[^>]+>', ' ', b_text)
                                body_text = re.sub(r'\s+', ' ', b_text).strip()
                        except Exception:
                            pass

                        case_no = extract_judicial_case_number(f"{clean_title} {body_text}") or ""
                        court_match = re.search(r'([\u4e00-\u9fa5]{2,15}(?:高级人民法院|中级人民法院|基层人民法院|人民法院|法庭))', f"{clean_title} {body_text}")
                        court_name = court_match.group(1) if court_match else "人民法院"

                        is_h, h_c, h_t = detect_henan_info(
                            title=clean_title,
                            content=body_text,
                            court_name=court_name,
                            case_number=case_no
                        )

                        raw_id = f"rmfyb_paper_{stable_hash(art_url)}"
                        found_date_articles.append({
                            "platform": "rmfyb",
                            "raw_id": raw_id,
                            "court_name": court_name,
                            "case_number": case_no,
                            "parties": "",
                            "notice_type": "法院公告",
                            "title": clean_title,
                            "content_text": body_text[:2000],
                            "publish_time": dt,
                            "source_url": art_url,
                            "is_henan": is_h,
                            "henan_city": h_c,
                            "henan_tag": h_t
                        })
            except Exception:
                continue

        if found_date_articles:
            results.extend(found_date_articles)
            break

    return results

async def fetch_rmfyb_real_notices() -> List[dict]:
    results = []
    warning_reasons = []

    async with async_playwright() as p:
        browser = await launch_smart_browser(p, headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="zh-CN"
        )
        page = await context.new_page()

        # 1. 抓取人民法院公告网真实最新公示 (优先按“河南”及重点地市法院定向检索 + 嗅探全国大盘跨域涉豫)
        try:
            await page.goto("https://rmfygg.court.gov.cn/web/rmfyportal/noticeinfo", timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            # 拦截检测
            page_title = await page.title()
            if any(k in page_title for k in ['访问受限', '安全检查', '系统维护', '403', '404', '502', '503']):
                warning_reasons.append(f"人民法院公告网异常拦截: {page_title}")

            henan_cities = [
                "河南", "郑州", "洛阳", "南阳", "商丘", "新乡", "周口", "驻马店",
                "信阳", "平顶山", "安阳", "开封", "焦作", "许昌", "濮阳", "漯河",
                "三门峡", "鹤壁", "济源"
            ]
            search_modes = [{"name": f"{c}法院定向" if c != "河南" else "河南省各级法院专场", "court_query": c} for c in henan_cities]
            search_modes.append({"name": "全国大盘实时公示", "court_query": ""})

            seen_raw_ids = set()

            today_str = datetime.now().strftime("%Y-%m-%d")
            for sm in search_modes:
                try:
                    court_q = sm["court_query"]
                    print(f"[rmfyb_crawler] Executing mode: {sm['name']}")
                    if court_q:
                        await page.fill("#courtVal", court_q)
                    else:
                        await page.fill("#courtVal", "")

                    # 检索近10天至今日最新发布内容，确保全量捕获法院发布的各类开庭、送达与执行公告
                    start_date_str = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
                    try:
                        start_input = await page.query_selector("#startVal, input[name='startDate']")
                        if start_input:
                            await start_input.fill(start_date_str)
                        end_input = await page.query_selector("#endVal, input[name='endDate']")
                        if end_input:
                            await end_input.fill(today_str)
                    except Exception:
                        pass

                    btn = await page.query_selector("button:has-text('查询'), .btn:has-text('查询'), a:has-text('查询')")
                    if btn:
                        await btn.click()
                        await page.wait_for_timeout(3000)

                    rows = await page.query_selector_all("table tbody tr, table tr")
                    print(f"[rmfyb_crawler] [{sm['name']}] Found {len(rows)} table rows")

                    for row in rows:
                        cols = await row.query_selector_all("td")
                        if len(cols) >= 4:
                            court_name = (await cols[0].inner_text()).strip()
                            parties = (await cols[1].inner_text()).strip()
                            notice_type = (await cols[2].inner_text()).strip()
                            pub_time_str = (await cols[3].inner_text()).strip()

                            # 排除表头
                            if "公告人" in court_name or "法院" not in court_name:
                                continue

                            # 提取详情链接
                            link_el = await cols[0].query_selector("a") or await cols[1].query_selector("a") or await cols[2].query_selector("a")
                            href = await link_el.get_attribute("href") if link_el else ""
                            if href.startswith('/'):
                                source_url = f"https://rmfygg.court.gov.cn{href}"
                            else:
                                source_url = href or "https://rmfygg.court.gov.cn/web/rmfyportal/noticeinfo"

                            param_m = re.search(r'paramStr=(\d+)', source_url)
                            uuid = param_m.group(1) if param_m else None
                            raw_id = f"rmfyb_{uuid}" if uuid else f"rmfyb_{stable_hash(court_name + parties + pub_time_str)}"

                            if raw_id in seen_raw_ids:
                                continue
                            seen_raw_ids.add(raw_id)

                            # 尝试跟进详情接口获取真实公告正文与案号
                            detail = fetch_rmfygg_detail(uuid) if uuid else {}
                            case_number = detail.get("case_number", "")
                            content_body = detail.get("content") or ""

                            try:
                                if detail.get("publish_date"):
                                    pub_time = datetime.strptime(detail["publish_date"], "%Y-%m-%d")
                                else:
                                    pub_time = datetime.strptime(pub_time_str, "%Y-%m-%d")
                            except Exception:
                                pub_time = None

                            # 时效门禁校验：放宽至 15 天内最新公告，避免刚刊登几天的有效公告被过滤
                            if pub_time is not None:
                                days_diff = (datetime.now() - pub_time).total_seconds() / 86400.0
                                if days_diff > 15.0:
                                    continue

                            # 标题与内容结构化规范化：包含案号以明确区分同一法院/当事人的不同案件
                            if case_number:
                                title = f"{court_name}关于{parties}的{notice_type}公告 [{case_number}]"
                            else:
                                title = f"{court_name}关于{parties}的{notice_type}公告"

                            content_lines = [
                                f"发布法院：{court_name}",
                                f"涉案当事人/受送达人：{parties}",
                                f"公告类型：{notice_type}",
                                f"刊登发布日期：{pub_time_str or '详见原站'}",
                            ]
                            if case_number:
                                content_lines.insert(1, f"案号：{case_number}")
                            if content_body:
                                content_lines.append(f"\n公告完整正文：\n{content_body}")
                            content_lines.append(f"\n官方详情链接：{source_url}")
                            content_text = "\n".join(content_lines)

                            # 河南智能识别 (河南属地法院 或 全国跨省涉豫当事人/资产)
                            is_henan, henan_city, henan_tag = detect_henan_info(
                                title=title,
                                content=content_text,
                                court_name=court_name,
                                case_number=case_number,
                                parties=parties
                            )

                            results.append({
                                "platform": "rmfyb",
                                "raw_id": raw_id,
                                "court_name": court_name,
                                "case_number": case_number,
                                "parties": parties,
                                "notice_type": notice_type,
                                "title": title,
                                "content_text": content_text,
                                "publish_time": pub_time,
                                "source_url": source_url,
                                "is_henan": is_henan,
                                "henan_city": henan_city,
                                "henan_tag": henan_tag
                            })
                except Exception as e_sm:
                    print(f"[rmfyb_crawler] Error in search mode {sm['name']}: {e_sm}")
        except Exception as e:
            print(f"[rmfyb_crawler] Error scraping noticeinfo: {e}")

        # 注：彻底剔除 rmfyb.com 离退休活动等政务新闻抓取，系统严格聚焦法院真实司法公告

        await browser.close()

    # 当主通道返回 0 条或请求异常时，自动触发备用通道抓取《人民法院报》静态数字报
    if len(results) == 0:
        print("[rmfyb_crawler] 主通道返回 0 条，触发备用通道抓取《人民法院报》静态数字报...")
        backup_items = fetch_rmfyb_static_epaper()
        print(f"[rmfyb_crawler] 备用通道静态数字报抓取到 {len(backup_items)} 条公告")
        results.extend(backup_items)

    warning_msg = " ; ".join(warning_reasons) if warning_reasons else None
    return results, warning_msg

from backend.utils import run_async, detect_henan_info, is_promotional_content, categorize_notice_module

from backend.database import SessionLocal

def crawl_rmfyb_notices(db: Optional[Session] = None, max_pages: int = 2):
    """主入口：执行抓取并存入数据库，返回(新记录, 发现总数, 警告信息)"""
    items, warning_msg = run_async(fetch_rmfyb_real_notices())
    new_records = []
    seen_db_ids = set()

    VALID_COURT_NOTICE_KEYWORDS = ["公告", "传票", "送达", "裁判文书", "判决", "裁定", "起诉状", "执行", "破产", "清算", "答辩状"]

    close_when_done = False
    if db is None:
        db = SessionLocal()
        close_when_done = True

    try:
        for item in items:
            # P0 要求：严格过滤掉非法院公告的新闻资讯（如标题不含公告、传票、送达、裁判文书等一律剔除）
            if not any(k in item["title"] for k in VALID_COURT_NOTICE_KEYWORDS):
                continue

            if is_promotional_content(item["title"], item["content_text"]):
                continue

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
                    parties=item["parties"],
                    notice_type=item["notice_type"],
                    module_type=mod_type,
                    title=item["title"],
                    content_text=item["content_text"],
                    publish_time=item["publish_time"],
                    source_url=item["source_url"],
                    is_henan=item.get("is_henan", False),
                    henan_city=item.get("henan_city"),
                    henan_tag=item.get("henan_tag")
                )
                db.add(notice)
                new_records.append(notice)
            else:
                existing.module_type = mod_type
                if not existing.is_henan and item.get("is_henan"):
                    existing.is_henan = item["is_henan"]
                    existing.henan_city = item["henan_city"]
                    existing.henan_tag = item["henan_tag"]

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[rmfyb_crawler] Commit error: {e}")
        return [], len(items), str(e)
    finally:
        if close_when_done:
            db.close()

    print(f"[rmfyb_crawler] Live scraped {len(items)} items, new ingested: {len(new_records)}")
    return new_records, len(items), warning_msg
