# -*- coding: utf-8 -*-
import sqlite3
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(os.path.join('data', 'court_notices.db'))
c = conn.cursor()
print("=== All JD notices created today ===")
for r in c.execute('''
    SELECT id, title, court_name, publish_time, created_at, is_henan, henan_city, module_type 
    FROM court_notices 
    WHERE platform = 'jd' AND substr(created_at, 1, 10) = '2026-10-13'
'''):
    print(r)
