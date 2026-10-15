# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import re

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, raw_id, title, case_number, substr(content_text, 1, 150) FROM court_notices WHERE platform='rmfyb'")
rows = c.fetchall()

print("--- Samples of RMFYB ---")
for r in rows[:20]:
    print(f"ID={r[0]}, case={r[3]}, title={r[2]}")
