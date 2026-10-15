# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT asset_category, count(*) FROM court_notices GROUP BY asset_category")
print("DB asset_categories:")
for r in c.fetchall():
    print(r)
