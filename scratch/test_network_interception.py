import asyncio
import json
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

        captured_urls = []
        captured_data = []

        async def handle_response(response):
            try:
                url = response.url
                if ("graphql" in url or "voyager" in url or "search" in url) and "json" in response.headers.get("content-type", ""):
                    captured_urls.append(url)
                    text = await response.text()
                    if "activity" in text:
                        captured_data.append((url, text))
            except Exception:
                pass

        page.on("response", handle_response)

        print("Navigating to LinkedIn search...")
        url = 'https://www.linkedin.com/search/results/content/?keywords=UI%20UX%20Designer%20hiring%20paid&sortBy=%22date_posted%22'
        await page.goto(url, timeout=40000)
        await asyncio.sleep(6)

        print(f"Captured {len(captured_urls)} JSON API calls.")
        print(f"Captured {len(captured_data)} API calls containing 'activity'.")

        for u, text in captured_data[:3]:
            print("\nURL:", u[:100])
            import re
            m = re.findall(r'urn:li:activity:[0-9]+', text)
            print("Found activity URNs in response:", list(set(m))[:5])
            links = re.findall(r'https://www.linkedin.com/feed/update/[^\s"\'\\,]+', text)
            print("Found feed links in response:", list(set(links))[:5])

        await context.close()

if __name__ == "__main__":
    asyncio.run(run())
