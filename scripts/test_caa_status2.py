# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import urllib.request
import json
from backend.crawlers.caa_crawler import fetch_caa_detail, HEADERS

url = "https://paimai.caa123.org.cn/paimai-search/publicity/list?start=0&count=5&publishStatus=2"
req = urllib.request.Request(url, headers=HEADERS)
with urllib.request.urlopen(req, timeout=10) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    items = data.get('data', {}).get('items', [])
    print(f"Items with publishStatus=2: {len(items)}")
    for it in items:
        pid = it.get('id')
        title = it.get('title')
        status = it.get('publishStatus')
        detail = fetch_caa_detail(pid)
        lots = detail.get('publicityLotDTOS') or []
        sp = lots[0].get('startPrice') if lots else None
        print(f"ID={pid}, status={status}, sp={sp}, title={title[:40]}")
