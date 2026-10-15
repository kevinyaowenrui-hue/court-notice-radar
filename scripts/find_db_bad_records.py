# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
from backend.utils import is_vehicle_or_equipment_item, is_promotional_content

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, platform, raw_id, title, asset_category, content_text FROM court_notices")
rows = c.fetchall()

vehicles = []
promos = []

for r in rows:
    nid, platform, raw_id, title, cat, content = r
    if is_vehicle_or_equipment_item(title, content):
        vehicles.append((nid, platform, title, cat))
    if is_promotional_content(title, content):
        promos.append((nid, platform, title, cat))

print(f"Vehicle/equipment items in DB: {len(vehicles)}")
for v in vehicles:
    print(f"  ID={v[0]} [{v[1]}] cat='{v[3]}' title='{v[2]}'")

print(f"\nPromotional items in DB: {len(promos)}")
for p in promos:
    print(f"  ID={p[0]} [{p[1]}] cat='{p[3]}' title='{p[2]}'")
