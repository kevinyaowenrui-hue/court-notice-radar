# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
from backend.utils import extract_starting_and_eval_price

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, raw_id, title, content_text FROM court_notices WHERE platform='jd' and starting_price is null")
rows = c.fetchall()

print(f"JD notices without starting_price: {len(rows)}")
can_extract = 0
for r in rows:
    sp, ep = extract_starting_and_eval_price(r[2], r[3])
    if sp:
        can_extract += 1
        print(f"ID={r[0]}, title={r[2][:30]}, extracted SP={sp}, EP={ep}")
    else:
        print(f"ID={r[0]}, title={r[2][:30]}, NO PRICE FOUND: {r[3][:120]}...")

print(f"Can extract: {can_extract} / {len(rows)}")
