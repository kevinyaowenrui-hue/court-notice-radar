# -*- coding: utf-8 -*-
"""
53BK 报纸种子库采集器
从 http://www.53bk.com 采集全国各省市数字报纸的名称、所在城市、官方电子报入口并入库
"""
import urllib.request
import re
import time
from typing import List, Dict
from sqlalchemy.orm import Session
from backend.models import PaperSeed

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

def fetch_url(url: str, timeout: int = 8) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        content = resp.read()
        for enc in ['gbk', 'utf-8', 'gb2312']:
            try:
                return content.decode(enc)
            except Exception:
                pass
        return content.decode('gbk', errors='ignore')

def extract_regions() -> List[Dict]:
    """获取所有省份与城市列表"""
    html = fetch_url("http://www.53bk.com/baokan/")
    regions = []
    pattern = re.compile(r'<a\s+[^>]*href=["\'](/Baokan/Press/Region\?[^"\']+)["\'][^>]*>(.*?)</a>', re.I)
    for href, label in pattern.findall(html):
        clean_name = re.sub(r'<[^>]+>', '', label).strip()
        match = re.search(r'^(.*?)\((\d+)份\)$', clean_name)
        if match:
            name = match.group(1).strip()
            count = int(match.group(2))
            regions.append({
                "name": name,
                "count": count,
                "url": f"http://www.53bk.com{href}" if href.startswith('/') else href
            })
    return regions

def extract_papers_from_region(region_url: str, region_name: str) -> List[Dict]:
    """从具体城市/地区页面提取报纸名称与官方数字报链接"""
    html = fetch_url(region_url)
    papers = []
    pattern = re.compile(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I)
    for href, label in pattern.findall(html):
        clean_name = re.sub(r'<[^>]+>', '', label).strip()
        if not clean_name or any(k in clean_name for k in ['阅读', '订阅', '返回', '图文', '文字', '常见问题']):
            continue
        if href.startswith('http') and '53bk.com' not in href and any(k in clean_name for k in ['报', '网', '周刊', '晨刊', '晚刊']):
            papers.append({
                "paper_name": clean_name,
                "epaper_url": href,
                "city": region_name
            })
    return papers

def sync_53bk_seeds(db: Session, max_regions: int = 15) -> int:
    """抓取 53BK 种子并存入数据库，返回新增条数"""
    regions = extract_regions()
    added_count = 0
    # 优先抽取重点省市
    priority_keywords = ["北京", "上海", "广东", "浙江", "江苏", "山东", "四川", "陕西", "湖北", "河南", "深圳", "广州", "杭州", "南京"]
    sorted_regions = sorted(
        regions,
        key=lambda r: any(k in r["name"] for k in priority_keywords),
        reverse=True
    )

    for reg in sorted_regions[:max_regions]:
        try:
            papers = extract_papers_from_region(reg["url"], reg["name"])
            for p in papers:
                existing = db.query(PaperSeed).filter(
                    PaperSeed.paper_name == p["paper_name"],
                    PaperSeed.epaper_url == p["epaper_url"]
                ).first()
                if not existing:
                    # 判断省份与城市
                    seed = PaperSeed(
                        province=reg["name"].replace("市", "").replace("省", ""),
                        city=reg["name"],
                        paper_name=p["paper_name"],
                        epaper_url=p["epaper_url"],
                        is_monitored=True if any(k in p["paper_name"] for k in ["法治", "法制", "法院", "日报"]) else False
                    )
                    db.add(seed)
                    added_count += 1
            db.commit()
            time.sleep(0.3)
        except Exception as e:
            print(f"Error extracting region {reg['name']}: {e}")
            continue

    return added_count
