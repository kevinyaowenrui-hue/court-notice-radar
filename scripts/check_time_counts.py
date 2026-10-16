# -*- coding: utf-8 -*-
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('data/court_notices.db')
cur = conn.cursor()

today = datetime.now().date()
today_start = today.strftime('%Y-%m-%d 00:00:00')
today_end = today.strftime('%Y-%m-%d 23:59:59')
d3_start = (today - timedelta(days=2)).strftime('%Y-%m-%d 00:00:00')
d7_start = (today - timedelta(days=6)).strftime('%Y-%m-%d 00:00:00')

print('Court Notices counts:')
print('today:', cur.execute("SELECT COUNT(*) FROM court_notices WHERE publish_time >= ? AND publish_time <= ?", (today_start, today_end)).fetchone()[0])
print('3days:', cur.execute("SELECT COUNT(*) FROM court_notices WHERE publish_time >= ? AND publish_time <= ?", (d3_start, today_end)).fetchone()[0])
print('7days:', cur.execute("SELECT COUNT(*) FROM court_notices WHERE publish_time >= ? AND publish_time <= ?", (d7_start, today_end)).fetchone()[0])
print('all:', cur.execute("SELECT COUNT(*) FROM court_notices").fetchone()[0])

print('\nAlert Events counts:')
print('today:', cur.execute("SELECT COUNT(*) FROM alert_events a JOIN court_notices n ON a.notice_id = n.id WHERE n.publish_time >= ? AND n.publish_time <= ?", (today_start, today_end)).fetchone()[0])
print('3days:', cur.execute("SELECT COUNT(*) FROM alert_events a JOIN court_notices n ON a.notice_id = n.id WHERE n.publish_time >= ? AND n.publish_time <= ?", (d3_start, today_end)).fetchone()[0])
print('7days:', cur.execute("SELECT COUNT(*) FROM alert_events a JOIN court_notices n ON a.notice_id = n.id WHERE n.publish_time >= ? AND n.publish_time <= ?", (d7_start, today_end)).fetchone()[0])
print('all:', cur.execute("SELECT COUNT(*) FROM alert_events").fetchone()[0])
