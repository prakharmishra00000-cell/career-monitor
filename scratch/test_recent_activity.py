import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir="browser_data/edge_profile",
            channel="msedge",
            headless=True,
            viewport={"width": 1366, "height": 768}
        )
        page = await context.new_page()
        # Souradip Sarkar was recruiter #2 in our search results
        url = 'https://www.linkedin.com/in/souradip-sarkar-ba3339156/recent-activity/all/'
        print(f"Navigating to {url}...")
        await page.goto(url, timeout=40000)
        await asyncio.sleep(5)

        links = await page.evaluate("""
        () => {
            const anchors = Array.from(document.querySelectorAll('a')).map(a => a.href);
            return anchors.filter(h => h.includes('/feed/update/') || h.includes('/posts/'));
        }
        """)

        print(f"Direct post links found on recent activity page: {len(links)}")
        for l in list(set(links))[:5]:
            print("  ->", l)

        await context.close()

if __name__ == "__main__":
    asyncio.run(run())
