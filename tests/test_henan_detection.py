# -*- coding: utf-8 -*-
import sys
import os

# 确保 backend 在 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.utils import detect_henan_info, HENAN_CITIES

def test_detect_henan():
    passed = 0
    total = 0

    cases = [
        # 1. 全国通用重名区县/商业词（非河南案件，绝不应误判为涉豫）
        {
            "name": "南京鼓楼区法院（外省重名）",
            "kwargs": {"court_name": "南京市鼓楼区人民法院", "title": "鼓楼区宁海路某住宅处置", "content": "江苏省南京市鼓楼区"},
            "expected_is_henan": False,
            "desc": "南京鼓楼区不应误判为开封"
        },
        {
            "name": "石家庄新华区法院（外省重名）",
            "kwargs": {"court_name": "石家庄市新华区人民法院", "title": "新华区合作路房屋拍卖", "content": "河北省石家庄市新华区"},
            "expected_is_henan": False,
            "desc": "石家庄新华区不应误判为平顶山"
        },
        {
            "name": "陕西商洛山阳县法院（外省重名）",
            "kwargs": {"court_name": "山阳县人民法院", "title": "山阳县城关镇某门面房变卖", "content": "陕西省商洛市山阳县"},
            "expected_is_henan": False,
            "desc": "陕西山阳县不应误判为焦作"
        },
        {
            "name": "青海黄南州河南县法院（外省同名县）",
            "kwargs": {"court_name": "河南蒙古族自治县人民法院", "case_number": "(2023)青0225执10号", "title": "优干宁镇某草场承包权拍卖", "content": "青海省黄南藏族自治州河南县"},
            "expected_is_henan": False,
            "desc": "青海河南县不应误判为河南省"
        },
        {
            "name": "杭州西湖湖滨商圈（商业词干扰）",
            "kwargs": {"court_name": "杭州市上城区人民法院", "title": "西湖湖滨商圈沿街商铺拍卖", "content": "浙江省杭州市延安路湖滨商圈"},
            "expected_is_henan": False,
            "desc": "西湖湖滨不应误判为三门峡"
        },
        {
            "name": "外省万达数码商城（商城字样干扰）",
            "kwargs": {"court_name": "合肥市蜀山区人民法院", "title": "合肥三里庵数码商城二楼商铺拍卖", "content": "位于安徽省合肥市蜀山区数码商城"},
            "expected_is_henan": False,
            "desc": "商业商城字样不应误判为信阳"
        },
        {
            "name": "红旗牌汽车拍卖（红旗字样干扰）",
            "kwargs": {"court_name": "成都市武侯区人民法院", "title": "一汽红旗 H9 轿车一辆网络司法拍卖", "content": "车架号xxxx，车牌川Axxxx"},
            "expected_is_henan": False,
            "desc": "红旗牌车辆不应误判为新乡"
        },

        # 2. 河南属地法院与案号识别（精准归属各市，防抢占，补漏词）
        {
            "name": "长垣市人民法院（原漏词补全）",
            "kwargs": {"court_name": "长垣市人民法院", "case_number": "(2024)豫0781执200号", "title": "长垣市蒲西区工业厂房拍卖", "content": "长垣市人民法院执行"},
            "expected_is_henan": True,
            "expected_city": "新乡",
            "desc": "长垣应精准归入新乡"
        },
        {
            "name": "济源产城融合示范区（直管区补全）",
            "kwargs": {"court_name": "济源市人民法院", "title": "济源产城融合示范区某宗工业用地处置", "content": "济源示范区自然资源局"},
            "expected_is_henan": True,
            "expected_city": "济源",
            "desc": "济源示范区应精准归入济源"
        },
        {
            "name": "洛阳法院审理，正文提及郑州公司（防郑州字典优先抢占）",
            "kwargs": {"court_name": "洛阳市洛龙区人民法院", "case_number": "(2023)豫0307执50号", "title": "洛龙区开元大道某房产拍卖", "content": "申请执行人：郑州市金水区某商贸发展有限公司。被执行人：洛阳某制造厂。"},
            "expected_is_henan": True,
            "expected_city": "洛阳",
            "desc": "洛阳法院案件不能被正文中的郑州公司抢占"
        },
        {
            "name": "开封鼓楼区法院审理（开封属地精准匹配）",
            "kwargs": {"court_name": "开封市鼓楼区人民法院", "case_number": "(2023)豫0204执88号", "title": "自由路沿街门面房司法拍卖", "content": "开封市鼓楼区人民法院执行"},
            "expected_is_henan": True,
            "expected_city": "开封",
            "desc": "开封市鼓楼区应精准归入开封"
        },
        {
            "name": "河南省高级人民法院案号（全省无具体市时规范为全省）",
            "kwargs": {"court_name": "河南省高级人民法院", "case_number": "(2023)豫执复100号", "title": "某涉省属重点工程债权资产处置", "content": "河南省高级人民法院执行局"},
            "expected_is_henan": True,
            "expected_city": "全省",
            "desc": "省高院无具体地市时应规范标准化为'全省'，绝非'河南全省'或'省本级'"
        },

        # 3. 全国跨域涉豫资产与当事人识别
        {
            "name": "北京朝阳法院处置郑州房产（跨省涉豫）",
            "kwargs": {"court_name": "北京市朝阳区人民法院", "case_number": "(2023)京0105执999号", "title": "处置被执行人名下位于河南省郑州市金水区农业路某住宅", "content": "标的物坐落于河南省郑州市金水区"},
            "expected_is_henan": True,
            "expected_city": "郑州",
            "desc": "外地法院处置河南郑州资产应正确识别为涉豫及郑州"
        },
        {
            "name": "上海一中院处置信阳商城县资产（跨省涉豫信阳）",
            "kwargs": {"court_name": "上海市第一中级人民法院", "case_number": "(2023)沪01执123号", "title": "处置河南省信阳市商城县产业集聚区工业厂房", "content": "标的坐落河南省信阳市商城县"},
            "expected_is_henan": True,
            "expected_city": "信阳",
            "desc": "外地法院处置信阳商城县资产应正确识别为涉豫及信阳"
        }
    ]

    print("=" * 60)
    print("开始运行涉豫识别与地名收敛测试集...")
    print("=" * 60)

    for case in cases:
        total += 1
        is_h, city, tag = detect_henan_info(**case["kwargs"])
        exp_h = case["expected_is_henan"]
        exp_c = case.get("expected_city")

        ok = True
        err_msg = []
        if is_h != exp_h:
            ok = False
            err_msg.append(f"is_henan 期望 {exp_h}，实际 {is_h}")
        if exp_c is not None and city != exp_c:
            ok = False
            err_msg.append(f"henan_city 期望 '{exp_c}'，实际 '{city}'")

        if ok:
            passed += 1
            print(f"PASS: [{case['name']}] -> is_henan={is_h}, city={city}, tag={tag}")
        else:
            print(f"FAIL: [{case['name']}] -> {', '.join(err_msg)} (实际: is_henan={is_h}, city={city}, tag={tag})")

    print("=" * 60)
    print(f"测试完成: 共 {total} 项，通过 {passed} 项，失败 {total - passed} 项")
    print("=" * 60)
    return passed == total

if __name__ == "__main__":
    success = test_detect_henan()
    sys.exit(0 if success else 1)
