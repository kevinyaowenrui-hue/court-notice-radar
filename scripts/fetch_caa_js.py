# -*- coding: utf-8 -*-
import urllib.request
import re

url = "https://paimai.caa123.org.cn/scripts/pages/publicity/noticelist-44b85481.js"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=10) as resp:
    code = resp.read().decode('utf-8')
    print("JS len:", len(code))
    # find URLs in JS
    matches = re.findall(r'[\'"](/paimai-[^\'"]+)[\'"]', code)
    print("APIs found:")
    for m in set(matches):
        print("  ", m)
