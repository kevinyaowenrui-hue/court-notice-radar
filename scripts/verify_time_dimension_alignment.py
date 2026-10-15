# -*- coding: utf-8 -*-
import sys
import os
from datetime import datetime

sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

print("==================================================")
print("实证校验：各时间维度预警数据与业务模块 Tab 联动测试")
print("==================================================")

time_dimensions = ["today", "3days", "7days", "all"]

for td in time_dimensions:
    print(f"\n>>> 测试时效维度: time_range = {td} (涉豫重点: henan_only=true)")
    
    # 1. 查询全部预警 (module_type='')
    res_all = client.get(f"/api/alerts?time_range={td}&henan_only=true&page=1&page_size=20")
    assert res_all.status_code == 200, f"Error: {res_all.status_code}"
    data_all = res_all.json()
    
    tab_counts = data_all.get("tab_counts", {})
    total_listed = data_all.get("total", 0)
    
    cnt_total = tab_counts.get("total", 0)
    cnt_notice = tab_counts.get("公告", 0)
    cnt_auction = tab_counts.get("拍卖公告", 0)
    cnt_debt = tab_counts.get("债权转让", 0)
    
    print(f"  Tab 统计数字: 全部预警={cnt_total} | 法院公告={cnt_notice} | 司法拍卖={cnt_auction} | 债权转让={cnt_debt}")
    print(f"  列表报告总数: {total_listed}")
    
    # 核心数学一致性断言：总数必须等于三业务模块之和
    assert cnt_total == cnt_notice + cnt_auction + cnt_debt, f"不一致: {cnt_total} != {cnt_notice} + {cnt_auction} + {cnt_debt}"
    # 列表总数必须与 Tab 统计的 total 完全一致
    assert total_listed == cnt_total, f"列表总数不一致: {total_listed} != {cnt_total}"
    
    # 2. 验证各个子模块 Tab 点击后的列表总数
    # 2.1 司法拍卖 Tab
    res_auction = client.get(f"/api/alerts?time_range={td}&henan_only=true&module_type=拍卖公告&page=1&page_size=20")
    assert res_auction.status_code == 200
    data_auction = res_auction.json()
    print(f"  -> 点击[司法拍卖] Tab: 列表显示 {data_auction['total']} 条 (Tab 显示 {cnt_auction}) - {'MATCH' if data_auction['total'] == cnt_auction else 'MISMATCH'}")
    assert data_auction['total'] == cnt_auction, f"司法拍卖数量不一致: {data_auction['total']} != {cnt_auction}"
    
    # 2.2 债权转让 Tab
    res_debt = client.get(f"/api/alerts?time_range={td}&henan_only=true&module_type=债权转让&page=1&page_size=20")
    assert res_debt.status_code == 200
    data_debt = res_debt.json()
    print(f"  -> 点击[债权转让] Tab: 列表显示 {data_debt['total']} 条 (Tab 显示 {cnt_debt}) - {'MATCH' if data_debt['total'] == cnt_debt else 'MISMATCH'}")
    assert data_debt['total'] == cnt_debt, f"债权转让数量不一致: {data_debt['total']} != {cnt_debt}"
    
    # 2.3 法院公告 Tab
    res_notice = client.get(f"/api/alerts?time_range={td}&henan_only=true&module_type=公告&page=1&page_size=20")
    assert res_notice.status_code == 200
    data_notice = res_notice.json()
    print(f"  -> 点击[法院公告] Tab: 列表显示 {data_notice['total']} 条 (Tab 显示 {cnt_notice}) - {'MATCH' if data_notice['total'] == cnt_notice else 'MISMATCH'}")
    assert data_notice['total'] == cnt_notice, f"法院公告数量不一致: {data_notice['total']} != {cnt_notice}"

print("\n==================================================")
print("各平台数据源采集与覆盖度检查 (今日 vs 历史)")
print("==================================================")
res_today_items = client.get("/api/alerts?time_range=today&henan_only=true&page_size=100").json()
platforms_today = set(item['notice']['platform'] for item in res_today_items['items'])
print(f"今日涉豫预警覆盖渠道: {platforms_today}")
print(f"今日涉豫预警总计: {len(res_today_items['items'])} 条")

print("\n[OK] 全部时间维度数据与 Tab 统计 100% 精准对应，校验完全通过！")
