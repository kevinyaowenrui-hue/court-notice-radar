# -*- coding: utf-8 -*-
import urllib.request
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://paimai.caa123.org.cn/pages/publicity/list.html'
}

endpoints = [
    "https://paimai.caa123.org.cn/paimai-search/publicity/detail?id=6148",
    "https://paimai.caa123.org.cn/paimai-search/publicity/get?id=6148",
    "https://paimai.caa123.org.cn/paimai-search/publicity/info?id=6148",
    "https://paimai.caa123.org.cn/paimai-search/publicity/item?id=6148",
    "https://paimai.caa123.org.cn/paimai-search/publicity/publicityDetail?id=6148",
    "https://paimai.caa123.org.cn/paimai-search/publicity/getPublicityInfo?id=6148",
    "https://paimai.caa123.org.cn/paimai-web/auction/publicity/detail?id=6148",
    "https://paimai.caa123.org.cn/paimai-web/auction/publicity/get?id=6148",
]

for ep in endpoints:
    try:
        req = urllib.request.Request(ep, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read().decode('utf-8')
            print(f"SUCCESS: {ep} -> {data[:100]}")
    except Exception as e:
        # print status code
        print(f"FAILED {ep}: {e}")
