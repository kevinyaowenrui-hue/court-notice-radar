# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()
c.execute("SELECT id, raw_id, title, asset_category, content_text FROM court_notices WHERE id=1107")
r = c.fetchone()
print(f"ID={r[0]}, title={r[2]}, cat={r[3]}")
print(f"Content: {r[4][:500]}")
