# -*- coding: utf-8 -*-
import asyncio
from playwright.async_api import async_playwright
from backend.utils import launch_smart_browser

async def test():
    async with async_playwright() as p:
        browser = await launch_smart_browser(p, headless=True)
        page = await browser.new_page()
        # Test homepage: https://sf.taobao.com/?order=createTime_desc
        url = 'https://sf.taobao.com/?order=createTime_desc'
        print('Navigating to:', url)
        await page.goto(url, timeout=30000, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        
        cards = await page.query_selector_all("a[href*='sf_item'], a[href*='sf-item.taobao.com'], a[href*='item.htm?id=']")
        print(f"Found cards on homepage: {len(cards)}")
        for c in cards[:5]:
            href = await c.get_attribute('href')
            text = (await c.inner_text()).strip()
            print(f"  Href: {href} | Text: {text[:60].replace(chr(10), ' ')}")

        # Now test what selector holds item cards on list page
        url2 = 'https://sf.taobao.com/item_list.htm?spm=a213w.7398504.filter.1.72d11e86iKkL9u&category=50025969&province=%BA%D3%C4%CF'
        print('\nNavigating to list page:', url2)
        await page.goto(url2, timeout=30000, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        all_links = await page.query_selector_all("a")
        print(f"Total links on list page: {len(all_links)}")
        sample_links = []
        for l in all_links:
            h = await l.get_attribute('href') or ''
            if any(k in h for k in ['sf_item', 'notice', 'paimai', 'detail', 'item']):
                sample_links.append(h)
        print(f"Item/notice links on list page: {len(sample_links)}")
        for sl in sample_links[:10]:
            print("  Link:", sl)
            
        await browser.close()

if __name__ == '__main__':
    asyncio.run(test())
