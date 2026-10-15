# -*- coding: utf-8 -*-
import os
import sys
import time
import shutil
import sqlite3
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

def ensure_db_integrity(db_path: str = None, backup_seed_path: str = None) -> bool:
    """
    启动前原生自检 SQLite 数据库完整性。
    若未传入参数，默认使用全局 DB_PATH 与 SEED_PATH。
    若文件损坏（抛出 DatabaseError 或 quick_check != 'ok'）：
    1. 自动备份损坏文件为 court_notices.db.corrupted.<timestamp>（同时清理关联的 -wal 与 -shm）
    2. 尝试从 backup_seed_path（如 _internal/data/court_notices.db）复制恢复
    3. 若无备份可用，则移除损坏文件，后续由 create_all 重建表结构
    返回 True 表示完整性正常或已自动修复，严禁直接崩溃退出
    """
    if db_path is None:
        db_path = globals().get('DB_PATH')
    if backup_seed_path is None:
        backup_seed_path = globals().get('SEED_PATH')
    if not db_path:
        return True

    if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
        if backup_seed_path and os.path.exists(backup_seed_path) and os.path.getsize(backup_seed_path) > 0:
            try:
                shutil.copy2(backup_seed_path, db_path)
                print(f"[Database] Seed database copied to {db_path}")
            except Exception as e:
                print(f"[Database] Failed to copy seed database: {e}")
        return True

    is_corrupted = False
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        cursor = conn.cursor()
        res = cursor.execute("PRAGMA quick_check;").fetchall()
        cursor.close()
        conn.close()
        if not res or res[0][0].lower() != "ok":
            is_corrupted = True
    except sqlite3.DatabaseError as e:
        print(f"[Database] SQLite integrity check error: {e}")
        is_corrupted = True
    except Exception as e:
        print(f"[Database] Unexpected error during quick_check: {e}")
        is_corrupted = True

    if is_corrupted:
        ts = int(time.time())
        corrupted_backup = f"{db_path}.corrupted.{ts}"
        print(f"[Database] Warning: {db_path} is corrupted! Moving to {corrupted_backup}...")
        try:
            if os.path.exists(db_path):
                os.rename(db_path, corrupted_backup)
            for suffix in ["-wal", "-shm"]:
                sidecar = db_path + suffix
                if os.path.exists(sidecar):
                    try:
                        os.rename(sidecar, f"{corrupted_backup}{suffix}")
                    except Exception:
                        pass
        except Exception as e:
            print(f"[Database] Error backing up corrupted file: {e}")

        # 尝试从初始种子库恢复
        if backup_seed_path and os.path.exists(backup_seed_path) and os.path.getsize(backup_seed_path) > 0:
            try:
                bconn = sqlite3.connect(backup_seed_path, timeout=5)
                bres = bconn.cursor().execute("PRAGMA quick_check;").fetchall()
                bconn.close()
                if bres and bres[0][0].lower() == "ok":
                    shutil.copy2(backup_seed_path, db_path)
                    print(f"[Database] Successfully recovered from backup seed: {backup_seed_path}")
                    return True
            except Exception as e:
                print(f"[Database] Error copying from seed: {e}")

        print("[Database] Clean database will be regenerated.")
        return False

    return True

if getattr(sys, 'frozen', False):
    # PyInstaller 打包独立运行环境：持久化存储在 exe 程序所在目录的 data 文件夹
    BASE_DIR = os.path.dirname(sys.executable)
    DB_DIR = os.path.join(BASE_DIR, "data")
    os.makedirs(DB_DIR, exist_ok=True)
    DB_PATH = os.path.join(DB_DIR, "court_notices.db")

    candidates = [
        os.path.join(getattr(sys, '_MEIPASS', ''), "data", "court_notices.db"),
        os.path.join(BASE_DIR, "_internal", "data", "court_notices.db"),
    ]
    SEED_PATH = None
    for c in candidates:
        if c and os.path.exists(c) and os.path.getsize(c) > 0:
            SEED_PATH = c
            break
else:
    # 源码开发调试环境：存储在项目工程根目录下的 data 文件夹
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_DIR = os.path.join(BASE_DIR, "data")
    os.makedirs(DB_DIR, exist_ok=True)
    DB_PATH = os.path.join(DB_DIR, "court_notices.db")
    bak_candidate = os.path.join(DB_DIR, "court_notices.db.bak")
    SEED_PATH = bak_candidate if os.path.exists(bak_candidate) and os.path.getsize(bak_candidate) > 0 else None

# 执行启动自检与恢复保护
ensure_db_integrity(DB_PATH, SEED_PATH)

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
    pool_pre_ping=True,
    echo=False
)

# Enable WAL mode, busy_timeout and foreign keys for SQLite performance & zero-lock concurrency
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA busy_timeout=30000;")
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()
    except Exception as e:
        print(f"[Database] Warning setting pragma: {e}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
