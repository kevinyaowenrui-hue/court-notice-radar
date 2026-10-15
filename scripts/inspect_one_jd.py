# -*- coding: utf-8 -*-
import sqlite3
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(os.path.join('data', 'court_notices.db'))
conn.row_factory = sqlite3.Row
c = conn.cursor()
r = c.execute("SELECT * FROM court_notices WHERE raw_id = 'jd_311261268'").fetchone()
for k in r.keys():
    print(f"{k}: {r[k]}")
