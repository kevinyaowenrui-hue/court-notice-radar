import sqlite3
import json
import sys
import os

# Set stdout encoding
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = 'data/court_notices.db'

def migrate_and_backfill():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Check and add columns
    c.execute("PRAGMA table_info(monitor_rules)")
    existing_cols = [col[1] for col in c.fetchall()]
    print(f"Existing monitor_rules columns: {existing_cols}")

    if 'exclude_keywords' not in existing_cols:
        print("Adding column: exclude_keywords")
        c.execute("ALTER TABLE monitor_rules ADD COLUMN exclude_keywords TEXT DEFAULT '[]'")
    if 'cities' not in existing_cols:
        print("Adding column: cities")
        c.execute("ALTER TABLE monitor_rules ADD COLUMN cities TEXT DEFAULT '[]'")
    if 'module_types' not in existing_cols:
        print("Adding column: module_types")
        c.execute("ALTER TABLE monitor_rules ADD COLUMN module_types TEXT DEFAULT '[]'")
    
    conn.commit()

    # 2. Update default rules to be clean and precise
    refined_rules = [
        {
            "id": 1,
            "name": "河南省重点不动产司法拍卖精准监控",
            "is_active": 1,
            "platforms": json.dumps(["ali", "jd", "caa"], ensure_ascii=False),
            "module_types": json.dumps(["拍卖公告"], ensure_ascii=False),
            "cities": json.dumps(["郑州", "洛阳", "开封", "新乡", "南阳"], ensure_ascii=False),
            "courts": json.dumps([], ensure_ascii=False),
            "parties": json.dumps([], ensure_ascii=False),
            "case_numbers": json.dumps([], ensure_ascii=False),
            "keywords": json.dumps(["住宅", "商铺", "厂房", "土地", "公寓", "大厦"], ensure_ascii=False),
            "exclude_keywords": json.dumps(["车位", "储藏室", "废旧", "杂物间"], ensure_ascii=False),
            "price_min": 100000,
            "price_max": None,
            "notify_browser": 1
        },
        {
            "id": 2,
            "name": "涉豫大额金融不良债权与资产包招商",
            "is_active": 1,
            "platforms": json.dumps(["caa", "ggzy"], ensure_ascii=False),
            "module_types": json.dumps(["债权转让"], ensure_ascii=False),
            "cities": json.dumps(["全省"], ensure_ascii=False),
            "courts": json.dumps([], ensure_ascii=False),
            "parties": json.dumps([], ensure_ascii=False),
            "case_numbers": json.dumps([], ensure_ascii=False),
            "keywords": json.dumps(["债权", "不良资产", "抵押", "借款合同", "资产包"], ensure_ascii=False),
            "exclude_keywords": json.dumps([], ensure_ascii=False),
            "price_min": None,
            "price_max": None,
            "notify_browser": 1
        },
        {
            "id": 3,
            "name": "河南重点法院企业破产清算与重组预警",
            "is_active": 1,
            "platforms": json.dumps(["rmfyb", "local_paper"], ensure_ascii=False),
            "module_types": json.dumps(["公告"], ensure_ascii=False),
            "cities": json.dumps(["郑州", "洛阳"], ensure_ascii=False),
            "courts": json.dumps(["河南省高级人民法院", "郑州市中级人民法院", "洛阳市中级人民法院", "金水区人民法院"], ensure_ascii=False),
            "parties": json.dumps([], ensure_ascii=False),
            "case_numbers": json.dumps(["破", "清", "重"], ensure_ascii=False),
            "keywords": json.dumps(["破产", "重整", "债权申报", "清算", "重组"], ensure_ascii=False),
            "exclude_keywords": json.dumps(["注销公告", "减资公告"], ensure_ascii=False),
            "price_min": None,
            "price_max": None,
            "notify_browser": 1
        }
    ]

    for r in refined_rules:
        c.execute("""
            UPDATE monitor_rules SET
                name = ?,
                is_active = ?,
                platforms = ?,
                module_types = ?,
                cities = ?,
                courts = ?,
                parties = ?,
                case_numbers = ?,
                keywords = ?,
                exclude_keywords = ?,
                price_min = ?,
                price_max = ?,
                notify_browser = ?
            WHERE id = ?
        """, (
            r["name"], r["is_active"], r["platforms"], r["module_types"], r["cities"],
            r["courts"], r["parties"], r["case_numbers"], r["keywords"], r["exclude_keywords"],
            r["price_min"], r["price_max"], r["notify_browser"], r["id"]
        ))
    conn.commit()
    print("Default monitor rules updated.")

    # 3. Clean and backfill alert_events
    c.execute("DELETE FROM alert_events")
    conn.commit()
    print("Cleared legacy noisy alert_events.")

    conn.close()

if __name__ == '__main__':
    migrate_and_backfill()
