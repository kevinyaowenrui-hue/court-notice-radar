# -*- coding: utf-8 -*-
import sys
import asyncio
from playwright.async_api import async_playwright

async def inspect_caa_home():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        reqs = []
        page.on("request", lambda r: reqs.append((r.method, r.url)) if not any(ext in r.url for ext in ['.css', '.png', '.jpg', '.gif', '.svg', '.woff']) else None)
        
        url = "https://paimai.caa123.org.cn/"
        await page.goto(url, timeout=20000)
        await page.wait_for_timeout(4000)
        
        print(f"Total requests: {len(reqs)}")
        for m, u in reqs:
            if "caa123" in u:
                print(f"{m} {u}")
                
        # Also let's check links on page
        links = await page.query_selector_all("a")
        print(f"Total links: {len(links)}")
        for l in links[:30]:
            h = await l.get_attribute("href")
            t = (await l.inner_text()).strip()
            if h and t:
                print(f"LINK: {t} -> {h}")
        await browser.close()

asyncio.run(inspect_caa_home())
