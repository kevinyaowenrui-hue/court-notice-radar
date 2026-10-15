# -*- coding: utf-8 -*-
"""
中拍平台 (CAA - 中国拍卖行业协会) 信息公示采集器
官方数据源: https://paimai.caa123.org.cn/pages/publicity/list.html
API 接口: https://paimai.caa123.org.cn/paimai-search/publicity/list
实时采集国家级网络拍卖平台最新公布的拍卖成交公示、司法与涉案财物处置结果公告
"""
import urllib.request
import json
import re
from datetime import datetime
from typing import List, Tuple, Optional
from urllib.parse import quote
from sqlalchemy.orm import Session
from backend.models import CourtNotice
from backend.utils import (
    detect_henan_info, is_promotional_content, categorize_notice_module,
    is_vehicle_or_equipment_item, extract_starting_and_eval_price,
    extract_bidding_times
)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://paimai.caa123.org.cn/pages/publicity/list.html'
}

def parse_caa_datetime(dt_str: str) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        clean = dt_str.replace('年', '-').replace('月', '-').replace('日', '').strip()
        fmt = "%Y-%m-%d %H:%M:%S" if len(clean) > 16 else "%Y-%m-%d %H:%M"
        return datetime.strptime(clean, fmt)
    except Exception:
        return None

def fetch_caa_detail(pid: int) -> dict:
    """获取中拍平台标的详情（含起拍价、成交价/当前价、详细竞价起止时间、标的物全称及正文）"""
    url = f"https://paimai.caa123.org.cn/paimai-search/publicity/detail?publicityId={pid}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('data') or {}
    except Exception:
        return {}

def fetch_caa_items(count: int = 30, filter_content: str = "") -> List[dict]:
    """请求中拍平台信息公示接口，优先抓取在拍公示(publishStatus=2)与预告/最新公示"""
    results = []
    kw = quote(filter_content) if filter_content else ""
    urls = []
    if filter_content:
        urls.append(f"https://paimai.caa123.org.cn/paimai-search/publicity/list?start=0&count={count}&filterContent={kw}&publishStatus=2")
        urls.append(f"https://paimai.caa123.org.cn/paimai-search/publicity/list?start=0&count={count}&filterContent={kw}")
    else:
        urls.append(f"https://paimai.caa123.org.cn/paimai-search/publicity/list?start=0&count={count}&publishStatus=2")
        urls.append(f"https://paimai.caa123.org.cn/paimai-search/publicity/list?start=0&count={count}")

    seen_pids = set()
    for url in urls:
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                items = data.get('data', {}).get('items', [])
                for it in items:
                    try:
                        pid = it.get('id')
                        if not pid or pid in seen_pids:
                            continue
                        seen_pids.add(pid)
                        title = (it.get('title') or '').strip()
                        if not title or is_vehicle_or_equipment_item(title):
                            continue
                        company = (it.get('companyName') or '').strip()
                        pub_time_str = it.get('publishTime', '')
                        status_code = it.get('publishStatus')
                        status_str = "公示中" if status_code == 2 else ("公示结束" if status_code == 4 else "已发布")

                        # 解析时间，严禁回退伪造 datetime.now()
                        try:
                            pub_time = datetime.strptime(pub_time_str, "%Y-%m-%d %H:%M:%S")
                        except Exception:
                            pub_time = None

                        # 状态与时效门禁：
                        # 若处于公示中(status_code == 2)，属于当前有效活跃标的，坚决保留；
                        # 其他已结束的公示保留近 15 天内的数据
                        if status_code != 2 and pub_time is not None:
                            days_diff = (datetime.now() - pub_time).total_seconds() / 86400.0
                            if days_diff > 15.0:
                                continue

                        detail_url = f"https://paimai.caa123.org.cn/pages/publicity/item.html?publicityList=true&id={pid}"

                        # 提取法院或处置主体
                        court_m = re.search(r'([^\s，。、（]+(?:人民法院|中院|公安局|分局|海关|税务局|财政局|管委会))', title)
                        court_name = court_m.group(1) if court_m else (company or "中拍平台网络科技")

                        # 获取详情以丰富价格、起止时间与资产分类
                        detail = fetch_caa_detail(pid)
                        starting_price = None
                        eval_price = None
                        bidding_start = None
                        bidding_end = None
                        lot_name = ""

                        lots = detail.get('publicityLotDTOS') or []
                        if lots:
                            first_lot = lots[0]
                            lot_name = (first_lot.get('name') or '').strip()
                            if lot_name and is_vehicle_or_equipment_item(lot_name):
                                continue
                            sp_val = first_lot.get('startPrice')
                            ep_val = first_lot.get('evalPrice') or first_lot.get('assessPrice')
                            if sp_val is not None:
                                try:
                                    starting_price = round(float(sp_val), 2)
                                except Exception:
                                    pass
                            if ep_val is not None:
                                try:
                                    eval_price = round(float(ep_val), 2)
                                except Exception:
                                    pass
                            if starting_price is not None and eval_price is not None and starting_price == eval_price:
                                eval_price = None

                        # 解析起止竞价时间
                        bidding_start = parse_caa_datetime(detail.get('startTime') or '')
                        bidding_end = parse_caa_datetime(detail.get('endTime') or '')
                        if not bidding_end and lots:
                            bidding_end = parse_caa_datetime(lots[0].get('endTime') or '')

                        # 若接口没有起拍价或竞价时间，尝试从正文或标题提取
                        notice_content = detail.get('noticeContent') or ''
                        if not starting_price or not bidding_start:
                            sp, ep = extract_starting_and_eval_price(title, notice_content)
                            if not starting_price:
                                starting_price = sp
                            if not eval_price:
                                eval_price = ep
                            if not bidding_start or not bidding_end:
                                bs, be = extract_bidding_times(notice_content)
                                if not bidding_start:
                                    bidding_start = bs
                                if not bidding_end:
                                    bidding_end = be

                        # 标的分类
                        combined_text = f"{title} {lot_name}"
                        category = "其他资产"
                        if any(k in combined_text for k in ["股", "证券", "债券", "债权", "资产包", "不良资产"]):
                            category = "金融债权与股权"
                        elif any(k in combined_text for k in ["地块", "土地", "厂房", "仓库", "工业园"]):
                            category = "工业厂房与土地"
                        elif any(k in combined_text for k in ["房", "室", "号楼", "公寓", "排屋", "大厦", "门面", "商铺", "车位", "车库", "人防车位", "住宅"]):
                            category = "住宅/商业房产"
                        elif any(k in combined_text for k in ["设备", "机械", "机床", "生产线", "工程机械", "变压器", "电缆"]):
                            category = "机械设备与物资"

                        content_text = (
                            f"【中拍平台·信息公示】\n"
                            f"公示标题：{title}\n"
                            f"发布主体：{company or court_name}\n"
                            f"公示状态：{status_str}\n"
                            f"公示时间：{pub_time_str}\n"
                        )
                        if starting_price:
                            content_text += f"起拍价格：¥{starting_price:,.2f} 元\n"
                        if eval_price:
                            content_text += f"评估/参考价：¥{eval_price:,.2f} 元\n"
                        if bidding_start:
                            content_text += f"竞价开始：{bidding_start.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        if bidding_end:
                            content_text += f"竞价截止：{bidding_end.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        content_text += (
                            f"平台来源：中拍平台（中国拍卖行业协会网络科技股份有限公司）\n"
                            f"查看原始公示：{detail_url}"
                        )

                        # 智能识别涉豫特征（河南属地机构 / 全国跨域处置河南资产）
                        is_henan, henan_city, henan_tag = detect_henan_info(
                            title=title,
                            content=content_text,
                            court_name=court_name,
                            parties=company
                        )
                        if is_henan and not henan_tag:
                            henan_tag = f"中拍平台涉豫信息公示 (涉及{henan_city})"

                        # 拍卖阶段提取 (从标题、正文及标的名称中深度提取)
                        auction_stage = "一拍"
                        stage_target = f"{title} {lot_name} {notice_content}"
                        if "二拍" in stage_target or "第二次" in stage_target:
                            auction_stage = "二拍"
                        elif "变卖" in stage_target:
                            auction_stage = "变卖"
                        elif "破产" in stage_target:
                            auction_stage = "破产资产处置"
                        elif "一拍" in stage_target or "第一次" in stage_target:
                            auction_stage = "一拍"

                        results.append({
                            "raw_id": f"caa_{pid}",
                            "court_name": court_name,
                            "case_number": "",
                            "parties": company,
                            "notice_type": "中拍平台信息公示",
                            "title": title,
                            "content_text": content_text,
                            "publish_time": pub_time,
                            "source_url": detail_url,
                            "starting_price": starting_price,
                            "eval_price": eval_price,
                            "auction_stage": auction_stage,
                            "bidding_start": bidding_start,
                            "bidding_end": bidding_end,
                            "asset_category": category,
                            "is_henan": is_henan,
                            "henan_city": henan_city,
                            "henan_tag": henan_tag
                        })
                    except Exception:
                        continue
        except Exception as e:
            print(f"[caa_crawler] Fetch error (kw='{filter_content}'): {e}")

    return results

def fetch_caa_lots(province_code: str = "410000", count: int = 40, filter_name: str = "") -> List[dict]:
    """
    抓取中拍平台正在进行/即将开拍的真实拍卖标的 (paimai-web/lots)
    province_code=410000 为河南省官方行政代码，直接获取河南属地核心法拍与资产标的
    """
    results = []
    kw = quote(filter_name) if filter_name else ""
    url = f"https://paimai.caa123.org.cn/paimai-web/lots?start=0&count={count}"
    if province_code:
        url += f"&provinceCode={province_code}"
    if kw:
        url += f"&name={kw}"

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Referer': 'https://paimai.caa123.org.cn/pages/lots/list.html'
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            items = data.get('items') or []
            for it in items:
                try:
                    lot_id = it.get('id')
                    if not lot_id:
                        continue
                    title = (it.get('name') or '').strip()
                    if not title or is_vehicle_or_equipment_item(title):
                        continue
                    company = (it.get('companyName') or '').strip()
                    meet_name = (it.get('auctionMeetName') or '').strip()
                    meet_id = it.get('meetId') or ''
                    
                    sp_val = it.get('startPrice')
                    starting_price = round(float(sp_val), 2) if sp_val is not None else None
                    ep_val = it.get('evalPrice') or it.get('assessPrice')
                    eval_price = round(float(ep_val), 2) if ep_val is not None else None
                    if starting_price is not None and eval_price is not None and starting_price == eval_price:
                        eval_price = None
                    
                    bidding_start = None
                    if it.get('startTime'):
                        try:
                            bidding_start = datetime.fromtimestamp(it['startTime'] / 1000)
                        except Exception:
                            pass
                    bidding_end = None
                    if it.get('endTime'):
                        try:
                            bidding_end = datetime.fromtimestamp(it['endTime'] / 1000)
                        except Exception:
                            pass
                    
                    # 发布时间优先开拍时间，若未来则为当前时间
                    pub_time = bidding_start if bidding_start and bidding_start <= datetime.now() else datetime.now()
                    detail_url = f"https://paimai.caa123.org.cn/pages/lots/profession.html?meetId={meet_id}&lotId={lot_id}"
                    
                    # 标的分类
                    combined = f"{title} {meet_name}"
                    category = "其他资产"
                    if any(k in combined for k in ["股", "证券", "债券", "债权", "资产包", "不良资产"]):
                        category = "金融债权与股权"
                    elif any(k in combined for k in ["地块", "土地", "厂房", "仓库", "工业园"]):
                        category = "工业厂房与土地"
                    elif any(k in combined for k in ["房", "室", "号楼", "公寓", "排屋", "大厦", "门面", "商铺", "车位", "车库", "住宅"]):
                        category = "住宅/商业房产"

                    content_text = (
                        f"【中拍平台·司法与网络拍卖标的】\n"
                        f"标的名称：{title}\n"
                        f"拍卖机构：{company or '中拍平台入围拍卖企业'}\n"
                        f"拍卖专场：{meet_name}\n"
                    )
                    if starting_price:
                        content_text += f"起拍价格：¥{starting_price:,.2f} 元\n"
                    if eval_price:
                        content_text += f"当前价/参考价：¥{eval_price:,.2f} 元\n"
                    if bidding_start:
                        content_text += f"竞价开始：{bidding_start.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    if bidding_end:
                        content_text += f"竞价截止：{bidding_end.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    content_text += (
                        f"平台来源：中拍平台（中国拍卖行业协会网络拍卖平台）\n"
                        f"查看原始标的：{detail_url}"
                    )

                    # 属地识别
                    is_henan = False
                    henan_city = None
                    henan_tag = None
                    if province_code == "410000" or "河南" in title or "河南" in company:
                        is_henan = True
                        h_is, h_c, h_t = detect_henan_info(title=title, content=content_text, court_name=company, parties=company)
                        henan_city = h_c or "省直/全省处置"
                        henan_tag = h_t or f"中拍平台涉豫标的 (涉及{henan_city})"

                    # 拍卖阶段提取 (从标题与专场名称中提取)
                    auction_stage = "一拍"
                    stage_target = f"{title} {meet_name}"
                    if "二拍" in stage_target or "第二次" in stage_target:
                        auction_stage = "二拍"
                    elif "变卖" in stage_target:
                        auction_stage = "变卖"
                    elif "破产" in stage_target:
                        auction_stage = "破产资产处置"
                    elif "一拍" in stage_target or "第一次" in stage_target:
                        auction_stage = "一拍"

                    results.append({
                        "raw_id": f"caa_lot_{lot_id}",
                        "court_name": company or "中拍平台",
                        "case_number": "",
                        "parties": company,
                        "notice_type": "中拍司法/涉案网络拍卖",
                        "title": title,
                        "content_text": content_text,
                        "publish_time": pub_time,
                        "source_url": detail_url,
                        "starting_price": starting_price,
                        "eval_price": eval_price,
                        "auction_stage": auction_stage,
                        "bidding_start": bidding_start,
                        "bidding_end": bidding_end,
                        "asset_category": category,
                        "is_henan": is_henan,
                        "henan_city": henan_city,
                        "henan_tag": henan_tag
                    })
                except Exception:
                    continue
    except Exception as e:
        print(f"[caa_crawler] Lots fetch error: {e}")

    return results

def fetch_caa_real_publicity() -> Tuple[List[dict], Optional[str]]:
    """纯网络抓取中拍平台数据，不持有数据库会话"""
    print("[caa_crawler] Starting CAA raw crawl...")
    all_items = []
    seen_ids = set()

    # 1. 优先抓取中拍平台河南官方专属实时在拍标的（provinceCode=410000）
    henan_lots = fetch_caa_lots(province_code="410000", count=50)
    for it in henan_lots:
        if it["raw_id"] not in seen_ids:
            seen_ids.add(it["raw_id"])
            all_items.append(it)

    # 2. 定向抓取包含“河南”关键词的全国重大处置资产
    nationwide_henan_lots = fetch_caa_lots(province_code="", count=30, filter_name="河南")
    for it in nationwide_henan_lots:
        if it["raw_id"] not in seen_ids:
            seen_ids.add(it["raw_id"])
            all_items.append(it)

    # 3. 轮询河南及重点地市 filterContent 抓取信息公示（补充成交结果与资产处置公告）
    filter_keywords = ["", "河南", "郑州", "洛阳", "南阳", "商丘", "开封", "新乡"]
    for kw in filter_keywords:
        publicity_items = fetch_caa_items(count=20, filter_content=kw)
        for it in publicity_items:
            if it["raw_id"] not in seen_ids:
                seen_ids.add(it["raw_id"])
                all_items.append(it)

    return all_items, None

from backend.database import SessionLocal

def crawl_caa_publicity(db: Optional[Session] = None, max_items: int = 50) -> Tuple[List[CourtNotice], int]:
    """执行中拍平台全量抓取：河南正在拍卖标的 + 全国跨域涉豫拍卖 + 历史成交结果公示"""
    all_items, _ = fetch_caa_real_publicity()

    new_records = []
    close_when_done = False
    if db is None:
        db = SessionLocal()
        close_when_done = True

    try:
        for it in all_items:
            # 严格过滤宣传类
            if is_promotional_content(it["title"], it["content_text"]):
                continue

            mod_type = categorize_notice_module(it["title"], it["content_text"], it["notice_type"], "caa")

            existing = db.query(CourtNotice).filter(
                CourtNotice.platform == "caa",
                CourtNotice.raw_id == it["raw_id"]
            ).first()

            if not existing:
                notice = CourtNotice(
                    platform="caa",
                    raw_id=it["raw_id"],
                    court_name=it["court_name"],
                    case_number=it["case_number"],
                    parties=it["parties"],
                    notice_type=it["notice_type"],
                    module_type=mod_type,
                    title=it["title"],
                    content_text=it["content_text"],
                    publish_time=it["publish_time"],
                    source_url=it["source_url"],
                    starting_price=it.get("starting_price"),
                    eval_price=it.get("eval_price"),
                    auction_stage=it.get("auction_stage"),
                    bidding_start=it.get("bidding_start"),
                    bidding_end=it.get("bidding_end"),
                    asset_category=it.get("asset_category"),
                    is_henan=it.get("is_henan", False),
                    henan_city=it.get("henan_city"),
                    henan_tag=it.get("henan_tag")
                )
                db.add(notice)
                new_records.append(notice)
            else:
                existing.module_type = mod_type
                if it.get("starting_price") is not None:
                    existing.starting_price = it["starting_price"]
                if it.get("eval_price") is not None:
                    existing.eval_price = it["eval_price"]
                if it.get("auction_stage") and (not existing.auction_stage or existing.auction_stage == '司法拍卖'):
                    existing.auction_stage = it["auction_stage"]
                if it.get("bidding_start") is not None:
                    existing.bidding_start = it["bidding_start"]
                if it.get("bidding_end") is not None:
                    existing.bidding_end = it["bidding_end"]
                if it.get("asset_category"):
                    existing.asset_category = it["asset_category"]
                if not existing.is_henan and it.get("is_henan"):
                    existing.is_henan = it["is_henan"]
                    existing.henan_city = it["henan_city"]
                    existing.henan_tag = it["henan_tag"]

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[caa_crawler] Commit error: {e}")
        return [], len(all_items)
    finally:
        if close_when_done:
            db.close()

    print(f"[caa_crawler] Scraped {len(all_items)} items from CAA, new ingested: {len(new_records)}")
    return new_records, len(all_items)
