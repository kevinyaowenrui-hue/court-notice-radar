# -*- coding: utf-8 -*-
import sys
import asyncio
from playwright.async_api import async_playwright

async def inspect_caa():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        apis = set()
        page.on("response", lambda res: apis.add(res.url) if "paimai" in res.url and not any(ext in res.url for ext in ['.css', '.png', '.jpg', '.svg', '.woff']) else None)
        
        # Test CAA notice list or auction list page
        for url in ["https://paimai.caa123.org.cn/pages/notice/list.html", "https://paimai.caa123.org.cn/pages/lots/list.html", "https://paimai.caa123.org.cn/pages/publicity/list.html"]:
            try:
                print(f"Loading {url}")
                await page.goto(url, timeout=15000)
                await page.wait_for_timeout(2500)
            except Exception as e:
                print(f"Error {url}: {e}")
                
        print("\nCaptured APIs:")
        for a in sorted(apis):
            if "search" in a or "list" in a or "notice" in a or "lot" in a:
                print("  ", a)
        await browser.close()

asyncio.run(inspect_caa())
