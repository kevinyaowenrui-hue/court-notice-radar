# -*- coding: utf-8 -*-
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from backend.database import SessionLocal
from backend.models import TaskLog
from backend.engine.rule_matcher import match_new_notices
from backend.engine.webhook import send_alert_webhook
from backend.crawlers.rmfyb_crawler import crawl_rmfyb_notices
from backend.crawlers.jd_crawler import crawl_jd_auctions
from backend.crawlers.ali_crawler import crawl_ali_auctions
from backend.crawlers.local_paper_crawler import scan_monitored_papers
from backend.crawlers.caa_crawler import crawl_caa_publicity
from backend.crawlers.ggzy_crawler import crawl_ggzy_publicity
from backend.crawlers.rmfysszc_crawler import crawl_rmfysszc_notices

scheduler = BackgroundScheduler()

# 渠道级互斥锁与运行状态注册表
PLATFORM_LOCKS = {
    "rmfysszc": threading.Lock(),
    "rmfyb": threading.Lock(),
    "jd": threading.Lock(),
    "ali": threading.Lock(),
    "local_paper": threading.Lock(),
    "caa": threading.Lock(),
    "ggzy": threading.Lock(),
}

RUNNING_TASKS: dict[str, bool] = {
    p: False for p in PLATFORM_LOCKS
}

# 并发控制信号量
# HTTP 轻量组：最大并发度 3
HTTP_SEMAPHORE = threading.Semaphore(3)
# Playwright 浏览器组：最大并发度 2
BROWSER_SEMAPHORE = threading.Semaphore(2)

HTTP_PLATFORMS = {"rmfysszc", "caa", "ggzy", "local_paper"}
BROWSER_PLATFORMS = {"ali", "jd", "rmfyb"}

# 专用于一键全网抓取的线程池
_CRAWLER_POOL = ThreadPoolExecutor(max_workers=7, thread_name_prefix="crawler_worker")

def get_running_platforms() -> list[str]:
    """获取当前正在执行抓取的渠道列表"""
    return [p for p, is_running in RUNNING_TASKS.items() if is_running]

def run_crawler_pipeline(platform: str):
    """通用爬虫执行与预警匹配管道（带互斥锁、并发信号量限制及短事务入库）"""
    lock = PLATFORM_LOCKS.get(platform)
    if not lock:
        raise ValueError(f"Unknown crawler platform: {platform}")

    # 1. 尝试非阻塞获取渠道级互斥锁
    acquired = lock.acquire(blocking=False)
    if not acquired:
        print(f"[{platform}] Task is already running, skipping duplicate invocation.")
        return {"status": "already_running", "platform": platform}

    t0 = time.time()
    task_name_map = {
        "rmfysszc": "人民法院诉讼资产网·一拍二拍房产公示巡检",
        "rmfyb": "《人民法院报》公告网巡检",
        "jd": "京东司法拍卖资产巡检",
        "ali": "阿里资产·司法拍卖巡检",
        "local_paper": "53BK重点地方报纸版面扫描",
        "caa": "中拍平台·信息公示与处置结果巡检",
        "ggzy": "公共资源交易平台·全省产权交易巡检"
    }
    task_name = task_name_map.get(platform, f"{platform} 采集任务")
    new_notices = []
    total_found = 0
    status = "success"
    err_msg = None
    crawl_warning = None

    try:
        RUNNING_TASKS[platform] = True
        sem = BROWSER_SEMAPHORE if platform in BROWSER_PLATFORMS else HTTP_SEMAPHORE

        # 2. 在受控信号量下执行网络/无头浏览器抓取（不持有任何外部 DB 事务会话）
        with sem:
            if platform == "rmfysszc":
                res = crawl_rmfysszc_notices(db=None)
            elif platform == "rmfyb":
                res = crawl_rmfyb_notices(db=None)
            elif platform == "jd":
                res = crawl_jd_auctions(db=None)
            elif platform == "ali":
                res = crawl_ali_auctions(db=None)
            elif platform == "local_paper":
                res = scan_monitored_papers(db=None)
            elif platform == "caa":
                res = crawl_caa_publicity(db=None)
            elif platform == "ggzy":
                res = crawl_ggzy_publicity(db=None)
            else:
                raise ValueError(f"Unknown crawler platform: {platform}")

        # 解构爬虫返回结果：支持 (new_notices, total_found, warning_msg) 或 (new_notices, total_found)
        if isinstance(res, tuple):
            if len(res) >= 3:
                new_notices, total_found, crawl_warning = res[0], res[1], res[2]
            elif len(res) == 2:
                new_notices, total_found = res[0], res[1]
            else:
                new_notices = res[0]
                total_found = len(new_notices)
        elif isinstance(res, list):
            new_notices = res
            total_found = len(new_notices)

        # 严格状态研判逻辑
        if crawl_warning:
            status = "warning"
            err_msg = crawl_warning
        elif total_found == 0:
            status = "warning"
            err_msg = "本次巡检发现 0 条数据，可能遭遇目标站点防爬验证码、频次限制或页面结构微调"
        else:
            status = "success"

        # 3. 短生命周期 DB 会话：规则匹配与 Webhook 调度
        if new_notices:
            with SessionLocal() as db:
                alerts = match_new_notices(db, new_notices)
                print(f"[{platform}] Pipeline completed: {len(new_notices)} new notices, {len(alerts)} alerts generated.")
                if alerts:
                    wh_res = send_alert_webhook(db, alerts)
                    print(f"[{platform}] Webhook dispatch result: {wh_res}")
    except Exception as e:
        status = "failed"
        err_msg = str(e)
        print(f"[{platform}] Pipeline error: {e}")
    finally:
        # 4. 短生命周期 DB 会话：记录 TaskLog
        duration_ms = int((time.time() - t0) * 1000)
        try:
            with SessionLocal() as db:
                log = TaskLog(
                    platform=platform,
                    task_name=task_name,
                    status=status,
                    items_found=total_found if total_found > 0 else len(new_notices),
                    new_items=len(new_notices),
                    duration_ms=duration_ms,
                    error_msg=err_msg
                )
                db.add(log)
                db.commit()
        except Exception as log_e:
            print(f"[{platform}] Failed to save TaskLog: {log_e}")
        finally:
            RUNNING_TASKS[platform] = False
            lock.release()

    return {
        "status": status,
        "platform": platform,
        "items_found": total_found,
        "new_items": len(new_notices),
        "duration_ms": duration_ms,
        "error_msg": err_msg
    }

def trigger_run_all_crawlers() -> dict:
    """一键受控并发调度 7 大渠道数据源采集"""
    platforms = ["rmfysszc", "caa", "ggzy", "local_paper", "ali", "jd", "rmfyb"]
    for p in platforms:
        _CRAWLER_POOL.submit(run_crawler_pipeline, p)
    return {
        "status": "triggered",
        "platforms": platforms,
        "message": "已启动全网 7 大数据源受控并发采集（HTTP组并发3，浏览器组并发2）与规则预警匹配"
    }

def start_scheduler():
    """启动后台定时任务调度"""
    if not scheduler.running:
        scheduler.add_job(lambda: run_crawler_pipeline("rmfysszc"), 'interval', minutes=30, id="job_rmfysszc", replace_existing=True)
        scheduler.add_job(lambda: run_crawler_pipeline("rmfyb"), 'interval', minutes=30, id="job_rmfyb", replace_existing=True)
        scheduler.add_job(lambda: run_crawler_pipeline("jd"), 'interval', minutes=30, id="job_jd", replace_existing=True)
        scheduler.add_job(lambda: run_crawler_pipeline("ali"), 'interval', minutes=45, id="job_ali", replace_existing=True)
        scheduler.add_job(lambda: run_crawler_pipeline("local_paper"), 'interval', hours=2, id="job_local", replace_existing=True)
        scheduler.add_job(lambda: run_crawler_pipeline("caa"), 'interval', minutes=30, id="job_caa", replace_existing=True)
        scheduler.add_job(lambda: run_crawler_pipeline("ggzy"), 'interval', minutes=30, id="job_ggzy", replace_existing=True)
        scheduler.start()
        print("[Scheduler] APScheduler background engine started successfully.")
