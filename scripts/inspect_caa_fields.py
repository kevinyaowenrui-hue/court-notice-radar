# -*- coding: utf-8 -*-
import urllib.request
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://paimai.caa123.org.cn/'
}

url = "https://paimai.caa123.org.cn/paimai-search/publicity/list?start=0&count=5"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=10) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    items = data.get('data', {}).get('items', [])
    for it in items:
        print("--- ITEM ---")
        for k, v in it.items():
            print(f"  {k}: {v}")
