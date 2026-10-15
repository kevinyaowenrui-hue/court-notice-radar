# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')
import sqlite3

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, raw_id, court_name, title, case_number, source_url, content_text FROM court_notices WHERE platform='rmfyb' AND raw_id NOT LIKE 'rmfyb_art_%' LIMIT 5")
rows = c.fetchall()
for r in rows:
    print("ID:", r[0])
    print("RAW_ID:", r[1])
    print("COURT:", r[2])
    print("TITLE:", r[3])
    print("CASE:", r[4])
    print("URL:", r[5])
    print("CONTENT:\n", r[6])
    print("="*40)
