# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')
from backend.crawlers.rmfyb_crawler import fetch_rmfygg_detail

uuid = "6091768814004008"
print(f"Testing fetch_rmfygg_detail for {uuid}...")
res = fetch_rmfygg_detail(uuid)
print("Result:", res)
