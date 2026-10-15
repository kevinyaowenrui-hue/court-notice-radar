# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
from backend.utils import extract_bidding_times

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, raw_id, title, bidding_start, bidding_end, content_text FROM court_notices WHERE platform='jd'")
rows = c.fetchall()

can_extract = 0
for r in rows:
    bs, be = extract_bidding_times(r[5] or "")
    if bs or be:
        can_extract += 1

print(f"Total JD notices: {len(rows)}")
print(f"Currently have bidding times: {sum(1 for r in rows if r[3])}")
print(f"Can extract bidding times from content_text: {can_extract}")
