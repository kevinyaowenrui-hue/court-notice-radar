# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()
c.execute("SELECT asset_category, count(*) FROM court_notices GROUP BY asset_category")
for r in c.fetchall():
    print(f"{r[0]}: {r[1]}")
