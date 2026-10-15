import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

def test():
    base = "http://127.0.0.1:5220/api"
    with urllib.request.urlopen(f"{base}/stats") as r:
        s = json.loads(r.read())
        print("TOTAL NOTICES:", s["total_notices"])
        print("HENAN STATS:", json.dumps(s.get("henan", {}), ensure_ascii=False))

    with urllib.request.urlopen(f"{base}/notices?henan_only=true&limit=6") as r:
        data = json.loads(r.read())
        print(f"\nHENAN NOTICES COUNT: {data['total']}")
        for n in data["items"]:
            print(f"- [{n['platform']}] [{n['henan_city']}] {n['title']} -> {n['henan_tag']}")

    with urllib.request.urlopen(f"{base}/alerts?henan_only=true&limit=5") as r:
        data = json.loads(r.read())
        print(f"\nHENAN ALERTS COUNT: {data['total']}")
        for a in data["items"]:
            print(f"- Rule: {a['rule_name']} | Reason: {a['match_reason']} | City: {a['notice'].get('henan_city')}")

if __name__ == '__main__':
    test()
