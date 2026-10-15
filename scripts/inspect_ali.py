# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import re

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, raw_id, title, publish_time, bidding_start, bidding_end, content_text FROM court_notices WHERE platform='ali' LIMIT 5")
for r in c.fetchall():
    print("="*60)
    print(f"ID={r[0]}, raw_id={r[1]}, title={r[2]}")
    print(f"publish_time={r[3]}, start={r[4]}, end={r[5]}")
    print(f"content: {r[6]}")
