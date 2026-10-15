# -*- coding: utf-8 -*-
import urllib.request
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://paimai.jd.com/'
}

for nid in ['14079241', '14079242']:
    url = f"https://api.m.jd.com/api?appid=paimai&functionId=queryAnnouncement&body=%7B%22noticeId%22%3A%22{nid}%22%7D"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            title = data.get('data', {}).get('title', '')
            content = data.get('data', {}).get('content', '')
            # clean html
            import re
            clean = re.sub(r'<[^>]+>', ' ', content)
            print(f"NID {nid} TITLE: {title}")
            print(f"NID {nid} CONTENT: {clean[:200]}")
    except Exception as e:
        print(f"Error {nid}:", e)
