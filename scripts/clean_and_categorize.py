# -*- coding: utf-8 -*-
import os
import sys
import json
import sqlite3

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from backend.database import SessionLocal
from backend.models import CourtNotice, AlertEvent, MonitorRule
from backend.utils import is_promotional_content, categorize_notice_module, detect_henan_info, HENAN_CITIES
from backend.engine.rule_matcher import match_new_notices

def clean_and_normalize_database():
    print("[Clean & Normalize] Starting comprehensive database cleaning...")
    db = SessionLocal()
    try:
        # 1. 清理早期测试伪造数据 (杭州西湖区某大厦、手写notice/1001等)
        mock_raw_ids = ['jd_12839102', 'jd_12839103', 'jd_12839104']
        mock_notices = db.query(CourtNotice).filter(
            (CourtNotice.raw_id.in_(mock_raw_ids)) |
            (CourtNotice.source_url.like('%rmfygg.court.gov.cn/web/rmfyportal/notice/100%'))
        ).all()
        mock_ids = [m.id for m in mock_notices]
        if mock_ids:
            db.query(AlertEvent).filter(AlertEvent.notice_id.in_(mock_ids)).delete(synchronize_session=False)
            for m in mock_notices:
                db.delete(m)
            db.commit()
            print(f"[Clean] 成功清理 {len(mock_ids)} 条早期测试伪造数据及相关预警。")

        # 2. 清理宣传类新闻报道 (如候鸟备忘录、救人、工作宣传等非司法/交易信息)
        all_notices = db.query(CourtNotice).all()
        promo_deleted = 0
        for n in all_notices:
            if is_promotional_content(n.title, n.content_text):
                db.query(AlertEvent).filter(AlertEvent.notice_id == n.id).delete(synchronize_session=False)
                db.delete(n)
                promo_deleted += 1
        if promo_deleted > 0:
            db.commit()
            print(f"[Clean] 成功清理 {promo_deleted} 条宣传报道与工作非涉案信息。")

        # 3. 同平台同标题重复数据去重 (保留最新一条 ID)
        all_valid = db.query(CourtNotice).order_by(CourtNotice.id.desc()).all()
        seen_keys = {}
        dup_deleted = 0
        for n in all_valid:
            key = (n.platform, (n.title or "").strip())
            if key in seen_keys:
                # 重复项：清理其预警并删除该条重复记录
                db.query(AlertEvent).filter(AlertEvent.notice_id == n.id).delete(synchronize_session=False)
                db.delete(n)
                dup_deleted += 1
            else:
                seen_keys[key] = n.id
        if dup_deleted > 0:
            db.commit()
            print(f"[Clean] 成功合并清理 {dup_deleted} 条同平台重复冗余记录。")

        # 4. 涉豫识别重新判定与地市规范化
        remaining_notices = db.query(CourtNotice).all()
        fixed_geo_count = 0
        for n in remaining_notices:
            # 特殊情况处理：地方报按具体报纸校准地市
            if n.platform == "local_paper":
                if "许昌日报" in n.title or "许昌" in n.court_name:
                    n.is_henan = True
                    n.henan_city = "许昌"
                    n.henan_tag = "河南属地报纸法治专版 (《许昌日报》)"
                    fixed_geo_count += 1
                    continue
                elif "漯河日报" in n.title or "漯河" in n.court_name:
                    n.is_henan = True
                    n.henan_city = "漯河"
                    n.henan_tag = "河南属地报纸法治专版 (《漯河日报》)"
                    fixed_geo_count += 1
                    continue

            # 使用增强版 detect_henan_info 重新评估
            is_hn, h_city, h_tag = detect_henan_info(
                title=n.title,
                content=n.content_text,
                court_name=n.court_name,
                case_number=n.case_number or "",
                parties=n.parties or ""
            )

            # 统一地市写法：将 '河南全域'、'河南'、'省本级' 规范为 '全省'
            if h_city in ['河南全域', '河南', '省本级', None] and is_hn:
                h_city = "全省"

            if n.is_henan != is_hn or n.henan_city != h_city:
                n.is_henan = is_hn
                n.henan_city = h_city if is_hn else None
                n.henan_tag = h_tag if is_hn else None
                fixed_geo_count += 1

            # 模块分类重新校准
            n.module_type = categorize_notice_module(n.title, n.content_text, n.notice_type, n.platform)

        db.commit()
        print(f"[Clean] 成功规范重估 {fixed_geo_count} 条记录的涉豫地市与分类。")

        # 5. 清理孤儿预警
        valid_notice_ids = set(n.id for n in remaining_notices)
        all_alerts = db.query(AlertEvent).all()
        orphan_count = 0
        for a in all_alerts:
            if a.notice_id not in valid_notice_ids:
                db.delete(a)
                orphan_count += 1
        if orphan_count > 0:
            db.commit()
            print(f"[Clean] 成功清理 {orphan_count} 条孤儿预警记录。")

        # 6. 统计清洗后的最终数据大盘
        final_total = db.query(CourtNotice).count()
        final_henan = db.query(CourtNotice).filter(CourtNotice.is_henan == True).count()
        final_alerts = db.query(AlertEvent).count()
        print("\n=== 清洗后数据库概况 ===")
        print(f"有效司法/法拍记录总数: {final_total} 条")
        print(f"其中涉豫记录总数: {final_henan} 条")
        print(f"当前监控有效预警数: {final_alerts} 条")

        # 地市分布统计
        city_stats = {}
        for n in db.query(CourtNotice).filter(CourtNotice.is_henan == True).all():
            city_stats[n.henan_city] = city_stats.get(n.henan_city, 0) + 1
        print("涉豫地市规范化分布:")
        for c, cnt in sorted(city_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  * {c}: {cnt} 条")

    finally:
        db.close()

if __name__ == "__main__":
    clean_and_normalize_database()
