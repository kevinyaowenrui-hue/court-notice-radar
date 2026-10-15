# -*- coding: utf-8 -*-
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

print("==================================================")
print("检查 data/court_notices.db 当前真实数据准确性")
print("==================================================")

today_str = '2026-10-13'

print("\n1. 今日全部标的 (CourtNotices) 平台分布:")
for r in c.execute("""
    SELECT platform, count(*), 
           SUM(CASE WHEN is_henan = 1 THEN 1 ELSE 0 END) as henan_count
    FROM court_notices 
    WHERE substr(COALESCE(publish_time, created_at), 1, 10) = ?
    GROUP BY platform
""", (today_str,)):
    print(f"  渠道 {r[0]:12s}: 今日总标的={r[1]:2d} 条 (涉豫={r[2]:2d} 条)")

print("\n2. 今日全部预警 (AlertEvents) 平台与模块分布:")
for r in c.execute("""
    SELECT cn.platform, 
           COALESCE(cn.module_type, '公告') as mod_type,
           cn.is_henan,
           count(ae.id)
    FROM alert_events ae
    JOIN court_notices cn ON ae.notice_id = cn.id
    WHERE substr(COALESCE(cn.publish_time, ae.created_at), 1, 10) = ?
    GROUP BY cn.platform, cn.module_type, cn.is_henan
""", (today_str,)):
    print(f"  渠道 {r[0]:12s} | 模块={r[1]:4s} | 涉豫={r[2]} | 预警数={r[3]:2d} 条")

print("\n3. 检查 MonitorRule 规则定义:")
for r in c.execute("SELECT id, name, platforms, keywords, cities FROM monitor_rules"):
    print(f"  Rule [{r[0]}] {r[1]}")
    print(f"    platforms: {r[2]}")
    print(f"    cities: {r[4]}")

conn.close()
