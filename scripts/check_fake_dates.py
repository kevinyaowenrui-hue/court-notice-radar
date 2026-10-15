# -*- coding: utf-8 -*-
import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, platform, title, publish_time, created_at FROM court_notices WHERE platform in ('ali', 'jd')")
rows = c.fetchall()
print(f"Total ali/jd rows: {len(rows)}")

fake_count = 0
for r in rows:
    nid, platform, title, pub_str, created_str = r
    # Check if publish_time has microsecond precision (e.g. 2026-10-11 16:02:27.454672)
    # Real published dates from web or forms are almost never microsecond precision!
    if pub_str and ('.' in pub_str or len(pub_str) > 19):
        fake_count += 1

print(f"Rows with microsecond publish_time (indicates datetime.now() was used): {fake_count}")

# Check publish_time vs created_at date/time difference
c.execute("""
    SELECT count(*) FROM court_notices 
    WHERE platform in ('ali', 'jd') 
      AND publish_time IS NOT NULL 
      AND (
          abs(julianday(publish_time) - julianday(created_at)) < 0.01 
          OR abs(julianday(publish_time) - julianday(created_at, '+8 hours')) < 0.01
      )
""")
print(f"Rows where publish_time is within minutes of created_at: {c.fetchone()[0]}")
