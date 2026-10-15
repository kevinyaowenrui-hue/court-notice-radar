# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('data/court_notices.db')
cur = conn.cursor()

cur.execute("SELECT id, title, court_name, auction_stage, publish_time, bidding_start, source_url FROM court_notices WHERE title LIKE '%郸城%'")
rows = cur.fetchall()
print(f"Found {len(rows)} notices for 郸城:")
for r in rows:
    print(r)
    # 查看这条标的的 content_text 中关于时间的原文
    cur.execute("SELECT content_text FROM court_notices WHERE id = ?", (r[0],))
    txt = cur.fetchone()[0]
    # 查找所有日期与时间
    import re
    dates = re.findall(r'(\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日[^\n，。]{0,30})', txt)
    print("  Dates in content:", dates)

conn.close()
