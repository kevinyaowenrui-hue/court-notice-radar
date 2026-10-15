# -*- coding: utf-8 -*-
import sqlite3
import re
import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

conn = sqlite3.connect('data/court_notices.db')
cur = conn.cursor()

# 1. 查看“郸城县人民法院关于郸城县安陵镇金色漫城·金兰园四期38号楼2单元17层1701”这条记录
cur.execute("""
    SELECT id, title, court_name, auction_stage, publish_time, bidding_start, source_url, content_text 
    FROM court_notices 
    WHERE title LIKE '%郸城县安陵镇金色漫城%'
""")
row = cur.fetchone()
if row:
    print("=== 郸城县标的核查 ===")
    print("ID:", row[0])
    print("Title:", row[1])
    print("Stage:", row[3])
    print("Publish time:", row[4])
    print("Bidding start:", row[5])
    print("URL:", row[6])
    print("Content preview:", row[7][:500])
else:
    print("未找到郸城县标的")

# 2. 检查诉讼资产网所有 114 条标的的 bidding_start 分布
cur.execute("""
    SELECT 
        count(*),
        sum(case when bidding_start is not null then 1 else 0 end) as has_bid_start,
        sum(case when bidding_start is null then 1 else 0 end) as no_bid_start
    FROM court_notices 
    WHERE platform = 'rmfysszc'
""")
stat = cur.fetchone()
print(f"\n诉讼资产网开拍时间提取情况: 总计 {stat[0]}, 成功提取 {stat[1]}, 未提取到 {stat[2]}")

# 3. 检查为什么“第一次拍卖”会命中“【捡漏】诉讼资产网 · 二拍超值涉豫房源”规则！
cur.execute("""
    SELECT r.name, r.keywords, r.exclude_keywords
    FROM monitor_rules r 
    WHERE r.name LIKE '%二拍%'
""")
rules = cur.fetchall()
print("\n二拍规则配置:")
for r in rules:
    print(f"Rule: {r[0]}")
    print(f"  keywords: {r[1]}")
    print(f"  exclude: {r[2]}")

# 4. 查看为什么一拍标的命中了该二拍规则
cur.execute("""
    SELECT a.id, a.rule_name, a.match_reason, n.title, n.auction_stage
    FROM alert_events a JOIN court_notices n ON a.notice_id = n.id
    WHERE a.rule_name LIKE '%二拍%' AND (n.title LIKE '%第一次拍卖%' OR n.title LIKE '%一拍%')
    LIMIT 3
""")
mis_alerts = cur.fetchall()
print("\n误命中的一拍预警条目:")
for m in mis_alerts:
    print(f"Alert ID {m[0]}: Rule={m[1]} | Reason={m[2]} | Stage={m[4]} | Title={m[3][:50]}")

conn.close()
