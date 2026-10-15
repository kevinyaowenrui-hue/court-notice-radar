# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, raw_id, title, publish_time, source_url, substr(content_text, 1, 200) FROM court_notices WHERE id in (1131, 1138)")
for r in c.fetchall():
    print(r)
