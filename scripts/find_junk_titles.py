# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, platform, raw_id, title, asset_category FROM court_notices")
rows = c.fetchall()

junk = []
for r in rows:
    nid, platform, raw_id, title, cat = r
    # Check countdown or status string titles
    if any(k in title for k in ["预计今日", "预计", "结束", "进行中", "即将开始"]) and len(title) < 25 and not any(k in title for k in ["房", "债", "地", "拍卖"]):
        junk.append(r)
    elif any(k in title for k in ["洗发水", "沐浴露", "打捆机"]):
        junk.append(r)

print(f"Junk titles found: {len(junk)}")
for j in junk:
    print(f"ID={j[0]}, [{j[1]}] cat='{j[4]}', title='{j[3]}'")
