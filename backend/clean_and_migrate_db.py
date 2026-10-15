# -*- coding: utf-8 -*-
"""
存量数据库清洗与规范化迁移模块
落实 prompt 中定义的数据清洗逻辑、规则优化与案号/类别规范化
"""
import sqlite3
import json
import re
import os

def clean_database(db_path: str = None):
    """执行存量数据与监控规则全面清洗与规范化"""
    if db_path is None:
        try:
            from backend.database import DB_PATH
            db_path = DB_PATH
        except Exception:
            return

    if not db_path or not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        # 1. 清理 53BK 硬编码预置假数据及关联误报
        cur.execute("""
            DELETE FROM alert_events WHERE notice_id IN (
                SELECT id FROM court_notices WHERE platform = 'local_paper' AND (raw_id LIKE '53bk_archive_%' OR raw_id LIKE '53bk_p2_%')
            );
        """)
        cur.execute("""
            DELETE FROM court_notices WHERE platform = 'local_paper' AND (raw_id LIKE '53bk_archive_%' OR raw_id LIKE '53bk_p2_%');
        """)

        # 2. 清理地方报误抓的非司法新闻（医院招聘、桂花市集、反恐论坛、友情链接等）
        cur.execute("""
            DELETE FROM alert_events WHERE notice_id IN (
                SELECT id FROM court_notices WHERE platform = 'local_paper' AND (
                    title LIKE '%招聘%' OR title LIKE '%桂花市集%' OR title LIKE '%反恐%' OR title LIKE '%东方圣城网%'
                    OR title LIKE '%威士公司%' OR title LIKE '%校园%' OR title LIKE '%学法%' OR title LIKE '%普法%'
                    OR title LIKE '%公积金%' OR title LIKE '%政法委员会%' OR title LIKE '%交付公告%' OR title LIKE '%水利%'
                )
            );
        """)
        cur.execute("""
            DELETE FROM court_notices WHERE platform = 'local_paper' AND (
                title LIKE '%招聘%' OR title LIKE '%桂花市集%' OR title LIKE '%反恐%' OR title LIKE '%东方圣城网%'
                OR title LIKE '%威士公司%' OR title LIKE '%校园%' OR title LIKE '%学法%' OR title LIKE '%普法%'
                OR title LIKE '%公积金%' OR title LIKE '%政法委员会%' OR title LIKE '%交付公告%' OR title LIKE '%水利%'
            );
        """)

        # 3. 修正 ggzy 中新疆哈密标的被误标为河南属地的问题，并清空错误填入 parties 的辖区名
        cur.execute("""
            UPDATE court_notices
            SET is_henan = 0, henan_city = NULL, henan_tag = NULL
            WHERE platform = 'ggzy' AND (
                title LIKE '%哈密%' OR title LIKE '%伊州%' OR title LIKE '%伊吾%' OR title LIKE '%巴里坤%'
                OR parties IN ('伊州区', '伊吾县', '巴里坤哈萨克自治县')
            );
        """)
        cur.execute("UPDATE court_notices SET parties = '' WHERE platform = 'ggzy';")

        # 4. 清空被误识别为案号的不动产权证号与租赁编号，并去除案号内部多余空格
        cur.execute("""
            UPDATE court_notices
            SET case_number = ''
            WHERE case_number LIKE '%不动产%' OR case_number LIKE '%产权%' OR case_number LIKE '%证明%'
               OR case_number LIKE '%租公房%' OR case_number LIKE '%字第000%';
        """)
        cur.execute("""
            UPDATE court_notices
            SET case_number = REPLACE(REPLACE(REPLACE(case_number, ' ', ''), '(', '（'), ')', '）')
            WHERE case_number IS NOT NULL AND case_number != '';
        """)

        # 5. 清空 ali 与 caa 中用起拍价伪造的评估价，并修复金额浮点精度问题
        cur.execute("UPDATE court_notices SET eval_price = NULL WHERE platform IN ('ali', 'caa') AND starting_price = eval_price;")
        cur.execute("UPDATE court_notices SET starting_price = ROUND(starting_price, 2) WHERE starting_price IS NOT NULL;")
        cur.execute("UPDATE court_notices SET eval_price = ROUND(eval_price, 2) WHERE eval_price IS NOT NULL;")

        # 6. 统一 rmfysszc 的房产分类枚举，修复 rmfyb 标题多余右括号
        cur.execute("UPDATE court_notices SET asset_category = '住宅/商业房产' WHERE asset_category = '房产';")
        cur.execute("UPDATE court_notices SET title = REPLACE(title, '号））', '号）') WHERE platform = 'rmfyb' AND title LIKE '%号））%';")
        cur.execute("""
            UPDATE court_notices SET title = SUBSTR(title, 1, INSTR(title, '号）') + 1) || SUBSTR(title, INSTR(title, '号）') + 3)
            WHERE platform = 'rmfyb' AND title LIKE '（%）%）%';
        """)

        # 7. 更新监控规则 4 和 7 中的 keywords，剔除单字词“公告”
        rules = cur.execute("SELECT id, keywords FROM monitor_rules WHERE id IN (4, 7)").fetchall()
        for rid, kw_json in rules:
            if not kw_json:
                continue
            try:
                kws = json.loads(kw_json)
                updated = False
                if "公告" in kws:
                    kws.remove("公告")
                    updated = True
                new_specifics = ["送达公告", "拍卖公告", "变卖公告", "破产公告", "执行公告", "催收公告"]
                for sp in new_specifics:
                    if sp not in kws:
                        kws.append(sp)
                        updated = True
                if updated:
                    cur.execute("UPDATE monitor_rules SET keywords = ? WHERE id = ?", (json.dumps(kws, ensure_ascii=False), rid))
            except Exception:
                pass

        conn.commit()

        # 8. 执行 WAL checkpoint TRUNCATE 合并与清理
        cur.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        cur.close()
        conn.close()
        print(f"[Clean] Database at {db_path} cleaned and checkpointed successfully.")
    except Exception as e:
        print(f"[Clean] Error cleaning database: {e}")
        try:
            conn.close()
        except Exception:
            pass

if __name__ == '__main__':
    clean_database('data/court_notices.db')
