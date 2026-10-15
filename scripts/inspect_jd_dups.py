# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')
import sqlite3

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, raw_id, title, court_name, starting_price, source_url FROM court_notices WHERE platform='jd' GROUP BY title HAVING count(*) > 1")
titles = [r[2] for r in c.fetchall()]

for t in titles[:5]:
    print(f"\n--- Title: {t} ---")
    c.execute("SELECT id, raw_id, title, court_name, starting_price, source_url FROM court_notices WHERE platform='jd' AND title=?", (t,))
    for r in c.fetchall():
        print(r)
