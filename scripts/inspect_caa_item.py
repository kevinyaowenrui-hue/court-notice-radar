# -*- coding: utf-8 -*-
import sys
import asyncio
from playwright.async_api import async_playwright

async def inspect_caa_item():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        apis = []
        page.on("response", lambda r: apis.append((r.url, r.status)) if "paimai" in r.url and not any(ext in r.url for ext in ['.css', '.png', '.jpg', '.js']) else None)
        
        url = "https://paimai.caa123.org.cn/pages/publicity/item.html?publicityList=true&id=6148"
        await page.goto(url, timeout=20000)
        await page.wait_for_timeout(3000)
        
        print(f"APIs called on item.html:")
        for u, s in apis:
            print(f"  {u} ({s})")
            
        text = await page.inner_text("body")
        sys.stdout.buffer.write(f"\nITEM TEXT:\n{text[:1000]}\n".encode('utf-8'))
        await browser.close()

asyncio.run(inspect_caa_item())
