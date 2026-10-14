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
        url = 'https://www.linkedin.com/in/hr-run-vijay-singh-99900b443/'
        print('Navigating to:', url)
        await page.goto(url, timeout=30000)
        print('URL:', page.url)
        print('Title:', await page.title())
        content = await page.content()
        print('Has Hyundai in page:', 'HYUNDAI' in content or 'Hyundai' in content)
        print('Has 7015859379 in page:', '7015859379' in content)
        links = await page.evaluate('Array.from(document.links).map(a => a.href).filter(h => h.includes("/feed/update/") || h.includes("/posts/"))')
        print('Post links on profile:', links)
        await browser.close()

if __name__ == '__main__':
    asyncio.run(inspect())
