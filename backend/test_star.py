import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
import urllib.request
import json

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()
c.execute("SELECT id, title, is_starred FROM court_notices WHERE title LIKE '%医药卫生报%'")
rows = c.fetchall()
print("Found rows:", len(rows))
for r in rows:
    print(r)

if rows:
    test_id = rows[0][0]
    print(f"\nTesting POST /api/notices/{test_id}/star ...")
    req = urllib.request.Request(f"http://127.0.0.1:5220/api/notices/{test_id}/star", data=b'', method='POST')
    try:
        with urllib.request.urlopen(req) as resp:
            print("Status:", resp.status)
            print("Response:", resp.read().decode('utf-8'))
    except Exception as e:
        print("API Error:", e)
