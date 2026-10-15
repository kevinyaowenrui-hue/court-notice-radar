# -*- coding: utf-8 -*-
"""
京东拍卖/资产真实采集器 (JD Auction Live Crawler)
来源: https://pmsearch.jd.com / https://paimai.jd.com / https://zichan.jd.com
重点聚焦司法房产、金融债权、企业破产清算与法院公告，彻底过滤衣服、鞋帽、洋酒等日用小物件
"""
import asyncio
import json
import re
from datetime import datetime
from typing import List, Tuple, Optional
from playwright.async_api import async_playwright
from sqlalchemy.orm import Session
from backend.models import CourtNotice
from backend.utils import (
    stable_hash, run_async, detect_henan_info, categorize_notice_module,
    HENAN_CITIES, is_vehicle_or_equipment_item, launch_smart_browser,
    extract_judicial_case_number, find_existing_notice
)

# 常用地市法院映射辅助
HENAN_DISTRICTS = {
    "金水": "郑州市金水区人民法院",
    "二七": "郑州市二七区人民法院",
    "中原": "郑州市中原区人民法院",
    "管城": "郑州市管城回族区人民法院",
    "惠济": "郑州市惠济区人民法院",
    "上街": "郑州市上街区人民法院",
    "中牟": "中牟县人民法院",
    "巩义": "巩义市人民法院",
    "荥阳": "荥阳市人民法院",
    "新密": "新密市人民法院",
    "新郑": "新郑市人民法院",
    "登封": "登封市人民法院",
    "航空港": "郑州航空港经济综合实验区人民法院",
    "高新": "郑州高新技术产业开发区人民法院",
    "经开": "郑州经济技术开发区人民法院",
    "洛龙": "洛阳市洛龙区人民法院",
    "涧西": "洛阳市涧西区人民法院",
    "西工": "洛阳市西工区人民法院",
    "老城": "洛阳市老城区人民法院",
    "瀍河": "洛阳市瀍河回族区人民法院",
    "偃师": "洛阳市偃师区人民法院",
    "孟津": "洛阳市孟津区人民法院",
    "新安": "新安县人民法院",
    "伊川": "伊川县人民法院",
    "宜阳": "宜阳县人民法院",
    "汝阳": "汝阳县人民法院",
    "洛宁": "洛宁县人民法院",
    "栾川": "栾川县人民法院",
    "嵩县": "嵩县人民法院",
    "淇滨": "鹤壁市淇滨区人民法院",
    "山城": "鹤壁市山城区人民法院",
    "鹤山": "鹤壁市鹤山区人民法院",
    "浚县": "浚县人民法院",
    "淇县": "淇县人民法院",
    "文峰": "安阳市文峰区人民法院",
    "北关": "安阳市北关区人民法院",
    "殷都": "安阳市殷都区人民法院",
    "龙安": "安阳市龙安区人民法院",
    "林州": "林州市人民法院",
    "滑县": "滑县人民法院",
    "汤阴": "汤阴县人民法院",
    "内黄": "内黄县人民法院",
    "鼓楼": "开封市鼓楼区人民法院",
    "龙亭": "开封市龙亭区人民法院",
    "顺河": "开封市顺河回族区人民法院",
    "禹王台": "开封市禹王台区人民法院",
    "祥符": "开封市祥符区人民法院",
    "兰考": "兰考县人民法院",
    "杞县": "杞县人民法院",
    "通许": "通许县人民法院",
    "尉氏": "尉氏县人民法院",
    "魏都": "许昌市魏都区人民法院",
    "建安": "许昌市建安区人民法院",
    "禹州": "禹州市人民法院",
    "长葛": "长葛市人民法院",
    "鄢陵": "鄢陵县人民法院",
    "襄城": "襄城县人民法院",
    "川汇": "周口市川汇区人民法院",
    "淮阳": "周口市淮阳区人民法院",
    "项城": "项城市人民法院",
    "西华": "西华县人民法院",
    "商水": "商水县人民法院",
    "太康": "太康县人民法院",
    "鹿邑": "鹿邑县人民法院",
    "郸城": "郸城县人民法院",
    "沈丘": "沈丘县人民法院",
    "扶沟": "扶沟县人民法院",
}

# 核心大宗资产关键词保护列表（绝不误杀）
CORE_ASSET_PROTECTED_KEYWORDS = [
    "房", "室", "楼", "住宅", "公寓", "洋房", "别墅", "门面", "门市", "商铺", "铺面",
    "写字楼", "不动产", "土地", "地块", "工业园", "厂房", "仓库", "车位", "车库", "人防车位", "地下室",
    "债权", "股权", "股份", "证券", "借款", "破产", "清算", "重整", "追偿权", "收益权", "应收账款"
]

# 法院诉讼行为词保护（确保司法裁判和开庭文书不被误拦截）
COURT_LITIGATION_WORDS = [
    "开庭传票", "送达", "裁判文书", "判决书", "起诉状", "答辩状", "执行通知", 
    "异议", "财产保全", "执行裁定", "终结执行", "拍卖公告"
]

# 日用小件与小物件过滤黑名单关键词（彻底拦截过滤）
TRIVIAL_ITEM_KEYWORDS = [
    # 衣服与鞋帽箱包
    "服饰", "服装", "衣服", "女装", "男装", "童装", "内衣", "短裤",
    "t恤", "大衣", "羽绒服", "外套", "西装", "西服", "衬衫", "毛衣", "针织衫", "裤",
    "皮带", "腰带", "围巾", "丝巾", "手套", "帽子", "鞋", "高跟鞋", "皮鞋", "运动鞋", "女鞋", "男鞋",
    "包", "女包", "男包", "手袋", "单肩包", "双肩包", "手提包", "斜挎包", "钱包", "卡包", "皮夹", "箱包",
    "奢侈品", "皮草", "貂皮", "prada", "gucci", "chanel", "louis vuitton", "givenchy", "balenciaga", "dior",
    "hermes", "fendi", "burberry", "versace", "armani", "celine", "loewe", "bottega", "mcm",
    "saint laurent", "ysl", "圣罗兰", "普拉达", "纪梵希", "巴黎世家", "路易威登", "香奈儿", "爱马仕",
    "古驰", "迪奥", "芬迪", "博柏利", "蔻驰", "coach", "罗杰维维亚", "roger vivier",
    # 珠宝首饰与腕表配饰
    "项链", "吊坠", "手镯", "手串", "手链", "耳钉", "耳环", "戒指", "指环", "首饰", "珠宝", "钻石",
    "翡翠", "和田玉", "蜜蜡", "琥珀", "玛瑙", "金条", "黄金首饰", "足金", "18k", "白银", "手表",
    "腕表", "劳力士", "欧米茄", "浪琴", "天梭", "卡地亚", "百达翡丽", "江诗丹顿",
    # 酒水与食品烟茶滋补品
    "白兰地", "威士忌", "人头马", "马爹利", "轩尼诗", "xo", "白酒", "红酒", "洋酒", "葡萄酒",
    "茅台", "五粮液", "剑南春", "泸州老窖", "郎酒", "汾酒", "习酒", "洋河", "董酒", "古井贡",
    "啤酒", "茶叶", "普洱", "铁观音", "茶行", "茶饼", "散料", "粮油", "香烟", "雪茄", "饮料",
    "燕窝", "虫草", "冬虫夏草", "人参", "海参", "阿胶", "滋补品",
    # 个人消费电子与小家电
    "手机", "iphone", "华为手机", "荣耀手机", "小米手机", "vivo", "oppo", "平板", "ipad",
    "耳机", "airpods", "相机", "单反", "镜头", "微单", "无人机", "大疆", "游戏机", "switch",
    "ps5", "xbox", "手办", "玩具", "吹风机", "剃须刀", "电饭煲", "微波炉", "吸尘器",
    # 日化与洗护用品
    "洗发水", "沐浴露", "洗发露", "洗护", "日化", "牙膏", "洗衣液", "洗洁精", "纸巾", "抽纸",
    # 日用杂货与散杂物资
    "办公杂物", "散杂物品", "二手旧衣", "办公桌椅", "餐具", "茶具", "被褥", "床上用品", "化妆品", "香水"
]

def is_trivial_consumer_item(title: str, house_attrs: dict = None, notice_type: str = "资产/司法拍卖") -> bool:
    """判定是否为服饰、鞋帽、酒水、数码、日化等日用散杂小物件或倒计时状态标签（此类标的完全过滤不入库）"""
    if not title:
        return True
    
    title_lower = title.lower()

    # 0. 过滤倒计时与非标的文本
    if any(k in title_lower for k in ["预计今日", "预计", "后结束", "即将开始", "正在进行", "距离结束"]):
        if not any(k in title_lower for k in ["房", "债", "地", "拍卖"]):
            return True

    # 1. 司法诉讼文书/法院公告绝不判定为小物件
    for clw in COURT_LITIGATION_WORDS:
        if clw in title_lower:
            return False

    if notice_type and any(k in notice_type for k in ["公告", "传票", "文书", "破产", "执行", "清算", "立案"]):
        if not any(k in notice_type for k in ["拍卖", "变卖"]):
            return False

    # 2. 如果有明确的房产属性（面积、房屋用途），绝不判定为小物件
    if house_attrs and (house_attrs.get("houseArea") or house_attrs.get("housePurpose")):
        return False

    # 3. 保护大宗核心资产（房产、土地、债权、车辆）
    for core in CORE_ASSET_PROTECTED_KEYWORDS:
        if core in title_lower:
            return False

    # 4. 检查是否命中日用小物件黑名单
    for kw in TRIVIAL_ITEM_KEYWORDS:
        if kw in title_lower:
            return True

    return False

def infer_court_and_disposer(title: str, city: str, province: str) -> Tuple[str, str]:
    """根据标的标题及地市智能推断所属法院或处置机构"""
    # 标题直接包含法院
    court_m = re.search(r'([^\s，。、（]{2,10}(?:人民法院|中级人民法院|中院|法庭))', title)
    if court_m:
        return court_m.group(1), court_m.group(1)

    # 区县匹配
    for district, court_name in HENAN_DISTRICTS.items():
        if district in title:
            return court_name, court_name

    # 地市匹配
    if city:
        clean_city = city.replace("市", "").strip()
        if clean_city in HENAN_CITIES:
            return f"{clean_city}市中级人民法院及辖区法院", f"{clean_city}市属地法院/金融机构"

    if province and "河南" in province:
        return "河南省辖区人民法院/金融处置机构", "河南省各级处置机构"

    return "人民法院/金融资产处置机构", "处置机构"

def fetch_jd_notice_detail(notice_id: str) -> dict:
    """通过京东官方接口获取公告详情，补全真实起拍价、评估价、真实发布时间及竞价时间"""
    import urllib.request
    from backend.utils import extract_starting_and_eval_price, extract_bidding_times
    
    url = f"https://api.m.jd.com/api?appid=paimai&functionId=queryAnnouncement&body=%7B%22noticeId%22%3A%22{notice_id}%22%7D"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Referer': f'https://paimai.jd.com/notice/{notice_id}'
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            d = data.get('data', {})
            content_html = d.get('content', '')
            clean_content = re.sub(r'<[^>]+>', ' ', content_html).strip()
            
            # 价格提取
            sp, ep = extract_starting_and_eval_price(d.get('title', ''), clean_content)
            
            # 真实发布时间提取
            pub_time = None
            m_pub = re.search(r'(?:发布时间|刊登时间|公告时间|二审发布|上架时间)[：:\s]*(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})日?(?:\s*(\d{1,2})[：:](\d{2}))?', clean_content)
            if m_pub:
                try:
                    hour = int(m_pub.group(4) or 0)
                    minute = int(m_pub.group(5) or 0)
                    pub_time = datetime(int(m_pub.group(1)), int(m_pub.group(2)), int(m_pub.group(3)), hour, minute)
                except Exception:
                    pass
            if not pub_time:
                # 尝试从正文末尾落款处提取签署/公布日期 (如: 某某银行 2026年10月10日)
                tail = clean_content[-400:]
                dates = re.findall(r'(\d{4})\s*[年\-/]\s*(\d{1,2})\s*[月\-/]\s*(\d{1,2})\s*日?', tail)
                if dates:
                    y, m, d_num = dates[-1]
                    try:
                        dt = datetime(int(y), int(m), int(d_num))
                        if 2018 <= dt.year <= 2027:
                            pub_time = dt
                    except Exception:
                        pass
            
            # 竞价时间提取
            bs, be = extract_bidding_times(clean_content)
            
            # 尝试提取具体标的物名称，解决同一公告多标的标题泛化重复问题
            lot_name = None
            m_lot = re.search(r'(?:竞买标的物|标的物|标的名称|持有[“"]|转让)\s*[：:\s]*([^，。\n“”"\'；;]{4,60})', clean_content)
            if m_lot:
                lot_name = m_lot.group(1).strip()
            elif re.search(r'标的物[：:\s]*([^，。\n]{3,60})', clean_content):
                lot_name = re.search(r'标的物[：:\s]*([^，。\n]{3,60})', clean_content).group(1).strip()
            
            return {
                "content": clean_content,
                "starting_price": sp,
                "eval_price": ep,
                "publish_time": pub_time,
                "bidding_start": bs,
                "bidding_end": be,
                "lot_name": lot_name
            }
    except Exception:
        return {}

def parse_jd_api_item(d: dict, max_days: int = 3) -> dict:
    """将京东 API 返回的单个标的原始数据转换为系统标准数据模型（时效优先，过滤旧数据与小物件）"""
    paimai_id = d.get("paimaiId") or d.get("id")
    if not paimai_id:
        return None

    title = (d.get("title") or "京东司法拍卖标的").strip()
    house_attrs = d.get("houseAttributes") or {}

    # 彻底过滤剔除日用散杂小物件（衣服、鞋帽、箱包、酒水、手机数码、首饰等）
    if is_trivial_consumer_item(title, house_attrs, "资产/司法拍卖"):
        return None

    # 彻底过滤剔除机动车辆、重型和大型机械设备
    if is_vehicle_or_equipment_item(title):
        return None

    raw_id = f"jd_{paimai_id}"
    source_url = f"https://paimai.jd.com/{paimai_id}"

    # 价格提取
    start_price = None
    if d.get("startPrice") is not None:
        try:
            start_price = float(d.get("startPrice"))
        except Exception:
            pass
    if start_price is None and d.get("currentPrice") is not None:
        try:
            start_price = float(d.get("currentPrice"))
        except Exception:
            pass

    eval_price = None
    if d.get("assessmentPrice") is not None:
        try:
            ep = float(d.get("assessmentPrice"))
            if ep > 0:
                eval_price = round(ep, 2)
        except Exception:
            pass

    if start_price is not None:
        start_price = round(start_price, 2)

    if start_price is not None and eval_price is not None and start_price == eval_price:
        eval_price = None

    # 折扣率（标准折数，如 7.0 折）
    discount_rate = None
    if start_price and eval_price and eval_price > 0:
        discount_rate = round((start_price / eval_price) * 10, 1)
    elif d.get("discountRate") is not None:
        try:
            raw_dr = float(d.get("discountRate"))
            discount_rate = round(raw_dr * 10 if raw_dr <= 1 else raw_dr, 1)
        except Exception:
            pass

    # 拍卖阶段（优先依据底层 API 字段 paimaiStage / stage，其次标题）
    stage_val = d.get("paimaiStage") or d.get("stage")
    auction_stage = "一拍"
    if stage_val is not None:
        stage_str = str(stage_val)
        if "2" in stage_str or "二" in stage_str:
            auction_stage = "二拍"
        elif "3" in stage_str or "变卖" in stage_str:
            auction_stage = "变卖"
        elif "破产" in stage_str:
            auction_stage = "破产清算"
        elif "1" in stage_str or "一" in stage_str:
            auction_stage = "一拍"
    elif "二拍" in title:
        auction_stage = "二拍"
    elif "变卖" in title:
        auction_stage = "变卖"
    elif "破产" in title:
        auction_stage = "破产清算"
    elif "一拍" in title:
        auction_stage = "一拍"

    # 案号提取（严格司法案号规范）
    case_number = extract_judicial_case_number(title)

    # 资产精准分类（未能识别类别的标的严禁默认归为住宅房产，归入“其他资产”）
    title_lower = title.lower()
    t_clean = re.sub(r'[\u4e00-\u9fa5]{2,30}(?:公司|分公司|支行|行)(?:名下|持有)?', '', title)
    if any(k in title_lower for k in ['债权', '股权', '证券', '不良资产', '借款', '追偿权', '收益权', '破产财产', '应收账款']):
        category = "金融债权与股权"
    elif any(k in title_lower for k in ['地块', '宗地', '土地使用权', '工业用地', '厂房', '仓库', '林地', '构筑物']):
        category = "工业厂房与土地"
    elif any(k in t_clean for k in ['房产', '住宅', '商品房', '公寓', '洋房', '别墅', '门市', '商铺', '写字楼', '车位', '车库', '人防车位', '地下室', '室', '号楼', '单元', '大厦', '楼房', '门面']):
        category = "住宅/商业房产"
    elif house_attrs.get("housePurpose") and house_attrs.get("houseArea"):
        category = "住宅/商业房产"
    else:
        category = "其他资产"

    # 建筑面积与房屋详情
    area_desc = ""
    if house_attrs.get("houseArea"):
        area_desc = f"{house_attrs.get('houseArea')} ㎡"
    avg_price_desc = ""
    if house_attrs.get("averagePrice"):
        avg_price_desc = f"{house_attrs.get('averagePrice')}"

    # 属地与城市及处置法院（优先使用底层 API 返回的 courtName）
    province = d.get("province") or ""
    city = d.get("city") or ""
    court_api = d.get("courtName") or d.get("vendorName") or d.get("shopName")
    if court_api:
        court_name = court_api
        disposer = court_api
    else:
        court_name, disposer = infer_court_and_disposer(title, city, province)

    # 涉豫判定（强化标题、处置机构与正文地市识别）
    is_henan = False
    henan_city = None
    henan_tag = None

    if d.get("provinceId") == 7 or "河南" in province:
        is_henan = True
        clean_city = city.replace("市", "").strip() if city else ""
        if clean_city in HENAN_CITIES:
            henan_city = clean_city
        else:
            for c_k, kws in HENAN_CITIES.items():
                if any(kw in title for kw in kws):
                    henan_city = c_k
                    break
        henan_city = henan_city or "全省"
        henan_tag = f"京东法拍·{henan_city}重点标的"
    else:
        # 全国标的跑强化 detect_henan_info
        is_h, h_c, h_t = detect_henan_info(title=title, content=f"{title} {disposer or ''}", court_name=court_name, parties=disposer)
        if is_h:
            is_henan = True
            henan_city = h_c
            henan_tag = h_t

    # 时间提取（真实审核/发布时间优先，严禁回退伪造为 datetime.now()）
    publish_time = None
    if d.get("auditTime"):
        try:
            publish_time = datetime.fromtimestamp(d.get("auditTime") / 1000)
        except Exception:
            pass
    elif d.get("publishTime"):
        try:
            publish_time = datetime.fromtimestamp(d.get("publishTime") / 1000)
        except Exception:
            pass
    elif d.get("onlineTime"):
        try:
            publish_time = datetime.fromtimestamp(d.get("onlineTime") / 1000)
        except Exception:
            pass
    elif d.get("createTime"):
        try:
            publish_time = datetime.fromtimestamp(d.get("createTime") / 1000)
        except Exception:
            pass

    if not publish_time:
        publish_time = datetime.now()

    # 竞价时间提取
    bidding_start = None
    if d.get("startTime"):
        try:
            bidding_start = datetime.fromtimestamp(d.get("startTime") / 1000)
        except Exception:
            pass
    bidding_end = None
    if d.get("endTime"):
        try:
            bidding_end = datetime.fromtimestamp(d.get("endTime") / 1000)
        except Exception:
            pass

    # 时效门禁过滤：若开启当日/时效优先，仅当有明确真实发布时间时过滤超出 max_days 天的旧数据
    if max_days is not None and publish_time is not None:
        days_diff = (datetime.now() - publish_time).total_seconds() / 86400.0
        if days_diff > max_days:
            # 超过时效门禁直接舍弃，杜绝陈旧数据入库
            return None

    price_str = f"¥{start_price:,.2f} 元" if start_price else "以竞买公告为准"
    eval_str = f"¥{eval_price:,.2f} 元" if eval_price else "无评估价/参考竞买公告"
    discount_str = f"{discount_rate}折" if discount_rate else "以公告为准"

    extra_lines = []
    if area_desc:
        extra_lines.append(f"建筑面积：{area_desc}")
    if avg_price_desc:
        extra_lines.append(f"参考单价：{avg_price_desc}")
    extra_text = ("\n" + "\n".join(extra_lines)) if extra_lines else ""

    content_text = (
        f"【京东拍卖·标的公告】\n"
        f"标的名称：{title}\n"
        f"处置主体：{court_name}\n"
        f"当前阶段：{auction_stage}\n"
        f"起拍价：{price_str}\n"
        f"评估价：{eval_str} (折扣率：{discount_str})\n"
        f"标的类别：{category}\n"
        f"属地位置：{province} · {city}{extra_text}\n"
        f"原站直达链接：{source_url}"
    )

    return {
        "platform": "jd",
        "raw_id": raw_id,
        "court_name": court_name,
        "case_number": case_number,
        "parties": disposer,
        "notice_type": "资产/司法拍卖",
        "title": title,
        "content_text": content_text,
        "publish_time": publish_time,
        "source_url": source_url,
        "starting_price": start_price,
        "eval_price": eval_price,
        "auction_stage": auction_stage,
        "asset_category": category,
        "bidding_start": bidding_start,
        "bidding_end": bidding_end,
        "is_henan": is_henan,
        "henan_city": henan_city,
        "henan_tag": henan_tag
    }

async def fetch_jd_real_auctions() -> List[dict]:
    """通过 Playwright 网络拦截获取京东拍卖最新真实数据，以房产、债权及法院公告为主"""
    results_map = {}
    
    async with async_playwright() as p:
        browser = await launch_smart_browser(p, headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="zh-CN"
        )
        page = await context.new_page()

        async def on_response(response):
            url = response.url
            if any(k in url for k in ['getSearchData', 'search', 'query', 'paimaiId']):
                try:
                    text = await response.text()
                    if not text:
                        return
                    clean_text = text.strip()
                    if clean_text.startswith('jQuery') or ('(' in clean_text and clean_text.endswith(')')):
                        s = clean_text.find('(')
                        e = clean_text.rfind(')')
                        clean_text = clean_text[s+1:e]
                    res = json.loads(clean_text)
                    items_to_parse = []
                    if isinstance(res, dict):
                        rd = res.get('data')
                        if isinstance(rd, dict):
                            items_to_parse.extend(rd.get('resultData', []))
                            items_to_parse.extend(rd.get('datas', []))
                            items_to_parse.extend(rd.get('items', []))
                        elif isinstance(rd, list):
                            items_to_parse.extend(rd)
                        if 'resultData' in res and isinstance(res['resultData'], list):
                            items_to_parse.extend(res['resultData'])
                    elif isinstance(res, list):
                        items_to_parse.extend(res)

                    for item in items_to_parse:
                        d = item.get('data') if isinstance(item, dict) and 'data' in item and isinstance(item['data'], dict) else item
                        if isinstance(d, dict) and (d.get('paimaiId') or d.get('id')):
                            parsed = parse_jd_api_item(d)
                            if parsed and parsed["raw_id"] not in results_map:
                                results_map[parsed["raw_id"]] = parsed
                except Exception:
                    pass

        page.on('response', on_response)

        # 核心抓取源 1：河南属地法拍房产与大盘 (provinceId=7&sortType=10 最新上架优先) 翻页遍历 1~4 页
        try:
            print("[jd_crawler] Accessing JD Henan Focus: https://pmsearch.jd.com/?provinceId=7&sortType=10")
            await page.goto("https://pmsearch.jd.com/?provinceId=7&sortType=10", timeout=30000, wait_until="networkidle")
            await page.wait_for_timeout(2000)

            for p_idx in range(2, 5):
                next_btn = await page.query_selector('button:has-text("下一页")')
                if next_btn:
                    await next_btn.click()
                    await page.wait_for_timeout(2500)
                else:
                    break
        except Exception as e:
            print(f"[jd_crawler] Error on Henan province search: {e}")

        # 核心抓取源 2：河南司法房产专场 (pawnThirdCateId=15 住宅用房, 最新上架)
        try:
            print("[jd_crawler] Accessing JD Henan Residential: https://pmsearch.jd.com/?provinceId=7&pawnThirdCateId=15&sortType=10")
            await page.goto("https://pmsearch.jd.com/?provinceId=7&pawnThirdCateId=15&sortType=10", timeout=30000, wait_until="networkidle")
            await page.wait_for_timeout(2000)
            for _ in range(2):
                next_btn = await page.query_selector('button:has-text("下一页")')
                if next_btn:
                    await next_btn.click()
                    await page.wait_for_timeout(2000)
                else:
                    break
        except Exception as e:
            print(f"[jd_crawler] Error on residential real estate: {e}")

        # 核心抓取源 3：河南金融债权与资产处置专场 (pawnThirdCateId=5 债权, 最新上架)
        try:
            print("[jd_crawler] Accessing JD Henan Debt: https://pmsearch.jd.com/?provinceId=7&pawnThirdCateId=5&sortType=10")
            await page.goto("https://pmsearch.jd.com/?provinceId=7&pawnThirdCateId=5&sortType=10", timeout=30000, wait_until="networkidle")
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"[jd_crawler] Error on debt assets: {e}")

        # 核心抓取源 4：河南商业用房与工业厂房 (pawnThirdCateId=14 商业, 最新上架)
        try:
            print("[jd_crawler] Accessing JD Henan Commercial: https://pmsearch.jd.com/?provinceId=7&pawnThirdCateId=14&sortType=10")
            await page.goto("https://pmsearch.jd.com/?provinceId=7&pawnThirdCateId=14&sortType=10", timeout=30000, wait_until="networkidle")
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"[jd_crawler] Error on commercial real estate: {e}")

        # 核心抓取源 5：搜索词“河南法院”定向抓取司法拍卖公告 (最新上架)
        try:
            print("[jd_crawler] Accessing keyword 河南法院: https://pmsearch.jd.com/?keyword=%E6%B2%B3%E5%8D%97%E6%B3%95%E9%99%A2&sortType=10")
            await page.goto("https://pmsearch.jd.com/?keyword=%E6%B2%B3%E5%8D%97%E6%B3%95%E9%99%A2&sortType=10", timeout=30000, wait_until="networkidle")
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"[jd_crawler] Error on keyword 河南法院: {e}")

        # 核心抓取源 6：搜索词“破产”定向抓取企业破产资产与重整拍卖 (最新上架)
        try:
            print("[jd_crawler] Accessing keyword 破产: https://pmsearch.jd.com/?provinceId=7&keyword=%E7%A0%B4%E4%BA%A7&sortType=10")
            await page.goto("https://pmsearch.jd.com/?provinceId=7&keyword=%E7%A0%B4%E4%BA%A7&sortType=10", timeout=30000, wait_until="networkidle")
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"[jd_crawler] Error on keyword 破产: {e}")

        # DOM 兜底分析：提取页面上的额外超链接（过滤小物件）
        try:
            links = await page.query_selector_all("a[href*='paimai.jd.com']")
            for l in links:
                href = await l.get_attribute("href")
                if not href:
                    continue
                clean_url = href.split('?')[0]
                if clean_url.startswith('//'):
                    clean_url = f"https:{clean_url}"
                id_m = re.search(r'paimai\.jd\.com/(?:notice/)?(\d+)', clean_url)
                if id_m:
                    p_id = id_m.group(1)
                    raw_id = f"jd_{p_id}"
                    if raw_id not in results_map:
                        text = (await l.inner_text()).strip()
                        if len(text) >= 6:
                            raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
                            valid_lines = [
                                l for l in raw_lines 
                                if not any(k in l for k in [
                                    "预计今日", "预计", "后结束", "即将开始", "正在进行", "距离结束", "已结束",
                                    "折起拍", "配资服务", "一键贷款", "精选资产", "免息分期", "服务保障",
                                    "限时特惠", "人围观", "起拍价", "评估价", "当前价", "以竞买公告为准"
                                ]) 
                                and len(l) >= 4
                            ]
                            first_line = valid_lines[0] if valid_lines else ""
                            if not first_line:
                                continue
                            if is_trivial_consumer_item(first_line, notice_type="资产/司法拍卖"):
                                continue
                            if is_vehicle_or_equipment_item(first_line, text):
                                continue

                            # 尝试调用详情接口获取公告正文、真实价格、多标的区分名称及竞价时间
                            detail = fetch_jd_notice_detail(p_id)
                            lot_title = first_line
                            if detail.get("lot_name") and detail["lot_name"] not in first_line:
                                lot_title = f"{first_line} - {detail['lot_name']}"

                            if is_vehicle_or_equipment_item(lot_title, detail.get("content", text)):
                                continue

                            # 提取价格兜底
                            sp = detail.get("starting_price")
                            if sp is None:
                                sp_m = re.search(r'(?:起拍价|当前价)[：:\s]*\n*[¥￥]?\s*([0-9.]+)\s*(万|万元|元)', text)
                                if sp_m:
                                    try:
                                        val = float(sp_m.group(1))
                                        if '万' in sp_m.group(2):
                                            val *= 10000.0
                                        sp = val
                                    except Exception:
                                        pass

                            ep = detail.get("eval_price")
                            if ep is None:
                                ep_m = re.search(r'评估价[：:\s]*\n*[¥￥]?\s*([0-9.]+)\s*(万|万元|元)', text)
                                if ep_m:
                                    try:
                                        val = float(ep_m.group(1))
                                        if '万' in ep_m.group(2):
                                            val *= 10000.0
                                        ep = val
                                    except Exception:
                                        pass

                            # 提取竞价时间兜底
                            b_start = detail.get("bidding_start")
                            b_end = detail.get("bidding_end")
                            if not b_start:
                                bs, be = extract_bidding_times(f"{text} {detail.get('content', '')}")
                                if bs:
                                    b_start = bs
                                if be and not b_end:
                                    b_end = be

                            is_h, h_c, h_t = detect_henan_info(title=lot_title, content=f"{text} {detail.get('content', '')}")
                            cat = "其他资产"
                            t_p = re.sub(r'[\u4e00-\u9fa5]{2,30}(?:公司|分公司|支行|行)(?:名下|持有)?', '', lot_title)
                            if any(k in lot_title for k in ["股", "证券", "债券", "债权", "资产包"]):
                                cat = "金融债权与股权"
                            elif any(k in lot_title for k in ["地块", "土地", "厂房", "仓库", "工业园"]):
                                cat = "工业厂房与土地"
                            elif any(k in t_p for k in ["房产", "住宅", "商品房", "公寓", "洋房", "别墅", "门面", "商铺", "车位", "车库", "室", "号楼", "单元", "大厦", "楼房"]):
                                cat = "住宅/商业房产"

                            results_map[raw_id] = {
                                "platform": "jd",
                                "raw_id": raw_id,
                                "court_name": "人民法院司法拍卖",
                                "case_number": "",
                                "parties": "处置机构",
                                "notice_type": "资产/司法拍卖",
                                "title": lot_title,
                                "content_text": f"【京东拍卖】\n标的名称：{lot_title}\n链接：{clean_url}\n{detail.get('content', text)[:300]}",
                                "publish_time": detail.get("publish_time") or datetime.now(),
                                "source_url": clean_url,
                                "starting_price": sp,
                                "eval_price": ep,
                                "auction_stage": "一拍",
                                "asset_category": cat,
                                "bidding_start": b_start,
                                "bidding_end": b_end,
                                "is_henan": is_h,
                                "henan_city": h_c if is_h else None,
                                "henan_tag": h_t or ("京东法拍·重点标的" if is_h else None)
                            }
        except Exception as e:
            print(f"[jd_crawler] Fallback error: {e}")

        # 风控与验证码拦截特征检测
        warning_reasons = []
        try:
            current_url = page.url
            page_title = await page.title()
            if any(k in current_url for k in ['passport.jd.com', 'risk.jd.com', 'captcha']):
                warning_reasons.append(f"触发京东风控安全验证重定向: {current_url}")
            elif any(k in page_title for k in ['验证码', '安全验证', '登录']):
                warning_reasons.append(f"页面提示安全验证: {page_title}")
        except Exception:
            pass
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            if context:
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
    print(f"[jd_crawler] Total parsed core assets (trivial items filtered): {len(results_map)}")
    return list(results_map.values()), warning_msg

from backend.database import SessionLocal

def crawl_jd_auctions(db: Optional[Session] = None, max_items: int = 15) -> Tuple[List[CourtNotice], int, Optional[str]]:
    """主入口：执行抓取并存入数据库（以房产、债权与法院公告为主，严格剔除日用小物件）"""
    items, warning_msg = run_async(fetch_jd_real_auctions())
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
                # 存量数据更新：更新价格、业务模块及属地标签
                existing.module_type = mod_type
                if item.get("asset_category"):
                    existing.asset_category = item["asset_category"]
                if item.get("starting_price") and (not existing.starting_price or existing.starting_price == 0):
                    existing.starting_price = item["starting_price"]
                if item.get("eval_price") and not existing.eval_price:
                    existing.eval_price = item["eval_price"]
                if not existing.publish_time:
                    existing.publish_time = item.get("publish_time") or existing.created_at or datetime.now()
                if item.get("bidding_start") and not existing.bidding_start:
                    existing.bidding_start = item["bidding_start"]
                if item.get("bidding_end") and not existing.bidding_end:
                    existing.bidding_end = item["bidding_end"]
                if item.get("is_henan") and not existing.is_henan:
                    existing.is_henan = item["is_henan"]
                    existing.henan_city = item["henan_city"]
                    existing.henan_tag = item["henan_tag"]
                if item.get("court_name") and existing.court_name in ["人民法院司法拍卖", "人民法院/金融处置机构"]:
                    existing.court_name = item["court_name"]

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[jd_crawler] Commit error: {e}")
        return [], len(items), str(e)
    finally:
        if close_when_done:
            db.close()

    print(f"[jd_crawler] Core assets scraped: {len(items)}, new ingested: {len(new_records)}")
    return new_records, len(items), warning_msg
