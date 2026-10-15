# -*- coding: utf-8 -*-
import sqlite3
import re

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, platform, title, content_text FROM court_notices WHERE platform in ('ali', 'jd')")
rows = c.fetchall()

found_dates = 0
for r in rows:
    nid, platform, title, content = r
    # look for dates in title or content
    matches = re.findall(r'(202[0-6][年\-/]\d{1,2}[月\-/]\d{1,2}(?:日)?)', f"{title} {content}")
    if matches:
        found_dates += 1

print(f"Total rows: {len(rows)}, with date strings: {found_dates}")
