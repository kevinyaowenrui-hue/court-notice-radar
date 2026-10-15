# -*- coding: utf-8 -*-
import sqlite3
import json
from datetime import datetime

def update_rules():
    conn = sqlite3.connect('data/court_notices.db')
    cursor = conn.cursor()

    # 1. 扩充规则 1 平台覆盖 (纳入人民法院报)
    cursor.execute("""
        UPDATE monitor_rules 
        SET platforms = ?
        WHERE id = 1
    """, (json.dumps(["ali", "jd", "caa", "local_paper", "ggzy", "rmfysszc", "rmfyb"], ensure_ascii=False),))

    # 2. 扩充规则 5 与规则 6 平台覆盖 (纳入中拍平台与公共资源)
    cursor.execute("""
        UPDATE monitor_rules 
        SET platforms = ?
        WHERE id IN (5, 6)
    """, (json.dumps(["rmfysszc", "ali", "jd", "caa", "ggzy"], ensure_ascii=False),))

    # 3. 检查是否存在专门针对《人民法院报》的诉讼送达开庭监控规则 (Rule 7)
    cursor.execute("SELECT id FROM monitor_rules WHERE name LIKE '%人民法院报%'")
    existing_r7 = cursor.fetchone()
    if not existing_r7:
        cursor.execute("""
            INSERT INTO monitor_rules (
                name, is_active, platforms, courts, parties, case_numbers, 
                keywords, exclude_keywords, cities, module_types, notify_browser, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "【法网雷达】《人民法院报》及公告网 · 涉豫诉讼送达/传票/执行拍卖全景监控",
            1,
            json.dumps(["rmfyb", "rmfysszc", "local_paper"], ensure_ascii=False),
            json.dumps([], ensure_ascii=False),
            json.dumps([], ensure_ascii=False),
            json.dumps([], ensure_ascii=False),
            json.dumps(["送达", "传票", "判决", "起诉", "执行", "拍卖", "变卖", "破产", "清算", "借款", "纠纷", "公告"], ensure_ascii=False),
            json.dumps(["注销声明", "寻人启事", "致歉声明"], ensure_ascii=False),
            json.dumps(["全省"], ensure_ascii=False),
            json.dumps(["公告", "拍卖公告"], ensure_ascii=False),
            1,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        print("成功创建规则 7: 【法网雷达】《人民法院报》及公告网 · 涉豫诉讼送达/传票/执行拍卖全景监控！")
    else:
        print("规则 7 已存在，跳过插入。")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    update_rules()
