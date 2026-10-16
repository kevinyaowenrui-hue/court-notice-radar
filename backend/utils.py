# -*- coding: utf-8 -*-
import re
import asyncio
import hashlib
import concurrent.futures
from datetime import datetime, date, timedelta
from typing import Tuple, Optional

def get_today_date_str(fmt: str = "%Y-%m-%d") -> str:
    """获取当前系统日期字符串"""
    return datetime.now().strftime(fmt)

def is_published_today(pub_time: Optional[datetime]) -> bool:
    """判断给定发布时间是否属于今天"""
    if not pub_time:
        return False
    return pub_time.date() == datetime.now().date()

def is_published_within_days(pub_time: Optional[datetime], days: int = 1) -> bool:
    """判断给定发布时间是否在指定天数内（如 days=1 为近 24 小时）"""
    if not pub_time:
        return False
    cutoff = datetime.now() - timedelta(days=days)
    return pub_time >= cutoff

def stable_hash(text: str) -> str:
    """生成跨进程与重启一致的确定性短哈希字符串，杜绝 Python 进程哈希加盐随机性引发重复入库"""
    return hashlib.md5((text or "").encode('utf-8', errors='ignore')).hexdigest()[:16]

def run_async(coro):
    """在任何同步上下文中安全执行异步协程，彻底避免 'asyncio.run() cannot be called from a running event loop'"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()

def parse_price_amount(text: str) -> Optional[float]:
    """
    通用价格提取函数：
    支持千分位逗号（如 1,280,000 或 1,280,000.00）、中文单位（万、万元、亿、亿元、元）。
    返回统一转换为以“元”为单位的浮点数值，未匹配成功返回 None。
    统一保留两位小数，消除浮点数精度尾巴。
    """
    if not text:
        return None
    clean = text.replace(',', '').replace('，', '').strip()
    m = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(亿元|亿|万元|万|元)?', clean)
    if not m:
        return None
    try:
        val = float(m.group(1))
        unit = m.group(2) or ''
        if '亿' in unit:
            val *= 100_000_000.0
        elif '万' in unit:
            val *= 10_000.0
        return round(val, 2)
    except Exception:
        return None

def extract_bidding_times(text: str = "") -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    从公告标题或正文中智能提取竞价/拍卖开始与结束时间：
    1. 完整区间：如 2026年10月18日10：00时起至2026年10月19日（截止时间无小时自动继承或默认）
    2. 标准 ISO 区间：2026-10-18 10:00 至 2026-10-19 10:00
    3. 单一开拍时间：2026年10月25日 10:00 开拍
    4. 电商无年份卡片格式：10月25日 10:00 开拍 / 10-25 10:00（自动填充合理年份）
    """
    if not text:
        return None, None
    curr_year = datetime.now().year

    # 1. 明确区间：X起至Y 或 X至Y 或 X~Y
    range_m = re.search(
        r'(\d{4}[年\-/]\d{1,2}[月\-/]\d{1,2}日?(?:\s*\d{1,2}(?:[：:]\d{1,2}|时(?:\d{1,2}分?)?))?)'
        r'[^\d至~到起]*(?:起?至|~|到)\s*'
        r'(\d{4}[年\-/]?\s*)?(\d{1,2}[月\-/]\d{1,2}日?(?:\s*\d{1,2}(?:[：:]\d{1,2}|时(?:\d{1,2}分?)?))?)',
        text
    )
    if range_m:
        s1 = range_m.group(1)
        y2_prefix = range_m.group(2) or ""
        s2 = range_m.group(3)
        if not re.match(r'^\d{4}', s2) and not y2_prefix:
            y1_m = re.match(r'^(\d{4})', s1)
            if y1_m:
                s2 = f"{y1_m.group(1)}年{s2}"
        elif y2_prefix:
            s2 = f"{y2_prefix}{s2}"

        def _parse_single_dt(s):
            m = re.search(r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})日?(?:\s*(\d{1,2})(?:[：:时](\d{1,2}))?)?', s)
            if m:
                y = int(m.group(1))
                mo = int(m.group(2))
                d = int(m.group(3))
                h = int(m.group(4) or 10)
                mi = int(m.group(5) or 0)
                return datetime(y, mo, d, h, mi)
            return None

        dt1 = _parse_single_dt(s1)
        dt2 = _parse_single_dt(s2)
        if dt1:
            return dt1, dt2

    # 2. 单一时间点（带 4 位年份）：如 2026年10月25日 10:00 / 2026-10-25 10:00
    m_single = re.search(r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})日?(?:\s*(?:上午|下午)?\s*(\d{1,2})(?:[：:时](\d{1,2}))?)?', text)
    if m_single:
        try:
            y = int(m_single.group(1))
            mo = int(m_single.group(2))
            d = int(m_single.group(3))
            h = int(m_single.group(4) or 10)
            mi = int(m_single.group(5) or 0)
            if 2020 <= y <= 2030 and 1 <= mo <= 12 and 1 <= d <= 31 and 0 <= h <= 23:
                return datetime(y, mo, d, h, mi), None
        except Exception:
            pass

    # 3. 电商无年份卡片格式：如 10月25日 10:00 开拍 / 10-25 10:00
    m_month = re.search(r'(\d{1,2})[月\-/](\d{1,2})日?(?:\s*(\d{1,2})[：:时](\d{1,2}))', text)
    if m_month:
        try:
            mo = int(m_month.group(1))
            d = int(m_month.group(2))
            h = int(m_month.group(3))
            mi = int(m_month.group(4))
            if 1 <= mo <= 12 and 1 <= d <= 31 and 0 <= h <= 23:
                y = curr_year if mo >= datetime.now().month - 1 else curr_year + 1
                return datetime(y, mo, d, h, mi), None
        except Exception:
            pass

    return None, None

def extract_judicial_case_number(text: str) -> str:
    """
    严格司法案号提取与清洗：
    1. 司法案号正则：r"[（(]\s*(\d{4})\s*[）)]\s*([京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼]\d{0,4}|最高法|兵)\s*(民|刑|执|破|行|赔|知|商|财保|清|重)[^号）)\s]{1,20}号"
    2. 显式排除含 不动产、产权、证明、权证、租公房、字第000 等匹配字符串
    3. 统一替换为全角括号 （） 并去除内部空格
    """
    if not text:
        return ""
    pattern = r'[（(]\s*(\d{4})\s*[）)]\s*([京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼]\d{0,4}|最高法|兵)\s*(民|刑|执|破|行|赔|知|商|财保|清|重)[^号）)\s]{1,20}号'
    m = re.search(pattern, text)
    if not m:
        return ""
    matched = m.group(0)
    exclude_words = ['不动产', '产权', '证明', '权证', '租公房', '字第000']
    if any(w in matched for w in exclude_words):
        return ""
    clean_case = re.sub(r'\s+', '', matched).replace('(', '（').replace(')', '）')
    return clean_case

def extract_starting_and_eval_price(title: str = "", content: str = "") -> Tuple[Optional[float], Optional[float]]:
    """
    从标题和正文中严格智能提取真实的起拍价与评估价：
    绝不将注册资本、借款本金、诉讼保全金额误作为起拍价，
    若无明确评估价则严格返回 None，坚决杜绝人工乘 1.2 编造虚假评估价或用起拍价充当评估价。
    """
    corpus = f"{title or ''} {content or ''}"
    starting_price = None
    eval_price = None

    # 1. 优先提取明确的起拍价/底价/挂牌价/租金
    sp_patterns = [
        r'(?:起拍价|起拍|底价|挂牌价|挂牌底价|拍卖底价|竞买底价|出让底价|出让价格|挂牌价格|转让底价|交易底价|转让价格|标的底价|起始价|成交价|成交金额|年租金)[：:\s]*([¥￥]?\s*[0-9,.]+\s*(?:亿元|亿|万元|万|元)?)',
        r'(?:租金)[：:\s]*([¥￥]?\s*[0-9,.]+\s*(?:亿元|亿|万元|万|元)?(?:\/年)?)',
        r'(?:起拍价|起始价|出让底价|挂牌底价|挂牌价|转让底价|底价|成交价)\s*[:：]?\s*([0-9,.]+\s*(?:亿元|亿|万元|万|元))',
        r'<td[^>]*>(?:起拍价|起始价|出让底价|挂牌底价|挂牌价|转让底价|底价|成交价)<\/td>\s*<td[^>]*>([¥￥]?\s*[0-9,.]+\s*(?:亿元|亿|万元|万|元)?)<\/td>',
        r'([¥￥]?\s*[0-9,.]+\s*(?:亿元|亿|万元|万|元)?)\s*起拍'
    ]
    for pat in sp_patterns:
        m = re.search(pat, corpus, re.IGNORECASE)
        if m:
            val = parse_price_amount(m.group(1))
            if val and val > 100:
                starting_price = round(val, 2)
                break

    # 2. 提取评估价/参考价
    ep_patterns = [
        r'(?:评估价|评估值|市场评估价|参考价|评估总值)[：:\s]*([¥￥]?\s*[0-9,.]+\s*(?:亿元|亿|万元|万|元)?)',
        r'<td[^>]*>(?:评估价|评估值|评估总值|参考价)<\/td>\s*<td[^>]*>([¥￥]?\s*[0-9,.]+\s*(?:亿元|亿|万元|万|元)?)<\/td>'
    ]
    for pat in ep_patterns:
        m = re.search(pat, corpus, re.IGNORECASE)
        if m:
            val = parse_price_amount(m.group(1))
            if val and val > 100:
                eval_price = round(val, 2)
                break

    # 严格校验：若评估价与起拍价完全一致，说明页面未给出独立评估价，置为 None 杜绝伪造
    if starting_price is not None and eval_price is not None and starting_price == eval_price:
        eval_price = None

    return starting_price, eval_price

# 河南省 18 地市全域关键词词典（严格区分地级市主名与专属区县，杜绝全国通用词误判）
HENAN_CITIES = {
    "郑州": [
        "郑州", "郑州市", "金水区", "二七区", "中原区", "管城区", "管城回族区", "管城法院",
        "惠济区", "上街区", "中牟县", "中牟", "巩义市", "巩义", "荥阳市", "荥阳",
        "新密市", "新密", "新郑市", "新郑", "登封市", "登封", "郑东新区", "郑州航空港",
        "航空港区", "郑州高新区", "郑州经开区"
    ],
    "开封": [
        "开封", "开封市", "龙亭区", "龙亭", "顺河回族区", "顺河区", "禹王台区", "祥符区", "祥符",
        "杞县", "通许县", "通许", "尉氏县", "尉氏", "兰考县", "兰考", "开封鼓楼", "鼓楼区（开封）"
    ],
    "洛阳": [
        "洛阳", "洛阳市", "老城区", "西工区", "瀍河回族区", "瀍河区", "瀍河", "涧西区", "洛龙区",
        "孟津区", "孟津", "偃师区", "偃师", "新安县", "栾川县", "栾川", "嵩县", "汝阳县", "汝阳",
        "宜阳县", "宜阳", "洛宁县", "洛宁", "伊川县", "伊川"
    ],
    "平顶山": [
        "平顶山", "平顶山市", "卫东区", "石龙区", "湛河区", "宝丰县", "宝丰", "叶县", "鲁山县", "鲁山",
        "郏县", "舞钢市", "舞钢", "汝州市", "汝州", "平顶山新华区"
    ],
    "安阳": [
        "安阳", "安阳市", "文峰区", "北关区", "殷都区", "龙安区", "汤阴县", "汤阴", "滑县",
        "内黄县", "内黄", "林州市", "林州"
    ],
    "鹤壁": [
        "鹤壁", "鹤壁市", "淇滨区", "山城区", "鹤山区", "浚县", "淇县"
    ],
    "新乡": [
        "新乡", "新乡市", "卫滨区", "红旗区", "凤泉区", "牧野区", "获嘉县", "获嘉", "原阳县", "原阳",
        "延津县", "延津", "封丘县", "封丘", "卫辉市", "卫辉", "辉县市", "辉县", "长垣市", "长垣县", "长垣"
    ],
    "焦作": [
        "焦作", "焦作市", "中站区", "马村区", "山阳区", "修武县", "修武", "博爱县", "博爱", "武陟县", "武陟",
        "温县", "沁阳市", "沁阳", "孟州市", "孟州", "焦作解放区"
    ],
    "濮阳": [
        "濮阳", "濮阳市", "华龙区", "清丰县", "清丰", "南乐县", "南乐", "范县", "台前县", "台前"
    ],
    "许昌": [
        "许昌", "许昌市", "魏都区", "建安区", "鄢陵县", "鄢陵", "襄城县", "禹州市", "禹州", "长葛市", "长葛"
    ],
    "漯河": [
        "漯河", "漯河市", "源汇区", "郾城区", "召陵区", "舞阳县", "舞阳", "临颍县", "临颍"
    ],
    "三门峡": [
        "三门峡", "三门峡市", "湖滨区", "陕州区", "陕州", "渑池县", "渑池", "卢氏县", "卢氏",
        "义马市", "义马", "灵宝市", "灵宝"
    ],
    "南阳": [
        "南阳", "南阳市", "宛城区", "卧龙区", "南召县", "南召", "方城县", "方城", "西峡县", "西峡",
        "镇平县", "镇平", "内乡县", "内乡", "淅川县", "淅川", "社旗县", "社旗", "唐河县", "唐河",
        "桐柏县", "桐柏", "新野县", "新野", "邓州市", "邓州"
    ],
    "商丘": [
        "商丘", "商丘市", "梁园区", "梁园", "睢阳区", "民权县", "睢县", "宁陵县", "宁陵", "柘城县", "柘城",
        "虞城县", "虞城", "夏邑县", "夏邑", "永城市", "永城"
    ],
    "信阳": [
        "信阳", "信阳市", "浉河区", "平桥区", "罗山县", "罗山", "光山县", "光山", "新县人民法院", "商城县",
        "固始县", "固始", "潢川县", "潢川", "淮滨县", "淮滨", "息县"
    ],
    "周口": [
        "周口", "周口市", "川汇区", "淮阳区", "淮阳", "扶沟县", "扶沟", "西华县", "西华", "商水县", "商水",
        "沈丘县", "沈丘", "郸城县", "郸城", "太康县", "太康", "鹿邑县", "鹿邑", "项城市", "项城"
    ],
    "驻马店": [
        "驻马店", "驻马店市", "驿城区", "西平县", "西平", "上蔡县", "上蔡", "平舆县", "平舆",
        "正阳县", "正阳", "确山县", "确山", "泌阳县", "泌阳", "汝南县", "汝南", "遂平县", "遂平", "新蔡县", "新蔡"
    ],
    "济源": [
        "济源", "济源市", "济源示范区", "济源产城融合示范区"
    ]
}

# 河南各级法院案号官方代字权威映射表 (豫01~豫17, 豫90)
HENAN_COURT_CODE_MAP = {
    "豫01": "郑州",
    "豫02": "开封",
    "豫03": "洛阳",
    "豫04": "平顶山",
    "豫05": "安阳",
    "豫06": "鹤壁",
    "豫07": "新乡",
    "豫08": "焦作",
    "豫09": "濮阳",
    "豫10": "许昌",
    "豫11": "漯河",
    "豫12": "三门峡",
    "豫13": "南阳",
    "豫14": "商丘",
    "豫15": "信阳",
    "豫16": "周口",
    "豫17": "驻马店",
    "豫90": "济源",
}

# 伪河南词汇（如外省市路名、街名、村名、以及青海省黄南州同名河南县），防止误判
PSEUDO_HENAN_WORDS = [
    "河南蒙古族自治县", "青海省黄南州河南县", "青海省河南县", "青海河南县", "河南县人民法院", "河南蒙古族",
    "滨河南", "河南路", "河南街", "河南村", "河南岸", "河南屯", "河南寨", "河南道", "河南里"
]

def _match_city_in_text(text: str) -> Optional[str]:
    """从单一文本片段中解析地市，优先匹配 18 地级市主名，杜绝字典序郑州抢占"""
    if not text:
        return None
    # 1. 优先匹配 18 地级市主名（如"洛阳"、"洛阳市"）
    for city in HENAN_CITIES.keys():
        if city in text or f"{city}市" in text:
            return city
    # 2. 次级匹配该市特色专属区县
    for city, kws in HENAN_CITIES.items():
        if any(kw in text for kw in kws):
            return city
    return None

def resolve_henan_city(court: str = "", title: str = "", content: str = "", case: str = "", parties: str = "") -> str:
    """按法院 > 标的物标题 > 正文与当事人的优先级确定归属地市，无具体市归为规范的'全省'"""
    # 1. 案号权威代字优先解析 (如豫0307 -> 豫03 -> 洛阳)
    if case:
        m = re.search(r'豫(0[1-9]|1[0-7]|90)', case)
        if m:
            code = f"豫{m.group(1)}"
            if code in HENAN_COURT_CODE_MAP:
                return HENAN_COURT_CODE_MAP[code]

    # 2. 法院所在地优先解析 (例如洛阳市洛龙区法院 -> 洛阳)
    c_city = _match_city_in_text(court)
    if c_city:
        return c_city

    # 3. 标的物标题与坐落解析 (例如位于洛阳市西工区房屋 -> 洛阳)
    t_city = _match_city_in_text(title)
    if t_city:
        return t_city

    # 4. 正文与当事人信息解析
    b_city = _match_city_in_text(f"{parties} {content}")
    if b_city:
        return b_city

    # 5. 省直管/省高院无具体地市时，统一规范为 "全省"
    return "全省"

def detect_henan_info(title: str = "", content: str = "", court_name: str = "", case_number: str = "", parties: str = "") -> Tuple[bool, Optional[str], Optional[str]]:
    """
    智能识别司法公示或法拍是否属于【河南省属地】或【全国跨域涉豫案件】
    返回: (is_henan, henan_city, henan_tag)
    """
    full_text = f"{title or ''} {content or ''} {parties or ''}"
    court = court_name or ""
    case = case_number or ""

    # 0. 排除青海同名“河南蒙古族自治县”等外省法院
    if any(k in court for k in ["河南蒙古族自治县", "青海省黄南", "青海河南县", "河南县人民法院"]):
        if "豫" not in case and "河南省" not in court:
            return False, None, None

    # 清理路名/街名等干扰词用于省份判断
    clean_text_for_prov = full_text
    for pw in PSEUDO_HENAN_WORDS:
        clean_text_for_prov = clean_text_for_prov.replace(pw, "")

    # 1. 优先判断案号是否为河南法院 (豫)
    if "豫" in case:
        city = resolve_henan_city(court=court, title=title, content=clean_text_for_prov, case=case, parties=parties)
        return True, city, "河南法院立案 (豫字号)"

    # 2. 判断执行法院/处置机构是否为河南省属地法院或省属机构
    court_clean = court
    for pw in PSEUDO_HENAN_WORDS:
        court_clean = court_clean.replace(pw, "")

    is_henan_court = False
    if "河南" in court_clean:
        is_henan_court = True
    elif any(city in court_clean or f"{city}市" in court_clean for city in HENAN_CITIES.keys()):
        is_henan_court = True
    elif any(any(kw in court_clean for kw in kws) for kws in HENAN_CITIES.values()):
        is_henan_court = True

    if is_henan_court:
        city = resolve_henan_city(court=court, title=title, content=clean_text_for_prov, case=case, parties=parties)
        return True, city, "河南属地机构审理/处置"

    # 3. 判断是否为全国外地法院处置河南资产或跨省涉豫当事人
    # 严格门槛：外省法院必须明确包含"河南"省名，或者出现明确的 18 地级市名称，或专属区县名称
    has_henan_prov = "河南" in clean_text_for_prov
    has_explicit_city = any(city in clean_text_for_prov for city in HENAN_CITIES.keys())
    specific_county_cities = [
        "巩义", "长垣", "林州", "永城", "邓州", "禹州", "汝州", "卫辉",
        "辉县", "沁阳", "孟州", "舞钢", "项城", "义马", "灵宝", "新密", "新郑", "登封", "郑东新区",
        "金水区", "二七区", "中原区", "管城区", "管城回族区", "惠济区", "上街区",
        "洛龙区", "涧西区", "西工区", "老城区", "瀍河区", "孟津区", "偃师区",
        "龙亭区", "顺河区", "顺河回族区", "禹王台区", "祥符区",
        "文峰区", "北关区", "殷都区", "龙安区", "淇滨区", "山城区", "鹤山区",
        "卫滨区", "红旗区", "凤泉区", "牧野区", "中站区", "马村区", "山阳区",
        "华龙区", "魏都区", "建安区", "源汇区", "郾城区", "召陵区", "湖滨区", "陕州区",
        "宛城区", "卧龙区", "梁园区", "睢阳区", "浉河区", "平桥区", "川汇区", "淮阳区", "驿城区",
        "中牟县", "中牟", "杞县", "通许县", "通许", "尉氏县", "尉氏", "兰考县", "兰考",
        "新安县", "新安", "栾川县", "栾川", "嵩县", "汝阳县", "汝阳", "宜阳县", "宜阳", "洛宁县", "洛宁", "伊川县", "伊川",
        "宝丰县", "宝丰", "叶县", "鲁山县", "鲁山", "郏县",
        "汤阴县", "汤阴", "滑县", "内黄县", "内黄", "浚县", "淇县",
        "获嘉县", "获嘉", "原阳县", "原阳", "延津县", "延津", "封丘县", "封丘",
        "修武县", "修武", "博爱县", "博爱", "武陟县", "武陟", "温县",
        "清丰县", "清丰", "南乐县", "南乐", "范县", "台前县", "台前",
        "鄢陵县", "鄢陵", "襄城县", "襄城", "舞阳县", "舞阳", "临颍县", "临颍",
        "渑池县", "渑池", "卢氏县", "卢氏",
        "南召县", "南召", "方城县", "方城", "西峡县", "西峡", "镇平县", "镇平", "内乡县", "内乡",
        "淅川县", "淅川", "社旗县", "社旗", "唐河县", "唐河", "桐柏县", "桐柏", "新野县", "新野",
        "民权县", "民权", "睢县", "宁陵县", "宁陵", "柘城县", "柘城", "虞城县", "虞城", "夏邑县", "夏邑",
        "罗山县", "罗山", "光山县", "光山", "新县人民法院", "商城县", "固始县", "固始", "潢川县", "潢川", "淮滨县", "淮滨", "息县",
        "扶沟县", "扶沟", "西华县", "西华", "商水县", "商水", "沈丘县", "沈丘", "郸城县", "郸城", "太康县", "太康", "鹿邑县", "鹿邑",
        "西平县", "西平", "上蔡县", "上蔡", "平舆县", "平舆", "正阳县", "正阳", "确山县", "确山", "泌阳县", "泌阳", "汝南县", "汝南", "遂平县", "遂平", "新蔡县", "新蔡"
    ]
    has_explicit_county = any(c in clean_text_for_prov for c in specific_county_cities)

    if has_henan_prov or has_explicit_city or has_explicit_county:
        city = resolve_henan_city(court=court, title=title, content=clean_text_for_prov, case=case, parties=parties)
        return True, city, f"全国跨域涉豫标的 (外地法院处置{city}资产/债务人)"

    return False, None, None

# 宣传类信息过滤黑名单
PROMO_KEYWORDS = [
    "新质生产力", "高质量发展", "总书记", "全面依法治国", "第一观察", "主题教育", 
    "思想", "精神文明", "党代会", "两会", "政府工作报告", "公勺公筷", "市民文明公约", 
    "文明公约", "自律公约", "倡议书", "全民阅读", "好书月享", "推荐书目", "健康教育", 
    "志愿服务", "座谈会", "调研", "宣誓仪式举行", "研讨会", "走访", "慰问", 
    "视察", "从“0”到“1”", "攻坚突围", "交响乐", "奏响", "耀赣鄱", "激情燃动", 
    "山乡公路", "秋色正好", "丹柿小院", "北平之秋", "愚公故里", "书香满城", 
    "两开放", "督查暗访", "情况通报", "典型案例", "表彰", "获奖", "活动安排", 
    "会风会纪", "意见征集", "民生实事建议", "公网安备", "版权声明", "法治周刊", 
    "彩票开奖", "关于停止销售", "体育彩票", "彩票", "打造内陆开放", "智能秒办", 
    "创新实践案例", "立案调查！", "警报试鸣", "事业单位公开招聘", "纠纷调解中心高效调处",
    "宣讲", "述职", "纪检举报", "学习贯彻", "心得体会", "文明创建", "社区风采",
    "备忘录", "迁飞通道", "跨域司法保护备忘录", "情暖", "福满", "救人", "挺身救人",
    "组织法", "居民委员会", "志愿", "跃迁", "法伴药乡", "法护沃野"
]

def is_promotional_content(title: str = "", content: str = "") -> bool:
    """判断是否属于政治宣传、政策宣讲、文明倡议、工作报道等宣传类信息"""
    text = f"{title or ''} {content or ''}"
    return any(k in text for k in PROMO_KEYWORDS)

def categorize_notice_module(title: str = "", content: str = "", notice_type: str = "", platform: str = "") -> str:
    """
    三大业务模块精准分类:
    1. 债权转让: 银行/AMC/企业不良债权、资产包、股权转让、产权债权等
    2. 拍卖公告: 司法拍卖、资产拍卖、成交公示、拍租、物资处置、罚没拍卖等
    3. 公告: 法院开庭传票、裁判文书送达、执行公告、破产清算等法定/司法公告
    """
    t = title or ""
    nt = notice_type or ""

    # 1. 债权转让
    credit_kws = ["债权", "不良资产", "资产包", "债权转让", "股权转让", "股权", "债权资产", "追偿", "抵押权"]
    if any(k in t for k in credit_kws) or any(k in nt for k in ["债权", "不良资产", "股权转让"]):
        return "债权转让"
    if ("转让公告" in t or "产权转让" in t or "出让公告" in t) and not any(k in t for k in ["拍卖", "拍租", "在拍"]):
        return "债权转让"

    # 2. 拍卖公告
    auction_kws = [
        "拍卖", "变卖", "在拍", "起拍", "成交公告", "结果公示", "拍租", "竞买", "竞价", 
        "报废车辆", "废旧物资", "车辆处置", "资产处置", "房屋拆除残值", "处置拍卖", "司法拍卖",
        "成交结果", "拍卖公告"
    ]
    if platform in ["ali", "jd", "caa"] or any(k in t or k in nt for k in auction_kws):
        return "拍卖公告"

    # 3. 兜底归类为 公告 (开庭传票/裁判送达/执行公告/破产重整/登报公告等)
    return "公告"

# 机动车辆排除关键词
VEHICLE_EXCLUDE_KEYWORDS = [
    "小型普通客车", "小型轿车", "越野客车", "普通客车", "越野车", "牵引车", "自卸车",
    "重型自卸", "重型货车", "轻型货车", "箱式货车", "厢式货车", "厢式车", "箱式车", "轻型厢式", "栏板货车",
    "轻型多用途货车", "半挂牵引车", "挂车", "半挂车", "搅拌车", "混凝土搅拌车", "冷藏车", "冷藏厢式", "散装水泥车",
    "面包车", "客运车", "大巴车", "中巴车", "大客车", "商务车", "跑车", "皮卡", "皮卡车", "摩托车", "电动车", "三轮车",
    "叉车", "装载机", "挖掘机", "推土机", "汽车一辆", "汽车1辆", "汽车2辆", "车辆一辆",
    "车辆1辆", "车辆2辆", "车辆4项", "两辆小型汽车", "小型汽车", "机动车", "轿车一辆",
    "轿车1辆", "客车一辆", "客车1辆", "货车一辆", "货车2台", "牵引车一辆", "牵引车公开竞价",
    "保时捷牌", "特斯拉牌", "宝马牌", "奔驰牌", "梅赛德斯-奔驰", "奥迪牌", "奥迪车",
    "本田牌", "丰田牌", "别克牌", "福特牌", "凯迪拉克", "大众牌", "比亚迪牌", "比亚迪车辆",
    "小鹏牌", "极狐牌", "腾势牌", "五菱牌", "长城牌", "徐工汽车", "重汽箱式货车", "解放牌",
    "解放天v", "东风牌", "天籁公爵车", "劳斯莱斯", "玛莎gt", "雷克萨斯牌", "报废处置丰田",
    "报废车辆", "车辆报废", "车辆处置", "报废汽车", "车一辆", "车1辆", "车2台", "车3台", "车4台", "车一台"
]

# 重型与大型设备及报废杂项排除关键词
EQUIPMENT_EXCLUDE_KEYWORDS = [
    "高空作业平台", "管带机", "自动化生产线", "加工流水线", "机器设备及电缆",
    "一批机器设备", "x射线诊断仪", "x光机专用工作站", "数控机床", "车床", "冲床",
    "铣床", "发电机组", "锅炉设备", "龙门吊", "塔吊", "行车设备", "压路机",
    "拌合站", "搅拌站", "石料开采加工生产线", "废旧设备", "报废设备", "废旧金属",
    "废旧物资", "废旧铅酸蓄电池", "报废固定资产", "报废资产", "报废家具", "质谱仪",
    "打捆机", "农机", "收割机", "推土机", "掘进机", "破碎机", "流水线设备"
]

# 核心不动产/司法文书/债权保护词（命中说明是不动产/文书/债权，绝不作为纯车辆或设备排除）
IMMOBILE_PROTECT_KEYWORDS = [
    "房屋", "房产", "住宅", "商品房", "公寓", "洋房", "别墅", "门面房", "门面", "门市房", "商铺", "铺面",
    "写字楼", "不动产", "土地使用权", "地块", "国有建设用地", "厂房", "车位", "车库",
    "人防车位", "地下室", "仓库", "林地", "宗地", "建筑物", "构筑物", "房地产及", "房产及", "房屋及",
    "传票", "送达", "判决", "裁定", "起诉状", "限消", "执行通知", "清算", "破产",
    "债权", "股权", "资产包", "借款", "应收账款"
]

def is_vehicle_or_equipment_item(title: str = "", content: str = "") -> bool:
    """
    智能判定是否为机动车辆或重型/大型机械设备。
    系统要求彻底过滤排除机动车辆与大型设备，专注于公告、法院公告、司法拍卖（不动产）与债权转让。
    规则：如果标的纯属车辆或机械设备，返回 True；如果有附带房产/土地或属于司法文书/债权，则返回 False。
    """
    if not title:
        return False
    t_lower = title.lower()

    # 1. 检查是否命中机动车辆
    has_vehicle = any(k in t_lower for k in VEHICLE_EXCLUDE_KEYWORDS)
    if not has_vehicle:
        # 车牌特征检测：如 豫A1826M、车牌号为粤BAM8886、晋E****1 等
        if re.search(r'(?:车牌号?为?|车牌|牌照)?[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Za-z0-9\*]{5,7}', title):
            if any(w in t_lower for w in ["车", "客车", "轿车", "汽车", "货车", "越野", "牌"]):
                has_vehicle = True

    # 2. 检查是否命中重型/大型设备
    has_equipment = any(k in t_lower for k in EQUIPMENT_EXCLUDE_KEYWORDS)
    if not has_equipment:
        if "机器设备" in t_lower or "机械设备" in t_lower or "生产线" in t_lower:
            has_equipment = True

    if not (has_vehicle or has_equipment):
        return False

    # 3. 剔除归属人公司名称中的“房地产/置业/建筑/开发”等干扰词用于不动产判定
    title_pure_target = re.sub(r'[\u4e00-\u9fa5]{2,30}(?:房地产|置业|建筑|建设|房产经纪|开发)[\w]*公司(?:名下|所属|查封)?', '', title)
    title_pure_target_lower = title_pure_target.lower()

    # 4. 检查是否为房产+设备合并处置或纯司法文书/债权
    has_immobile = any(k in title_pure_target_lower for k in IMMOBILE_PROTECT_KEYWORDS)
    if has_immobile:
        if any(k in title_pure_target_lower for k in ["房屋", "房产", "房地产", "住宅", "商品房", "厂房", "土地", "建设用地", "地块", "商铺", "门面", "建筑物", "车位", "车库"]):
            return False
        if any(k in title_pure_target_lower for k in ["传票", "送达", "判决", "裁定", "债权", "股权", "资产包"]):
            return False

    return True

async def launch_smart_browser(playwright_instance, headless: bool = True):
    """
    智能自适应启动浏览器：
    优先尝试 Windows 10/11 系统自带的 Microsoft Edge (channel="msedge")，
    次选 Google Chrome (channel="chrome")，最后回退至自带的 Chromium。
    使得打包成独立客户端发给对方电脑后，无需对方额外下载安装 200MB 的 Chromium 驱动即可直接运行！
    """
    # 1. 尝试系统自带 Edge (Windows 10/11 100% 自带)
    try:
        return await playwright_instance.chromium.launch(channel="msedge", headless=headless)
    except Exception:
        pass
    # 2. 尝试系统自带 Chrome
    try:
        return await playwright_instance.chromium.launch(channel="chrome", headless=headless)
    except Exception:
        pass
    # 3. 回退默认 Chromium
    return await playwright_instance.chromium.launch(headless=headless)

def extract_area_and_unit_price(title: str = "", content: str = "", starting_price: Optional[float] = None) -> Tuple[Optional[float], Optional[float]]:
    """
    智能提取房产建筑面积 (㎡) 并计算折合单价 (元/㎡)：
    优先从明确的「建筑面积/房屋面积/专有面积」匹配，次选「XX平方米/㎡」，
    结合起拍价 starting_price 换算真实单价，辅助投资客秒判性价比与剔除注水评估价。
    """
    corpus = f"{title or ''} {(content or '')[:800]}"
    area = None

    # 1. 明确关键词匹配面积
    area_patterns = [
        r'(?:建筑面积|套内面积|房屋面积|专有面积|产权面积|总面积|面积)\s*[：:为约]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:平方米|平方|平米|㎡|m2|m²)',
        r'([0-9]+(?:\.[0-9]+)?)\s*(?:平方米|平米|㎡|m2|m²)\s*(?:住宅|房屋|商品房|商铺|门面|公寓|写字楼|房产|房)',
        r'（\s*([0-9]+(?:\.[0-9]+)?)\s*(?:平方米|平米|㎡)\s*）',
        r'\(\s*([0-9]+(?:\.[0-9]+)?)\s*(?:平方米|平米|㎡)\s*\)'
    ]
    for pat in area_patterns:
        m = re.search(pat, corpus, re.IGNORECASE)
        if m:
            try:
                val = float(m.group(1))
                if 10.0 <= val <= 50000.0:
                    area = round(val, 2)
                    break
            except Exception:
                pass

    unit_price = None
    if area and starting_price and starting_price > 1000:
        unit_price = round(starting_price / area, 2)

    return area, unit_price

def extract_risk_tags(text: str) -> list[str]:
    """
    实战派法拍 10 大核心排雷矩阵（红黄绿分级警示）：
    🔴 致命红灯（清场死结/产权陷阱）：不负责清场、设立居住权、仅拍部分份额、划拨/集体土地、违建/无产证
    🟡 警惕黄灯（必须核减成本）：带租约、买受人全担税、垫付税费、欠费买受人承担、存在抵押
    🟢 安全绿灯（确定性加分项）：已腾空、无租约、税费各付、有产权证、法拍贷支持
    """
    if not text:
        return []
    tags = []

    # 1. 致命红灯：居住权 (《民法典》新规，终身无法腾退；排除“未设立居住权/无居住权”)
    if not re.search(r'无居住权|未设立居住权|未发现.*居住权|未登记居住权|暂无居住权', text):
        if re.search(r'已设立居住权|设有居住权|存在居住权|设立有居住权|设立居住权|被设立居住权', text):
            tags.append("设立居住权")

    # 2. 致命红灯：共有产权与部分份额拍卖 (无法独立变现处置)
    if re.search(r'拍卖.*(?:部分份额|50%|二分之一|1/2|共有份额)|共有产权|仅拍卖.*份额|部分产权|共有份额', text):
        tags.append("仅拍部分份额")

    # 3. 致命红灯：法院不负责清场 / 腾退责任转嫁
    if re.search(r'不负责腾退|不负责清场|买受人自行解决|买受人自行腾空|不负责交付|自行清场|自行腾退|不承担腾退|由买受人负责清场|由买受人自行与占用人协商|现状拍卖，自行解决', text):
        tags.append("不负责清场")
    elif re.search(r'未腾空|暂未腾空|尚未腾空|有人居住|被执行人居住|由被执行人使用|由案外人使用|有人占用|被执行人占用|占用中|暂不腾退|未搬离', text):
        tags.append("未腾空")
    elif re.search(r'已腾空|已清空|无障碍交割|房屋空置|现已空置|已搬空|现空置|法院负责腾空|法院负责清退', text):
        tags.append("已腾空")

    # 4. 致命红灯：土地性质风险（划拨土地需补天价出让金，集体土地无法过户）
    if re.search(r'划拨土地|土地性质为划拨|划拨地|划拨性质|集体土地|宅基地|集体建设用地|出让金由买受人承担|补缴土地出让金', text):
        tags.append("划拨/集体土地")

    # 5. 权证与违建情况
    if re.search(r'无产权证|无房产证|暂未办理产权证|未取得权属证书|未办理不动产权证|暂无房产证|无不动产权证|暂无不动产登记|违章建筑|违法建筑|未批先建|违建', text):
        tags.append("违建/无产证")
    elif re.search(r'不动产权证号|房产证号|房屋所有权证|权属证书号', text):
        tags.append("有产权证")

    # 6. 租赁占有情况（优先判定否定词“无租赁合同/未发现租赁”，防止被“租赁合同”子串误判）
    if re.search(r'无租[约赁]|未见租[约赁]|无承租人|未发现.*租赁|无租赁合同|未有租赁|无租赁|不带租', text):
        tags.append("无租约")
    elif re.search(r'带租[约赁]|有租[约赁]|存在租赁|租赁期至|有人承租|有租赁合同|存在租赁合同|承租期至|长租', text):
        tags.append("带租约")

    # 7. 税费与垫付陷阱
    if re.search(r'先行垫付|买受人垫付|垫付后|自行向原权利人追偿|凭票向法院退付|垫交|垫付税费', text):
        tags.append("垫付税费")
    elif re.search(r'买受人承担(?:全部|一切|所有)?税费|税费均由买受人|买受人全担税|全部税费由买受人|一切税费均?由买受人|由买受人承担.*税费|税费.*全部由买受人', text):
        tags.append("买受人全担税")
    elif re.search(r'税费各[自担付]|各自承担.*税费|各自缴[纳付]|各付税费|税费各自分担|税费由双方各自承担', text):
        tags.append("税费各付")

    # 8. 欠费转嫁
    if re.search(r'欠缴的物业|物业(?:欠)?费.*买受人|水电费.*买受人|欠费.*由?买受人|拖欠的物业|取暖费.*买受人|欠缴.*费用.*买受人', text):
        tags.append("欠费买受人承担")

    # 9. 抵押情况（排除“无抵押/未设有抵押”）
    if not re.search(r'无抵押|未设定抵押|未设立抵押|未设有抵押|未发现.*抵押', text):
        if re.search(r'存在抵押|设有抵押|已抵押登记|有抵押', text):
            tags.append("存在抵押")

    # 10. 法拍贷/按揭支持 (降低参拍门槛)
    if re.search(r'可申请贷款|支持贷款|法拍贷|按揭贷款|贷款须知|协助办理贷款', text):
        tags.append("法拍贷支持")

    return tags

def find_existing_notice(db, platform: str, raw_id: str, title: str, auction_stage: Optional[str] = None):
    """
    通用两级精准查重函数：
    1. 剥离平台前缀（如 sszc_、ali_、jd_、caa_、rmfyb_、hns_、sq_、zz_ 等）得到 pure_id，
       同时多路比对 CourtNotice.raw_id.in_([raw_id, pure_id, f"{platform}_{pure_id}", f"sszc_{pure_id}"])，
       彻底解决新旧版本 raw_id 前缀不一致导致的重复入库。
    2. 若 ID 未命中，再按 platform == platform 且 func.trim(CourtNotice.title) == title.strip() 
       且 (CourtNotice.auction_stage == auction_stage) 进行标题二次查重，防止跨城市关键词搜索重复入库同一房源。
    """
    from backend.models import CourtNotice
    from sqlalchemy import func, or_
    
    if db is None:
        return None

    clean_raw_id = str(raw_id or '').strip()
    clean_title = str(title or '').strip()
    clean_stage = str(auction_stage or '').strip() if auction_stage else None

    # 1. 前缀剥离与多路 raw_id 候选集匹配
    candidate_ids = set()
    if clean_raw_id:
        candidate_ids.add(clean_raw_id)
        pure_id = re.sub(r'^(sszc_|ali_|jd_|caa_|rmfyb_|hns_|sq_|zz_|lot_|paper_)', '', clean_raw_id)
        if pure_id:
            candidate_ids.add(pure_id)
            candidate_ids.add(f"{platform}_{pure_id}")
            candidate_ids.add(f"sszc_{pure_id}")
            candidate_ids.add(f"jd_{pure_id}")
            candidate_ids.add(f"caa_{pure_id}")
            candidate_ids.add(f"rmfyb_{pure_id}")
            candidate_ids.add(f"caa_lot_{pure_id}")

        existing = db.query(CourtNotice).filter(
            CourtNotice.platform == platform,
            CourtNotice.raw_id.in_(list(candidate_ids))
        ).first()
        if existing:
            return existing

    # 2. 标题与拍卖阶段二次严密查重
    if clean_title:
        q = db.query(CourtNotice).filter(
            CourtNotice.platform == platform,
            func.trim(CourtNotice.title) == clean_title
        )
        if clean_stage:
            q = q.filter(
                or_(
                    CourtNotice.auction_stage == clean_stage,
                    CourtNotice.auction_stage.is_(None)
                )
            )
        existing_title = q.first()
        if existing_title:
            return existing_title

    return None

