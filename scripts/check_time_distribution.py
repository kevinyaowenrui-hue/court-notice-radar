# -*- coding: utf-8 -*-
import sqlite3
import os
import sys
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(os.path.join('data', 'court_notices.db'))
c = conn.cursor()

today = datetime.now().date()
d_today = today.strftime('%Y-%m-%d')
d_3days = (today - timedelta(days=3)).strftime('%Y-%m-%d')
d_7days = (today - timedelta(days=7)).strftime('%Y-%m-%d')

print(f"Time anchors: Today={d_today}, 3Days={d_3days}, 7Days={d_7days}")

print("\n--- CourtNotices (Total in Database) by TimeRange & Henan ---")
for tr_name, start_date in [("Today", d_today), ("3Days", d_3days), ("7Days", d_7days), ("All", "2000-01-01")]:
    q = """
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN is_henan = 1 THEN 1 ELSE 0 END) as henan_total,
        SUM(CASE WHEN is_henan = 1 AND (module_type = '公告' OR module_type IS NULL) THEN 1 ELSE 0 END) as henan_notice,
        SUM(CASE WHEN is_henan = 1 AND module_type = '拍卖公告' THEN 1 ELSE 0 END) as henan_auction,
        SUM(CASE WHEN is_henan = 1 AND module_type = '债权转让' THEN 1 ELSE 0 END) as henan_debt
    FROM court_notices
    WHERE substr(COALESCE(publish_time, created_at), 1, 10) >= ?
    """
    row = c.execute(q, (start_date,)).fetchone()
    print(f"[{tr_name:5s}] Total: {row[0]:3d} | Henan: {row[1]:3d} (公告:{row[2]:2d}, 拍卖:{row[3]:3d}, 债权:{row[4]:2d})")

print("\n--- AlertEvents (Active Alerts) by TimeRange & Henan ---")
for tr_name, start_date in [("Today", d_today), ("3Days", d_3days), ("7Days", d_7days), ("All", "2000-01-01")]:
    q = """
    SELECT 
        COUNT(ae.id) as total,
        SUM(CASE WHEN cn.is_henan = 1 THEN 1 ELSE 0 END) as henan_total,
        SUM(CASE WHEN cn.is_henan = 1 AND (cn.module_type = '公告' OR cn.module_type IS NULL) THEN 1 ELSE 0 END) as henan_notice,
        SUM(CASE WHEN cn.is_henan = 1 AND cn.module_type = '拍卖公告' THEN 1 ELSE 0 END) as henan_auction,
        SUM(CASE WHEN cn.is_henan = 1 AND cn.module_type = '债权转让' THEN 1 ELSE 0 END) as henan_debt
    FROM alert_events ae
    JOIN court_notices cn ON ae.notice_id = cn.id
    WHERE substr(COALESCE(cn.publish_time, ae.created_at), 1, 10) >= ?
    """
    row = c.execute(q, (start_date,)).fetchone()
    print(f"[{tr_name:5s}] Total Alerts: {row[0]:3d} | Henan: {row[1]:3d} (公告:{row[2]:2d}, 拍卖:{row[3]:3d}, 债权:{row[4]:2d})")

print("\n--- AlertEvents by Platform (All Time) ---")
for r in c.execute("""
    SELECT cn.platform, COUNT(ae.id)
    FROM alert_events ae
    JOIN court_notices cn ON ae.notice_id = cn.id
    GROUP BY cn.platform
"""):
    print(f"  Platform {r[0]:12s}: {r[1]} alerts")

print("\n--- CourtNotices by Platform (All Time) ---")
for r in c.execute("""
    SELECT platform, COUNT(*)
    FROM court_notices
    GROUP BY platform
"""):
    print(f"  Platform {r[0]:12s}: {r[1]} notices")

conn.close()
