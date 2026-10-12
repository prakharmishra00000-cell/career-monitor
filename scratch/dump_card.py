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

        html = await page.evaluate("""
        () => {
            const spans = Array.from(document.querySelectorAll('span')).filter(s => s.innerText.trim() === 'Feed post');
            if (!spans.length) return '';
            let card = spans[0];
            while (card && card.parentElement && card.parentElement.tagName !== 'MAIN' && card.parentElement.id !== 'root') {
                const feedSpansInParent = Array.from(card.parentElement.querySelectorAll('span')).filter(sp => sp.innerText.trim() === 'Feed post');
                if (feedSpansInParent.length > 1) break;
                card = card.parentElement;
            }
            return card.innerHTML;
        }
        """)

        with open("scratch/sample_post_card.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Wrote sample_post_card.html, size:", len(html))
        await context.close()

if __name__ == "__main__":
    asyncio.run(run())
