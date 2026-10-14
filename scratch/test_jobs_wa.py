import asyncio
from playwright.async_api import async_playwright

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir='browser_data/edge_profile',
            headless=True,
            channel='msedge'
        )
        page = await browser.new_page()
        url = 'https://www.linkedin.com/jobs/search/?keywords=Fresher%20WhatsApp&location=India'
        await page.goto(url, timeout=30000)
        links = await page.evaluate('Array.from(document.querySelectorAll("a[href*=\\"/jobs/view/\\"]")).map(a => a.href).slice(0, 15)')
        print('Total jobs matching Fresher WhatsApp on LinkedIn:', len(links))
        for l in links:
            print(l.split('?')[0])
        await browser.close()

if __name__ == '__main__':
    asyncio.run(inspect())
