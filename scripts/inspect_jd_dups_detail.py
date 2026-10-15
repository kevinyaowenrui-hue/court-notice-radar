# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("""
    SELECT title, count(*) 
    FROM court_notices 
    WHERE platform='jd'
    GROUP BY title 
    HAVING count(*) > 1
""")
for r in c.fetchall():
    print(r)
    c.execute("SELECT id, raw_id, title, court_name, starting_price, publish_time, source_url FROM court_notices WHERE platform='jd' and title=?", (r[0],))
    for item in c.fetchall():
        print("   ", item)
