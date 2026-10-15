# -*- coding: utf-8 -*-
"""
河南省及各地级市公共资源交易平台 (GGZY) - 产权交易模块采集器
覆盖渠道：
1. 商丘市公共资源交易平台 (https://ggzyjy.shangqiu.gov.cn/HNSQ/TradeCenter/tradeList.do?Deal_Type=Deal_Type7)
   - 深度覆盖商丘市本级及睢阳区、梁园区、夏邑县、永城市、民权县等区县国有产权与罚没资产拍卖
2. 河南省公共资源交易中心 (https://hnsggzyjy.henan.gov.cn/jyxx/002003/transaction_notice.html)
   - 统筹汇聚河南省本级及全省18地市国有产权交易、股权转让、涉案财物/闲置资产处置
3. 郑州市公共资源交易中心 (https://zzggzy.zhengzhou.gov.cn/cqjy/subpage.html)
   - 覆盖省会郑州市及各区县行政企事业单位报废车辆、房产场地招租、废旧物资拍卖
"""
import urllib.request
import urllib.parse
import http.cookiejar
import ssl
import json
import re
import os
import subprocess
from datetime import datetime, timedelta

NO_WINDOW_FLAGS = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000) if os.name == 'nt' else 0
from typing import List, Tuple, Optional
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from backend.models import CourtNotice
from backend.utils import (
    detect_henan_info, HENAN_CITIES, is_promotional_content,
    categorize_notice_module, stable_hash, is_vehicle_or_equipment_item,
    parse_price_amount, extract_starting_and_eval_price, extract_bidding_times,
    find_existing_notice
)

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE
try:
    SSL_CTX.set_ciphers('DEFAULT@SECLEVEL=1')
except Exception:
    pass

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
}

def safe_curl_or_urllib(url: str, post_data: Optional[str] = None, headers: Optional[dict] = None, timeout: int = 12) -> str:
    """
    优先使用 curl.exe -k 发起网络请求；
    当 curl.exe 调用失败或异常时，自动优雅降级为原生 urllib.request（支持 DEFAULT@SECLEVEL=1 算法握手）
    """
    req_headers = {**HEADERS, **(headers or {})}
    try:
        cmd = ['curl.exe', '-k', '-s']
        if post_data is not None:
            cmd.extend(['-X', 'POST', '-d', post_data])
        for k, v in req_headers.items():
            cmd.extend(['-H', f"{k}: {v}"])
        cmd.append(url)
        return subprocess.check_output(cmd, timeout=timeout, creationflags=NO_WINDOW_FLAGS).decode('utf-8', errors='ignore')
    except Exception:
        data_bytes = post_data.encode('utf-8') if post_data is not None else None
        req = urllib.request.Request(url, data=data_bytes, headers=req_headers)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='ignore')

def extract_prices_and_times_from_html(html_content: str, title: str = "") -> Tuple[Optional[float], Optional[float], Optional[datetime], Optional[datetime]]:
    """从公共资源交易公告正文与HTML表格中智能提取起拍价/挂牌底价、评估价/参考价及竞价时间"""
    if not html_content:
        return None, None, None, None

    soup = BeautifulSoup(html_content, 'html.parser')
    sp, ep = None, None

    # 1. 解析 HTML 表格
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        sp_col, ep_col = -1, -1
        sp_unit, ep_unit = '', ''
        for r_idx, tr in enumerate(rows):
            cells = [td.get_text(strip=True) for td in tr.find_all(['th', 'td'])]
            if not cells:
                continue

            # 检测表头列
            for c_idx, cell in enumerate(cells):
                if any(k in cell for k in ['起拍价', '挂牌价', '出让价', '起始价', '底价', '成交价', '转让价', '租金', '年租金']):
                    sp_col = c_idx
                    if '万元' in cell or '万' in cell:
                        sp_unit = '万元'
                    elif '亿元' in cell or '亿' in cell:
                        sp_unit = '亿元'
                    elif '元' in cell:
                        sp_unit = '元'
                if any(k in cell for k in ['评估价', '评估值', '参考价', '评估总值']):
                    ep_col = c_idx
                    if '万元' in cell or '万' in cell:
                        ep_unit = '万元'
                    elif '亿元' in cell or '亿' in cell:
                        ep_unit = '亿元'
                    elif '元' in cell:
                        ep_unit = '元'

            # 如果是横向2列键值对表格（如 河南省公共资源: ['挂牌价（元）', '11998800.00 元']）
            if len(cells) == 2:
                k, v = cells[0], cells[1]
                if any(w in k for w in ['起拍价', '挂牌价', '出让价', '起始价', '底价', '成交价', '转让底价', '交易底价', '租金', '年租金']):
                    val = parse_price_amount(v)
                    if not val:
                        val = parse_price_amount(v + ('万元' if '万' in k else '元'))
                    if val and val > 100 and not sp:
                        sp = val
                if any(w in k for w in ['评估价', '评估值', '参考价', '评估总值']):
                    val = parse_price_amount(v)
                    if not val:
                        val = parse_price_amount(v + ('万元' if '万' in k else '元'))
                    if val and val > 100 and not ep:
                        ep = val
            # 如果是多列表格且定位到了列索引，提取后续数据行
            elif (sp_col != -1 or ep_col != -1) and r_idx + 1 < len(rows):
                for next_tr in rows[r_idx + 1:]:
                    dcells = [td.get_text(strip=True) for td in next_tr.find_all(['td', 'th'])]
                    if sp_col != -1 and sp_col < len(dcells) and not sp:
                        raw_v = dcells[sp_col]
                        m = re.search(r'([0-9]+(?:\.[0-9]+)?)', raw_v)
                        if m:
                            parsed = parse_price_amount(m.group(1) + (sp_unit or '元'))
                            if parsed and parsed > 100:
                                sp = parsed
                    if ep_col != -1 and ep_col < len(dcells) and not ep:
                        raw_v = dcells[ep_col]
                        m = re.search(r'([0-9]+(?:\.[0-9]+)?)', raw_v)
                        if m:
                            parsed = parse_price_amount(m.group(1) + (ep_unit or '元'))
                            if parsed and parsed > 100:
                                ep = parsed
                    if sp or ep:
                        break
        if sp or ep:
            break

    # 2. 从纯文本正则提取兜底
    text = soup.get_text('\n')
    usp, uep = extract_starting_and_eval_price(title, text)
    if not sp:
        sp = usp
    if not ep:
        ep = uep

    # 3. 提取竞价起止时间
    bs, be = extract_bidding_times(text)
    return sp, ep, bs, be

def fetch_shangqiu_cqjy(max_pages: int = 2) -> List[dict]:
    """抓取商丘市公共资源交易平台-产权交易模块 (国有产权、实物资产、罚没拍卖)"""
    results = []
    print("[ggzy_crawler] Fetching Shangqiu GGZY property transactions...")
    try:
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=SSL_CTX),
            urllib.request.HTTPCookieProcessor(cj)
        )
        init_url = 'https://ggzyjy.shangqiu.gov.cn/HNSQ/TradeCenter/tradeList.do?Deal_Type=Deal_Type7'
        opener.open(urllib.request.Request(init_url, headers=HEADERS), timeout=10)

        post_headers = {
            'User-Agent': HEADERS['User-Agent'],
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': init_url,
            'X-Requested-With': 'XMLHttpRequest',
        }

        today_str = datetime.now().strftime("%Y-%m-%d")
        begin_str = (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d")
        # 抓取 noticType=1 (转让公告) 和 noticType=3 (结果公告)，放宽至近15天覆盖完整时间纵深
        for notic_type in ['1', '3']:
            for p in range(1, max_pages + 1):
                body = (
                    f"projectName=&date=&begin_time={begin_str}&end_time={today_str}&begin_time2=&end_time2="
                    f"&dealType=Deal_Type7&noticType={notic_type}&area=&huanJie=NOTICE&pageIndex={p}"
                )
                req = urllib.request.Request(
                    'https://ggzyjy.shangqiu.gov.cn/HNSQ/TradeCenter/ColTableInfo.do?',
                    data=body.encode('utf-8'),
                    headers=post_headers
                )
                try:
                    with opener.open(req, timeout=10) as resp:
                        html = resp.read().decode('utf-8', errors='ignore')
                        soup = BeautifulSoup(html, 'html.parser')
                        rows = soup.find_all('tr')
                        for tr in rows:
                            try:
                                a = tr.find('a')
                                if not a:
                                    continue
                                title = a.get_text(strip=True)
                                href = a.get('href', '').strip()
                                if not href:
                                    continue
                                if is_vehicle_or_equipment_item(title):
                                    continue
                                detail_url = f"https://ggzyjy.shangqiu.gov.cn{href}" if href.startswith('/') else href

                                # 提取 raw_id
                                id_m = re.search(r'id=([a-zA-Z0-9\-]+)', href)
                                raw_id = f"sq_{id_m.group(1)}" if id_m else f"sq_{stable_hash(title)}"

                                tds = [td.get_text(strip=True) for td in tr.find_all('td')]
                                district = tds[2] if len(tds) > 2 else "商丘市"
                                date_str = tds[3] if len(tds) > 3 else ""

                                try:
                                    pub_time = datetime.strptime(date_str, "%Y-%m-%d")
                                except Exception:
                                    pub_time = None

                                # 时效门禁校验：放宽至 15 天以完整覆盖近半个月公告
                                if pub_time is not None:
                                    days_diff = (datetime.now() - pub_time).total_seconds() / 86400.0
                                    if days_diff > 15.0:
                                        continue

                                # 穿透详情页抓取起拍价、评估价及竞价时间
                                sp, ep, bs, be = None, None, None, None
                                try:
                                    d_req = urllib.request.Request(detail_url, headers=HEADERS)
                                    with opener.open(d_req, timeout=6) as d_resp:
                                        d_html = d_resp.read().decode('utf-8', errors='ignore')
                                        sp, ep, bs, be = extract_prices_and_times_from_html(d_html, title)
                                except Exception:
                                    pass

                                type_name = "转让/挂牌公告" if notic_type == '1' else "成交结果公告"
                                content_text = (
                                    f"【全国公共资源交易平台（河南省·商丘市）·国有产权交易】\n"
                                    f"公告名称：{title}\n"
                                    f"所属管辖：河南省商丘市（{district}）\n"
                                    f"公告类别：{type_name}\n"
                                    f"发布日期：{date_str}\n"
                                )
                                if sp:
                                    content_text += f"起拍/挂牌价：¥{sp:,.2f} 元\n"
                                if ep:
                                    content_text += f"评估/参考价：¥{ep:,.2f} 元\n"
                                if bs:
                                    content_text += f"竞价开始：{bs.strftime('%Y-%m-%d %H:%M:%S')}\n"
                                if be:
                                    content_text += f"竞价截止：{be.strftime('%Y-%m-%d %H:%M:%S')}\n"
                                content_text += (
                                    f"交易平台：商丘市公共资源交易平台\n"
                                    f"查看原始公告：{detail_url}"
                                )

                                results.append({
                                    "raw_id": raw_id,
                                    "court_name": f"商丘市公共资源交易平台 ({district})",
                                    "case_number": "",
                                    "parties": "",
                                    "notice_type": f"公共资源产权交易·{type_name}",
                                    "title": title,
                                    "content_text": content_text,
                                    "publish_time": pub_time,
                                    "source_url": detail_url,
                                    "starting_price": round(sp, 2) if sp is not None else None,
                                    "eval_price": round(ep, 2) if ep is not None else None,
                                    "bidding_start": bs,
                                    "bidding_end": be,
                                    "is_henan": True,
                                    "henan_city": "商丘",
                                    "henan_tag": f"公共资源产权交易 (商丘市·{district})"
                                })
                            except Exception:
                                continue
                except Exception as e:
                    print(f"[ggzy_crawler] Shangqiu page {p} error: {e}")
                    break
    except Exception as e:
        print(f"[ggzy_crawler] Shangqiu fetch failed: {e}")

    print(f"[ggzy_crawler] Shangqiu fetched {len(results)} notices.")
    return results

def fetch_henan_provincial_cqjy(page_size: int = 30, kw: str = "") -> List[dict]:
    """抓取河南省公共资源交易中心-全省产权交易大盘 (覆盖全省18地市)"""
    results = []
    print(f"[ggzy_crawler] Fetching Henan Provincial GGZY all-cities property transactions (kw='{kw}')...")
    try:
        url = 'https://hnsggzyjy.henan.gov.cn/EpointWebBuilder/rest/frontAppCustomAction/getPageInfoListNewYzm'
        post_data = (
            f"siteGuid=7eb5f7f1-9041-43ad-8e13-8fcb82ea831a&categoryNum=002003"
            f"&kw={kw}&startDate=&endDate=&pageIndex=0&pageSize={page_size}&jytype=&YZM=&ImgGuid=&xiaqucode="
        )
        req_headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': 'https://hnsggzyjy.henan.gov.cn/jyxx/002003/transaction_notice.html'
        }
        out = safe_curl_or_urllib(url, post_data=post_data, headers=req_headers, timeout=12)
        data = json.loads(out)
        items = data.get('custom', {}).get('infodata', [])

        for it in items:
            try:
                infoid = it.get('infoid')
                if not infoid:
                    continue
                title = it.get('title', '').strip()
                if not title or is_vehicle_or_equipment_item(title):
                    continue
                date_str = it.get('infodate', '')
                xiaquname = it.get('xiaquname') or ""
                cat_name = it.get('categoryname') or "产权交易"
                infourl = it.get('infourl', '')
                detail_url = f"https://hnsggzyjy.henan.gov.cn{infourl}" if infourl.startswith('/') else infourl

                try:
                    pub_time = datetime.strptime(date_str, "%Y-%m-%d")
                except Exception:
                    pub_time = None

                # 时效门禁校验：放宽至 15 天以完整覆盖近半个月公告
                if pub_time is not None:
                    days_diff = (datetime.now() - pub_time).total_seconds() / 86400.0
                    if days_diff > 15.0:
                        continue

                # 穿透详情页抓取起拍价、评估价及竞价时间（优先curl，自动降级urllib）
                sp, ep, bs, be = None, None, None, None
                try:
                    d_html = safe_curl_or_urllib(detail_url, timeout=12)
                    if d_html:
                        sp, ep, bs, be = extract_prices_and_times_from_html(d_html, title)
                except Exception:
                    pass

                content_text = (
                    f"【河南省公共资源交易中心·全省产权交易大盘】\n"
                    f"项目名称：{title}\n"
                    f"所属辖区：{xiaquname or '河南省本级'}\n"
                    f"业务分类：{cat_name}\n"
                    f"发布日期：{date_str}\n"
                )
                if sp:
                    content_text += f"起拍/挂牌价：¥{sp:,.2f} 元\n"
                if ep:
                    content_text += f"评估/参考价：¥{ep:,.2f} 元\n"
                if bs:
                    content_text += f"竞价开始：{bs.strftime('%Y-%m-%d %H:%M:%S')}\n"
                if be:
                    content_text += f"竞价截止：{be.strftime('%Y-%m-%d %H:%M:%S')}\n"
                content_text += (
                    f"发布机构：河南省公共资源交易中心\n"
                    f"官方详情：{detail_url}"
                )

                # 智能地市识别
                city = None
                city_keywords = {
                    "郑州": ["郑州", "花花牛", "老君堂", "嵩山", "登封", "新郑", "巩义", "中牟", "荥阳", "新密"],
                    "开封": ["开封", "杞县", "通许", "尉氏", "兰考"],
                    "洛阳": ["洛阳", "汇晶", "栾川", "嵩县", "汝阳", "宜阳", "洛宁", "伊川", "新安", "偃师"],
                    "平顶山": ["平顶山", "中安贸易", "汝州", "舞钢", "鲁山", "宝丰", "叶县", "郏县"],
                    "安阳": ["安阳", "林州", "滑县", "内黄", "汤阴"],
                    "鹤壁": ["鹤壁", "鹤煤", "浚县", "淇县"],
                    "新乡": ["新乡", "卫辉", "辉县", "获嘉", "原阳", "延津", "封丘"],
                    "焦作": ["焦作", "沁阳", "孟州", "修武", "博爱", "武陟", "温县"],
                    "濮阳": ["濮阳", "清丰", "南乐", "范县", "台前"],
                    "许昌": ["许昌", "禹州", "长葛", "鄢陵", "襄城"],
                    "漯河": ["漯河", "诚尚", "舞阳", "临颍"],
                    "三门峡": ["三门峡", "义马", "灵宝", "渑池", "卢氏", "陕州"],
                    "南阳": ["南阳", "邓州", "南召", "镇平", "内乡", "淅川", "社旗", "唐河", "方城", "西峡"],
                    "商丘": ["商丘", "永城", "睢阳", "梁园", "民权", "睢县", "宁陵", "柘城", "虞城", "夏邑"],
                    "信阳": ["信阳", "罗山", "光山", "新县", "商城", "固始", "潢川", "淮滨", "息县"],
                    "周口": ["周口", "益海嘉里", "项城", "扶沟", "西华", "商水", "沈丘", "郸城", "淮阳", "太康", "鹿邑"],
                    "驻马店": ["驻马店", "确山", "泌阳", "遂平", "西平", "上蔡", "汝南", "平舆", "正阳", "新蔡"],
                    "济源": ["济源"]
                }
                for c_name, kws in city_keywords.items():
                    if any(k in (xiaquname or '') or k in title for k in kws):
                        city = c_name
                        break
                if not city:
                    is_hn, matched_city, _ = detect_henan_info(title=title, content=content_text)
                    city = matched_city or "全省"

                # 严格甄别新疆哈密（伊州区、伊吾县、巴里坤县）跨域援建/共享标的
                is_hami = any(k in title or k in (xiaquname or '') for k in ['新疆', '哈密', '伊州', '伊吾', '巴里坤'])
                if is_hami:
                    is_henan = False
                    henan_city = None
                    henan_tag = None
                    court_display = "河南省公共资源交易中心 (哈密)"
                else:
                    is_henan = True
                    henan_city = city
                    henan_tag = f"公共资源产权交易 ({city}·{cat_name})"
                    court_display = f"河南省公共资源交易中心 ({city})"

                # 价格精度与倒置研判
                clean_sp = round(sp, 2) if sp is not None else None
                clean_ep = round(ep, 2) if ep is not None else None
                if clean_sp is not None and clean_ep is not None:
                    if clean_sp == clean_ep:
                        clean_ep = None
                    elif clean_sp > clean_ep:
                        # 挂牌底价与评估价倒置时进行纠正
                        clean_sp, clean_ep = clean_ep, clean_sp

                results.append({
                    "raw_id": f"hns_{infoid}",
                    "court_name": court_display,
                    "case_number": "",
                    "parties": "",
                    "notice_type": f"公共资源产权交易·{cat_name}",
                    "title": title,
                    "content_text": content_text,
                    "publish_time": pub_time,
                    "source_url": detail_url,
                    "starting_price": clean_sp,
                    "eval_price": clean_ep,
                    "bidding_start": bs,
                    "bidding_end": be,
                    "is_henan": is_henan,
                    "henan_city": henan_city,
                    "henan_tag": henan_tag
                })
            except Exception:
                continue
    except Exception as e:
        print(f"[ggzy_crawler] Henan Provincial fetch failed: {e}")

    print(f"[ggzy_crawler] Henan Provincial fetched {len(results)} notices.")
    return results

def fetch_zhengzhou_cqjy(page_size: int = 25) -> List[dict]:
    """抓取郑州市公共资源交易中心-产权交易板块"""
    results = []
    print("[ggzy_crawler] Fetching Zhengzhou GGZY property transactions...")
    try:
        url = 'https://zzggzy.zhengzhou.gov.cn/inteligentsearch/rest/esinteligentsearch/getFullTextDataNew'
        payload = {
            "esdsid": "1",
            "token": "",
            "pn": 0,
            "rn": page_size,
            "sdt": "",
            "edt": "",
            "wd": "%20",
            "inc_wd": "",
            "exc_wd": "",
            "fields": "title",
            "cnum": "012",
            "sort": "{\"webdate\":\"0\"}",
            "ssort": "title",
            "cl": 1000,
            "cutIngore": "title;linkurl",
            "terminal": "",
            "condition": [{"fieldName": "categorynum", "equal": "018", "notEqual": None, "equalList": None, "notEqualList": None, "isLike": True, "likeType": 2}],
            "time": [],
            "highlights": "title;searchtitle",
            "statistics": None,
            "unionCondition": None,
            "accuracy": "",
            "noParticiple": "1",
            "searchRange": [],
            "isBusiness": "1"
        }
        req_headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': 'https://zzggzy.zhengzhou.gov.cn/cqjy/subpage.html'
        }
        out = safe_curl_or_urllib(url, post_data=json.dumps(payload), headers=req_headers, timeout=12)
        data = json.loads(out)
        records = data.get('result', {}).get('records', [])

        for r in records:
            try:
                infoid = r.get('infoid')
                if not infoid:
                    continue
                title = r.get('title', '').strip()
                if not title or is_vehicle_or_equipment_item(title):
                    continue
                date_str = (r.get('infodate') or r.get('webdate') or '')[:10]
                linkurl = r.get('linkurl', '')
                detail_url = f"https://zzggzy.zhengzhou.gov.cn{linkurl}" if linkurl.startswith('/') else linkurl
                raw_content = r.get('content', '')

                try:
                    pub_time = datetime.strptime(date_str, "%Y-%m-%d")
                except Exception:
                    pub_time = None

                # 时效门禁校验：放宽至 15 天以完整覆盖近半个月公告
                if pub_time is not None:
                    days_diff = (datetime.now() - pub_time).total_seconds() / 86400.0
                    if days_diff > 15.0:
                        continue

                # 提取挂牌价格 / 成交价格及竞价时间
                sp, ep, bs, be = extract_prices_and_times_from_html(raw_content, title)

                content_text = (
                    f"【郑州市公共资源交易中心·产权交易】\n"
                    f"公告名称：{title}\n"
                    f"发布日期：{date_str}\n"
                )
                if sp:
                    content_text += f"起拍/挂牌价：¥{sp:,.2f} 元\n"
                if ep:
                    content_text += f"评估/参考价：¥{ep:,.2f} 元\n"
                if bs:
                    content_text += f"竞价开始：{bs.strftime('%Y-%m-%d %H:%M:%S')}\n"
                if be:
                    content_text += f"竞价截止：{be.strftime('%Y-%m-%d %H:%M:%S')}\n"
                content_text += (
                    f"主要内容：{raw_content[:300]}...\n"
                    f"交易平台：郑州市公共资源交易中心\n"
                    f"查看原始公告：{detail_url}"
                )

                results.append({
                    "raw_id": f"zz_{infoid}",
                    "court_name": "郑州市公共资源交易中心",
                    "case_number": "",
                    "parties": "",
                    "notice_type": "公共资源产权交易·车辆/物资/资产处置",
                    "title": title,
                    "content_text": content_text,
                    "publish_time": pub_time,
                    "source_url": detail_url,
                    "starting_price": round(sp, 2) if sp is not None else None,
                    "eval_price": round(ep, 2) if ep is not None else None,
                    "bidding_start": bs,
                    "bidding_end": be,
                    "is_henan": True,
                    "henan_city": "郑州",
                    "henan_tag": "公共资源产权交易 (郑州市)"
                })
            except Exception:
                continue
    except Exception as e:
        print(f"[ggzy_crawler] Zhengzhou fetch failed: {e}")

    print(f"[ggzy_crawler] Zhengzhou fetched {len(results)} notices.")
    return results

from backend.database import SessionLocal

def crawl_ggzy_publicity(db: Optional[Session] = None, max_items: int = 80) -> Tuple[List[CourtNotice], int]:
    """
    全量抓取河南省及各地级市公共资源交易平台产权交易信息：
    包含商丘专属专线 + 河南省本级统筹专线 + 郑州市级专线
    """
    print("[ggzy_crawler] Starting GGZY property transactions crawl across Henan...")
    all_raw: List[dict] = []

    # 1. 商丘公共资源交易平台 (用户指定重点平台)
    sq_items = fetch_shangqiu_cqjy(max_pages=2)
    all_raw.extend(sq_items)

    # 2. 河南省公共资源交易中心 (全省统筹大盘 + 专项全省债权资产)
    hn_items = fetch_henan_provincial_cqjy(page_size=25)
    all_raw.extend(hn_items)
    hn_debt_items = fetch_henan_provincial_cqjy(page_size=20, kw="%E5%80%BA%E6%9D%83")
    all_raw.extend(hn_debt_items)

    # 3. 郑州市公共资源交易中心 (省会重点)
    zz_items = fetch_zhengzhou_cqjy(page_size=20)
    all_raw.extend(zz_items)

    # 入库
    new_records: List[CourtNotice] = []
    seen_raw_ids = set()

    close_when_done = False
    if db is None:
        db = SessionLocal()
        close_when_done = True

    try:
        for item in all_raw:
            # 严格过滤宣传类以及机动车辆、重型和大型机械设备
            if is_promotional_content(item["title"], item["content_text"]):
                continue
            if is_vehicle_or_equipment_item(item["title"], item["content_text"]):
                continue

            raw_id = item["raw_id"]
            if raw_id in seen_raw_ids:
                continue
            seen_raw_ids.add(raw_id)

            mod_type = categorize_notice_module(item["title"], item["content_text"], item["notice_type"], "ggzy")

            # 细分大宗类别
            cat = "国有产权/资产拍卖"
            t_str = item["title"]
            if any(k in t_str for k in ["债权", "股权", "不良资产", "资产包"]):
                cat = "金融债权与股权"
            elif any(k in t_str for k in ["地块", "土地", "厂房", "仓库", "工业园"]):
                cat = "工业厂房与土地"
            elif any(k in t_str for k in ["房", "室", "楼", "门面", "商铺", "大厦", "公寓"]):
                cat = "住宅/商业房产"

            existing = find_existing_notice(db, "ggzy", raw_id, item["title"], item.get("auction_stage"))
            if existing:
                existing.module_type = mod_type
                existing.asset_category = cat
                if item.get("starting_price") is not None:
                    existing.starting_price = item["starting_price"]
                if item.get("eval_price") is not None:
                    existing.eval_price = item["eval_price"]
                if item.get("bidding_start") is not None:
                    existing.bidding_start = item["bidding_start"]
                if item.get("bidding_end") is not None:
                    existing.bidding_end = item["bidding_end"]
                continue

            notice = CourtNotice(
                platform="ggzy",
                raw_id=raw_id,
                court_name=item["court_name"],
                case_number=item.get("case_number", ""),
                parties=item.get("parties", ""),
                notice_type=item["notice_type"],
                module_type=mod_type,
                title=item["title"],
                content_text=item["content_text"],
                publish_time=item["publish_time"],
                source_url=item["source_url"],
                starting_price=item.get("starting_price"),
                eval_price=item.get("eval_price"),
                auction_stage=item.get("auction_stage"),
                asset_category=cat,
                bidding_start=item.get("bidding_start"),
                bidding_end=item.get("bidding_end"),
                is_henan=item.get("is_henan", True),
                henan_city=item.get("henan_city", "商丘"),
                henan_tag=item.get("henan_tag", "公共资源产权交易")
            )
            db.add(notice)
            new_records.append(notice)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[ggzy_crawler] Commit error: {e}")
        return [], len(all_raw)
    finally:
        if close_when_done:
            db.close()

    print(f"[ggzy_crawler] GGZY crawl finished: Scraped {len(all_raw)}, Newly ingested: {len(new_records)}")
    return new_records, len(all_raw)

if __name__ == "__main__":
    from backend.database import SessionLocal
    db = SessionLocal()
    notices, count = crawl_ggzy_publicity(db)
    print(f"Test run completed. Total: {len(notices)}, New: {count}")
    db.close()
