# -*- coding: utf-8 -*-
"""
人民法院诉讼资产网采集器 (RMFYSSZC Live Crawler)
来源: https://www.rmfysszc.gov.cn / https://www1.rmfysszc.gov.cn
核心定位: 最高人民法院指定诉讼资产与司法拍卖统一权威发布平台
重点抓取: 刚上拍的一拍房源（法定公示期30天）、二拍房源（法定公示期15天），在刚发布公示的首日/初期第一时间捕获
"""
import ssl
import json
import re
import urllib.request
import urllib.parse
import html
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.models import CourtNotice
from backend.utils import detect_henan_info, categorize_notice_module, extract_judicial_case_number

# SSL 上下文（忽略过期/自签名证书）
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://www1.rmfysszc.gov.cn/News/Pmgg.shtml'
}

API_URL = "https://www1.rmfysszc.gov.cn/News/Handler.aspx"

def fetch_notice_list(keyword: str = "", page: int = 1) -> List[Dict[str, Any]]:
    """向诉讼资产网接口请求司法拍卖公告列表"""
    data = {
        'search': keyword,
        'fid1': '',
        'fid2': '',
        'fid3': '',
        'page': str(page),
        'include': '0'
    }
    post_bytes = urllib.parse.urlencode(data).encode('utf-8')
    req = urllib.request.Request(API_URL, data=post_bytes, headers=HEADERS)

    results = []
    try:
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=12) as resp:
            res_str = resp.read().decode('utf-8', errors='ignore')
            res_json = json.loads(res_str)
            html = res_json.get('html', '')
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S)
            for r in rows:
                tds = re.findall(r'<td[^>]*>(.*?)</td>', r, re.S)
                if len(tds) >= 3:
                    # 标题与链接
                    link_m = re.search(r'href=[\'"](.*?)[\'"]', tds[0])
                    if not link_m:
                        continue
                    url = link_m.group(1).strip()
                    title_m = re.search(r'title=[\'"](.*?)[\'"]', tds[0])
                    title = title_m.group(1).strip() if title_m else re.sub(r'<[^>]+>', '', tds[0]).strip()

                    # 法院名称
                    court_m = re.search(r'title=[\'"](.*?)[\'"]', tds[1])
                    court = court_m.group(1).strip() if court_m else re.sub(r'<[^>]+>', '', tds[1]).strip()

                    # 刊登日期 (形如 2026.10.13)
                    date_str = re.sub(r'<[^>]+>', '', tds[2]).strip()

                    # 提取 raw_id
                    pid_m = re.search(r'/(\d+)\.shtml', url)
                    raw_id = pid_m.group(1) if pid_m else url

                    results.append({
                        'raw_id': str(raw_id),
                        'title': title,
                        'court': court,
                        'date_str': date_str,
                        'url': url
                    })
    except Exception as e:
        print(f"[rmfysszc] fetch_notice_list error (kw='{keyword}', p={page}): {e}")

    return results

def parse_auction_times_from_text(text: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """从公告详情正文中提取竞价开始与结束时间，容错HTML空格隔断、全角冒号及上午下午等格式"""
    if not text:
        return None, None

    # 1. HTML实体转义与特殊字符清理
    clean_text = html.unescape(text)
    clean_text = re.sub(r'&(?:nbsp|ensp|emsp|#160);?', ' ', clean_text)
    clean_text = clean_text.replace('：', ':')

    # 2. 消除数字间因HTML标签剥离产生的空格，如 "202 6" -> "2026", "1 1" -> "11", "2 0" -> "20"
    while re.search(r'(\d)\s+(\d)', clean_text):
        clean_text = re.sub(r'(\d)\s+(\d)', r'\1\2', clean_text)

    # 消除时间冒号两侧空格，如 "10 : 00" -> "10:00"
    clean_text = re.sub(r'(\d{1,2})\s*:\s*(\d{1,2})', r'\1:\2', clean_text)

    # 模式1: YYYY年M月D日(上午/下午)?H[:时点](m分?)? 至 YYYY年M月D日...
    p1 = re.search(
        r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*(?:[上下]午)?\s*(\d{1,2})(?:\s*[:时点]\s*(\d{1,2})|\s*[时点])?'
        r'[\s\S]{0,35}?'
        r'(?:至|到|—|–|-|~)\s*'
        r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*(?:[上下]午)?\s*(\d{1,2})(?:\s*[:时点]\s*(\d{1,2})|\s*[时点])?',
        clean_text
    )
    if p1:
        g = p1.groups()
        try:
            h1 = int(g[3])
            m1 = int(g[4]) if g[4] else 0
            h2 = int(g[8])
            m2 = int(g[9]) if g[9] else 0
            s_dt = datetime(int(g[0]), int(g[1]), int(g[2]), h1, m1, 0)
            e_dt = datetime(int(g[5]), int(g[6]), int(g[7]), h2, m2, 0)
            return s_dt, e_dt
        except Exception:
            pass

    # 模式2: 同一年内的起止 (跨月或同月)
    p2 = re.search(
        r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*(?:[上下]午)?\s*(\d{1,2})(?:\s*[:时点]\s*(\d{1,2})|\s*[时点])?'
        r'[\s\S]{0,35}?'
        r'(?:至|到|—|–|-|~)\s*'
        r'(?:(\d{4})\s*年\s*)?(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*(?:[上下]午)?\s*(\d{1,2})(?:\s*[:时点]\s*(\d{1,2})|\s*[时点])?',
        clean_text
    )
    if p2:
        g = p2.groups()
        try:
            y1 = int(g[0])
            y2 = int(g[5]) if g[5] else y1
            h1 = int(g[3])
            m1 = int(g[4]) if g[4] else 0
            h2 = int(g[8])
            m2 = int(g[9]) if g[9] else 0
            s_dt = datetime(y1, int(g[1]), int(g[2]), h1, m1, 0)
            e_dt = datetime(y2, int(g[6]), int(g[7]), h2, m2, 0)
            return s_dt, e_dt
        except Exception:
            pass

    # 模式3: 标准格式 2026-10-29 10:00 至 2026-10-30 10:00
    p3 = re.search(
        r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\s*(?:[上下]午)?\s*(\d{1,2}):(\d{1,2})'
        r'[\s\S]{0,35}?'
        r'(?:至|到|—|–|-|~)\s*'
        r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\s*(?:[上下]午)?\s*(\d{1,2}):(\d{1,2})',
        clean_text
    )
    if p3:
        g = p3.groups()
        try:
            s_dt = datetime(int(g[0]), int(g[1]), int(g[2]), int(g[3]), int(g[4]), 0)
            e_dt = datetime(int(g[5]), int(g[6]), int(g[7]), int(g[8]), int(g[9]), 0)
            return s_dt, e_dt
        except Exception:
            pass

    # 模式4: 单独起拍时间 (定于/将于/拍卖时间: ...)
    p4 = re.search(
        r'(?:定于|将于|于|开拍时间|竞价开始时间|拍卖时间)\s*[:：]?\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*(?:[上下]午)?\s*(\d{1,2})(?:\s*[:时点]\s*(\d{1,2})|\s*[时点])?',
        clean_text
    )
    if p4:
        g = p4.groups()
        try:
            h = int(g[3])
            m = int(g[4]) if g[4] else 0
            s_dt = datetime(int(g[0]), int(g[1]), int(g[2]), h, m, 0)
            return s_dt, None
        except Exception:
            pass

    return None, None

def fetch_detail_data(url: str, title: str = "") -> Dict[str, Any]:
    """抓取并深度解析诉讼资产网标的详情页（起拍价、评估价、开拍时间、阶段、标的分类）"""
    req = urllib.request.Request(url, headers={
        'User-Agent': HEADERS['User-Agent'],
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    })
    
    html_src = ""
    try:
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=10) as resp:
            content = resp.read()
            try:
                html_src = content.decode('utf-8')
            except Exception:
                html_src = content.decode('gbk', errors='ignore')
    except Exception as e:
        # 网络波动等容错
        return {}

    # 提取纯文本
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', html_src, flags=re.S|re.I)
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.S|re.I)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    # 起拍价
    price = None
    price_match = re.search(r'起拍价\s*[:：]?\s*([0-9\.,]+)\s*元', text)
    if not price_match:
        price_match = re.search(r'起拍价\s*[:：]?\s*([0-9\.,]+)\s*万', text)
        if price_match:
            try:
                price = float(price_match.group(1).replace(',', '')) * 10000
            except Exception:
                pass
    else:
        try:
            price = float(price_match.group(1).replace(',', ''))
        except Exception:
            pass

    # 评估价
    eval_price = None
    eval_match = re.search(r'评估价\s*[:：]?\s*([0-9\.,]+)\s*元', text)
    if not eval_match:
        eval_match = re.search(r'评估价\s*[:：]?\s*([0-9\.,]+)\s*万', text)
        if eval_match:
            try:
                eval_price = float(eval_match.group(1).replace(',', '')) * 10000
            except Exception:
                pass
    else:
        try:
            eval_price = float(eval_match.group(1).replace(',', ''))
        except Exception:
            pass

    # 竞价开始时间与结束时间 (高精提取)
    start_dt, end_dt = parse_auction_times_from_text(text)

    # 拍卖阶段判定：标题具有最高权威性，正文辅助
    stage = "司法拍卖"
    target_str = f"{title} {text[:600]}"
    if "第二次拍卖" in title or "二拍" in title:
        stage = "二拍"
    elif "第一次拍卖" in title or "一拍" in title or "首拍" in title:
        stage = "一拍"
    elif "变卖" in title:
        stage = "变卖"
    elif "第二次拍卖" in text[:1000] or "二拍" in text[:1000]:
        stage = "二拍"
    elif "第一次拍卖" in text[:1000] or "一拍" in text[:1000] or "首拍" in text[:1000]:
        stage = "一拍"
    elif "变卖" in text[:1000]:
        stage = "变卖"

    # 标的分类与标准化归一
    category = "其他资产"
    if any(k in text for k in ['地块', '土地', '宗地', '国有土地使用权', '厂房', '仓库', '工业园']):
        category = "工业厂房与土地"
    elif any(k in text for k in ['房产', '房屋', '住宅', '公寓', '套房', '门面房', '商铺', '不动产', '车库', '地下车位', '车位']):
        category = "住宅/商业房产"
    elif any(k in text for k in ['股权', '股票', '证券', '债权', '资产包']):
        category = "金融债权与股权"

    # 提取案号（严格司法案号规范，排除不动产权证号与租赁编号）
    case_number = extract_judicial_case_number(text) or ""

    return {
        'starting_price': price,
        'eval_price': eval_price,
        'bidding_start': start_dt,
        'bidding_end': end_dt,
        'auction_stage': stage,
        'asset_category': category,
        'case_number': case_number,
        'content_text': text[:2000]
    }

from backend.database import SessionLocal

def crawl_rmfysszc_notices(db: Optional[Session] = None, max_pages: int = 2) -> Tuple[List[CourtNotice], int, Optional[str]]:
    """
    抓取人民法院诉讼资产网司法拍卖与公告数据
    重点关注：刚上拍的一拍房源（公示期30天）、二拍房源（公示期15天）
    返回: (新录入标的列表, 发现总条数, 告警信息)
    """
    print("[*] 开始执行《人民法院诉讼资产网》一拍/二拍房产与司法拍卖巡检...")
    all_raw_items = []
    seen_ids = set()

    # 多维定向搜索词：保证河南属地全覆盖 + 全国最新一拍二拍房产
    search_keywords = [
        "",         # 全网最新发布第一页和第二页（捕获今日全国刚上拍标的）
        "河南",     # 河南专属定向
        "郑州",     # 郑州重点定向
        "洛阳",     # 洛阳重点定向
        "房产",     # 房产专项
        "第一次拍卖",# 一拍专项
        "第二次拍卖" # 二拍专项
    ]

    for kw in search_keywords:
        for p in range(1, max_pages + 1):
            items = fetch_notice_list(keyword=kw, page=p)
            for it in items:
                if it['raw_id'] not in seen_ids:
                    seen_ids.add(it['raw_id'])
                    all_raw_items.append(it)
            if not items:
                break

    total_found = len(all_raw_items)
    print(f"[rmfysszc] 汇总发现标的 {total_found} 条，开始解析详情并增量入库...")

    # 1. 快速读取存量已存在的 raw_id 与价格信息（瞬时会话，严禁跨网络请求持有）
    existing_map = {}
    try:
        with SessionLocal() as check_db:
            raw_tuples = check_db.query(CourtNotice.raw_id, CourtNotice.starting_price, CourtNotice.bidding_start).filter(
                CourtNotice.platform == "rmfysszc"
            ).all()
            for r in raw_tuples:
                existing_map[r[0]] = (r[1], r[2])
    except Exception as e:
        print(f"[rmfysszc] Check existing map notice: {e}")

    # 2. 网络抓取详情阶段：完全在 DB 会话之外执行
    for it in all_raw_items:
        raw_id = it['raw_id']
        url = it['url']
        title = it['title']
        has_existing = raw_id in existing_map
        sp, bs = existing_map.get(raw_id, (None, None))
        detail = {}
        if not has_existing or not sp or not bs:
            detail = fetch_detail_data(url, title=title)
        it['detail'] = detail

    new_records = []
    close_when_done = False
    if db is None:
        db = SessionLocal()
        close_when_done = True

    try:
        for it in all_raw_items:
            raw_id = it['raw_id']
            url = it['url']
            title = it['title']
            court = it['court']
            date_str = it['date_str']
            detail = it.get('detail', {})

            existing = db.query(CourtNotice).filter(
                CourtNotice.platform == "rmfysszc",
                CourtNotice.raw_id == raw_id
            ).first()

            # 解析发布时间
            pub_dt = datetime.now()
            if date_str:
                try:
                    clean_date = date_str.replace('.', '-').strip()
                    pub_dt = datetime.strptime(clean_date, "%Y-%m-%d")
                except Exception:
                    pass

            # 阶段与分类推断 (标题先行兜底)
            stage = detail.get('auction_stage')
            if not stage or stage == "司法拍卖":
                if "第二次拍卖" in title or "二拍" in title:
                    stage = "二拍"
                elif "第一次拍卖" in title or "一拍" in title:
                    stage = "一拍"
                elif "变卖" in title:
                    stage = "变卖"
                else:
                    stage = "一拍"

            category = detail.get('asset_category') or "其他资产"
            if category in ["综合资产", "其他资产"]:
                if any(k in title for k in ['地块', '土地', '厂房', '仓库']):
                    category = "工业厂房与土地"
                elif any(k in title for k in ['房', '住宅', '公寓', '商业', '商铺', '不动产', '车位']):
                    category = "住宅/商业房产"
                elif any(k in title for k in ['股权', '股票', '债权']):
                    category = "金融债权与股权"

            content_text = detail.get('content_text') or title
            is_henan, henan_city, henan_tag = detect_henan_info(title, court, content_text)
            mod_type = "拍卖公告"

            if not existing:
                notice = CourtNotice(
                    platform="rmfysszc",
                    raw_id=raw_id,
                    court_name=court or "人民法院诉讼资产网",
                    case_number=detail.get('case_number'),
                    parties="",
                    notice_type="司法拍卖",
                    module_type=mod_type,
                    title=title,
                    content_text=content_text,
                    publish_time=pub_dt,
                    source_url=url,
                    starting_price=detail.get('starting_price'),
                    eval_price=detail.get('eval_price'),
                    auction_stage=stage,
                    asset_category=category,
                    bidding_start=detail.get('bidding_start'),
                    bidding_end=detail.get('bidding_end'),
                    is_henan=is_henan,
                    henan_city=henan_city,
                    henan_tag=henan_tag
                )
                db.add(notice)
                new_records.append(notice)
            else:
                if detail.get('starting_price') and not existing.starting_price:
                    existing.starting_price = detail.get('starting_price')
                if detail.get('eval_price') and not existing.eval_price:
                    existing.eval_price = detail.get('eval_price')
                if detail.get('bidding_start') and not existing.bidding_start:
                    existing.bidding_start = detail.get('bidding_start')
                if detail.get('bidding_end') and not existing.bidding_end:
                    existing.bidding_end = detail.get('bidding_end')
                if stage and (not existing.auction_stage or existing.auction_stage == '司法拍卖'):
                    existing.auction_stage = stage
                if category and (not existing.asset_category or existing.asset_category == '综合资产'):
                    existing.asset_category = category
                if is_henan and not existing.is_henan:
                    existing.is_henan = is_henan
                    existing.henan_city = henan_city
                    existing.henan_tag = henan_tag

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[rmfysszc] db commit error: {e}")
        return [], total_found, str(e)
    finally:
        if close_when_done:
            db.close()

    print(f"[rmfysszc] 巡检入库完成: 共发现 {total_found} 条，新入库 {len(new_records)} 条")
    return new_records, total_found, None

if __name__ == "__main__":
    from backend.database import SessionLocal
    db = SessionLocal()
    records, found, err = crawl_rmfysszc_notices(db, max_pages=1)
    print(f"Test run completed: found={found}, new={len(records)}, err={err}")
