# -*- coding: utf-8 -*-
import json
import sqlite3
from backend.database import SessionLocal
from backend.models import MonitorRule, CourtNotice, AlertEvent
from backend.engine.rule_matcher import match_new_notices

db = SessionLocal()

# 1. 检查现有规则并将 rmfysszc 加入多渠道监控规则
rules = db.query(MonitorRule).all()
print(f"Total existing rules: {len(rules)}")

for r in rules:
    try:
        plats = json.loads(r.platforms) if r.platforms else []
    except Exception:
        plats = []
    
    # 如果该规则监控了法拍平台 (ali 或 jd)，自动补上 rmfysszc
    if "ali" in plats or "jd" in plats or not plats:
        if "rmfysszc" not in plats:
            plats.append("rmfysszc")
            r.platforms = json.dumps(plats, ensure_ascii=False)
            print(f"Updated platforms for rule [{r.id}] {r.name}: {r.platforms}")

# 2. 注入针对一拍/二拍刚上拍房源的专属黄金规则
rule1_name = "【高优】诉讼资产网 · 刚上拍一拍涉豫房源 (30天尽调黄金期)"
r1 = db.query(MonitorRule).filter(MonitorRule.name == rule1_name).first()
if not r1:
    r1 = MonitorRule(
        name=rule1_name,
        is_active=True,
        platforms=json.dumps(["rmfysszc", "ali", "jd"], ensure_ascii=False),
        module_types=json.dumps(["拍卖公告"], ensure_ascii=False),
        keywords=json.dumps(["一拍", "第一次拍卖", "房", "住宅", "不动产"], ensure_ascii=False),
        cities=json.dumps(["全省"], ensure_ascii=False),
        notify_browser=True
    )
    db.add(r1)
    print(f"Created golden rule: {rule1_name}")

rule2_name = "【捡漏】诉讼资产网 · 二拍超值涉豫房源 (15天公示捡漏)"
r2 = db.query(MonitorRule).filter(MonitorRule.name == rule2_name).first()
if not r2:
    r2 = MonitorRule(
        name=rule2_name,
        is_active=True,
        platforms=json.dumps(["rmfysszc", "ali", "jd"], ensure_ascii=False),
        module_types=json.dumps(["拍卖公告"], ensure_ascii=False),
        keywords=json.dumps(["二拍", "第二次拍卖", "房", "住宅"], ensure_ascii=False),
        cities=json.dumps(["全省"], ensure_ascii=False),
        notify_browser=True
    )
    db.add(r2)
    print(f"Created golden rule: {rule2_name}")

db.commit()

# 3. 对所有 rmfysszc 标的执行规则匹配，生成预警事件
rmfysszc_notices = db.query(CourtNotice).filter(CourtNotice.platform == "rmfysszc").all()
print(f"Matching rules against {len(rmfysszc_notices)} rmfysszc notices...")
new_alerts = match_new_notices(db, rmfysszc_notices)
print(f"New alerts generated for rmfysszc: {len(new_alerts)}")

# 统计当前 rmfysszc 命中预警总数
total_rmfysszc_alerts = db.query(AlertEvent).join(CourtNotice, AlertEvent.notice_id == CourtNotice.id).filter(CourtNotice.platform == "rmfysszc").count()
print(f"Total rmfysszc alerts in database: {total_rmfysszc_alerts}")

db.close()
