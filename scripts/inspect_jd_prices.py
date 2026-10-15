# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')
import sqlite3
from backend.utils import extract_starting_and_eval_price

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, raw_id, title, starting_price, eval_price, source_url, content_text FROM court_notices WHERE platform='jd' AND starting_price IS NULL LIMIT 10")
rows = c.fetchall()

print(f"Sample JD rows without starting_price:")
for r in rows:
    sp, ep = extract_starting_and_eval_price(r[2], r[6])
    print(f"ID={r[0]} | raw_id={r[1]} | title={r[2][:30]} | extracted_sp={sp} | extracted_ep={ep} | url={r[5]}")
