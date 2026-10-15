# -*- coding: utf-8 -*-
import sys
import asyncio
from playwright.async_api import async_playwright

async def inspect_caa_body():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        url = "https://paimai.caa123.org.cn/pages/publicity/list.html"
        await page.goto(url, timeout=20000)
        await page.wait_for_timeout(3000)
        print("TITLE:", await page.title())
        print("URL:", page.url)
        content = await page.content()
        print("CONTENT LEN:", len(content))
        # check scripts in content
        import re
        scripts = re.findall(r'<script[^>]*src=[\'"]([^\'"]+)[\'"]', content)
        for s in scripts:
            print("SCRIPT SRC:", s)
        await browser.close()

asyncio.run(inspect_caa_body())
