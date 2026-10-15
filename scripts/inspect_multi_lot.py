# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

ids = [737, 736, 735, 605, 604, 610, 608]
for nid in ids:
    c.execute("SELECT id, raw_id, title, starting_price, substr(content_text, 1, 300) FROM court_notices WHERE id=?", (nid,))
    r = c.fetchone()
    print("="*60)
    print(f"ID={r[0]}, raw={r[1]}, price={r[3]}, title={r[2]}")
    print(r[4])
