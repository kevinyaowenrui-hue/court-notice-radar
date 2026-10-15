# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')
import sqlite3

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, raw_id, court_name, title, case_number, source_url, content_text FROM court_notices WHERE platform='rmfyb'")
rows = c.fetchall()
print(f"Total rmfyb rows: {len(rows)}")

news_count = 0
notice_count = 0
for r in rows:
    nid, raw_id, court, title, case_no, url, content = r
    if raw_id.startswith("rmfyb_art_"):
        news_count += 1
        print(f"NEWS: ID={nid} | raw_id={raw_id} | title={title}")
    else:
        notice_count += 1

print(f"News rows: {news_count}, Notice rows: {notice_count}")
