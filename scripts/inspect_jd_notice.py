# -*- coding: utf-8 -*-
import urllib.request
import re

url = "https://paimai.jd.com/notice/14074839"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}
req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        print(f"HTML len: {len(html)}")
        # Look for prices, script data, json
        for line in html.splitlines():
            if any(k in line for k in ['price', 'Price', '评估', '起拍', 'current', 'assessment', 'start']):
                if len(line.strip()) < 300:
                    print("LINE:", line.strip())
except Exception as e:
    print("Error:", e)
