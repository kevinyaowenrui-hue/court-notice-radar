# -*- coding: utf-8 -*-
import sqlite3
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(os.path.join('data', 'court_notices.db'))
c = conn.cursor()

print("=== Today Henan JD notices without alerts ===")
q = """
SELECT cn.id, cn.raw_id, cn.title, cn.henan_city, cn.module_type, cn.starting_price
FROM court_notices cn
WHERE cn.platform = 'jd' 
  AND cn.is_henan = 1 
  AND substr(COALESCE(cn.publish_time, cn.created_at), 1, 10) = '2026-10-13'
  AND cn.id NOT IN (SELECT notice_id FROM alert_events)
"""
for r in c.execute(q):
    print(r)

print("\n=== Today Henan GGZY notices without alerts ===")
q_ggzy = """
SELECT cn.id, cn.raw_id, cn.title, cn.henan_city, cn.module_type
FROM court_notices cn
WHERE cn.platform = 'ggzy' 
  AND cn.is_henan = 1 
  AND substr(COALESCE(cn.publish_time, cn.created_at), 1, 10) = '2026-10-13'
  AND cn.id NOT IN (SELECT notice_id FROM alert_events)
"""
for r in c.execute(q_ggzy):
    print(r)

conn.close()
