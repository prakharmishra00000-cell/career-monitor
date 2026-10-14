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
        url = 'https://www.linkedin.com/jobs/search/?keywords=Mechanical%20Fresher%202026%202027&location=India'
        await page.goto(url, timeout=30000)
        print('URL:', page.url)
        print('Title:', await page.title())
        links = await page.evaluate('Array.from(document.links).map(a => a.href).filter(h => h.includes("/jobs/view/")).slice(0, 10)')
        print('Jobs links count:', len(links))
        for j in links:
            print(j)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
