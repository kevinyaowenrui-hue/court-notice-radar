# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import re

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, title, court_name, parties, content_text FROM court_notices WHERE platform='jd' and is_henan=0")
rows = c.fetchall()

print(f"Non-Henan JD notices: {len(rows)}")
regions = []
for r in rows:
    # 提取省份或城市
    m = re.search(r'([\u4e00-\u9fa5]{2,6}(?:省|市|区|县))', r[1])
    reg = m.group(1) if m else "未知"
    regions.append(reg)

from collections import Counter
print("Region distribution:", Counter(regions).most_common(15))
for r in rows[:10]:
    print(f"ID={r[0]}, title={r[1][:35]}")
