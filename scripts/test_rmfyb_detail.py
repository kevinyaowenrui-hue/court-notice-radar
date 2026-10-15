# -*- coding: utf-8 -*-
import asyncio
from playwright.async_api import async_playwright

async def test_detail():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        url = "https://rmfygg.court.gov.cn/web/rmfyportal/noticedetail?paramStr=6091616044004473"
        print(f"Going to {url}")
        page.on("response", lambda res: print("API Response:", res.url) if "notice" in res.url else None)
        try:
            await page.goto(url, timeout=20000)
            await page.wait_for_timeout(3000)
            text = await page.inner_text("body")
            print("PAGE BODY:\n", text[:1000])
        except Exception as e:
            print("Error:", e)
        await browser.close()

asyncio.run(test_detail())
