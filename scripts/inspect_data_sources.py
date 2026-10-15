# -*- coding: utf-8 -*-
import sqlite3
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
db_path = os.path.join('data', 'court_notices.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

print('=== 1. All CourtNotices by Platform ===')
for row in c.execute('SELECT platform, count(*), min(publish_time), max(publish_time) FROM court_notices GROUP BY platform'):
    print(row)

print('\n=== 2. CourtNotices by Platform where date is today (2026-10-13) ===')
for row in c.execute("""
SELECT platform, count(*) 
FROM court_notices 
WHERE substr(COALESCE(publish_time, created_at), 1, 10) = '2026-10-13'
GROUP BY platform
"""):
    print(row)

print('\n=== 3. CourtNotices by Platform (Today AND is_henan=1) ===')
for row in c.execute("""
SELECT platform, count(*) 
FROM court_notices 
WHERE substr(COALESCE(publish_time, created_at), 1, 10) = '2026-10-13' AND is_henan = 1
GROUP BY platform
"""):
    print(row)

print('\n=== 4. AlertEvents by Platform (All time) ===')
for row in c.execute("""
SELECT cn.platform, count(*) 
FROM alert_events ae 
JOIN court_notices cn ON ae.notice_id = cn.id
GROUP BY cn.platform
"""):
    print(row)

print('\n=== 5. AlertEvents by Platform (Today, 2026-10-13) ===')
for row in c.execute("""
SELECT cn.platform, count(*) 
FROM alert_events ae 
JOIN court_notices cn ON ae.notice_id = cn.id
WHERE substr(COALESCE(cn.publish_time, ae.created_at), 1, 10) = '2026-10-13'
GROUP BY cn.platform
"""):
    print(row)

print('\n=== 6. Recent Task Logs ===')
for row in c.execute('SELECT platform, task_name, status, items_found, new_items, created_at, error_msg FROM task_logs ORDER BY id DESC LIMIT 15'):
    print(row)

conn.close()
