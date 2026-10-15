# -*- coding: utf-8 -*-
import sqlite3
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(os.path.join('data', 'court_notices.db'))
c = conn.cursor()
print("=== Ali alerts today ===")
for r in c.execute('''
    SELECT ae.id, ae.rule_id, ae.rule_name, ae.match_reason, cn.title 
    FROM alert_events ae 
    JOIN court_notices cn ON ae.notice_id = cn.id 
    WHERE cn.platform = 'ali' AND substr(COALESCE(cn.publish_time, ae.created_at), 1, 10) = '2026-10-13'
'''):
    print(r)
