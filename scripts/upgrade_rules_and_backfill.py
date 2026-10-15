# -*- coding: utf-8 -*-
import sqlite3
import os
import sys
import json
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
from backend.database import SessionLocal
from backend.models import CourtNotice, MonitorRule, AlertEvent
from backend.engine.rule_matcher import match_new_notices

db = SessionLocal()

# 1. 修复数据库中 publish_time 为 NULL 的记录
null_records = db.query(CourtNotice).filter(CourtNotice.publish_time == None).all()
print(f"Found {len(null_records)} notices with NULL publish_time. Updating to created_at...")
for n in null_records:
    n.publish_time = n.created_at or datetime.now()
db.commit()

# 2. 升级核心监控规则
rules = db.query(MonitorRule).all()
all_henan_cities = [
    "全省", "郑州", "洛阳", "开封", "平顶山", "安阳", "鹤壁",
    "新乡", "焦作", "濮阳", "许昌", "漯河", "三门峡", "南阳",
    "商丘", "信阳", "周口", "驻马店", "济源"
]

for r in rules:
    if r.id == 1:
        # 河南省重点不动产司法拍卖精准监控
        r.platforms = json.dumps(["ali", "jd", "caa", "local_paper", "ggzy"], ensure_ascii=False)
        r.module_types = json.dumps(["拍卖公告"], ensure_ascii=False)
        r.cities = json.dumps(all_henan_cities, ensure_ascii=False)
        r.keywords = json.dumps([
            "住宅", "商铺", "厂房", "土地", "公寓", "大厦", "房产", "房屋",
            "写字楼", "门面", "别墅", "楼房", "不动产", "起拍", "拍卖", "变卖"
        ], ensure_ascii=False)
        r.exclude_keywords = json.dumps(["车位", "储藏室", "废旧", "杂物间"], ensure_ascii=False)
        print("Updated Rule 1 (不动产司法拍卖)")
    elif r.id == 2:
        # 涉豫大额金融不良债权与资产包招商
        r.platforms = json.dumps(["ali", "jd", "caa", "ggzy", "local_paper"], ensure_ascii=False)
        r.module_types = json.dumps(["债权转让"], ensure_ascii=False)
        r.cities = json.dumps(["全省"], ensure_ascii=False)
        r.keywords = json.dumps([
            "债权", "不良资产", "抵押", "借款合同", "资产包", "应收账款", "股权", "破产资产"
        ], ensure_ascii=False)
        print("Updated Rule 2 (金融不良债权)")
    elif r.id == 3:
        # 河南重点法院企业破产清算与重组预警
        r.platforms = json.dumps(["ali", "jd", "rmfyb", "local_paper", "ggzy"], ensure_ascii=False)
        r.module_types = json.dumps(["公告"], ensure_ascii=False)
        r.cities = json.dumps(all_henan_cities, ensure_ascii=False)
        r.keywords = json.dumps(["破产", "重整", "债权申报", "清算", "重组"], ensure_ascii=False)
        print("Updated Rule 3 (破产重组)")
    elif r.id == 4:
        # 53BK地方报纸
        r.platforms = json.dumps(["local_paper"], ensure_ascii=False)
        r.cities = json.dumps(["全省"], ensure_ascii=False)
        print("Updated Rule 4 (地方报纸)")

db.commit()

# 3. 执行全量预警回溯匹配
all_notices = db.query(CourtNotice).all()
print(f"Total notices in DB: {len(all_notices)}. Running match_new_notices...")
created_alerts = match_new_notices(db, all_notices)
print(f"Created {len(created_alerts)} new alerts through backfill.")

total_alerts = db.query(AlertEvent).count()
print(f"Total alert events now in DB: {total_alerts}")

db.close()
