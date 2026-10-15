# -*- coding: utf-8 -*-
import os

HOST = "127.0.0.1"
# 遵循全局端口注册表，统一绑定 5220
PORT = int(os.environ.get("SERVER_PORT", 5220))

# 采集调度周期（分钟）
CRAWLER_INTERVAL_MINUTES = 30

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
