# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT min(created_at), max(created_at) FROM court_notices")
print("court_notices created_at min/max:", c.fetchone())

c.execute("SELECT id, platform, title, created_at, publish_time FROM court_notices ORDER BY id DESC LIMIT 5")
for r in c.fetchall():
    print(r)

print("Current local time now:", datetime.now())
print("Current utc time now:", datetime.utcnow())
