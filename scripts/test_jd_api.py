# -*- coding: utf-8 -*-
import sys
import asyncio
from playwright.async_api import async_playwright

async def test_jd_api():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        async def on_res(res):
            if "queryAnnouncement" in res.url:
                data = await res.json()
                sys.stdout.buffer.write(f"\nQUERY ANNOUNCEMENT DATA:\n{data}\n".encode('utf-8'))
            elif "getPaimaiCurrentInfo" in res.url:
                data = await res.json()
                sys.stdout.buffer.write(f"\nGET PAIMAI CURRENT INFO:\n{data}\n".encode('utf-8'))

        page.on("response", on_res)
        url = "https://paimai.jd.com/notice/14074839"
        await page.goto(url, timeout=20000)
        await page.wait_for_timeout(3000)
        await browser.close()

asyncio.run(test_jd_api())
