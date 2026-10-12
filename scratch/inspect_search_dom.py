import asyncio
import json
from core.browser import BrowserManager

async def test_span_parent_cards():
    bm = BrowserManager(headless=False)
    context = await bm.start()
    page = await bm.get_page()
    await page.goto(
        'https://www.linkedin.com/search/results/content/?keywords=UI%20UX%20designer%20hiring&sortBy=%22date_posted%22',
        wait_until='domcontentloaded',
        timeout=60000
    )
    await asyncio.sleep(6)
    
    js_code = """
    () => {
        // Find spans that strictly equal "Feed post"
        const spans = Array.from(document.querySelectorAll('span')).filter(s => s.innerText.trim() === 'Feed post');
        
        const extracted = [];
        for (const s of spans) {
            // Traverse up to find the card container for this specific post
            let card = s;
            while (card && card.parentElement && card.parentElement.tagName !== 'MAIN' && card.parentElement.id !== 'root') {
                // Stop when parent contains multiple "Feed post" spans
                const countInParent = card.parentElement.querySelectorAll('span.gflarb, span').length;
                const feedSpansInParent = Array.from(card.parentElement.querySelectorAll('span')).filter(sp => sp.innerText.trim() === 'Feed post');
                if (feedSpansInParent.length > 1) {
                    break;
                }
                card = card.parentElement;
            }
            
            // Extract recruiter link inside this card
            const authorLink = card.querySelector('a[href*="/in/"]');
            const authorName = authorLink ? authorLink.innerText.trim() : 'Recruiter';
            const profileUrl = authorLink ? authorLink.href.split('?')[0] : '';
            
            // Extract buttons (Comment, Like, Send, etc.)
            const buttons = Array.from(card.querySelectorAll('button')).map(b => b.innerText.trim()).filter(Boolean);
            
            extracted.push({
                authorName,
                profileUrl,
                buttons,
                textSnippet: card.innerText.slice(0, 250).replace(/\\s+/g, ' ')
            });
        }
        return extracted;
    }
    """
    results = await page.evaluate(js_code)
    print("Extracted individual post cards count:", len(results))
    print(json.dumps(results[:3], indent=2))
    await bm.close()

if __name__ == '__main__':
    asyncio.run(test_span_parent_cards())
