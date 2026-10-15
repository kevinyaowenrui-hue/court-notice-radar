# -*- coding: utf-8 -*-
import sys
import asyncio
from playwright.async_api import async_playwright

async def test_pw_fetch():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        print("Navigating to noticeinfo...")
        await page.goto("https://rmfygg.court.gov.cn/web/rmfyportal/noticeinfo", timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        uuid = "6091616044004473"
        print(f"Executing fetch inside page for uuid {uuid}...")
        res = await page.evaluate("""async (uuid) => {
            const url = '/web/rmfyportal/noticedetail?p_p_id=noticedetail_WAR_rmfynoticeDetailportlet&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_resource_id=noticeDetail&p_p_cacheability=cacheLevelPage&p_p_col_id=column-1&p_p_col_count=1';
            const formData = new URLSearchParams();
            formData.append('_noticedetail_WAR_rmfynoticeDetailportlet_uuid', uuid);
            const resp = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData
            });
            return await resp.json();
        }""", uuid)
        print("Fetch result status/keys:", list(res.keys()) if isinstance(res, dict) else res)
        if isinstance(res, dict) and "noticeContent" in res:
            print("SUCCESS! Content:", res["noticeContent"][:150])
            print("PublishDate:", res.get("publishDate"))
        await browser.close()

asyncio.run(test_pw_fetch())
