# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, raw_id, title, court_name, parties, case_number, publish_time, substr(content_text, 1, 150) FROM court_notices WHERE platform='rmfyb' and parties like '%恒大%'")
rows = c.fetchall()
print(f"Total Evergrande rows: {len(rows)}")
for r in rows:
    print(f"ID={r[0]}, raw_id={r[1]}, case={r[5]}, pub={r[6]}")
    print(f"  title={r[2]}")
    print(f"  content={r[7]}\n")
