# -*- coding: utf-8 -*-
import re

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

EQUIPMENT_EXCLUDE_KEYWORDS = [
    "高空作业平台", "管带机", "自动化生产线", "加工流水线", "机器设备及电缆",
    "一批机器设备", "x射线诊断仪", "x光机专用工作站", "数控机床", "车床", "冲床",
    "铣床", "发电机组", "锅炉设备", "龙门吊", "塔吊", "行车设备", "压路机",
    "拌合站", "搅拌站", "石料开采加工生产线", "废旧设备", "报废设备", "废旧金属",
    "废旧物资", "废旧铅酸蓄电池", "报废固定资产", "报废资产", "报废家具", "质谱仪"
]

IMMOBILE_PROTECT_KEYWORDS = [
    "房屋", "房产", "住宅", "商品房", "公寓", "洋房", "别墅", "门面房", "门面", "门市房", "商铺", "铺面",
    "写字楼", "不动产", "土地使用权", "地块", "国有建设用地", "厂房", "车位", "车库",
    "人防车位", "地下室", "仓库", "林地", "宗地", "建筑物", "构筑物", "房地产及", "房产及", "房屋及",
    "传票", "送达", "判决", "裁定", "起诉状", "限消", "执行通知", "清算", "破产",
    "债权", "股权", "资产包", "借款", "应收账款"
]

def is_vehicle_or_equipment_item_test(title: str = "", content: str = "") -> bool:
    if not title:
        return False
    t_lower = title.lower()
    
    # 纯车辆/机械一票否决检测
    has_vehicle = any(k in t_lower for k in VEHICLE_EXCLUDE_KEYWORDS)
    if not has_vehicle:
        # 车牌检测
        if re.search(r'(?:车牌号?为?|车牌|牌照)?[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Za-z0-9\*]{5,7}', title):
            if any(w in t_lower for w in ["车", "客车", "轿车", "汽车", "货车", "越野", "牌"]):
                has_vehicle = True

    has_equipment = any(k in t_lower for k in EQUIPMENT_EXCLUDE_KEYWORDS)
    if not has_equipment:
        if "机器设备" in t_lower or "机械设备" in t_lower or "生产线" in t_lower:
            has_equipment = True

    if not (has_vehicle or has_equipment):
        return False

    # 剔除归属人公司名称中的“房地产/置业/建筑”等干扰词用于不动产判定
    title_pure_target = re.sub(r'[\u4e00-\u9fa5]{2,30}(?:房地产|置业|建筑|建设|房产经纪|开发)[\w]*公司(?:名下|所属|查封)?', '', title)
    title_pure_target_lower = title_pure_target.lower()

    # 检查是否为房产+设备合并处置或纯司法文书/债权
    has_immobile = any(k in title_pure_target_lower for k in IMMOBILE_PROTECT_KEYWORDS)
    if has_immobile:
        # 如果标的纯粹以车为结尾或主体（如“...奥迪轿车一辆”、“...厢式车2台”），且不含房屋建筑厂房，仍属车辆
        if any(k in title_pure_target_lower for k in ["房屋", "房产", "房地产", "住宅", "商品房", "厂房", "土地", "建设用地", "地块", "商铺", "门面", "建筑物", "车位", "车库"]):
            return False
        if any(k in title_pure_target_lower for k in ["传票", "送达", "判决", "裁定", "债权", "股权", "资产包"]):
            return False

    return True

test_titles = [
    ("车牌号为豫ADL2818的小型小型轿车一辆", True),
    ("徐工牌 厢式车2台（再次）", True),
    ("徐工牌 冷藏车1台（再次）", True),
    ("徐工牌 搅拌车1台（再次）", True),
    ("河南某某房地产开发有限公司名下陕汽牌重型半挂牵引车一辆", True),
    ("952号车牌号为晋E****1的解放天V牵引车", True),
    ("郑州市金水区某某小区1号楼2单元501室房屋及地下车位一个", False),
    ("开封市祥符区某某房产及地下车位", False),
    ("某某公司房地产及机器设备一批", False),
    ("某某摩托车制造有限公司名下国有建设用地使用权", False),
    ("最高人民法院关于某某公司借款合同纠纷的开庭传票", False)
]

for t, expected in test_titles:
    res = is_vehicle_or_equipment_item_test(t)
    status = "PASS" if res == expected else "FAIL"
    print(f"{status}: '{t}' -> got {res}, expected {expected}")
