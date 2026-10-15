# -*- coding: utf-8 -*-
import sys
import asyncio
from playwright.async_api import async_playwright

async def test_detail_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        page.on("request", lambda req: print("REQ:", req.method, req.url[:120]))
        page.on("response", lambda res: print("RESP:", res.status, res.url[:120]))

        print("Navigating to detail page directly...")
        try:
            await page.goto("https://rmfygg.court.gov.cn/web/rmfyportal/noticedetail?paramStr=6091616044004473", timeout=20000, wait_until="domcontentloaded")
            await page.wait_for_timeout(4000)
            title = await page.title()
            print("Page title:", title)
            text = await page.inner_text("body")
            print("Body text snippet:\n", text[:600])
        except Exception as e:
            print("Error navigating:", e)

        await browser.close()

asyncio.run(test_detail_page())
