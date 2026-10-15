# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import re

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, raw_id, title, case_number, length(content_text), content_text FROM court_notices WHERE platform='rmfyb'")
rows = c.fetchall()

full_text_count = 0
template_only = 0
case_in_text = 0

for r in rows:
    nid, raw_id, title, case_no, clen, content = r
    if clen and clen > 150 and "发布法院：" not in content:
        full_text_count += 1
    elif "公告完整正文：" in (content or ""):
        full_text_count += 1
    else:
        template_only += 1

    # Check if case number can be extracted from content
    if not case_no and content:
        # 尝试更多案号正则
        m = re.search(r'([（\(]\d{4}[）\)][\u4e00-\u9fa5\d]+[号字][\d\s\-号]*)', content)
        if m:
            case_in_text += 1
            print(f"Found case in ID={nid}: {m.group(1)}")

print(f"Total RMFYB: {len(rows)}")
print(f"Full text notices: {full_text_count}")
print(f"Template-only notices: {template_only}")
print(f"Case numbers currently present: {sum(1 for r in rows if r[3])}")
print(f"New case numbers extracted from content: {case_in_text}")
