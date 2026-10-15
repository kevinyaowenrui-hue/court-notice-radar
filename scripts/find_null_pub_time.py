# -*- coding: utf-8 -*-
import sqlite3
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(os.path.join('data', 'court_notices.db'))
c = conn.cursor()
print("=== Records with publish_time IS NULL ===")
for r in c.execute('''
    SELECT platform, raw_id, title, created_at 
    FROM court_notices 
    WHERE publish_time IS NULL
    LIMIT 20
'''):
    print(r)
