# -*- coding: utf-8 -*-
import urllib.request
import urllib.parse
import json

url = "https://rmfygg.court.gov.cn/web/rmfyportal/noticedetail?p_p_id=noticedetail_WAR_rmfynoticeDetailportlet&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_resource_id=noticeDetail&p_p_cacheability=cacheLevelPage&p_p_col_id=column-1&p_p_col_count=1"
data = urllib.parse.urlencode({
    "_noticedetail_WAR_rmfynoticeDetailportlet_uuid": "6091616044004473"
}).encode('utf-8')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://rmfygg.court.gov.cn/web/rmfyportal/noticedetail?paramStr=6091616044004473'
}

req = urllib.request.Request(url, data=data, headers=headers)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print("SUCCESS! Content length:", len(res.get("noticeContent", "")))
        print("noticeContent:", res.get("noticeContent")[:100])
except Exception as e:
    print("FAILED:", e)
