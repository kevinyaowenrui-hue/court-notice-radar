"""Live Test for Playwright-based Crawlers:
- Ali (阿里司法拍卖)
- JD (京东资产/法拍)
- RMFYB (人民法院公告网 / 人民法院报)
"""

import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import asyncio
from backend.crawlers.ali_crawler import fetch_ali_real_auctions
from backend.crawlers.jd_crawler import fetch_jd_real_auctions
from backend.crawlers.rmfyb_crawler import fetch_rmfyb_real_notices

async def main():
    print("=== 开始 Playwright 真实无头浏览器抓取测试 ===")
    
    # 1. 阿里司法拍卖
    print("\n[1] 正在测试阿里司法拍卖 (Ali)...")
    try:
        ali_items = await fetch_ali_real_auctions()
        print(f"阿里抓取结果: 成功获取 {len(ali_items)} 条")
        if ali_items:
            for it in ali_items[:2]:
                print(f"  -> 标的: {it['title'][:35]} | 起拍价: {it['starting_price']} | 阶段: {it['auction_stage']} | 涉豫: {it['is_henan']}")
    except Exception as e:
        print(f"阿里抓取异常: {e}")

    # 2. 京东资产/法拍
    print("\n[2] 正在测试京东拍卖 (JD)...")
    try:
        jd_items = await fetch_jd_real_auctions()
        print(f"京东抓取结果: 成功获取 {len(jd_items)} 条")
        if jd_items:
            for it in jd_items[:2]:
                print(f"  -> 标的: {it['title'][:35]} | 处置方: {it['parties']} | 涉豫: {it['is_henan']}")
    except Exception as e:
        print(f"京东抓取异常: {e}")

    # 3. 人民法院公告网
    print("\n[3] 正在测试人民法院公告网 (RMFYB)...")
    try:
        rmfyb_items = await fetch_rmfyb_real_notices()
        print(f"人民法院公告网抓取结果: 成功获取 {len(rmfyb_items)} 条")
        if rmfyb_items:
            for it in rmfyb_items[:2]:
                print(f"  -> 法院: {it['court_name']} | 当事人: {it['parties']} | 类型: {it['notice_type']} | 涉豫: {it['is_henan']}")
    except Exception as e:
        print(f"人民法院公告网抓取异常: {e}")

if __name__ == "__main__":
    asyncio.run(main())
