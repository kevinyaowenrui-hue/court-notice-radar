# -*- coding: utf-8 -*-
"""
彻底清洗数据库中的机动车辆、重型和大型机械设备
确保系统严格以公告、法院公告、司法拍卖（不动产）和债权转让为主
"""
import sys
from sqlalchemy import func
from backend.database import SessionLocal
from backend.models import CourtNotice, AlertEvent
from backend.utils import is_vehicle_or_equipment_item

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def clean_database():
    db = SessionLocal()
    try:
        all_notices = db.query(CourtNotice).all()
        print(f"Total notices before cleaning: {len(all_notices)}")

        deleted_count = 0
        corrected_count = 0

        # 不动产误判保护纠偏列表
        # 例如包含车位、车库、厂房、房地产且非纯车辆纯设备的标的
        immobile_corrections = [
            ("车位", "住宅/商业房产"),
            ("车库", "住宅/商业房产"),
            ("人防车位", "住宅/商业房产"),
            ("车房", "住宅/商业房产"),
            ("房产和办公电子设备", "住宅/商业房产"),
            ("房地产及机器设备", "住宅/商业房产"),
            ("房屋建筑物、土地使用权、机器设备", "工业厂房与土地"),
            ("国有建设用地使用权", "工业厂房与土地"),
        ]

        for n in all_notices:
            t = n.title or ""
            c = n.content_text or ""
            current_cat = n.asset_category or ""

            # 1. 优先检查是否为“附带车位/附带设备的不动产”误判，进行修正
            is_corrected = False
            for kw, target_cat in immobile_corrections:
                if kw in t and any(core in t for core in ["房", "室", "楼", "住宅", "别墅", "房地产", "土地", "建设用地", "厂房"]):
                    if current_cat in ["机动车辆", "机械与重型设备", "机器设备", "机器设备与车辆", "综合大宗资产"]:
                        print(f"[CORRECTED] ID {n.id} -> {target_cat}: {t[:60]}")
                        n.asset_category = target_cat
                        corrected_count += 1
                        is_corrected = True
                        break
            if is_corrected:
                continue

            # 2. 判断是否属于机动车辆或重型设备
            should_delete = False
            delete_reason = ""

            if current_cat in ["机动车辆", "机械与重型设备", "机器设备", "机器设备与车辆", "工业采矿及机械设备"]:
                should_delete = True
                delete_reason = f"Category '{current_cat}'"
            elif is_vehicle_or_equipment_item(t, c):
                should_delete = True
                delete_reason = "Hit vehicle/equipment exclusion"

            if should_delete:
                print(f"[DELETED] ID {n.id} [{n.platform}] ({delete_reason}): {t[:60]}")
                # 清除可能关联的告警记录
                db.query(AlertEvent).filter(AlertEvent.notice_id == n.id).delete()
                db.delete(n)
                deleted_count += 1

        db.commit()
        print(f"\nCleaning Complete!")
        print(f"  Corrected to Real Estate: {corrected_count}")
        print(f"  Deleted Vehicles & Heavy Machinery: {deleted_count}")

        # 验证清洗后统计
        remaining_total = db.query(CourtNotice).count()
        print(f"Remaining notices in DB: {remaining_total}")

        print("\n--- Remaining Asset Categories ---")
        cats = db.query(CourtNotice.asset_category, func.count(CourtNotice.id)).group_by(CourtNotice.asset_category).all()
        for cat, cnt in cats:
            print(f"  {cat}: {cnt}")

        print("\n--- Remaining Module Types ---")
        mods = db.query(CourtNotice.module_type, func.count(CourtNotice.id)).group_by(CourtNotice.module_type).all()
        for mod, cnt in mods:
            print(f"  {mod}: {cnt}")

    finally:
        db.close()

if __name__ == "__main__":
    clean_database()
