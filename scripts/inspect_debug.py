# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()
c.execute("SELECT id, publish_time FROM court_notices WHERE publish_time LIKE '%.%' AND publish_time NOT LIKE '%.000000'")
rows = c.fetchall()
print("Non-zero microseconds in publish_time:", len(rows), rows)
