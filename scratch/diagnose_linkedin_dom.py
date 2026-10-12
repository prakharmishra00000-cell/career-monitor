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
        for _ in range(2):
            await page.mouse.wheel(0, 800)
            await asyncio.sleep(2)

        data = await page.evaluate("""
        () => {
            const spans = Array.from(document.querySelectorAll('span')).filter(s => s.innerText.trim() === 'Feed post');
            const items = [];
            for (let i = 0; i < spans.length; i++) {
                const s = spans[i];
                let card = s;
                while (card && card.parentElement && card.parentElement.tagName !== 'MAIN' && card.parentElement.id !== 'root') {
                    const feedSpansInParent = Array.from(card.parentElement.querySelectorAll('span')).filter(sp => sp.innerText.trim() === 'Feed post');
                    if (feedSpansInParent.length > 1) break;
                    card = card.parentElement;
                }
                const container = card.closest('li') || card.closest('.artdeco-card') || card;
                
                // Collect all links inside container
                const links = Array.from(container.querySelectorAll('a')).map(a => a.href);
                // Also collect all links on the entire page
                // And collect HTML snippet
                items.push({
                    cardTag: card ? card.tagName : 'null',
                    cardClass: card ? card.className : '',
                    containerTag: container ? container.tagName : 'null',
                    containerClass: container ? container.className : '',
                    links: links,
                    htmlSnippet: container ? container.outerHTML.slice(0, 1500) : ''
                });
            }
            return {
                spansCount: spans.length,
                items: items
            };
        }
        """)

        print(f"Spans count: {data['spansCount']}")
        for idx, item in enumerate(data['items'][:3]):
            print(f"\n=== ITEM #{idx+1} ===")
            print(f"Card: {item['cardTag']} ({item['cardClass'][:30]})")
            print(f"Container: {item['containerTag']} ({item['containerClass'][:30]})")
            print("Links in container:")
            for l in item['links']:
                print(f"  -> {l}")
            print("HTML Snippet (first 500 chars):")
            safe_html = item['htmlSnippet'][:500].encode('ascii', 'ignore').decode('ascii')
            print(safe_html)

        await context.close()

if __name__ == "__main__":
    asyncio.run(run())
