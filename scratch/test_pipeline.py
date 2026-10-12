import asyncio
from core.browser import BrowserManager
from core.linkedin_actions import search_and_ingest_posts

async def test_full_pipeline():
    bm = BrowserManager(headless=False)
    context = await bm.start()
    page = await bm.get_page()
    leads = await search_and_ingest_posts(page, 'UI UX designer hiring', max_posts=5)
    print(f"Pipeline completed! Extracted count: {len(leads)}")
    for l in leads:
        print(f" - Recruiter: {l.get('recruiter_name')} | Domain: {l.get('domain_detected')} | Paid: {l.get('is_paid')} | Status: {l.get('status')}")
    await bm.close()

if __name__ == '__main__':
    asyncio.run(test_full_pipeline())
