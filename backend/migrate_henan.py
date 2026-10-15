# -*- coding: utf-8 -*-
"""
数据库字段平滑迁移与存量数据涉豫打标
为 court_notices 增加 is_henan, henan_city, henan_tag 字段并自动为存量数据分类
"""
import sqlite3
import os
from backend.utils import detect_henan_info

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "court_notices.db")

def migrate():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    existing_cols = [c[1] for c in cur.execute("PRAGMA table_info(court_notices)").fetchall()]
    print("Existing cols:", existing_cols)

    if "is_henan" not in existing_cols:
        print("Adding is_henan column...")
        cur.execute("ALTER TABLE court_notices ADD COLUMN is_henan BOOLEAN DEFAULT 0")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_court_notices_is_henan ON court_notices (is_henan)")

    if "henan_city" not in existing_cols:
        print("Adding henan_city column...")
        cur.execute("ALTER TABLE court_notices ADD COLUMN henan_city VARCHAR(64)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_court_notices_henan_city ON court_notices (henan_city)")

    if "henan_tag" not in existing_cols:
        print("Adding henan_tag column...")
        cur.execute("ALTER TABLE court_notices ADD COLUMN henan_tag VARCHAR(128)")

    con.commit()

    # 对所有存量数据执行打标
    rows = cur.execute("SELECT id, platform, court_name, case_number, parties, title, content_text FROM court_notices").fetchall()
    updated_count = 0
    henan_count = 0

    for r in rows:
        cid, platform, court_name, case_number, parties, title, content_text = r
        is_hn, city, tag = detect_henan_info(
            title=title or "",
            content=content_text or "",
            court_name=court_name or "",
            case_number=case_number or "",
            parties=parties or ""
        )
        cur.execute(
            "UPDATE court_notices SET is_henan = ?, henan_city = ?, henan_tag = ? WHERE id = ?",
            (1 if is_hn else 0, city, tag, cid)
        )
        updated_count += 1
        if is_hn:
            henan_count += 1

    con.commit()
    con.close()
    print(f"Migration completed! Processed {updated_count} notices, {henan_count} identified as Henan local/cross-provincial cases.")

if __name__ == '__main__':
    migrate()
