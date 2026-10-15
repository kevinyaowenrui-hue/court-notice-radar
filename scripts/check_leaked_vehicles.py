# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
from backend.utils import is_vehicle_or_equipment_item

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, platform, raw_id, title, asset_category, substr(content_text, 1, 200) FROM court_notices")
rows = c.fetchall()

flagged = []
for r in rows:
    nid, platform, raw_id, title, cat, content = r
    if is_vehicle_or_equipment_item(title, content):
        flagged.append(r)

print(f"Total notices checked: {len(rows)}")
print(f"Notices flagged as vehicle/equipment: {len(flagged)}")
for f in flagged:
    print(f"ID={f[0]}, [{f[1]}] cat='{f[4]}', title='{f[3]}'")
