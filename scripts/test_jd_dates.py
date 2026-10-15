# -*- coding: utf-8 -*-
import sqlite3
import re
from datetime import datetime

conn = sqlite3.connect('data/court_notices.db')
c = conn.cursor()

c.execute("SELECT id, raw_id, title, content_text FROM court_notices WHERE platform='jd' and publish_time is null")
rows = c.fetchall()
print(f"Total JD notices with publish_time IS NULL: {len(rows)}")

found = 0
not_found = []

def extract_notice_date(text):
    if not text:
        return None
    # 1. 查找明确标记的发布时间/刊登时间/公告时间
    m1 = re.search(r'(?:发布时间|刊登时间|公告时间|二审发布|上架时间)[：:\s]*(\d{4})[\s年\-/](\d{1,2})[\s月\-/](\d{1,2})日?', text)
    if m1:
        try:
            return datetime(int(m1.group(1)), int(m1.group(2)), int(m1.group(3)))
        except Exception:
            pass

    # 2. 查找文末落款日期 (如：某某法院 / 某某公司 ... 2026年10月10日)
    # 取末尾 500 个字符
    tail = text[-500:]
    # 支持 2026年10月10日 或 2026  年10月10日 或 2026-10-10
    dates = re.findall(r'(\d{4})\s*[年\-/]\s*(\d{1,2})\s*[月\-/]\s*(\d{1,2})\s*日?', tail)
    if dates:
        # 取最后一个日期（通常是落款发布日期）
        y, m, d = dates[-1]
        try:
            dt = datetime(int(y), int(m), int(d))
            # 过滤明显不是发布日期的年份（如未来年份超过1年，或者小于2015）
            if 2015 <= dt.year <= 2027:
                return dt
        except Exception:
            pass

    # 3. 查找中文数字落款日期（如：二〇二六年十月十日）
    cn_num = {'〇': '0', '一': '1', '二': '2', '三': '3', '四': '4', '五': '5', '六': '6', '七': '7', '八': '8', '九': '9', '十': '10', '0': '0', '1': '1', '2': '2', '3': '3'}
    m3 = re.search(r'([二2][〇0一1二2][〇0-9一-九]{2})\s*年\s*([一-十\d]{1,2})\s*月\s*([一-十\d]{1,3})\s*日', tail)
    if m3:
        # 尝试解析
        pass

    return None

for r in rows:
    dt = extract_notice_date(r[3])
    if dt:
        found += 1
    else:
        not_found.append((r[0], r[1], r[2]))

print(f"Can extract date from content: {found} / {len(rows)} ({(found/len(rows))*100:.1f}%)")
print(f"Remaining unknown: {len(not_found)}")
for nf in not_found[:10]:
    print("  Unknown:", nf)
