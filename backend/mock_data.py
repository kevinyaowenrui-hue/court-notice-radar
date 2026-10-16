# -*- coding: utf-8 -*-
"""
初始化数据库与基准数据填充
"""
import json
import time
from datetime import datetime
from backend.database import engine, SessionLocal, Base, create_db_indexes
from backend.models import CourtNotice, MonitorRule, AlertEvent, PaperSeed, TaskLog
from backend.engine.rule_matcher import match_new_notices
from backend.crawlers.seed_53bk import sync_53bk_seeds
from backend.crawlers.rmfyb_crawler import crawl_rmfyb_notices
from backend.crawlers.jd_crawler import crawl_jd_auctions
from backend.crawlers.ali_crawler import crawl_ali_auctions
from backend.crawlers.local_paper_crawler import scan_monitored_papers

def init_database_and_seeds():
    """初始化建表并填装初始数据"""
    print("[Init] Creating tables if not exist...")
    Base.metadata.create_all(bind=engine)
    create_db_indexes(engine)
    db = SessionLocal()

    try:
        # 1. 初始化或升级监控规则（确保 caa 和 ggzy 平台被纳入监控）
        existing_rules = db.query(MonitorRule).all()
        if not existing_rules:
            print("[Init] Inserting default monitoring rules...")
            default_rules = [
                MonitorRule(
                    name="【全网法拍】河南省全域司法拍卖与优质资产监控",
                    is_active=True,
                    platforms=json.dumps(["ali", "jd", "caa", "ggzy"]),
                    courts=json.dumps([]),
                    parties=json.dumps([]),
                    case_numbers=json.dumps([]),
                    keywords=json.dumps(["河南", "郑州", "洛阳", "开封", "新乡", "南阳", "金水", "二七", "郑东新区", "豫"]),
                    price_min=None,
                    price_max=None,
                    notify_browser=True
                ),
                MonitorRule(
                    name="【涉豫案件】全国法院涉河南案号与跨域当事人雷达",
                    is_active=True,
                    platforms=json.dumps(["rmfyb", "local_paper", "ali", "jd", "caa", "ggzy"]),
                    courts=json.dumps([]),
                    parties=json.dumps([]),
                    case_numbers=json.dumps(["豫"]),
                    keywords=json.dumps(["河南", "郑州", "洛阳", "新乡", "开封", "许昌", "平顶山", "南阳", "焦作", "商丘", "安阳"]),
                    price_min=None,
                    price_max=None,
                    notify_browser=True
                ),
                MonitorRule(
                    name="【重点法院】郑州中院及河南地市级法院公告与破产监控",
                    is_active=True,
                    platforms=json.dumps(["rmfyb", "local_paper", "ggzy"]),
                    courts=json.dumps(["河南省高级人民法院", "郑州市中级人民法院", "洛阳市中级人民法院", "新乡市中级人民法院", "金水区人民法院", "二七区人民法院"]),
                    parties=json.dumps([]),
                    case_numbers=json.dumps([]),
                    keywords=json.dumps(["执行", "拍卖", "破产", "清算", "传票", "送达"]),
                    price_min=None,
                    price_max=None,
                    notify_browser=True
                )
            ]
            for r in default_rules:
                db.add(r)
            db.commit()
        else:
            # 平滑升级已有规则中的平台覆盖
            for r in existing_rules:
                try:
                    p_list = json.loads(r.platforms) if r.platforms else []
                    updated = False
                    if "全网法拍" in r.name:
                        for p in ["caa", "ggzy"]:
                            if p not in p_list:
                                p_list.append(p)
                                updated = True
                    elif "涉豫案件" in r.name:
                        for p in ["caa", "ggzy"]:
                            if p not in p_list:
                                p_list.append(p)
                                updated = True
                    if updated:
                        r.platforms = json.dumps(p_list, ensure_ascii=False)
                except Exception:
                    pass
            db.commit()

        # 2. 抓取 53BK 报纸种子 (仅在为空时异步填充，不阻塞启动)
        if db.query(PaperSeed).count() == 0:
            import threading
            def _async_seed_sync():
                from backend.database import SessionLocal
                s_db = SessionLocal()
                try:
                    t0 = time.time()
                    cnt = sync_53bk_seeds(s_db, max_regions=8)
                    s_db.add(TaskLog(
                        platform="53bk",
                        task_name="53BK全国电子报入口同步",
                        status="success",
                        items_found=cnt,
                        new_items=cnt,
                        duration_ms=int((time.time() - t0) * 1000)
                    ))
                    s_db.commit()
                except Exception as e:
                    print(f"[Init] 53BK sync note: {e}")
                finally:
                    s_db.close()
            threading.Thread(target=_async_seed_sync, daemon=True).start()

        # 3. 首次启动且数据库为空时，在后台异步线程执行初始抓取；已有数据则直接跳过，由调度器和用户按需触发
        if db.query(CourtNotice).count() == 0:
            import threading
            def _async_initial_crawl():
                from backend.database import SessionLocal
                c_db = SessionLocal()
                try:
                    t0 = time.time()
                    new_rmfyb, tot_rmfyb = crawl_rmfyb_notices(c_db)
                    c_db.add(TaskLog(
                        platform="rmfyb",
                        task_name="《人民法院报》公告网巡检",
                        status="success",
                        items_found=tot_rmfyb,
                        new_items=len(new_rmfyb),
                        duration_ms=int((time.time() - t0) * 1000)
                    ))

                    t0 = time.time()
                    new_jd, tot_jd = crawl_jd_auctions(c_db)
                    c_db.add(TaskLog(
                        platform="jd",
                        task_name="京东司法拍卖资产巡检",
                        status="success",
                        items_found=tot_jd,
                        new_items=len(new_jd),
                        duration_ms=int((time.time() - t0) * 1000)
                    ))

                    t0 = time.time()
                    new_ali, tot_ali = crawl_ali_auctions(c_db)
                    c_db.add(TaskLog(
                        platform="ali",
                        task_name="阿里资产·司法拍卖巡检",
                        status="success",
                        items_found=tot_ali,
                        new_items=len(new_ali),
                        duration_ms=int((time.time() - t0) * 1000)
                    ))

                    t0 = time.time()
                    new_local, tot_local = scan_monitored_papers(c_db)
                    c_db.add(TaskLog(
                        platform="local_paper",
                        task_name="53BK重点地方报纸版面扫描",
                        status="success",
                        items_found=tot_local,
                        new_items=len(new_local),
                        duration_ms=int((time.time() - t0) * 1000)
                    ))
                    c_db.commit()

                    notices = c_db.query(CourtNotice).all()
                    match_new_notices(c_db, notices)
                except Exception as e:
                    print(f"[Init] Async initial crawl note: {e}")
                finally:
                    c_db.close()
            threading.Thread(target=_async_initial_crawl, daemon=True).start()

        # 4. 触发规则匹配，生成预警事件
        all_notices = db.query(CourtNotice).all()
        created_alerts = match_new_notices(db, all_notices)
        print(f"[Init] Total notices in DB: {len(all_notices)}, Total alerts generated: {len(created_alerts)}")

    finally:
        db.close()

if __name__ == '__main__':
    init_database_and_seeds()
