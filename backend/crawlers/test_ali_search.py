# -*- coding: utf-8 -*-
import asyncio
from urllib.parse import quote
from playwright.async_api import async_playwright
from backend.utils import launch_smart_browser

async def test():
    async with async_playwright() as p:
        browser = await launch_smart_browser(p, headless=True)
        page = await browser.new_page()
        
        # 尝试通过搜索参数 q=河南 / q=郑州
        test_queries = ['河南', '郑州', '洛阳']
        for kw in test_queries:
            gbk_kw = quote(kw.encode('gbk'))
            utf8_kw = quote(kw.encode('utf-8'))
            url1 = f"https://sf.taobao.com/item_list.htm?q={gbk_kw}"
            url2 = f"https://sf.taobao.com/item_list.htm?q={utf8_kw}"
            for u in [url1, url2]:
                try:
                    await page.goto(u, timeout=20000, wait_until='domcontentloaded')
                    await page.wait_for_timeout(2500)
                    cards = await page.query_selector_all("a[href*='sf_item'], a[href*='sf-item.taobao.com']")
                    items = await page.query_selector_all(".sf-item, .item-list, li.item")
                    print(f"URL: {u} -> cards: {len(cards)}, li items: {len(items)}")
                except Exception as e:
                    print("Error:", e)

        await browser.close()

if __name__ == '__main__':
    asyncio.run(test())
