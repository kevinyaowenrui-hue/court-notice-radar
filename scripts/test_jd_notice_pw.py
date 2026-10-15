# -*- coding: utf-8 -*-
import sys
import asyncio
from playwright.async_api import async_playwright

async def test_jd_notice():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        apis = []
        page.on("response", lambda res: apis.append((res.url, res.status)) if any(k in res.url for k in ['json', 'notice', 'detail', 'query', 'paimai', 'api']) else None)
        
        url = "https://paimai.jd.com/notice/14074839"
        await page.goto(url, timeout=20000)
        await page.wait_for_timeout(3000)
        
        # print api calls
        sys.stdout.buffer.write(f"Total API calls: {len(apis)}\n".encode('utf-8'))
        for u, s in apis:
            if not any(ext in u for ext in ['.js', '.css', '.png', '.jpg', '.svg']):
                sys.stdout.buffer.write(f"URL: {u} (status {s})\n".encode('utf-8'))
        
        # Check text on page
        text = await page.inner_text("body")
        sys.stdout.buffer.write(f"\nPAGE TEXT (first 1000 chars):\n{text[:1000]}\n".encode('utf-8'))
        await browser.close()

asyncio.run(test_jd_notice())
