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

        # Look for the post body or timestamp
        # In sample_post_card.html, Anchor #4 or the post text
        print("Page URL before click:", page.url)

        # Let's inspect what elements have click handlers or anchors inside card
        res = await page.evaluate("""
        () => {
            const spans = Array.from(document.querySelectorAll('span')).filter(s => s.innerText.trim() === 'Feed post');
            if (!spans.length) return null;
            const card = spans[0].closest('div[data-display-contents="true"]') || spans[0].parentElement;
            
            // Look for timestamp span, e.g., '15m', '2h', '1d', etc.
            const allSpans = Array.from(card.querySelectorAll('span'));
            const timeSpans = allSpans.filter(s => /^[0-9]+[mhdwy](\s*Edited)?$/i.test(s.innerText.trim()));
            return {
                timeSpans: timeSpans.map(s => ({ text: s.innerText, parentTag: s.parentElement.tagName, parentClass: s.parentElement.className }))
            };
        }
        """)
        print("Time spans found:", res)

        # Let's see if clicking the timestamp or the card navigates or opens modal
        time_el = page.locator('span:has-text("Feed post")').first
        # Find time text near recruiter
        time_click = page.locator('div[data-display-contents="true"] span').filter(has_text=asyncio.run if False else None)

        await context.close()

if __name__ == "__main__":
    asyncio.run(run())
