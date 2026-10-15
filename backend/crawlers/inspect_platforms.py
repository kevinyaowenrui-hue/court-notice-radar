# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('data/court_notices.db')
cursor = conn.cursor()

print("=== CAA 样本数据 (前5条) ===")
cursor.execute("SELECT id, title, module_type, is_henan, henan_city, starting_price FROM court_notices WHERE platform='caa' LIMIT 5")
for r in cursor.fetchall():
    print(" ", r)

print("\n=== RMFYB 样本数据 (前5条) ===")
cursor.execute("SELECT id, title, module_type, is_henan, henan_city, notice_type FROM court_notices WHERE platform='rmfyb' LIMIT 5")
for r in cursor.fetchall():
    print(" ", r)

print("\n=== CAA 模块分布 ===")
cursor.execute("SELECT module_type, is_henan, COUNT(*) FROM court_notices WHERE platform='caa' GROUP BY module_type, is_henan")
for r in cursor.fetchall():
    print(" ", r)

print("\n=== RMFYB 模块分布 ===")
cursor.execute("SELECT module_type, is_henan, COUNT(*) FROM court_notices WHERE platform='rmfyb' GROUP BY module_type, is_henan")
for r in cursor.fetchall():
    print(" ", r)

print("\n=== 各平台 is_henan 比例 ===")
cursor.execute("SELECT platform, is_henan, COUNT(*) FROM court_notices GROUP BY platform, is_henan")
for r in cursor.fetchall():
    print(" ", r)

conn.close()
