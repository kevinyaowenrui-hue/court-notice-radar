# -*- coding: utf-8 -*-
import sqlite3
import re

PAPERS_MAP = {
    "郑州日报": "https://zzrb.zynews.cn/",
    "郑州晚报": "https://zzwb.zynews.cn/",
    "河南日报": "https://newpaper.dahe.cn/hnrb/",
    "大河报": "https://newpaper.dahe.cn/dhb/",
    "河南法制报": "http://epaper.hnfzb.com:8080/",
    "河南商报": "https://newpaper.dahe.cn/hnsb/",
    "开封日报": "https://www.kf.cn/",
    "汴梁晚报": "https://www.kf.cn/",
    "洛阳日报": "http://lyrb.lyd.com.cn/",
    "洛阳晚报": "http://lywb.lyd.com.cn/",
    "平顶山日报": "http://epaper.pdsxww.com/pdsrb/",
    "平顶山晚报": "http://epaper.pdsxww.com/pdswb/",
    "安阳日报": "https://www.ayrbs.com/szb/",
    "鹤壁日报": "https://paper.hebiw.com/epaper/hbrb/",
    "新乡日报": "http://rb.xxrb.com.cn/",
    "平原晚报": "http://wb.xxrb.com.cn/",
    "焦作日报": "http://epaper.jzrb.com/",
    "焦作晚报": "http://wbpaper.jzrb.com/",
    "濮阳日报": "http://pyrb.pyxww.com/",
    "许昌日报": "http://www.21xc.com/",
    "许昌晨报": "http://szb.21xc.com/xccb/",
    "漯河日报": "http://www.lhrb.com.cn/",
    "三门峡日报": "https://szb.ismx.cn/smxrb/",
    "南阳日报": "http://epaper.01ny.cn/",
    "南阳晚报": "http://epaper.01ny.cn/",
    "商丘日报": "https://epaper.sqrb.com.cn/",
    "京九晚报": "https://epaper.sqrb.com.cn/",
    "信阳日报": "https://ribao.xyxww.com.cn/",
    "周口日报": "http://www.zhld.com/",
    "驻马店日报": "http://zmdrb.zmdnews.cn/",
    "济源日报": "http://www.jyrb.cn/"
}

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, title, content_text, source_url FROM court_notices WHERE platform='local_paper'")
rows = c.fetchall()

updated = 0
for rid, title, content, s_url in rows:
    # 查找报纸名字
    paper_found = None
    for p_name in PAPERS_MAP:
        if p_name in title or (content and p_name in content):
            paper_found = p_name
            break
    
    if paper_found:
        real_url = PAPERS_MAP[paper_found]
        # 更新 source_url
        c.execute("UPDATE court_notices SET source_url=? WHERE id=?", (real_url, rid))
        updated += 1

conn.commit()
print(f"Total local_paper notices updated with official e-paper URLs: {updated}/{len(rows)}")

# 验证更新结果
c.execute("SELECT count(*) FROM court_notices WHERE source_url LIKE '%53bk.com/baokan/%'")
print("Remaining invalid 53bk/baokan URLs:", c.fetchone()[0])
conn.close()
