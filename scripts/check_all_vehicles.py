# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

vehicle_keywords = [
    "车", "货车", "轿车", "客车", "挂车", "牵引车", "搅拌车", "冷藏车", "厢式车",
    "自卸车", "半挂", "重卡", "轻卡", "皮卡", "挖掘机", "装载机", "起重机", "吊车",
    "压路机", "推土机", "叉车", "泵车", "收割机", "拖拉机", "机动车", "小轿车", "越野车",
    "龙门吊", "行车", "冲床", "剪板机", "折弯机", "数控机床", "高空作业平台"
]

print("=== Checking all potential vehicles/machinery in DB ===")
c.execute("SELECT id, platform, raw_id, title, asset_category FROM court_notices")
rows = c.fetchall()

found = []
for r in rows:
    nid, platform, raw_id, title, cat = r
    for kw in vehicle_keywords:
        if kw in title:
            found.append((nid, platform, raw_id, title, cat, kw))
            break

print(f"Total potential matches: {len(found)}")
for f in found:
    print(f"ID={f[0]}, [{f[1]}] cat='{f[4]}', kw='{f[5]}', title='{f[3]}'")
