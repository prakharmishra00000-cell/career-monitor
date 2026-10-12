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

        calls = []

        async def handle_response(response):
            try:
                url = response.url
                if "voyager" in url or "graphql" in url:
                    text = await response.text()
                    calls.append((url, len(text), text[:300]))
            except Exception:
                pass

        page.on("response", handle_response)
        await page.goto('https://www.linkedin.com/search/results/content/?keywords=UI%20UX%20Designer%20hiring%20paid&sortBy=%22date_posted%22', timeout=40000)
        await asyncio.sleep(6)

        print(f"Total Voyager calls: {len(calls)}")
        for u, l, snippet in calls:
            print(f"[{l} bytes] {u}")

        await context.close()

if __name__ == "__main__":
    asyncio.run(run())
