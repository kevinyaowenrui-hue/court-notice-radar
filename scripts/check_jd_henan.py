# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
from backend.utils import detect_henan_info

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, raw_id, title, court_name, parties, is_henan, henan_city, content_text FROM court_notices WHERE platform='jd'")
rows = c.fetchall()

detected = 0
missed_before = []

for r in rows:
    nid, raw_id, title, court, parties, is_h, h_city, content = r
    new_h, new_city, new_tag = detect_henan_info(
        title=title,
        content=content or "",
        court_name=court or "",
        parties=parties or ""
    )
    if new_h:
        detected += 1
        if not is_h:
            missed_before.append((nid, title, new_city, new_tag))

print(f"Total JD notices: {len(rows)}")
print(f"Currently is_henan=True: {sum(1 for r in rows if r[5])}")
print(f"Detected by detect_henan_info: {detected}")
print(f"Newly detected: {len(missed_before)}")
for m in missed_before:
    print(f"  ID={m[0]}, city={m[2]}, tag={m[3]}, title={m[1][:40]}")
