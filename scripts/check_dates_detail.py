# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

print("--- Check fake dates / microseconds in court_notices ---")
c.execute("SELECT id, platform, raw_id, title, publish_time, created_at FROM court_notices WHERE publish_time LIKE '%.%'")
micro_rows = c.fetchall()
print(f"Records with microseconds in publish_time: {len(micro_rows)}")
for r in micro_rows[:5]:
    print(r)

c.execute("SELECT id, platform, raw_id, title, publish_time, created_at FROM court_notices WHERE date(publish_time) = date('now')")
today_rows = c.fetchall()
print(f"Records with publish_time = today ({datetime.now().strftime('%Y-%m-%d')}): {len(today_rows)}")
for r in today_rows:
    print(r)

c.execute("SELECT id, platform, raw_id, title, publish_time, created_at FROM court_notices WHERE date(publish_time) = '2026-10-13'")
t13_rows = c.fetchall()
print(f"Records with publish_time = 2026-10-13: {len(t13_rows)}")
for r in t13_rows:
    print(r)
