# -*- coding: utf-8 -*-
import sqlite3
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(os.path.join('data', 'court_notices.db'))
c = conn.cursor()
print("=== CAA Notices ===")
for r in c.execute("SELECT id, title, is_henan, henan_city, module_type, publish_time FROM court_notices WHERE platform = 'caa' LIMIT 10"):
    print(r)
conn.close()
