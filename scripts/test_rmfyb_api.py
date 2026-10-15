# -*- coding: utf-8 -*-
import sys
import asyncio
from playwright.async_api import async_playwright

async def test_detail():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        async def handle_response(res):
            if "resource_id=noticeDetail" in res.url:
                try:
                    data = await res.json()
                    sys.stdout.buffer.write(f"\nAPI DATA: {data}\n".encode('utf-8'))
                except Exception as e:
                    text = await res.text()
                    sys.stdout.buffer.write(f"\nAPI TEXT: {text[:500]}\n".encode('utf-8'))

        page.on("response", handle_response)
        url = "https://rmfygg.court.gov.cn/web/rmfyportal/noticedetail?paramStr=6091616044004473"
        await page.goto(url, timeout=20000)
        await page.wait_for_timeout(3000)
        
        # Also check page elements
        content_el = await page.query_selector(".content, .notice-content, .detail-content, #content, .table")
        if content_el:
            txt = await content_el.inner_text()
            sys.stdout.buffer.write(f"\nELEMENT TEXT: {txt}\n".encode('utf-8'))
        else:
            body = await page.inner_text("body")
            sys.stdout.buffer.write(f"\nFULL BODY:\n{body}\n".encode('utf-8'))

        await browser.close()

asyncio.run(test_detail())
