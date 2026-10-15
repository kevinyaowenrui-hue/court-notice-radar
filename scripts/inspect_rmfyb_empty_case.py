# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, raw_id, title, content_text FROM court_notices WHERE platform='rmfyb' and (case_number='' or case_number is null) LIMIT 5")
for r in c.fetchall():
    print("="*60)
    print(f"ID={r[0]}, raw_id={r[1]}, title={r[2]}")
    print(f"Content:\n{r[3]}")
