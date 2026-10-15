# -*- coding: utf-8 -*-
import subprocess
import json

url = 'https://hnsggzyjy.henan.gov.cn/EpointWebBuilder/rest/frontAppCustomAction/getPageInfoListNewYzm'
post_data = "siteGuid=7eb5f7f1-9041-43ad-8e13-8fcb82ea831a&categoryNum=002003&kw=&startDate=&endDate=&pageIndex=0&pageSize=5&jytype=&YZM=&ImgGuid=&xiaqucode="
cmd = ['curl.exe', '-k', '-s', '-X', 'POST', '-d', post_data, '-H', 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8', url]
out = subprocess.check_output(cmd).decode('utf-8', errors='ignore')
data = json.loads(out)
items = data.get('custom', {}).get('infodata', [])
print(f"Henan Provincial items count: {len(items)}")
if items:
    print("Item keys:", list(items[0].keys()))
    for it in items[:3]:
        print("TITLE:", it.get('title'))
        print("KEYS & VALUES:")
        for k in ['title', 'infodate', 'categoryname', 'xiaquname', 'infourl', 'zhaiyao', 'intro', 'content']:
            if it.get(k):
                print(f"  {k}: {str(it.get(k))[:150]}")
