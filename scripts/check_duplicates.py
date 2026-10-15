# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')
import sqlite3

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

print("--- Duplicate titles per platform ---")
c.execute("""
    SELECT platform, title, count(*) 
    FROM court_notices 
    GROUP BY platform, title 
    HAVING count(*) > 1
""")
rows = c.fetchall()
print(f"Total title duplicate groups: {len(rows)}")
for r in rows[:15]:
    print(r[0], r[2], r[1][:50])

print("\n--- Check raw_id duplicates or near-duplicates ---")
c.execute("""
    SELECT platform, court_name, parties, notice_type, count(*)
    FROM court_notices
    WHERE platform in ('rmfyb', 'jd')
    GROUP BY platform, court_name, parties, notice_type
    HAVING count(*) > 1
""")
dup_c = c.fetchall()
print(f"Total court+parties duplicate groups: {len(dup_c)}")
for r in dup_c[:10]:
    print(r)
