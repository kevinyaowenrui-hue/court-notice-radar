# -*- coding: utf-8 -*-
import urllib.request
import re

url = "https://paimai.caa123.org.cn/pages/publicity/item.html?publicityList=true&id=6148"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=10) as resp:
    html = resp.read().decode('utf-8')
    scripts = re.findall(r'<script[^>]*src=[\'"]([^\'"]+)[\'"]', html)
    print("Item scripts:")
    for s in scripts:
        print(" ", s)
