# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import re
from datetime import datetime

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, raw_id, title, content_text FROM court_notices WHERE platform='jd'")
rows = c.fetchall()

def advanced_extract_bidding_times(text):
    if not text:
        return None, None
    # 允许年月日中间有多余空格, 且时间支持 10:00, 10：00, 10时00分, 10时00, 10时
    # 格式 1: YYYY年MM月DD日 HH:MM 起至 YYYY年MM月DD日 HH:MM
    pat1 = r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?\s*(\d{1,2})\s*(?:[：:]|时)\s*(\d{1,2})?\s*(?:分|分?钟|秒)?\s*(?:起?至|到|-|~)\s*(\d{4})?\s*年?\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?\s*(\d{1,2})\s*(?:[：:]|时)\s*(\d{1,2})?'
    m = re.search(pat1, text)
    if m:
        try:
            y1, m1, d1 = int(m.group(1)), int(m.group(2)), int(m.group(3))
            h1 = int(m.group(4))
            min1 = int(m.group(5) or 0)
            
            y2 = int(m.group(6)) if m.group(6) else y1
            m2 = int(m.group(7))
            d2 = int(m.group(8))
            h2 = int(m.group(9))
            min2 = int(m.group(10) or 0)
            return datetime(y1, m1, d1, h1, min1), datetime(y2, m2, d2, h2, min2)
        except Exception:
            pass
    return None, None

matched = 0
for r in rows:
    bs, be = advanced_extract_bidding_times(r[3] or "")
    if bs:
        matched += 1

print(f"Total JD notices: {len(rows)}")
print(f"Matched with enhanced regex: {matched} / {len(rows)}")
