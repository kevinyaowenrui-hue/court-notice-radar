# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT count(*), count(case_number), sum(case when case_number != '' and case_number is not null then 1 else 0 end) FROM court_notices WHERE platform='rmfyb'")
total, not_null, non_empty = c.fetchone()
print(f"RMFYB total: {total}, with case_number: {non_empty} ({non_empty/total*100:.1f}%)")

c.execute("SELECT id, raw_id, title, case_number, court_name, parties, length(content_text) FROM court_notices WHERE platform='rmfyb' LIMIT 10")
for r in c.fetchall():
    print(r)

print("\n--- Check if any non-court notices exist in RMFYB ---")
# 检查标题是否包含公告、传票、送达、裁判文书、破产、执行等法定公告词汇
c.execute("SELECT id, title FROM court_notices WHERE platform='rmfyb' AND NOT (title LIKE '%公告%' OR title LIKE '%传票%' OR title LIKE '%送达%' OR title LIKE '%裁判文书%' OR title LIKE '%判决%' OR title LIKE '%裁定%' OR title LIKE '%执行%' OR title LIKE '%破产%')")
bad = c.fetchall()
print(f"Non-notice titles in RMFYB: {len(bad)}")
for b in bad:
    print("  Bad title:", b)
