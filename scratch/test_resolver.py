import asyncio
from playwright.async_api import async_playwright

async def resolve_direct_post_link(context, author_url: str) -> str:
    activity_url = f"{author_url.rstrip('/')}/recent-activity/all/"
    try:
        page = await context.new_page()
        await page.goto(activity_url, timeout=30000)
        await asyncio.sleep(2)
        links = await page.evaluate("""
        () => {
            const anchors = Array.from(document.querySelectorAll('a')).map(a => a.href);
            return anchors.filter(h => h.includes('/feed/update/') || h.includes('/posts/'));
        }
        """)
        await page.close()
        if links:
            return links[0].split('?')[0]
    except Exception as e:
        print(f"Error: {e}")
    return ""

async def test():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir="browser_data/edge_profile",
            channel="msedge",
            headless=True,
            viewport={"width": 1366, "height": 768}
        )
        url = "https://www.linkedin.com/in/souradip-sarkar-ba3339156/"
        direct_link = await resolve_direct_post_link(context, url)
        print("Resolved direct post link:", direct_link)
        await context.close()

if __name__ == "__main__":
    asyncio.run(test())
