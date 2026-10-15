import sys
sys.path.insert(0, '.')
import sqlite3

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, platform, title, asset_category FROM court_notices")
rows = c.fetchall()

from backend.utils import is_vehicle_or_equipment_item

print(f"Total notices in db: {len(rows)}")

leaked = []
for r in rows:
    nid, platform, title, cat = r
    # check if title contains vehicle or equipment keywords
    v_words = ["车", "挂车", "牵引车", "货车", "搅拌车", "轿车", "自卸车", "挖掘机", "叉车", "机械", "机床", "设备", "冷藏车"]
    if any(w in title for w in v_words):
        is_ve = is_vehicle_or_equipment_item(title)
        leaked.append((nid, platform, title, cat, is_ve))

print(f"Items matching vehicle/equipment keywords: {len(leaked)}")
for r in leaked:
    nid, platform, title, cat, is_ve = r
    print(f"[{platform}] ID={nid} | CAT={cat} | IS_VE={is_ve} | TITLE={title}")
