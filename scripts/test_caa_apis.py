# -*- coding: utf-8 -*-
import urllib.request
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://paimai.caa123.org.cn/'
}

# Test 1: publicity list with status
# In caa_crawler.py:
# status_code = it.get('publishStatus')
# status_str = "公示中" if status_code == 2 else ("公示结束" if status_code == 4 else "已发布")
# Can we filter by publishStatus=2 (公示中) or auction list?
urls = [
    "https://paimai.caa123.org.cn/paimai-search/publicity/list?start=0&count=10&publishStatus=2",
    "https://paimai.caa123.org.cn/paimai-search/publicity/list?start=0&count=10",
    "https://paimai.caa123.org.cn/paimai-search/lots/list?start=0&count=10",
    "https://paimai.caa123.org.cn/paimai-search/lots/list?start=0&count=10&status=2"
]

for u in urls:
    try:
        req = urllib.request.Request(u, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            items = data.get('data', {}).get('items', [])
            total = data.get('data', {}).get('total', len(items))
            print(f"URL: {u.split('?')[0]}?{u.split('?')[-1][:50]}")
            print(f"Total: {total}, items returned: {len(items)}")
            if items:
                print("First item keys:", list(items[0].keys())[:8])
                print("First item title/name:", items[0].get('title') or items[0].get('lotName') or items[0].get('name'))
                print("First item price/status:", items[0].get('price') or items[0].get('startPrice'), items[0].get('publishStatus') or items[0].get('status'))
    except Exception as e:
        print(f"Error {u}:", e)
