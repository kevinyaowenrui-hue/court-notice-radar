# -*- coding: utf-8 -*-
import urllib.request
import urllib.parse
import json

def test():
    req = urllib.request.urlopen('http://127.0.0.1:5220/api/stats')
    stats = json.loads(req.read().decode('utf-8'))
    print("=== Dashboard Stats ===")
    print("Total notices:", stats.get("total_notices"))
    print("Module counts:", stats.get("module_counts"))
    print("Henan module counts:", stats.get("henan", {}).get("module_counts"))

    print("\n=== Module Notices Query ===")
    for m in ["公告", "拍卖公告", "债权转让"]:
        url = f"http://127.0.0.1:5220/api/notices?module_type={urllib.parse.quote(m)}&limit=2"
        res = json.loads(urllib.request.urlopen(url).read().decode('utf-8'))
        print(f"[{m}] Total: {res['total']}")
        for item in res['items']:
            print(f"   -> [{item['platform']}] {item['module_type']} | {item['title'][:40]}")

if __name__ == '__main__':
    test()
