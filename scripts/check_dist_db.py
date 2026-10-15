# -*- coding: utf-8 -*-
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('dist/法拍雷达/data/court_notices.db')
c = conn.cursor()
print('=== Notices count in dist DB ===')
print(c.execute('SELECT count(*) FROM court_notices').fetchone())
print('=== Alerts count in dist DB ===')
print(c.execute('SELECT count(*) FROM alert_events').fetchone())
print('=== Rules in dist DB ===')
for r in c.execute('SELECT id, name, platforms, keywords, cities FROM monitor_rules'):
    print(r)
print('=== Today notices in dist DB ===')
print(c.execute("SELECT count(*) FROM court_notices WHERE substr(COALESCE(publish_time, created_at), 1, 10) = '2026-10-13'").fetchone())
print('=== Today alerts in dist DB ===')
print(c.execute("SELECT count(*) FROM alert_events ae JOIN court_notices cn ON ae.notice_id = cn.id WHERE substr(COALESCE(cn.publish_time, ae.created_at), 1, 10) = '2026-10-13'").fetchone())
print('=== Today henan alerts in dist DB ===')
print(c.execute("SELECT count(*) FROM alert_events ae JOIN court_notices cn ON ae.notice_id = cn.id WHERE substr(COALESCE(cn.publish_time, ae.created_at), 1, 10) = '2026-10-13' AND cn.is_henan = 1").fetchone())
print('=== Today henan alerts details ===')
for r in c.execute("SELECT ae.id, cn.platform, cn.module_type, cn.title FROM alert_events ae JOIN court_notices cn ON ae.notice_id = cn.id WHERE substr(COALESCE(cn.publish_time, ae.created_at), 1, 10) = '2026-10-13' AND cn.is_henan = 1"):
    print(r)
conn.close()
