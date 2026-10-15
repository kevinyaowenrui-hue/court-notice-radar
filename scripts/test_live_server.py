# -*- coding: utf-8 -*-
import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
url = 'http://127.0.0.1:5220/api/alerts?time_range=today&henan_only=true'
with urllib.request.urlopen(url) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    print('Status: OK')
    print('Total:', data['total'])
    print('Tab counts:', data['tab_counts'])
    print('Items returned:', len(data['items']))
    for it in data['items'][:5]:
        n = it['notice']
        print(f"  [{n['platform']:5s}] {n['module_type']:4s} | {n['publish_time']} | {n['title'][:32]}")
