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
        url = 'https://www.linkedin.com/search/results/content/?keywords=UI%20UX%20Designer%20hiring%20paid&sortBy=%22date_posted%22'
        await page.goto(url, timeout=40000)
        await asyncio.sleep(5)

        # Check for activity urns on the entire page (scripts, state, etc.)
        res = await page.evaluate("""
        () => {
            const scripts = Array.from(document.querySelectorAll('script')).map(s => s.innerText);
            let matches = [];
            for (const s of scripts) {
                const m = s.match(/urn:li:activity:[0-9]+/g);
                if (m) matches.push(...m);
            }
            return {
                scriptMatches: Array.from(new Set(matches)),
                windowKeys: Object.keys(window).filter(k => k.includes('STATE') || k.includes('APOLLO') || k.includes('ember') || k.includes('linkedin'))
            };
        }
        """)

        print("Activity matches in scripts:", res['scriptMatches'])
        print("Window keys:", res['windowKeys'])
        await context.close()

if __name__ == "__main__":
    asyncio.run(run())
