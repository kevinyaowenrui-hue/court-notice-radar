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
    WHERE platform='rmfyb'
    GROUP BY title 
    HAVING count(*) > 1
""")
for r in c.fetchall():
    print(r)
    c.execute("SELECT id, raw_id, title, court_name, parties, case_number, publish_time, substr(content_text, 1, 150) FROM court_notices WHERE platform='rmfyb' and title=?", (r[0],))
    for item in c.fetchall():
        print("   ", item)
