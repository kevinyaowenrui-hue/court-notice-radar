# -*- coding: utf-8 -*-
import io
import sys
import csv
import json
import os
from datetime import datetime, timedelta, time as dt_time
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, and_, case, func

from backend.database import get_db, SessionLocal
from backend.models import CourtNotice, MonitorRule, AlertEvent, PaperSeed, TaskLog, SystemSetting
from backend.mock_data import init_database_and_seeds
from contextlib import asynccontextmanager
import ipaddress
import socket
from urllib.parse import urlparse

from backend.engine.scheduler import start_scheduler, run_crawler_pipeline, trigger_run_all_crawlers, get_running_platforms
from backend.engine.rule_matcher import check_match, match_new_notices
from backend.engine.webhook import get_webhook_config, save_webhook_config, test_webhook
from backend.crawlers.seed_53bk import sync_53bk_seeds
from backend.utils import extract_risk_tags

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Server] Ensuring DB integrity & clean startup...")
    from backend.database import ensure_db_integrity, DB_PATH, SEED_PATH, engine
    ensure_db_integrity(DB_PATH, SEED_PATH)
    try:
        from backend.clean_and_migrate_db import clean_database
        clean_database(DB_PATH)
    except Exception as ce:
        print(f"[Server] Startup database clean note: {ce}")
    init_database_and_seeds()
    print("[Server] Starting scheduler...")
    start_scheduler()
    yield
    print("[Server] Shutting down scheduler & checkpointing SQLite WAL...")
    try:
        from backend.engine.scheduler import scheduler
        if scheduler.running:
            scheduler.shutdown(wait=False)
    except Exception as e:
        print(f"[Server] Scheduler shutdown note: {e}")
    try:
        from backend.database import engine
        with engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE);")
        engine.dispose()
        print("[Server] SQLite WAL checkpointed and engine disposed.")
    except Exception as e:
        print(f"[Server] WAL checkpoint error: {e}")

app = FastAPI(title="法院案件公示与法拍监控采集系统", version="1.0.0", lifespan=lifespan)

# Enable CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def validate_webhook_url(url: str, platform: str):
    """验证 Webhook URL，严防 SSRF 探测内网或回环地址"""
    if not url:
        return
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Webhook URL 必须使用 http 或 https 协议")
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="Webhook URL 缺少有效的主机名")

    whitelist = {
        "wecom": ["qyapi.weixin.qq.com"],
        "dingtalk": ["oapi.dingtalk.com"],
        "feishu": ["open.feishu.cn"],
    }
    if platform in whitelist:
        if not any(hostname.lower() == d or hostname.lower().endswith("." + d) for d in whitelist[platform]):
            raise HTTPException(status_code=400, detail=f"{platform} Webhook 域名必须为官方合法域名 ({', '.join(whitelist[platform])})")
        if parsed.scheme.lower() != "https":
            raise HTTPException(status_code=400, detail=f"{platform} Webhook 必须使用 https 协议")
    else:
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for item in addr_info:
                ip_str = item[4][0]
                ip_obj = ipaddress.ip_address(ip_str)
                if ip_obj.is_loopback or ip_obj.is_private or ip_obj.is_link_local or ip_obj.is_reserved or ip_obj.is_multicast:
                    raise HTTPException(status_code=400, detail=f"安全拒绝: 目标 IP ({ip_str}) 属于内网或回环地址，禁止 SSRF 访问")
        except socket.gaierror:
            raise HTTPException(status_code=400, detail="无法解析 Webhook 主机名")

def sanitize_csv_cell(val):
    """CSV 公式注入防御转义"""
    if val is None:
        return ""
    s = str(val)
    if s and s[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + s
    return s

# ----------------- Schemas -----------------
class RuleCreateOrUpdate(BaseModel):
    name: str
    is_active: bool = True
    platforms: List[str] = ["ali", "jd", "rmfyb", "local_paper", "caa", "ggzy"]
    module_types: List[str] = []
    cities: List[str] = []
    courts: List[str] = []
    parties: List[str] = []
    case_numbers: List[str] = []
    keywords: List[str] = []
    exclude_keywords: List[str] = []
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    notify_browser: bool = True
    backfill: bool = False

class WebhookConfigUpdate(BaseModel):
    enabled: bool = False
    platform: str = "wecom"
    webhook_url: str = ""
    secret: str = ""
    notify_on_new: bool = True

class NoticeNotesUpdate(BaseModel):
    notes: str

# ----------------- API Endpoints -----------------

@app.get("/api/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """获取看板整体统计数据（含河南专属指标）"""
    total_notices = db.query(CourtNotice).count()
    total_alerts = db.query(AlertEvent).count()
    unread_alerts = db.query(AlertEvent).filter(AlertEvent.is_read == False).count()
    monitored_papers = db.query(PaperSeed).filter(PaperSeed.is_monitored == True).count()
    total_papers = db.query(PaperSeed).count()
    
    # 河南专注模式指标统计
    total_henan_notices = db.query(CourtNotice).filter(CourtNotice.is_henan == True).count()
    henan_auctions = db.query(CourtNotice).filter(
        CourtNotice.is_henan == True,
        or_(CourtNotice.platform.in_(["ali", "jd"]), CourtNotice.notice_type == "司法拍卖")
    ).count()
    henan_cases = db.query(CourtNotice).filter(
        CourtNotice.is_henan == True,
        CourtNotice.platform.in_(["rmfyb", "local_paper"])
    ).count()

    # 河南地市覆盖统计
    henan_cities = [c[0] for c in db.query(CourtNotice.henan_city).filter(CourtNotice.is_henan == True, CourtNotice.henan_city.isnot(None)).distinct().all() if c[0]]

    # 分平台公示统计
    platforms = ["ali", "jd", "rmfysszc", "rmfyb", "local_paper", "caa", "ggzy"]
    platform_counts = {p: db.query(CourtNotice).filter(CourtNotice.platform == p).count() for p in platforms}

    # 三大核心业务模块统计（严格排除任何宣传类）
    module_counts = {
        "公告": db.query(CourtNotice).filter(CourtNotice.module_type == "公告").count(),
        "拍卖公告": db.query(CourtNotice).filter(CourtNotice.module_type == "拍卖公告").count(),
        "债权转让": db.query(CourtNotice).filter(CourtNotice.module_type == "债权转让").count(),
    }

    # 河南专属三大模块分布
    henan_module_counts = {
        "公告": db.query(CourtNotice).filter(CourtNotice.is_henan == True, CourtNotice.module_type == "公告").count(),
        "拍卖公告": db.query(CourtNotice).filter(CourtNotice.is_henan == True, CourtNotice.module_type == "拍卖公告").count(),
        "债权转让": db.query(CourtNotice).filter(CourtNotice.is_henan == True, CourtNotice.module_type == "债权转让").count(),
    }

    # 标的关注统计
    starred_count = db.query(CourtNotice).filter(CourtNotice.is_starred == True).count()

    # 最近预警
    recent_alerts = db.query(AlertEvent).order_by(desc(AlertEvent.created_at)).limit(5).all()

    today_start = datetime.combine(datetime.now().date(), dt_time.min)
    notice_today_filter = or_(CourtNotice.publish_time >= today_start, CourtNotice.created_at >= today_start)
    today_notices_count = db.query(CourtNotice).filter(notice_today_filter).count()
    today_henan_notices_count = db.query(CourtNotice).filter(notice_today_filter, CourtNotice.is_henan == True).count()
    alert_today_filter = or_(
        AlertEvent.created_at >= today_start,
        CourtNotice.created_at >= today_start,
        CourtNotice.publish_time >= today_start
    )
    today_alerts_count = db.query(AlertEvent).join(CourtNotice, AlertEvent.notice_id == CourtNotice.id).filter(alert_today_filter).count()
    today_henan_alerts_count = db.query(AlertEvent).join(CourtNotice, AlertEvent.notice_id == CourtNotice.id).filter(alert_today_filter, CourtNotice.is_henan == True).count()
    today_unread_alerts = db.query(AlertEvent).join(CourtNotice, AlertEvent.notice_id == CourtNotice.id).filter(alert_today_filter, AlertEvent.is_read == False).count()
    today_henan_unread_alerts = db.query(AlertEvent).join(CourtNotice, AlertEvent.notice_id == CourtNotice.id).filter(alert_today_filter, CourtNotice.is_henan == True, AlertEvent.is_read == False).count()

    return {
        "total_notices": total_notices,
        "total_alerts": total_alerts,
        "unread_alerts": unread_alerts,
        "today_unread_alerts": today_unread_alerts,
        "today_henan_unread_alerts": today_henan_unread_alerts,
        "starred_count": starred_count,
        "today_notices_count": today_notices_count,
        "today_henan_notices_count": today_henan_notices_count,
        "today_alerts_count": today_alerts_count,
        "today_henan_alerts_count": today_henan_alerts_count,
        "monitored_papers": monitored_papers,
        "total_papers": total_papers,
        "platform_counts": platform_counts,
        "module_counts": module_counts,
        "recent_alerts_count": len(recent_alerts),
        # 河南专精大屏指标
        "henan": {
            "total_notices": total_henan_notices,
            "auctions": henan_auctions,
            "court_cases": henan_cases,
            "cities_count": len(henan_cities),
            "cities": henan_cities,
            "module_counts": henan_module_counts
        }
    }

@app.get("/api/alerts")
def get_alerts(
    unread_only: bool = False,
    platform: Optional[str] = None,
    rule_id: Optional[int] = None,
    module_type: Optional[str] = None,
    henan_only: bool = False,
    henan_city: Optional[str] = None,
    time_range: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    db: Session = Depends(get_db)
):
    # 全局范围查询（未过滤 platform 与 module_type），用于动态统计 7 大平台在当前时效与地域下的预警分布
    scope_query = db.query(AlertEvent, CourtNotice).join(CourtNotice, AlertEvent.notice_id == CourtNotice.id)
    
    if unread_only:
        scope_query = scope_query.filter(AlertEvent.is_read == False)
    if rule_id:
        scope_query = scope_query.filter(AlertEvent.rule_id == rule_id)
    if henan_only:
        scope_query = scope_query.filter(CourtNotice.is_henan == True)
    if henan_city:
        scope_query = scope_query.filter(CourtNotice.henan_city == henan_city)

    # 时效过滤胶囊（预警触发时间或关联标的发布/入库时间满足范围）
    if time_range == "today":
        today_start = datetime.combine(datetime.now().date(), dt_time.min)
        scope_query = scope_query.filter(
            or_(
                AlertEvent.created_at >= today_start,
                CourtNotice.created_at >= today_start,
                CourtNotice.publish_time >= today_start
            )
        )
    elif time_range == "3days":
        cutoff = datetime.combine((datetime.now() - timedelta(days=3)).date(), dt_time.min)
        scope_query = scope_query.filter(
            or_(
                AlertEvent.created_at >= cutoff,
                CourtNotice.created_at >= cutoff,
                CourtNotice.publish_time >= cutoff
            )
        )
    elif time_range == "7days":
        cutoff = datetime.combine((datetime.now() - timedelta(days=7)).date(), dt_time.min)
        scope_query = scope_query.filter(
            or_(
                AlertEvent.created_at >= cutoff,
                CourtNotice.created_at >= cutoff,
                CourtNotice.publish_time >= cutoff
            )
        )

    # 1. 动态聚合当前时效/地域下的各数据源渠道预警数（7大平台全景，联动当前选中的业务模块）
    plat_query = scope_query
    if module_type:
        plat_query = plat_query.filter(CourtNotice.module_type == module_type)

    plat_group = plat_query.with_entities(
        CourtNotice.platform,
        func.count(AlertEvent.id)
    ).group_by(CourtNotice.platform).all()
    plat_counts_map = {p: c for p, c in plat_group}
    platform_counts = {
        "total": sum(plat_counts_map.values()),
        "rmfysszc": plat_counts_map.get("rmfysszc", 0),
        "ali": plat_counts_map.get("ali", 0),
        "jd": plat_counts_map.get("jd", 0),
        "rmfyb": plat_counts_map.get("rmfyb", 0),
        "local_paper": plat_counts_map.get("local_paper", 0),
        "caa": plat_counts_map.get("caa", 0),
        "ggzy": plat_counts_map.get("ggzy", 0),
    }

    # 2. 基础过滤：施加已选 platform 后的预警集合，用于动态计算各业务模块 Tab 数量
    base_query = scope_query
    if platform:
        base_query = base_query.filter(CourtNotice.platform == platform)

    # 动态聚合当前时间与属地筛选条件下的各业务模块预警数，确保 Tab 数量与当前维度严密对应
    tab_group = base_query.with_entities(
        func.coalesce(CourtNotice.module_type, "公告"),
        func.count(AlertEvent.id)
    ).group_by(func.coalesce(CourtNotice.module_type, "公告")).all()

    module_counts_map = {m: c for m, c in tab_group}
    total_in_scope = sum(module_counts_map.values())
    tab_counts = {
        "total": total_in_scope,
        "公告": module_counts_map.get("公告", 0),
        "拍卖公告": module_counts_map.get("拍卖公告", 0),
        "债权转让": module_counts_map.get("债权转让", 0),
    }

    query = base_query
    if module_type:
        query = query.filter(CourtNotice.module_type == module_type)

    total = query.count()

    # 分页计算 (兼容原有 limit/offset，同时支持页码 page/page_size)
    if limit is not None:
        actual_limit = limit
        actual_offset = offset or 0
        actual_page = (actual_offset // actual_limit) + 1
        actual_page_size = actual_limit
    else:
        actual_page = max(1, page)
        actual_page_size = max(1, min(page_size, 100))
        actual_offset = (actual_page - 1) * actual_page_size
        actual_limit = actual_page_size

    total_pages = max(1, (total + actual_page_size - 1) // actual_page_size)
    # 核心重构：预警触发时间最新优先呈现，次级按标的入库时间倒序
    items = query.order_by(desc(AlertEvent.created_at), desc(CourtNotice.created_at)).offset(actual_offset).limit(actual_limit).all()

    result = []
    for alert, notice in items:
        discount = round((notice.starting_price / notice.eval_price) * 10, 1) if (notice.starting_price and notice.eval_price and notice.eval_price > 0) else None
        eff_dt = notice.publish_time or notice.created_at
        is_today = bool((eff_dt and eff_dt.date() == datetime.now().date()) or (alert.created_at and alert.created_at.date() == datetime.now().date()))
        
        # 拍卖倒计时与刚上拍研判 (一拍法定30天，二拍法定15天)
        days_until = None
        if notice.bidding_start:
            try:
                days_until = (notice.bidding_start.date() - datetime.now().date()).days
            except Exception:
                pass
        
        is_newly_listed = False
        if notice.auction_stage in ['一拍', '第一次拍卖']:
            if (days_until is not None and days_until >= 20) or (eff_dt and (datetime.now() - eff_dt).days <= 3):
                is_newly_listed = True
        elif notice.auction_stage in ['二拍', '第二次拍卖']:
            if (days_until is not None and days_until >= 10) or (eff_dt and (datetime.now() - eff_dt).days <= 3):
                is_newly_listed = True

        result.append({
            "id": alert.id,
            "rule_id": alert.rule_id,
            "rule_name": alert.rule_name,
            "is_read": alert.is_read,
            "match_reason": alert.match_reason,
            "highlight_text": alert.highlight_text,
            "created_at": alert.created_at.strftime("%Y-%m-%d %H:%M:%S") if alert.created_at else "",
            "notice": {
                "id": notice.id,
                "platform": notice.platform,
                "module_type": notice.module_type or "公告",
                "court_name": notice.court_name,
                "case_number": notice.case_number,
                "parties": notice.parties,
                "notice_type": notice.notice_type,
                "title": notice.title,
                "content_text": notice.content_text,
                "publish_time": notice.publish_time.strftime("%Y-%m-%d %H:%M:%S") if notice.publish_time else "",
                "is_today": is_today,
                "source_url": notice.source_url,
                "starting_price": notice.starting_price,
                "eval_price": notice.eval_price,
                "discount_rate": discount,
                "auction_stage": notice.auction_stage,
                "asset_category": notice.asset_category,
                "bidding_start": notice.bidding_start.strftime("%Y-%m-%d %H:%M") if notice.bidding_start else None,
                "bidding_end": notice.bidding_end.strftime("%Y-%m-%d %H:%M") if notice.bidding_end else None,
                "days_until_bidding": days_until,
                "is_newly_listed": is_newly_listed,
                "is_henan": notice.is_henan,
                "henan_city": notice.henan_city,
                "henan_tag": notice.henan_tag,
                "is_starred": bool(getattr(notice, "is_starred", False)),
                "user_notes": getattr(notice, "user_notes", "") or "",
                "risk_tags": extract_risk_tags(f"{notice.title or ''} {notice.content_text or ''}")
            }
        })

    return {
        "total": total,
        "page": actual_page,
        "page_size": actual_page_size,
        "total_pages": total_pages,
        "tab_counts": tab_counts,
        "platform_counts": platform_counts,
        "items": result
    }

@app.post("/api/alerts/{alert_id}/read")
def mark_alert_read(alert_id: int, db: Session = Depends(get_db)):
    """标记单条预警为已读"""
    alert = db.query(AlertEvent).filter(AlertEvent.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_read = True
    db.commit()
    return {"status": "ok", "id": alert_id}

@app.post("/api/alerts/read-all")
def mark_all_alerts_read(db: Session = Depends(get_db)):
    """一键标记所有预警为已读"""
    db.query(AlertEvent).filter(AlertEvent.is_read == False).update({"is_read": True})
    db.commit()
    return {"status": "ok"}

@app.get("/api/rules")
def get_rules(db: Session = Depends(get_db)):
    """获取所有监控规则"""
    rules = db.query(MonitorRule).order_by(desc(MonitorRule.created_at)).all()
    res = []
    for r in rules:
        res.append({
            "id": r.id,
            "name": r.name,
            "is_active": r.is_active,
            "platforms": json.loads(r.platforms) if r.platforms else [],
            "module_types": json.loads(r.module_types) if getattr(r, "module_types", None) else [],
            "cities": json.loads(r.cities) if getattr(r, "cities", None) else [],
            "courts": json.loads(r.courts) if r.courts else [],
            "parties": json.loads(r.parties) if r.parties else [],
            "case_numbers": json.loads(r.case_numbers) if r.case_numbers else [],
            "keywords": json.loads(r.keywords) if r.keywords else [],
            "exclude_keywords": json.loads(r.exclude_keywords) if getattr(r, "exclude_keywords", None) else [],
            "price_min": r.price_min,
            "price_max": r.price_max,
            "notify_browser": r.notify_browser,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else ""
        })
    return res

@app.post("/api/rules/preview")
def preview_rule_matches(req: RuleCreateOrUpdate, db: Session = Depends(get_db)):
    """试运行规则：在当前数据库中模拟匹配，返回预计命中数和前 3 条样本，辅助精准调优"""
    temp_rule = MonitorRule(
        name=req.name,
        is_active=True,
        platforms=json.dumps(req.platforms, ensure_ascii=False),
        module_types=json.dumps(req.module_types, ensure_ascii=False),
        cities=json.dumps(req.cities, ensure_ascii=False),
        courts=json.dumps(req.courts, ensure_ascii=False),
        parties=json.dumps(req.parties, ensure_ascii=False),
        case_numbers=json.dumps(req.case_numbers, ensure_ascii=False),
        keywords=json.dumps(req.keywords, ensure_ascii=False),
        exclude_keywords=json.dumps(req.exclude_keywords, ensure_ascii=False),
        price_min=req.price_min,
        price_max=req.price_max
    )
    all_notices = db.query(CourtNotice).order_by(desc(CourtNotice.publish_time)).all()
    matched = []
    for n in all_notices:
        res = check_match(n, temp_rule)
        if res:
            matched.append({
                "id": n.id,
                "title": n.title,
                "platform": n.platform,
                "module_type": n.module_type,
                "court_name": n.court_name,
                "henan_city": n.henan_city,
                "match_reason": res["match_reason"]
            })
    return {
        "matched_count": len(matched),
        "total_tested": len(all_notices),
        "samples": matched[:3]
    }

@app.post("/api/rules")
def create_rule(req: RuleCreateOrUpdate, db: Session = Depends(get_db)):
    """新建监控规则（支持排除词、模块与地市定向，可选回溯存量数据）"""
    rule = MonitorRule(
        name=req.name,
        is_active=req.is_active,
        platforms=json.dumps(req.platforms, ensure_ascii=False),
        module_types=json.dumps(req.module_types, ensure_ascii=False),
        cities=json.dumps(req.cities, ensure_ascii=False),
        courts=json.dumps(req.courts, ensure_ascii=False),
        parties=json.dumps(req.parties, ensure_ascii=False),
        case_numbers=json.dumps(req.case_numbers, ensure_ascii=False),
        keywords=json.dumps(req.keywords, ensure_ascii=False),
        exclude_keywords=json.dumps(req.exclude_keywords, ensure_ascii=False),
        price_min=req.price_min,
        price_max=req.price_max,
        notify_browser=req.notify_browser
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    backfilled_count = 0
    if req.backfill:
        all_notices = db.query(CourtNotice).all()
        created_alerts = match_new_notices(db, all_notices)
        backfilled_count = len(created_alerts)

    return {"status": "ok", "id": rule.id, "backfilled_alerts": backfilled_count}

@app.put("/api/rules/{rule_id}")
def update_rule(rule_id: int, req: RuleCreateOrUpdate, db: Session = Depends(get_db)):
    """更新监控规则"""
    rule = db.query(MonitorRule).filter(MonitorRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule.name = req.name
    rule.is_active = req.is_active
    rule.platforms = json.dumps(req.platforms, ensure_ascii=False)
    rule.module_types = json.dumps(req.module_types, ensure_ascii=False)
    rule.cities = json.dumps(req.cities, ensure_ascii=False)
    rule.courts = json.dumps(req.courts, ensure_ascii=False)
    rule.parties = json.dumps(req.parties, ensure_ascii=False)
    rule.case_numbers = json.dumps(req.case_numbers, ensure_ascii=False)
    rule.keywords = json.dumps(req.keywords, ensure_ascii=False)
    rule.exclude_keywords = json.dumps(req.exclude_keywords, ensure_ascii=False)
    rule.price_min = req.price_min
    rule.price_max = req.price_max
    rule.notify_browser = req.notify_browser
    db.commit()

    if req.backfill:
        all_notices = db.query(CourtNotice).all()
        match_new_notices(db, all_notices)

    return {"status": "ok"}

@app.delete("/api/rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    """删除监控规则"""
    rule = db.query(MonitorRule).filter(MonitorRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
    return {"status": "ok"}

# ----------------- Webhook 推送配置接口 -----------------

@app.get("/api/settings/webhook")
def get_webhook_settings_api(db: Session = Depends(get_db)):
    """获取当前 Webhook 机器人推送配置（脱敏密钥）"""
    conf = get_webhook_config(db)
    if conf.get("secret"):
        conf["secret"] = "******"
    return conf

@app.post("/api/settings/webhook")
def save_webhook_settings_api(req: WebhookConfigUpdate, db: Session = Depends(get_db)):
    """保存 Webhook 机器人推送配置（校验 SSRF 及密钥脱敏兼容）"""
    validate_webhook_url(req.webhook_url, req.platform)
    old_conf = get_webhook_config(db)
    data = req.dict()
    if data.get("secret") == "******":
        data["secret"] = old_conf.get("secret", "")
    return save_webhook_config(db, data)

@app.post("/api/settings/webhook/test")
def test_webhook_settings_api(req: WebhookConfigUpdate, db: Session = Depends(get_db)):
    """测试 Webhook 连通性并向目标机器人推送一条测试卡片"""
    validate_webhook_url(req.webhook_url, req.platform)
    data = req.dict()
    if data.get("secret") == "******":
        old_conf = get_webhook_config(db)
        data["secret"] = old_conf.get("secret", "")
    return test_webhook(data)

# ----------------- 公示检索与导出接口 -----------------

@app.get("/api/notices/export")
def export_notices(
    query: Optional[str] = None,
    platform: Optional[str] = None,
    court: Optional[str] = None,
    notice_type: Optional[str] = None,
    module_type: Optional[str] = None,
    asset_category: Optional[str] = None,
    henan_only: bool = False,
    henan_city: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    discount_max: Optional[float] = None,
    sort_by: str = "publish_time_desc",
    starred_only: bool = False,
    time_range: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """导出公示检索结果为 CSV 报表（含三大业务模块及河南专属字段、折扣率、跟进便签）"""
    q = db.query(CourtNotice)
    if starred_only:
        q = q.filter(CourtNotice.is_starred == True)
    if platform:
        q = q.filter(CourtNotice.platform == platform)
    if module_type:
        q = q.filter(CourtNotice.module_type == module_type)
    if asset_category:
        if asset_category in ("房产", "住宅/商业房产"):
            q = q.filter(CourtNotice.asset_category.in_(["房产", "住宅/商业房产"]))
        else:
            q = q.filter(CourtNotice.asset_category == asset_category)
    if court:
        q = q.filter(CourtNotice.court_name.like(f"%{court}%"))
    if notice_type:
        q = q.filter(CourtNotice.notice_type.like(f"%{notice_type}%"))
    if henan_only:
        q = q.filter(CourtNotice.is_henan == True)
    if henan_city:
        q = q.filter(CourtNotice.henan_city == henan_city)

    # 时效过滤胶囊（标的发布时间或采集入库时间满足范围）
    if time_range == "today":
        today_start = datetime.combine(datetime.now().date(), dt_time.min)
        q = q.filter(
            or_(
                CourtNotice.publish_time >= today_start,
                CourtNotice.created_at >= today_start
            )
        )
    elif time_range == "3days":
        cutoff = datetime.combine((datetime.now() - timedelta(days=3)).date(), dt_time.min)
        q = q.filter(
            or_(
                CourtNotice.publish_time >= cutoff,
                CourtNotice.created_at >= cutoff
            )
        )
    elif time_range == "7days":
        cutoff = datetime.combine((datetime.now() - timedelta(days=7)).date(), dt_time.min)
        q = q.filter(
            or_(
                CourtNotice.publish_time >= cutoff,
                CourtNotice.created_at >= cutoff
            )
        )

    if price_min is not None:
        q = q.filter(CourtNotice.starting_price >= price_min)
    if price_max is not None:
        q = q.filter(CourtNotice.starting_price <= price_max)
    if discount_max is not None:
        ratio = (discount_max / 10.0) if discount_max <= 10 else (discount_max / 100.0)
        q = q.filter(
            CourtNotice.starting_price.isnot(None),
            CourtNotice.eval_price.isnot(None),
            CourtNotice.eval_price > 0,
            (CourtNotice.starting_price / CourtNotice.eval_price) <= ratio
        )
    if query:
        q = q.filter(
            or_(
                CourtNotice.title.like(f"%{query}%"),
                CourtNotice.content_text.like(f"%{query}%"),
                CourtNotice.case_number.like(f"%{query}%"),
                CourtNotice.parties.like(f"%{query}%")
            )
        )

    if sort_by == "discount_asc":
        discount_expr = case(
            (and_(CourtNotice.starting_price.isnot(None), CourtNotice.eval_price.isnot(None), CourtNotice.eval_price > 0),
             CourtNotice.starting_price / CourtNotice.eval_price),
            else_=9999.0
        )
        items = q.order_by(discount_expr.asc(), desc(CourtNotice.publish_time)).all()
    elif sort_by == "price_asc":
        price_expr = case(
            (CourtNotice.starting_price.isnot(None), CourtNotice.starting_price),
            else_=9999999999.0
        )
        items = q.order_by(price_expr.asc(), desc(CourtNotice.publish_time)).all()
    elif sort_by == "price_desc":
        price_expr = case(
            (CourtNotice.starting_price.isnot(None), CourtNotice.starting_price),
            else_=-1.0
        )
        items = q.order_by(price_expr.desc(), desc(CourtNotice.publish_time)).all()
    else:
        items = q.order_by(desc(CourtNotice.publish_time)).all()

    output = io.StringIO()
    # Write UTF-8 BOM for Excel compatibility in Windows
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow([
        "ID", "核心业务模块", "来源平台", "法院名称", "案号", "涉及当事人", "公示类型",
        "标题/标的物", "是否涉豫", "涉及地市", "涉豫特征标签",
        "起拍价(元)", "评估价(元)", "折扣率", "拍卖阶段", "发布时间", "处置便签", "原始链接"
    ])
    for n in items:
        discount = f"{round((n.starting_price / n.eval_price) * 10, 1)}折" if (n.starting_price and n.eval_price and n.eval_price > 0) else ""
        row = [
            n.id, n.module_type or "公告", n.platform, n.court_name, n.case_number or "", n.parties or "", n.notice_type,
            n.title, "是" if n.is_henan else "否", n.henan_city or "", n.henan_tag or "",
            n.starting_price or "", n.eval_price or "", discount, n.auction_stage or "",
            n.publish_time.strftime("%Y-%m-%d %H:%M") if n.publish_time else "", getattr(n, "user_notes", "") or "", n.source_url
        ]
        writer.writerow([sanitize_csv_cell(c) for c in row])

    output.seek(0)
    filename = f"court_notices_henan_{datetime.now().strftime('%Y%m%d%H%M')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )

@app.get("/api/notices")
def get_notices(
    query: Optional[str] = None,
    platform: Optional[str] = None,
    court: Optional[str] = None,
    notice_type: Optional[str] = None,
    module_type: Optional[str] = None,
    asset_category: Optional[str] = None,
    henan_only: bool = False,
    henan_city: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    discount_max: Optional[float] = None,
    sort_by: str = "publish_time_desc",
    starred_only: bool = False,
    time_range: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """多维检索司法公示与拍卖数据库（支持河南省属地及跨域涉豫过滤，严格区分三大业务模块，支持时效筛选、真分页与捡漏筛选）"""
    # 基础检索大盘（在施加 platform 和 module_type 过滤之前，用于统计 7 大平台全景分布）
    scope_q = db.query(CourtNotice)
    if starred_only:
        scope_q = scope_q.filter(CourtNotice.is_starred == True)
    if asset_category:
        if asset_category in ("房产", "住宅/商业房产"):
            scope_q = scope_q.filter(CourtNotice.asset_category.in_(["房产", "住宅/商业房产"]))
        else:
            scope_q = scope_q.filter(CourtNotice.asset_category == asset_category)
    if court:
        scope_q = scope_q.filter(CourtNotice.court_name.like(f"%{court}%"))
    if notice_type:
        scope_q = scope_q.filter(CourtNotice.notice_type.like(f"%{notice_type}%"))
    if henan_only:
        scope_q = scope_q.filter(CourtNotice.is_henan == True)
    if henan_city:
        scope_q = scope_q.filter(CourtNotice.henan_city == henan_city)

    effective_time = func.coalesce(CourtNotice.publish_time, CourtNotice.created_at)
    # 时效过滤胶囊（标的发布时间或采集入库时间满足范围）
    if time_range == "today":
        today_start = datetime.combine(datetime.now().date(), dt_time.min)
        scope_q = scope_q.filter(
            or_(
                CourtNotice.publish_time >= today_start,
                CourtNotice.created_at >= today_start
            )
        )
    elif time_range == "3days":
        cutoff = datetime.combine((datetime.now() - timedelta(days=3)).date(), dt_time.min)
        scope_q = scope_q.filter(
            or_(
                CourtNotice.publish_time >= cutoff,
                CourtNotice.created_at >= cutoff
            )
        )
    elif time_range == "7days":
        cutoff = datetime.combine((datetime.now() - timedelta(days=7)).date(), dt_time.min)
        scope_q = scope_q.filter(
            or_(
                CourtNotice.publish_time >= cutoff,
                CourtNotice.created_at >= cutoff
            )
        )
    if price_min is not None:
        scope_q = scope_q.filter(CourtNotice.starting_price >= price_min)
    if price_max is not None:
        scope_q = scope_q.filter(CourtNotice.starting_price <= price_max)
    if discount_max is not None:
        ratio = (discount_max / 10.0) if discount_max <= 10 else (discount_max / 100.0)
        scope_q = scope_q.filter(
            CourtNotice.starting_price.isnot(None),
            CourtNotice.eval_price.isnot(None),
            CourtNotice.eval_price > 0,
            (CourtNotice.starting_price / CourtNotice.eval_price) <= ratio
        )
    if query:
        scope_q = scope_q.filter(
            or_(
                CourtNotice.title.like(f"%{query}%"),
                CourtNotice.content_text.like(f"%{query}%"),
                CourtNotice.case_number.like(f"%{query}%"),
                CourtNotice.parties.like(f"%{query}%")
            )
        )

    # 1. 动态聚合当前检索范围下的各平台公示数（7大平台全景，联动当前选中的业务模块）
    plat_q = scope_q
    if module_type:
        plat_q = plat_q.filter(CourtNotice.module_type == module_type)

    scope_plat_group = plat_q.with_entities(
        CourtNotice.platform,
        func.count(CourtNotice.id)
    ).group_by(CourtNotice.platform).all()

    n_plat_map = {p: c for p, c in scope_plat_group}
    notice_platform_counts = {
        "total": sum(n_plat_map.values()),
        "rmfysszc": n_plat_map.get("rmfysszc", 0),
        "ali": n_plat_map.get("ali", 0),
        "jd": n_plat_map.get("jd", 0),
        "rmfyb": n_plat_map.get("rmfyb", 0),
        "local_paper": n_plat_map.get("local_paper", 0),
        "caa": n_plat_map.get("caa", 0),
        "ggzy": n_plat_map.get("ggzy", 0),
    }

    # 2. 施加 platform 过滤后的查询
    base_q = scope_q
    if platform:
        base_q = base_q.filter(CourtNotice.platform == platform)

    # 动态聚合当前时间与检索范围下的各业务模块公示数
    notice_tab_group = base_q.with_entities(
        func.coalesce(CourtNotice.module_type, "公告"),
        func.count(CourtNotice.id)
    ).group_by(func.coalesce(CourtNotice.module_type, "公告")).all()

    notice_counts_map = {m: c for m, c in notice_tab_group}
    notice_tab_counts = {
        "total": sum(notice_counts_map.values()),
        "公告": notice_counts_map.get("公告", 0),
        "拍卖公告": notice_counts_map.get("拍卖公告", 0),
        "债权转让": notice_counts_map.get("债权转让", 0),
    }

    q = base_q
    if module_type:
        q = q.filter(CourtNotice.module_type == module_type)

    total = q.count()

    # 分页计算 (兼容原有 limit/offset，同时支持页码 page/page_size)
    if limit is not None:
        actual_limit = limit
        actual_offset = offset or 0
        actual_page = (actual_offset // actual_limit) + 1
        actual_page_size = actual_limit
    else:
        actual_page = max(1, page)
        actual_page_size = max(1, min(page_size, 100))
        actual_offset = (actual_page - 1) * actual_page_size
        actual_limit = actual_page_size

    total_pages = max(1, (total + actual_page_size - 1) // actual_page_size)

    if sort_by == "discount_asc":
        # 捡漏优先：折扣率升序 (起拍价/评估价 比值最小的排在前面)
        discount_expr = case(
            (and_(CourtNotice.starting_price.isnot(None), CourtNotice.eval_price.isnot(None), CourtNotice.eval_price > 0),
             CourtNotice.starting_price / CourtNotice.eval_price),
            else_=9999.0
        )
        items = q.order_by(discount_expr.asc(), desc(effective_time)).offset(actual_offset).limit(actual_limit).all()
    elif sort_by == "price_asc":
        price_expr = case(
            (CourtNotice.starting_price.isnot(None), CourtNotice.starting_price),
            else_=9999999999.0
        )
        items = q.order_by(price_expr.asc(), desc(effective_time)).offset(actual_offset).limit(actual_limit).all()
    elif sort_by == "price_desc":
        price_expr = case(
            (CourtNotice.starting_price.isnot(None), CourtNotice.starting_price),
            else_=-1.0
        )
        items = q.order_by(price_expr.desc(), desc(effective_time)).offset(actual_offset).limit(actual_limit).all()
    else:
        items = q.order_by(desc(effective_time)).offset(actual_offset).limit(actual_limit).all()

    notices = []
    for n in items:
        discount = round((n.starting_price / n.eval_price) * 10, 1) if (n.starting_price and n.eval_price and n.eval_price > 0) else None
        eff_dt = n.publish_time or n.created_at
        is_today = bool((eff_dt and eff_dt.date() == datetime.now().date()) or (n.created_at and n.created_at.date() == datetime.now().date()))
        
        # 拍卖倒计时与刚上拍研判 (一拍法定30天，二拍法定15天)
        days_until = None
        if n.bidding_start:
            try:
                days_until = (n.bidding_start.date() - datetime.now().date()).days
            except Exception:
                pass
        
        is_newly_listed = False
        if n.auction_stage in ['一拍', '第一次拍卖']:
            if (days_until is not None and days_until >= 20) or (eff_dt and (datetime.now() - eff_dt).days <= 3):
                is_newly_listed = True
        elif n.auction_stage in ['二拍', '第二次拍卖']:
            if (days_until is not None and days_until >= 10) or (eff_dt and (datetime.now() - eff_dt).days <= 3):
                is_newly_listed = True

        notices.append({
            "id": n.id,
            "platform": n.platform,
            "module_type": n.module_type or "公告",
            "court_name": n.court_name,
            "case_number": n.case_number,
            "parties": n.parties,
            "notice_type": n.notice_type,
            "title": n.title,
            "content_text": n.content_text,
            "publish_time": eff_dt.strftime("%Y-%m-%d %H:%M") if eff_dt else "",
            "source_url": n.source_url,
            "starting_price": n.starting_price,
            "eval_price": n.eval_price,
            "discount_rate": discount,
            "auction_stage": n.auction_stage,
            "asset_category": n.asset_category,
            "bidding_start": n.bidding_start.strftime("%Y-%m-%d %H:%M") if n.bidding_start else None,
            "bidding_end": n.bidding_end.strftime("%Y-%m-%d %H:%M") if n.bidding_end else None,
            "days_until_bidding": days_until,
            "is_newly_listed": is_newly_listed,
            "is_henan": n.is_henan,
            "henan_city": n.henan_city,
            "henan_tag": n.henan_tag,
            "is_today": is_today,
            "is_starred": bool(getattr(n, "is_starred", False)),
            "user_notes": getattr(n, "user_notes", "") or "",
            "risk_tags": extract_risk_tags(f"{n.title or ''} {n.content_text or ''}")
        })
    return {
        "total": total,
        "page": actual_page,
        "page_size": actual_page_size,
        "total_pages": total_pages,
        "tab_counts": notice_tab_counts,
        "platform_counts": notice_platform_counts,
        "items": notices
    }

# ----------------- 标的跟进与便签接口 -----------------

@app.post("/api/notices/{notice_id}/star")
def toggle_notice_star(notice_id: int, db: Session = Depends(get_db)):
    """切换标的关注/收藏状态"""
    notice = db.query(CourtNotice).filter(CourtNotice.id == notice_id).first()
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    notice.is_starred = not bool(notice.is_starred)
    db.commit()
    return {"id": notice_id, "is_starred": notice.is_starred}

@app.post("/api/notices/{notice_id}/notes")
def update_notice_notes(notice_id: int, req: NoticeNotesUpdate, db: Session = Depends(get_db)):
    """更新标的业务跟进便签"""
    notice = db.query(CourtNotice).filter(CourtNotice.id == notice_id).first()
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    notice.user_notes = req.notes
    db.commit()
    return {"id": notice_id, "user_notes": notice.user_notes}

@app.get("/api/notices/{notice_id}")
def get_notice_detail(notice_id: int, db: Session = Depends(get_db)):
    """获取单条标的公示详情"""
    n = db.query(CourtNotice).filter(CourtNotice.id == notice_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notice not found")
    
    discount_rate = None
    if n.starting_price is not None and n.eval_price is not None and n.eval_price > 0:
        discount_rate = round((n.starting_price / n.eval_price) * 10, 1)

    return {
        "id": n.id,
        "platform": n.platform,
        "court_name": n.court_name,
        "case_number": n.case_number,
        "parties": n.parties,
        "notice_type": n.notice_type,
        "module_type": n.module_type or "公告",
        "title": n.title,
        "content_text": n.content_text,
        "publish_time": n.publish_time.isoformat() if n.publish_time else None,
        "source_url": n.source_url,
        "starting_price": n.starting_price,
        "eval_price": n.eval_price,
        "discount_rate": discount_rate,
        "auction_stage": n.auction_stage,
        "asset_category": n.asset_category,
        "bidding_start": n.bidding_start.isoformat() if n.bidding_start else None,
        "bidding_end": n.bidding_end.isoformat() if n.bidding_end else None,
        "is_henan": n.is_henan,
        "henan_city": n.henan_city,
        "henan_tag": n.henan_tag,
        "is_starred": bool(getattr(n, "is_starred", False)),
        "user_notes": getattr(n, "user_notes", "") or "",
        "risk_tags": extract_risk_tags(f"{n.title or ''} {n.content_text or ''}")
    }

@app.get("/api/notices/{notice_id}/related")
def get_related_notices(notice_id: int, db: Session = Depends(get_db)):
    """获取与当前标的关联的历史公示与跨平台全流程时间线（支持同债务人/企业、同小区、同案号历史关联）"""
    import re
    notice = db.query(CourtNotice).filter(CourtNotice.id == notice_id).first()
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")

    related_map = {}

    # 1. 相同案号关联
    if notice.case_number and len(notice.case_number.strip()) >= 5:
        case_matches = db.query(CourtNotice).filter(
            CourtNotice.id != notice.id,
            CourtNotice.case_number == notice.case_number
        ).all()
        for m in case_matches:
            if m.module_type == "拍卖公告":
                stg = m.auction_stage or "拍卖"
                reason_text = f"同案号司法拍卖 ({stg}): {notice.case_number}"
            elif m.platform in ['rmfyb', 'local_paper']:
                reason_text = f"同案号裁判/送达公告: {notice.case_number}"
            else:
                reason_text = f"同案号关联: {notice.case_number}"
            related_map[m.id] = {
                "notice": m,
                "reason": reason_text
            }

    # 2. 相同机构/债务人/当事人主体关联（跨平台关联送达公告、债权催收与一拍/二拍）
    entity_names = []
    if notice.parties:
        raw_parties = [p.strip() for p in re.split(r'[；;,，、\s]+', notice.parties) if len(p.strip()) >= 2]
        for p in raw_parties:
            p_clean = re.sub(r'^(?:被执行人|申请执行人|原告|被告|当事人|借款人|担保人)[:：]?', '', p).strip()
            if 2 <= len(p_clean) <= 30 and not any(bad in p_clean for bad in ["人民法院", "中级法院", "基层法院", "法院", "待查", "自然人", "未公开"]):
                entity_names.append(p_clean)

    # 从标题与正文提取企业主体
    full_text = f"{notice.title or ''} {(notice.content_text or '')[:1000]}"
    corp_matches = re.findall(r'([\u4e00-\u9fa5]{2,25}(?:(?:股份)?有限(?:责任)?公司|集团有限公司|集团|商贸公司|置业公司|房地产公司|实业公司|工程公司|重工公司|制药厂|化工厂|合作社))', full_text)
    for c in corp_matches:
        if 4 <= len(c) <= 25 and not any(bad in c for bad in ["人民法院", "基层法院", "交易中心", "拍卖公司"]):
            entity_names.append(c)

    # 从标题与正文提取自然人债务人
    debtor_matches = re.findall(r'(?:被执行人|债务人|保证人|被催告人)[：:\s]*([\u4e00-\u9fa5]{2,4})', full_text)
    for d in debtor_matches:
        if 2 <= len(d) <= 4 and d not in ["法院", "申请", "执行", "公告"]:
            entity_names.append(d)

    # 限制查询主体去重后的前 4 个主体
    unique_entities = list(dict.fromkeys(entity_names))[:4]
    for entity in unique_entities:
        party_matches = db.query(CourtNotice).filter(
            CourtNotice.id != notice.id,
            or_(
                CourtNotice.parties.like(f"%{entity}%"),
                CourtNotice.title.like(f"%{entity}%"),
                CourtNotice.content_text.like(f"%{entity}%")
            )
        ).limit(6).all()

        for m in party_matches:
            if m.id not in related_map:
                m_title = m.title or ""
                if m.platform in ['rmfyb', 'local_paper'] or any(k in m_title for k in ["送达", "传票", "判决", "起诉状", "开庭"]):
                    reason = f"同债务人/企业历史送达: {entity}"
                elif m.module_type == "债权转让" or any(k in m_title for k in ["债权", "催收", "资产包", "不良资产"]):
                    reason = f"同债务人/企业债权催收: {entity}"
                elif m.module_type == "拍卖公告" or m.platform in ['ali', 'jd', 'rmfysszc', 'caa']:
                    stg = m.auction_stage or "拍卖"
                    reason = f"同债务人/主体法拍 ({stg}): {entity}"
                else:
                    reason = f"同债务人/关联主体: {entity}"
                related_map[m.id] = {
                    "notice": m,
                    "reason": reason
                }

    # 3. 房产小区名称跨平台关联（同小区房产拍卖、一拍/二拍流转记录）
    clean_title = re.sub(r'[\u4e00-\u9fa5]{2,12}(?:人民法院|中级法院|基层法院|法院|交易中心|委员会)', '', notice.title or '')
    clean_full = f"{clean_title} {(notice.content_text or '')[:500]}"
    community_matches = re.findall(r'([\u4e00-\u9fa5A-Za-z0-9]{2,12}(?:小区|花园|家园|雅苑|公馆|新城|广场|大厦|世家|华庭|名都|名门|城|苑|湾|坊|翠庭|山庄))', clean_full)
    
    unique_communities = []
    for cm in community_matches:
        if cm not in unique_communities and not any(bad in cm for bad in ["住宅小区", "某小区", "商业广场", "行政服务中心", "办公大楼", "省", "市", "区", "县"]):
            unique_communities.append(cm)

    for comm in unique_communities[:2]:
        comm_matches = db.query(CourtNotice).filter(
            CourtNotice.id != notice.id,
            or_(
                CourtNotice.title.like(f"%{comm}%"),
                CourtNotice.content_text.like(f"%{comm}%")
            )
        ).limit(6).all()

        for m in comm_matches:
            if m.id not in related_map:
                if m.module_type == "拍卖公告" or m.platform in ['ali', 'jd', 'rmfysszc', 'caa']:
                    stg = m.auction_stage or "拍卖"
                    reason = f"同小区房产拍卖 ({stg}): {comm}"
                elif m.platform in ['rmfyb', 'local_paper']:
                    reason = f"同小区涉案诉讼/送达: {comm}"
                else:
                    reason = f"同小区标的资产: {comm}"
                related_map[m.id] = {
                    "notice": m,
                    "reason": reason
                }

    # 组装时间线
    timeline_items = [
        {"notice": notice, "reason": "当前查看标的", "is_current": True}
    ]
    for m_id, item in related_map.items():
        timeline_items.append({
            "notice": item["notice"],
            "reason": item["reason"],
            "is_current": False
        })

    def sort_key(x):
        dt = x["notice"].publish_time or x["notice"].created_at
        return dt.timestamp() if dt else 0
    timeline_items.sort(key=sort_key)

    items = []
    for item in timeline_items:
        n = item["notice"]
        discount = None
        if n.starting_price is not None and n.eval_price is not None and n.eval_price > 0:
            discount = round((n.starting_price / n.eval_price) * 10, 1)

        items.append({
            "id": n.id,
            "platform": n.platform,
            "court_name": n.court_name,
            "case_number": n.case_number,
            "title": n.title,
            "notice_type": n.notice_type,
            "module_type": n.module_type or "公告",
            "auction_stage": n.auction_stage,
            "starting_price": n.starting_price,
            "eval_price": n.eval_price,
            "discount_rate": discount,
            "publish_time": n.publish_time.strftime("%Y-%m-%d %H:%M") if n.publish_time else None,
            "source_url": n.source_url,
            "match_reason": item["reason"],
            "is_current": item["is_current"],
            "risk_tags": extract_risk_tags(f"{n.title or ''} {n.content_text or ''}")
        })

    return {
        "notice_id": notice.id,
        "case_number": notice.case_number,
        "related_count": len(related_map),
        "items": items
    }

@app.post("/api/crawlers/ali/manual-verify")
def ali_manual_verify():
    """唤起可视化浏览器完成阿里拍卖滑块验证与Cookie持久化"""
    def _worker():
        import asyncio
        from backend.crawlers.ali_crawler import run_ali_manual_verification
        try:
            asyncio.run(run_ali_manual_verification(timeout_sec=120))
        except Exception as e:
            print(f"[ManualVerify] Error: {e}")

    import threading
    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return {
        "status": "ok",
        "message": "已在桌面唤起阿里拍卖独立窗口，请在弹出的浏览器中手动完成滑块拖拽或登录，完成后关闭窗口即可。"
    }

@app.post("/api/alerts/countdown/check")
def trigger_bidding_countdown_check():
    """手动立即触发一次关注标的48小时开拍倒计时巡检与推送"""
    from backend.engine.scheduler import check_starred_bidding_countdown
    check_starred_bidding_countdown()
    return {"status": "ok", "message": "已执行关注标的48小时开拍倒计时巡检"}


@app.get("/api/papers")
def get_papers(
    province: Optional[str] = None,
    monitored_only: bool = False,
    query: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """获取 53BK 地方报纸种子库"""
    q = db.query(PaperSeed)
    if province:
        q = q.filter(PaperSeed.province == province)
    if monitored_only:
        q = q.filter(PaperSeed.is_monitored == True)
    if query:
        q = q.filter(
            or_(
                PaperSeed.paper_name.like(f"%{query}%"),
                PaperSeed.city.like(f"%{query}%"),
                PaperSeed.province.like(f"%{query}%")
            )
        )

    total = q.count()
    items = q.order_by(desc(PaperSeed.is_monitored), PaperSeed.province, PaperSeed.paper_name).offset(offset).limit(limit).all()

    # 所有省份列表供筛选
    all_provinces = [p[0] for p in db.query(PaperSeed.province).distinct().all() if p[0]]

    return {
        "total": total,
        "provinces": all_provinces,
        "items": [
            {
                "id": p.id,
                "province": p.province,
                "city": p.city,
                "paper_name": p.paper_name,
                "epaper_url": p.epaper_url,
                "is_monitored": p.is_monitored,
                "last_scanned_at": p.last_scanned_at.strftime("%Y-%m-%d %H:%M") if p.last_scanned_at else "尚未巡检",
                "status": p.status
            }
            for p in items
        ]
    }

@app.post("/api/papers/{paper_id}/toggle-monitor")
def toggle_paper_monitor(paper_id: int, db: Session = Depends(get_db)):
    """开启或暂停某地方报纸的每日定向公告巡检"""
    paper = db.query(PaperSeed).filter(PaperSeed.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    paper.is_monitored = not paper.is_monitored
    db.commit()
    return {"status": "ok", "is_monitored": paper.is_monitored}

@app.post("/api/papers/sync-53bk")
def trigger_sync_53bk(bg_tasks: BackgroundTasks):
    """后台触发 53BK 全国报纸目录同步"""
    def do_sync():
        db = SessionLocal()
        try:
            sync_53bk_seeds(db, max_regions=15)
        finally:
            db.close()
    bg_tasks.add_task(do_sync)
    return {"status": "started", "message": "53BK 同步任务已在后台启动"}

@app.get("/api/tasks")
def get_task_logs(limit: int = 20, db: Session = Depends(get_db)):
    """获取爬虫任务执行日志与当前正在执行的渠道"""
    logs = db.query(TaskLog).order_by(desc(TaskLog.created_at)).limit(limit).all()
    formatted_logs = [
        {
            "id": l.id,
            "platform": l.platform,
            "task_name": l.task_name,
            "status": l.status,
            "items_found": l.items_found,
            "new_items": l.new_items,
            "duration_ms": l.duration_ms,
            "error_msg": l.error_msg,
            "created_at": l.created_at.strftime("%Y-%m-%d %H:%M:%S") if l.created_at else ""
        }
        for l in logs
    ]
    return {
        "running_platforms": get_running_platforms(),
        "logs": formatted_logs
    }

@app.post("/api/tasks/run")
def trigger_manual_crawl(platform: str, db: Session = Depends(get_db)):
    """手动立即触发特定渠道的真实抓取管道"""
    if platform not in ["rmfysszc", "rmfyb", "jd", "ali", "local_paper", "caa", "ggzy"]:
        raise HTTPException(status_code=400, detail="Invalid platform")
    res = run_crawler_pipeline(platform)
    if isinstance(res, dict) and res.get("status") == "already_running":
        return {
            "status": "already_running",
            "platform": platform,
            "message": f"{platform} 采集任务当前已在运行中，请勿重复触发"
        }
    latest_log = db.query(TaskLog).filter(TaskLog.platform == platform).order_by(desc(TaskLog.created_at)).first()
    return {
        "status": "completed",
        "platform": platform,
        "items_found": latest_log.items_found if latest_log else 0,
        "new_items": latest_log.new_items if latest_log else 0,
        "duration_ms": latest_log.duration_ms if latest_log else 0,
        "message": f"{platform} 实时采集执行完成"
    }

@app.post("/api/tasks/run-all")
def trigger_all_crawlers():
    """一键后台受控并发触发全部 7 大数据源采集管道"""
    return trigger_run_all_crawlers()

@app.post("/api/maintenance/clean-historical")
def clean_historical_data(days: int = 7, keep_starred: bool = True, db: Session = Depends(get_db)):
    """一键清理早于指定天数（默认7天）的陈旧历史数据，保持库容纯净与最新时效"""
    cutoff = datetime.now() - timedelta(days=days)
    
    # 查找需清理的标的
    del_query = db.query(CourtNotice.id).filter(CourtNotice.publish_time < cutoff)
    if keep_starred:
        del_query = del_query.filter(CourtNotice.is_starred == False)
    
    target_ids = [r[0] for r in del_query.all()]
    if not target_ids:
        return {"status": "ok", "deleted_notices": 0, "deleted_alerts": 0, "message": "没有需要清理的陈旧数据"}
    
    # 分批删除关联预警与标的
    del_alerts_count = db.query(AlertEvent).filter(AlertEvent.notice_id.in_(target_ids)).delete(synchronize_session=False)
    del_notices_count = db.query(CourtNotice).filter(CourtNotice.id.in_(target_ids)).delete(synchronize_session=False)
    db.commit()
    
    return {
        "status": "ok",
        "deleted_notices": del_notices_count,
        "deleted_alerts": del_alerts_count,
        "message": f"成功清理 {del_notices_count} 条历史旧标的及关联的 {del_alerts_count} 条预警"
    }

# 前端构建产物挂载 (兼容源码调试与 PyInstaller 独立打包运行环境)
if getattr(sys, 'frozen', False):
    candidate_paths = [
        getattr(sys, '_MEIPASS', ''),
        os.path.join(getattr(sys, '_MEIPASS', ''), "frontend", "dist"),
        os.path.join(os.path.dirname(sys.executable), "_internal", "frontend", "dist"),
        os.path.join(os.path.dirname(sys.executable), "frontend", "dist"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")
    ]
    FRONTEND_DIST = ""
    for cp in candidate_paths:
        if cp and os.path.exists(os.path.join(cp, "index.html")):
            FRONTEND_DIST = cp
            break
else:
    FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")

if FRONTEND_DIST and os.path.exists(FRONTEND_DIST):
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

if __name__ == "__main__":
    import uvicorn
    from backend.config import HOST, PORT
    print(f"Starting server on http://{HOST}:{PORT}...")
    uvicorn.run("backend.app:app", host=HOST, port=PORT, reload=False)
