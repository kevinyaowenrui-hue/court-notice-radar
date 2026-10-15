# -*- coding: utf-8 -*-
import sys
import asyncio
from playwright.async_api import async_playwright

async def test_detail_req():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        async def handle_request(req):
            if "resource_id=noticeDetail" in req.url:
                sys.stdout.buffer.write(f"\nMETHOD: {req.method}\nURL: {req.url}\nHEADERS: {req.headers}\nPOST DATA: {req.post_data}\n".encode('utf-8'))

        page.on("request", handle_request)
        url = "https://rmfygg.court.gov.cn/web/rmfyportal/noticedetail?paramStr=6091616044004473"
        await page.goto(url, timeout=20000)
        await page.wait_for_timeout(2000)
        await browser.close()

asyncio.run(test_detail_req())
