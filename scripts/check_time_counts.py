import sqlite3

conn = sqlite3.connect('data/court_notices.db')
cur = conn.cursor()

print('Court Notices counts:')
print('today:', cur.execute("SELECT COUNT(*) FROM court_notices WHERE publish_time >= '2026-10-15 00:00:00' AND publish_time <= '2026-10-15 23:59:59'").fetchone()[0])
print('3days:', cur.execute("SELECT COUNT(*) FROM court_notices WHERE publish_time >= '2026-10-13 00:00:00' AND publish_time <= '2026-10-15 23:59:59'").fetchone()[0])
print('7days:', cur.execute("SELECT COUNT(*) FROM court_notices WHERE publish_time >= '2026-10-09 00:00:00' AND publish_time <= '2026-10-15 23:59:59'").fetchone()[0])
print('all:', cur.execute("SELECT COUNT(*) FROM court_notices").fetchone()[0])

print('\nAlert Events counts:')
print('today:', cur.execute("SELECT COUNT(*) FROM alert_events a JOIN court_notices n ON a.notice_id = n.id WHERE n.publish_time >= '2026-10-15 00:00:00' AND n.publish_time <= '2026-10-15 23:59:59'").fetchone()[0])
print('3days:', cur.execute("SELECT COUNT(*) FROM alert_events a JOIN court_notices n ON a.notice_id = n.id WHERE n.publish_time >= '2026-10-13 00:00:00' AND n.publish_time <= '2026-10-15 23:59:59'").fetchone()[0])
print('7days:', cur.execute("SELECT COUNT(*) FROM alert_events a JOIN court_notices n ON a.notice_id = n.id WHERE n.publish_time >= '2026-10-09 00:00:00' AND n.publish_time <= '2026-10-15 23:59:59'").fetchone()[0])
print('all:', cur.execute("SELECT COUNT(*) FROM alert_events").fetchone()[0])
