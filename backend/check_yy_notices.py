import sqlite3

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()
c.execute("SELECT id, platform, raw_id, title, is_starred, user_notes FROM court_notices WHERE title LIKE '%医药卫生报%'")
for r in c.fetchall():
    print(r)
