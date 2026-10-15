# -*- coding: utf-8 -*-
import time
from backend.database import SessionLocal
from backend.models import CourtNotice, AlertEvent
from backend.engine.scheduler import run_crawler_pipeline
from backend.engine.rule_matcher import match_new_notices

def run_all_seven():
    print("=== 开始全量巡检 7 大数据源 ===")
    platforms = ["rmfysszc", "ali", "jd", "rmfyb", "local_paper", "caa", "ggzy"]
    for p in platforms:
        print(f"\n--- 执行 {p} 采集管道 ---")
        try:
            run_crawler_pipeline(p)
        except Exception as e:
            print(f"Error running pipeline {p}: {e}")

    # 全局查漏补缺式预警重算
    print("\n=== 执行全部标的与新规则二次全量对齐与匹配 ===")
    db = SessionLocal()
    all_notices = db.query(CourtNotice).all()
    new_alerts = match_new_notices(db, all_notices)
    print(f"新生成预警条数: {len(new_alerts)}")

    # 统计最新各平台预警数
    print("\n=== 各平台预警覆盖最终统计 ===")
    import sqlite3
    conn = sqlite3.connect('data/court_notices.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.platform, COUNT(a.id)
        FROM alert_events a
        JOIN court_notices c ON a.notice_id = c.id
        GROUP BY c.platform
    ''')
    for r in cursor.fetchall():
        print(f"  {r[0]}: {r[1]} 条预警")
    conn.close()
    db.close()

if __name__ == "__main__":
    run_all_seven()
