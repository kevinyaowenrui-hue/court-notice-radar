# -*- coding: utf-8 -*-
import urllib.request
import json

url = "https://paimai.caa123.org.cn/paimai-search/publicity/detail?publicityId=6148"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=10) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    print("KEYS:", list(data.get("data", {}).keys()))
    for k, v in data.get("data", {}).items():
        if k in ['title', 'startTime', 'endTime', 'publishStatus', 'companyName', 'noticeContent', 'publicityLotDTOS', 'publicitySummaryInfo', 'publicitySummaryInfoDTO']:
            print(f"  {k}: {v}")
