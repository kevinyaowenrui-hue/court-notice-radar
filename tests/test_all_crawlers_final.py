"""Final Verification Test Suite for All 6 Data Ingestion Modules.

Verifies end-to-end live scraping and structured extraction for:
1. CAA (中拍平台)
2. GGZY (公共资源交易平台)
3. Local Paper (53BK地方数字报)
4. Ali (阿里司法拍卖)
5. JD (京东司法拍卖与资产)
6. RMFYB (人民法院公告网)
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import asyncio
from backend.database import SessionLocal
from backend.models import PaperSeed

async def run_all_verification():
    print("=" * 60)
    print(" CourtNoticeRadar 全数据采集渠道 Live 获取能力最终大体验 ")
    print("=" * 60)

    summary = {}

    # 1. 中拍平台 (CAA)
    print("\n>>> [1/6] 测试中拍平台 (CAA)...")
    try:
        from backend.crawlers.caa_crawler import fetch_caa_items
        caa_items = fetch_caa_items(count=15, filter_content="河南")
        summary["CAA"] = {"count": len(caa_items), "status": "OK"}
        print(f"CAA 抓取成功: {len(caa_items)} 条公示")
        if caa_items:
            print(f"  示例: {caa_items[0]['title'][:35]} | 主体: {caa_items[0]['court_name']} | 涉豫: {caa_items[0]['is_henan']}")
    except Exception as e:
        summary["CAA"] = {"count": 0, "status": f"FAILED: {e}"}
        print(f"CAA 抓取失败: {e}")

    # 2. 公共资源交易平台 (GGZY)
    print("\n>>> [2/6] 测试公共资源交易平台 (GGZY)...")
    try:
        from backend.crawlers.ggzy_crawler import fetch_shangqiu_cqjy
        ggzy_items = fetch_shangqiu_cqjy(max_pages=1)
        summary["GGZY"] = {"count": len(ggzy_items), "status": "OK"}
        print(f"GGZY 抓取成功: {len(ggzy_items)} 条产权标的")
        if ggzy_items:
            print(f"  示例: {ggzy_items[0]['title'][:35]} | 类型: {ggzy_items[0]['notice_type']}")
    except Exception as e:
        summary["GGZY"] = {"count": 0, "status": f"FAILED: {e}"}
        print(f"GGZY 抓取失败: {e}")

    # 3. 地方报纸 (Local Paper)
    print("\n>>> [3/6] 测试地方报纸专版与数字报 (Local Paper)...")
    try:
        from backend.crawlers.local_paper_crawler import scan_single_paper
        db = SessionLocal()
        # 挑选已验证的商丘日报
        seed = db.query(PaperSeed).filter(PaperSeed.id == 340).first()
        if seed:
            paper_items = scan_single_paper(seed)
            summary["LocalPaper"] = {"count": len(paper_items), "status": "OK"}
            print(f"《{seed.paper_name}》抓取成功: {len(paper_items)} 篇司法/政府公告")
            if paper_items:
                print(f"  示例: {paper_items[0]['title'][:40]}")
        else:
            summary["LocalPaper"] = {"count": 0, "status": "No seed"}
        db.close()
    except Exception as e:
        summary["LocalPaper"] = {"count": 0, "status": f"FAILED: {e}"}
        print(f"地方报纸抓取失败: {e}")

    # 4. 阿里司法拍卖 (Ali)
    print("\n>>> [4/6] 测试阿里司法拍卖 (Ali)...")
    try:
        from backend.crawlers.ali_crawler import fetch_ali_real_auctions
        ali_items = await fetch_ali_real_auctions()
        summary["Ali"] = {"count": len(ali_items), "status": "OK"}
        print(f"阿里法拍抓取成功: {len(ali_items)} 条真实法拍标的")
        if ali_items:
            item_desc = f"{ali_items[0]['title'][:30]} | 起拍: {ali_items[0]['starting_price']} | 阶段: {ali_items[0]['auction_stage']} | 涉豫: {ali_items[0]['is_henan']}"
            print(f"  示例: {item_desc.encode('gbk', errors='replace').decode('gbk')}")
    except Exception as e:
        summary["Ali"] = {"count": 0, "status": f"FAILED: {e}"}
        print(f"阿里法拍抓取失败: {e}")

    # 5. 京东司法拍卖与资产大盘 (JD)
    print("\n>>> [5/6] 测试京东司法拍卖与资产大盘 (JD)...")
    try:
        from backend.crawlers.jd_crawler import fetch_jd_real_auctions
        jd_items = await fetch_jd_real_auctions()
        summary["JD"] = {"count": len(jd_items), "status": "OK"}
        print(f"京东资产/法拍抓取成功: {len(jd_items)} 条真实标的")
        if jd_items:
            henan_samples = [it for it in jd_items if it['is_henan']]
            show_item = henan_samples[0] if henan_samples else jd_items[0]
            item_desc = f"{show_item['title'][:30]} | 起拍: {show_item['starting_price']} | 阶段: {show_item['auction_stage']} | 涉豫: {show_item['is_henan']}"
            print(f"  示例: {item_desc.encode('gbk', errors='replace').decode('gbk')}")
    except Exception as e:
        summary["JD"] = {"count": 0, "status": f"FAILED: {e}"}
        print(f"京东法拍抓取失败: {e}")

    # 6. 人民法院公告网 (RMFYB)
    print("\n>>> [6/6] 测试人民法院公告网 (RMFYB)...")
    try:
        from backend.crawlers.rmfyb_crawler import fetch_rmfyb_real_notices
        rmfyb_items = await fetch_rmfyb_real_notices()
        summary["RMFYB"] = {"count": len(rmfyb_items), "status": "OK"}
        print(f"人民法院公告网抓取成功: {len(rmfyb_items)} 条权威法院公告")
        if rmfyb_items:
            item_desc = f"法院: {rmfyb_items[0]['court_name']} | 当事人: {rmfyb_items[0]['parties']} | 类型: {rmfyb_items[0]['notice_type']} | 涉豫: {rmfyb_items[0]['is_henan']}"
            print(f"  示例: {item_desc.encode('gbk', errors='replace').decode('gbk')}")
    except Exception as e:
        summary["RMFYB"] = {"count": 0, "status": f"FAILED: {e}"}
        print(f"人民法院公告网抓取失败: {e}")

    print("\n" + "=" * 60)
    print(" 各平台数据采集能力汇总考核结果 ")
    print("=" * 60)
    all_passed = True
    for k, v in summary.items():
        tag = "[PASS]" if v["status"] == "OK" and v["count"] > 0 else "[FAIL]"
        print(f"{tag} 平台: {k:<12} | 状态: {v['status']} | 成功获取条数: {v['count']}")
        if v["count"] == 0:
            all_passed = False

    return all_passed

if __name__ == "__main__":
    asyncio.run(run_all_verification())
