# -*- coding: utf-8 -*-
import urllib.request
import json

url = "https://api.m.jd.com/api?appid=paimai&functionId=queryAnnouncement&body=%7B%22noticeId%22%3A%2214074839%22%7D"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://paimai.jd.com/notice/14074839'
}
req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        content = data.get('data', {}).get('content', '')
        print("SUCCESS! Content length:", len(content))
except Exception as e:
    print("FAILED:", e)
