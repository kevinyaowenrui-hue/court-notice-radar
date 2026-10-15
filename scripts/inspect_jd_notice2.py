# -*- coding: utf-8 -*-
import urllib.request
import re
from bs4 import BeautifulSoup

url = "https://paimai.jd.com/notice/14074839"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=10) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

soup = BeautifulSoup(html, 'html.parser')
scripts = soup.find_all('script')
print(f"Scripts count: {len(scripts)}")
for i, s in enumerate(scripts):
    txt = s.get_text()
    if any(k in txt for k in ['notice', 'item', 'price', 'product', 'detail', 'data']):
        print(f"Script {i} len {len(txt)}: {txt[:200]}...")

# Also look for main content text
main = soup.find('div', class_='notice-detail') or soup.find('div', id='content') or soup.find('div', class_='main')
if main:
    print("Main text:\n", main.get_text(separator=' ', strip=True)[:500])
else:
    body_text = soup.body.get_text(separator=' ', strip=True) if soup.body else ""
    print("Body text sample:\n", body_text[:500])
