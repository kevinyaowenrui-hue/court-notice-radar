# -*- coding: utf-8 -*-
import urllib.request
import json
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://paimai.jd.com/'
}

for nid in ['14079241', '14079242']:
    url = f"https://api.m.jd.com/api?appid=paimai&functionId=queryAnnouncement&body=%7B%22noticeId%22%3A%22{nid}%22%7D"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        content = data.get('data', {}).get('content', '')
        clean = re.sub(r'<[^>]+>', ' ', content)
        # find标的物 or 债务人
        m = re.findall(r'标的物[：:\s]*([^。\n]+)', clean)
        print(f"NID {nid} targets:", m)
        prices = re.findall(r'([0-9,.]+\s*(?:万元|元))', clean)
        print(f"NID {nid} prices:", prices[:5])
