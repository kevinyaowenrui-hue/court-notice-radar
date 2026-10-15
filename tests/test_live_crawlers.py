"""Live Crawler Health & Ingestion Test Suite.

Tests live fetching ability for each crawler platform:
1. CAA (中拍平台 API)
2. GGZY (公共资源交易平台 HTTP)
3. 53BK & Local Paper (地方报纸 / 电子报版面)
4. Ali (阿里司法拍卖 Playwright)
5. JD (京东司法拍卖 / 资产处置 Playwright)
6. RMFYB (人民法院公告网 / 人民法院报 Playwright)
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import asyncio
from backend.database import SessionLocal
from backend.models import PaperSeed

def test_caa_live():
    print("\n--- [1] 测试中拍平台 (CAA) Live 获取能力 ---")
    from backend.crawlers.caa_crawler import fetch_caa_items
    items = fetch_caa_items(count=10, filter_content="河南")
    print(f"CAA 抓取结果: 成功获取 {len(items)} 条公示")
    if items:
        sample = items[0]
        print(f"示例标的: 标题='{sample['title'][:30]}...', 发布主体='{sample['court_name']}', 涉豫={sample['is_henan']}")
    assert len(items) > 0, "CAA 应该能获取到至少 1 条数据"
    return True

def test_ggzy_live():
    print("\n--- [2] 测试公共资源交易平台 (GGZY) Live 获取能力 ---")
    from backend.crawlers.ggzy_crawler import fetch_shangqiu_cqjy
    items = fetch_shangqiu_cqjy(max_pages=1)
    print(f"GGZY 商丘产权抓取结果: 成功获取 {len(items)} 条")
    if items:
        sample = items[0]
        print(f"示例标的: 标题='{sample['title'][:30]}...', 类型='{sample['notice_type']}', 来源='{sample['source_url']}'")
    assert len(items) > 0, "GGZY 商丘产权应该能获取到数据"
    return True

def test_53bk_and_local_paper():
    print("\n--- [3] 测试 53BK 种子与地方报纸 Live 获取能力 ---")
    from backend.crawlers.seed_53bk import extract_regions
    from backend.crawlers.local_paper_crawler import scan_single_paper

    # 1. 测试 53bk 网站入口
    regions = extract_regions()
    print(f"53BK 地区导航解析: 获取到 {len(regions)} 个省市地区")
    assert len(regions) > 0, "53BK 应该能解析出地区"

    # 2. 从数据库挑一个真实的已监控地方报纸进行扫描
    db = SessionLocal()
    try:
        sample_seed = db.query(PaperSeed).filter(PaperSeed.is_monitored == True, PaperSeed.epaper_url != "").first()
        if sample_seed:
            print(f"测试扫描地方报: 《{sample_seed.paper_name}》 ({sample_seed.epaper_url})")
            articles = scan_single_paper(sample_seed)
            print(f"扫描结果: 发现有效文章/公告 {len(articles)} 条")
    finally:
        db.close()
    return True

async def test_ali_live():
    print("\n--- [4] 测试阿里司法拍卖 (Ali) Live 获取能力 ---")
    from backend.crawlers.ali_crawler import fetch_ali_real_auctions
    items = await fetch_ali_real_auctions()
    print(f"阿里司法拍卖抓取结果: 成功获取 {len(items)} 条标的")
    if items:
        sample = items[0]
        print(f"示例标的: 标题='{sample['title'][:30]}...', 起拍价={sample['starting_price']}, 阶段={sample['auction_stage']}, 涉豫={sample['is_henan']}")
    return len(items)

async def test_jd_live():
    print("\n--- [5] 测试京东司法拍卖 (JD) Live 获取能力 ---")
    from backend.crawlers.jd_crawler import fetch_jd_real_auctions
    items = await fetch_jd_real_auctions()
    print(f"京东资产/司法拍卖抓取结果: 成功获取 {len(items)} 条标的")
    if items:
        sample = items[0]
        print(f"示例标的: 标题='{sample['title'][:30]}...', 处置方='{sample['parties']}', 涉豫={sample['is_henan']}")
    return len(items)

async def test_rmfyb_live():
    print("\n--- [6] 测试人民法院公告网 (RMFYB) Live 获取能力 ---")
    from backend.crawlers.rmfyb_crawler import fetch_rmfyb_real_notices
    items = await fetch_rmfyb_real_notices()
    print(f"人民法院公告网抓取结果: 成功获取 {len(items)} 条公示")
    if items:
        sample = items[0]
        print(f"示例公示: 法院='{sample['court_name']}', 当事人='{sample['parties']}', 类型='{sample['notice_type']}'")
    return len(items)

if __name__ == "__main__":
    print("开始各平台爬虫 Live 连通与数据获取检测...")
    test_caa_live()
    test_ggzy_live()
    test_53bk_and_local_paper()
