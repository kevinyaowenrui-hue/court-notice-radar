# -*- coding: utf-8 -*-
"""
53BK 地方数字报纸公告专版全量采集器
通过 53BK 地方报纸种子库 (PaperSeed)，全面覆盖河南省 18 地市各类报纸及全国重点法治大报，
全版面深度穿透扫描司法拍卖、法院送达、破产重整、金融债权转让、产权变卖等所有相关公告。
"""
import urllib.request
import re
import html
from datetime import datetime, timedelta
import random
from typing import List, Tuple, Optional
from urllib.parse import urljoin, urlparse
from sqlalchemy.orm import Session
from backend.models import PaperSeed, CourtNotice
from backend.utils import (
    detect_henan_info, is_promotional_content, categorize_notice_module, stable_hash,
    extract_starting_and_eval_price, is_vehicle_or_equipment_item, HENAN_CITIES,
    extract_judicial_case_number
)

HENAN_PAPER_CITY_MAP = {
    "商丘日报": "商丘", "京九晚报": "商丘",
    "平顶山日报": "平顶山", "平顶山晚报": "平顶山",
    "周口日报": "周口", "周口晚报": "周口",
    "洛阳日报": "洛阳", "洛阳晚报": "洛阳",
    "开封日报": "开封", "汴梁晚报": "开封",
    "新乡日报": "新乡", "新乡晚报": "新乡",
    "焦作日报": "焦作", "焦作晚报": "焦作",
    "安阳日报": "安阳", "安阳晚报": "安阳",
    "鹤壁日报": "鹤壁",
    "濮阳日报": "濮阳",
    "许昌日报": "许昌", "许昌晨报": "许昌",
    "漯河日报": "漯河",
    "三门峡日报": "三门峡",
    "南阳日报": "南阳", "南阳晚报": "南阳",
    "信阳日报": "信阳", "信阳晚报": "信阳",
    "驻马店日报": "驻马店", "天中晚报": "驻马店",
    "济源日报": "济源",
    "郑州日报": "郑州", "郑州晚报": "郑州",
    "河南日报": "全省", "大河报": "全省", "河南法制报": "全省", "东方今报": "全省", "河南商报": "全省"
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

# 全品类法律与公告关键词矩阵（涵盖拍卖、送达、执行、破产、债权转让、公共资源出让等所有类型）
EXPANDED_LEGAL_KEYWORDS = [
    # 1. 司法拍卖与资产变卖类
    '拍卖', '变卖', '在拍', '起拍', '拍租', '竞买', '竞价', '司法拍卖', '标的物变价', 
    '财产处置', '处置招商', '公开拍卖', '涉案资产', '动产拍卖', '不动产拍卖', '拍卖公告', '变价公告',
    # 2. 法院诉讼送达与执行类
    '法院', '法官', '法庭', '中院', '裁判', '判决', '裁定', '传票', '执行',
    '起诉', '撤诉', '送达', '限消', '限制高消费', '失信', '财产申报', '执行裁定', 
    '应诉通知', '开庭传票', '借款合同纠纷', '民事判决', '民事裁定', '公告送达',
    # 3. 破产重整与清算注销类
    '破产', '清算', '重整', '债权申报', '债权人会议', '清算组', '减资公告', '合并公告', 
    '分立公告', '解散公告', '注销公告', '企业注销', '减资注销', '破产清算',
    # 4. 金融不良资产与债权转让处置类
    '债权', '不良资产', '资产包', '债权转让', '债权催收', '联合催收', '资产管理公司', 
    '中原资产', '河南资产', '华融', '信达', '东方', '长城', '抵押权', '追偿', '金融借款', '催收公告',
    # 5. 土地矿业与产权出让类
    '土地出让', '采矿权', '挂牌出让', '国有建设用地', '产权转让', '资产出让', '出让公告',
    # 6. 不动产确权与遗失声明类
    '遗失声明', '作废声明', '权属证明', '不动产权证书遗失', '首次登记公告', '催告'
]

def fetch_paper_html(url: str, timeout: int = 8):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            real_url = resp.geturl()
            content = resp.read()
            html = ""
            for enc in ['utf-8', 'gbk', 'gb2312']:
                try:
                    html = content.decode(enc)
                    break
                except Exception:
                    pass
            if not html:
                html = content.decode('gbk', errors='ignore')
            return real_url, html
    except Exception:
        return url, ""

def scan_single_paper(seed: PaperSeed) -> List[dict]:
    """扫描单家地方报社官网与数字报专版，全版面深度提取真实刊登的所有相关公告"""
    results = []
    try:
        real_url, html = fetch_paper_html(seed.epaper_url, timeout=8)
        if not html:
            return results

        # 1. 深度穿透数字报期刊入口（处理 meta refresh / JS 跳转 / paperindex.htm 自动跳转到当期版面）
        current_issue_url = real_url
        refresh_m = re.search(r'content=["\']0;\s*url=([^"\']+)["\']', html, re.I)
        js_m = re.search(r'location\.href\s*=\s*["\']([^"\']+)["\']', html, re.I)
        if refresh_m:
            current_issue_url = urljoin(real_url, refresh_m.group(1).split('?')[0])
        elif js_m:
            current_issue_url = urljoin(real_url, js_m.group(1).split('?')[0])
        elif "paperindex.htm" in html:
            current_issue_url = urljoin(real_url, "paperindex.htm")

        if current_issue_url != real_url:
            current_issue_url, issue_html = fetch_paper_html(current_issue_url, timeout=8)
            # 检查二次跳转 (如 paperindex.htm 跳转到 html/node_1.htm)
            refresh_m2 = re.search(r'content=["\']0;\s*url=([^"\']+)["\']', issue_html, re.I)
            if refresh_m2:
                current_issue_url, html = fetch_paper_html(urljoin(current_issue_url, refresh_m2.group(1)), timeout=8)
            elif issue_html:
                html = issue_html

        # 2. 全面提取版面列表 (涵盖 node_*.htm / Page_*.html / layout 等各类数字报系统架构)
        node_matches = re.findall(r'<a[^>]*href=["\']?([^"\'\s>]*(?:node_|page_|layout|szb)[^"\'\s>]*)["\']?[^>]*>(.*?)</a>', html, re.I | re.S)
        editions = []
        seen_nodes = set()
        for href, title in node_matches:
            clean_t = re.sub(r'<[^>]+>', '', title).strip()
            full_nurl = urljoin(current_issue_url, href)
            if full_nurl not in seen_nodes and clean_t:
                seen_nodes.add(full_nurl)
                editions.append((clean_t, full_nurl))

        # 收集待筛选的文章列表：[(版面名, 文章标题, 文章完整URL)]
        candidate_articles = []
        seen_art_urls = set()

        def add_candidate(ename, atitle, aurl):
            clean_t = re.sub(r'<[^>]+>', '', atitle).strip()
            clean_t = re.sub(r'\s+', ' ', clean_t)
            if 5 <= len(clean_t) <= 150 and aurl not in seen_art_urls:
                seen_art_urls.add(aurl)
                candidate_articles.append((ename, clean_t, aurl))

        if editions:
            # 优先扫描包含公告、法治、政法、要闻、综合、经济、社会的版面，最大扫描前 16 个版面（彻底避免遗漏后置公告版）
            sorted_editions = sorted(
                editions,
                key=lambda x: any(k in x[0] for k in ['公告', '法', '专版', '声明', '政法', '要闻', '综合', '社会', '经济']),
                reverse=True
            )
            for ename, eurl in sorted_editions[:16]:
                _, ehtml = fetch_paper_html(eurl, timeout=5)
                if not ehtml:
                    continue

                # 模式 A: 鲁棒提取 <area ...> 热区切片（无论 href 与 title 谁先谁后）
                for area_tag in re.findall(r'<area\s+[^>]*>', ehtml, re.I):
                    href_m = re.search(r'href=["\']([^"\']+)["\']', area_tag, re.I)
                    title_m = re.search(r'title=["\']([^"\']+)["\']', area_tag, re.I)
                    if href_m and title_m:
                        add_candidate(ename, title_m.group(1), urljoin(eurl, href_m.group(1)))

                # 模式 B: 提取 <a ...> 列表文字与超链接
                for a_tag in re.findall(r'<a\s+[^>]*>.*?</a>', ehtml, re.I | re.S):
                    href_m = re.search(r'href=["\']([^"\']+)["\']', a_tag, re.I)
                    title_m = re.search(r'title=["\']([^"\']+)["\']', a_tag, re.I)
                    inner_text = re.sub(r'<[^>]+>', '', a_tag).strip()
                    cand_title = title_m.group(1).strip() if (title_m and len(title_m.group(1).strip()) >= 5) else inner_text
                    if href_m and len(cand_title) >= 5:
                        add_candidate(ename, cand_title, urljoin(eurl, href_m.group(1)))
        else:
            # 兼容普通新闻门户或单页版面：解析全页超链接
            links = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.S)
            for href, text in links:
                clean_text = re.sub(r'<[^>]+>', '', text).strip()
                if len(clean_text) >= 5:
                    add_candidate("数字报刊", clean_text, urljoin(current_issue_url, href))

        # 3. 严格匹配法治、司法、拍卖、债权及法定公告（双因子主体+动作强校验，彻底剔除招聘、市集、外链等无关内容）
        seed_domain = urlparse(seed.epaper_url).netloc

        for ename, title, raw_art_url in candidate_articles:
            # 域名同源校验：彻底过滤友情链接与外部广告链接
            art_domain = urlparse(raw_art_url).netloc
            if seed_domain and art_domain and seed_domain != art_domain:
                continue

            # 清理 URL 中的 HTML 实体转义符（如 &amp;）
            art_url = html.unescape(raw_art_url)

            # 初步排除明显的反恐/招聘/生活宣传类标题
            if bool(re.search(r'招聘|市集|反恐|大赛|校园|学法|普法|公积金|选调|政法委|交房|交付公告|友情链接', title)):
                continue

            # 深度穿透：请求详情页正文（前 2000 字），以支持正文级主体+动作双因子研判与关键要素抽取
            body_text = ""
            try:
                _, art_html = fetch_paper_html(art_url, timeout=5)
                if art_html:
                    clean_art = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', art_html, flags=re.I | re.S)
                    main_m = re.search(r'<(?:div|td|article|section)[^>]*(?:content|article|detail|main|news|text)[^>]*>(.*?)</(?:div|td|article|section)>', clean_art, re.I | re.S)
                    txt_source = main_m.group(1) if main_m else clean_art
                    raw_body = re.sub(r'<[^>]+>', ' ', txt_source)
                    body_text = re.sub(r'\s+', ' ', raw_body).strip()[:2000]
            except Exception:
                body_text = ""

            check_text = f"{title}\n{body_text}" if body_text else title

            # 正文/标题二次强校验：必须同时具备司法/处置主体词与业务动作词
            has_subject = bool(re.search(r'人民法院|中级法院|基层法院|法庭|金融资产|资产管理|银行|农商行|破产管理人|拍卖行|产权交易|清算组', check_text))
            has_action = bool(re.search(r'拍卖|变卖|送达|传票|破产|清算|重整|债权转让|催收|执行裁定|起诉状', check_text))

            if not (has_subject and has_action):
                continue
            if is_promotional_content(check_text):
                continue
            if is_vehicle_or_equipment_item(title, body_text):
                continue

            raw_id = f"paper_{seed.id}_{stable_hash(title)}"

            # 从正文/标题智能提取真实法院或债权处置机构；未提取到时标记为报纸公告版，严禁伪造“XX地方人民法院”
            court_m = re.search(r'([^\s，。、（]{2,15}(?:人民法院|中级法院|基层法院|法庭|金融资产管理公司|破产管理人|拍卖行|产权交易中心))', check_text)
            court_name = court_m.group(1) if court_m else f"《{seed.paper_name}》公告版"

            # 严格案号抽取（正文联合检索）
            case_number = extract_judicial_case_number(check_text) or ""

            # 智能提取真实的起拍价与评估价
            starting_price, eval_price = extract_starting_and_eval_price(title, body_text or title)
            if starting_price is not None:
                starting_price = round(starting_price, 2)
            if eval_price is not None:
                eval_price = round(eval_price, 2)

            content_text = (
                f"报纸媒体：{seed.paper_name}（{seed.province} · {seed.city}）\n"
                f"所属版面：{ename}\n刊登标题：{title}\n"
                f"报社电子报入口：{seed.epaper_url}\n原文阅读链接：{art_url}\n"
                f"【公告正文摘录】\n{body_text[:1200] if body_text else title}"
            )

            # 河南 18 地市精确映射，严禁出现 henan_city="河南"，严禁将带“日报/晚报”的外省报纸误判为河南属地
            if "河南" in (seed.province or "") or "河南" in (seed.city or "") or seed.paper_name in HENAN_PAPER_CITY_MAP:
                is_henan = True
                mapped_city = HENAN_PAPER_CITY_MAP.get(seed.paper_name)
                if not mapped_city:
                    for pn, pc in HENAN_PAPER_CITY_MAP.items():
                        if pn in seed.paper_name:
                            mapped_city = pc
                            break
                if not mapped_city and seed.city:
                    c_clean = seed.city.replace("市", "").replace("省", "").strip()
                    if c_clean in HENAN_CITIES:
                        mapped_city = c_clean
                henan_city = mapped_city or "全省"
                henan_tag = f"河南属地报纸法治与公告专版 (《{seed.paper_name}》· {ename})"
            else:
                is_henan, henan_city, henan_tag = detect_henan_info(
                    title=title,
                    content=content_text,
                    court_name=court_name,
                    case_number=case_number
                )
                if is_henan:
                    henan_tag = f"全国地方报跨域涉豫刊登 (《{seed.paper_name}》刊登涉{henan_city}公告)"

            # 细分公告类型
            if any(k in title for k in ['拍卖', '变卖', '拍租', '竞买', '变价']):
                notice_type = "报刊司法拍卖"
            elif any(k in title for k in ['债权', '不良资产', '资产包', '催收']):
                notice_type = "报刊债权转让"
            elif any(k in title for k in ['清算', '破产', '减资', '重整']):
                notice_type = "报刊清算重整公告"
            elif any(k in title for k in ['送达', '传票', '判决', '裁定', '起诉状']):
                notice_type = "报刊诉讼送达公告"
            else:
                notice_type = "地方报纸法治刊登"

            module_type = categorize_notice_module(title, content_text, notice_type, "local_paper")

            # 智能提取报刊出刊实际日期
            date_m = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', f"{art_url} {current_issue_url} {ename}")
            if not date_m:
                date_m = re.search(r'(\d{4})(\d{2})(\d{2})', f"{art_url} {current_issue_url}")
            if not date_m:
                date_m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', f"{ename} {title}")

            if date_m:
                try:
                    y, m, d = int(date_m.group(1)), int(date_m.group(2)), int(date_m.group(3))
                    paper_date = datetime(y, m, d, 8, 30, 0)
                except Exception:
                    paper_date = datetime.now()
            else:
                paper_date = datetime.now()

            # 时效门禁校验：严格以当天最新刊发为主，过滤超出 3 天的历史往期废旧版面
            days_diff = (datetime.now() - paper_date).total_seconds() / 86400.0
            if days_diff > 3.0:
                continue

            results.append({
                "platform": "local_paper",
                "raw_id": raw_id,
                "court_name": court_name,
                "case_number": case_number,
                "parties": "",
                "notice_type": notice_type,
                "module_type": module_type,
                "title": f"《{seed.paper_name}》刊登: {title}",
                "content_text": content_text,
                "publish_time": paper_date,
                "source_url": art_url,
                "starting_price": starting_price,
                "eval_price": eval_price,
                "is_henan": is_henan,
                "henan_city": henan_city,
                "henan_tag": henan_tag
            })
    except Exception as e:
        print(f"[local_paper_crawler] Error scanning {seed.paper_name}: {e}")

    return results

from backend.database import SessionLocal

def scan_monitored_papers(db: Optional[Session] = None, max_papers: int = 50) -> Tuple[List[CourtNotice], int]:
    """巡检所有已开启监控的地方数字报（全量扫描河南 18 地市所有报纸与全国重点大报）"""
    # 1. 快速读取监控种子（瞬时会话，严禁跨网络请求持有）
    class SeedInfo:
        def __init__(self, id, paper_name, province, city, epaper_url):
            self.id = id
            self.paper_name = paper_name
            self.province = province
            self.city = city
            self.epaper_url = epaper_url

    seeds_info = []
    try:
        with SessionLocal() as check_db:
            monitored_seeds = check_db.query(PaperSeed).filter(PaperSeed.is_monitored == True).order_by(
                (PaperSeed.province == "河南").desc(),
                PaperSeed.last_scanned_at.asc()
            ).limit(max_papers).all()
            for s in monitored_seeds:
                seeds_info.append(SeedInfo(s.id, s.paper_name, s.province, s.city, s.epaper_url))
    except Exception as e:
        print(f"[local_paper_crawler] Seed fetch error: {e}")

    # 2. 网络抓取阶段：完全在 DB 会话之外执行
    scanned_results = []
    for seed in seeds_info:
        items = scan_single_paper(seed)
        scanned_results.append((seed.id, items))

    # 3. 集中入库与状态更新：短事务
    new_records = []
    seen_raw_ids = set()
    close_when_done = False
    if db is None:
        db = SessionLocal()
        close_when_done = True

    try:
        for seed_id, items in scanned_results:
            for it in items:
                raw_id = it["raw_id"]
                if raw_id in seen_raw_ids:
                    continue
                seen_raw_ids.add(raw_id)

                existing = db.query(CourtNotice).filter(
                    CourtNotice.platform == it["platform"],
                    CourtNotice.raw_id == raw_id
                ).first()
                if not existing:
                    notice = CourtNotice(
                        platform=it["platform"],
                        raw_id=raw_id,
                        court_name=it["court_name"],
                        case_number=it["case_number"],
                        parties=it["parties"],
                        notice_type=it["notice_type"],
                        module_type=it.get("module_type") or categorize_notice_module(it["title"], it["content_text"], it["notice_type"], it["platform"]),
                        title=it["title"],
                        content_text=it["content_text"],
                        publish_time=it["publish_time"],
                        source_url=it["source_url"],
                        starting_price=it.get("starting_price"),
                        eval_price=it.get("eval_price"),
                        is_henan=it.get("is_henan", False),
                        henan_city=it.get("henan_city"),
                        henan_tag=it.get("henan_tag")
                    )
                    db.add(notice)
                    new_records.append(notice)
                else:
                    if not existing.is_henan and it.get("is_henan"):
                        existing.is_henan = it["is_henan"]
                        existing.henan_city = it["henan_city"]
                        existing.henan_tag = it["henan_tag"]

            db_seed = db.query(PaperSeed).filter(PaperSeed.id == seed_id).first()
            if db_seed:
                db_seed.last_scanned_at = datetime.now()
                db_seed.status = "active" if items else "idle"

        total_found = len(seen_raw_ids)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[local_paper_crawler] Commit error: {e}")
        return [], 0
    finally:
        if close_when_done:
            db.close()

    print(f"[local_paper_crawler] Scanned {len(seeds_info)} papers, new notices ingested: {len(new_records)}, total found: {total_found}")
    return new_records, total_found
