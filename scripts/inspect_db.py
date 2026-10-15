import sqlite3

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

print("--- JD SAMPLES ---")
c.execute("SELECT raw_id, title, publish_time, created_at FROM court_notices WHERE platform='jd' LIMIT 5")
for r in c.fetchall():
    print(r)

print("\n--- ALI SAMPLES ---")
c.execute("SELECT raw_id, title, publish_time, created_at FROM court_notices WHERE platform='ali' LIMIT 5")
for r in c.fetchall():
    print(r)

print("\n--- RMFYB SAMPLES ---")
c.execute("SELECT raw_id, title, publish_time, case_number, content_text FROM court_notices WHERE platform='rmfyb' LIMIT 5")
for r in c.fetchall():
    print(r[0], r[1], r[2], r[3], r[4][:60])

print("\n--- VEHICLES / MACHINERY IN DB ---")
c.execute("SELECT id, platform, title, asset_category FROM court_notices WHERE title LIKE '%车%' or title LIKE '%机械%' or title LIKE '%货车%' LIMIT 10")
for r in c.fetchall():
    print(r)
