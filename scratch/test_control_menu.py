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
        await page.goto('https://www.linkedin.com/search/results/content/?keywords=UI%20UX%20Designer%20hiring%20paid&sortBy=%22date_posted%22', timeout=40000)
        await asyncio.sleep(5)

        # Find the first "Open control menu" button
        btn = page.locator('button[aria-label*="Open control menu"]').first
        if await btn.count() > 0:
            print("Found control menu button, clicking...")
            await btn.click()
            await asyncio.sleep(2)

            # Inspect all menu items or popovers on the page
            menu_info = await page.evaluate("""
            () => {
                const popovers = Array.from(document.querySelectorAll('[role="menu"], [role="listbox"], .artdeco-dropdown__content, [data-view-name*="overflow"]'));
                const items = [];
                for (const p of popovers) {
                    items.push({
                        text: p.innerText,
                        html: p.innerHTML.slice(0, 1000)
                    });
                }
                const allButtonsAndLinks = Array.from(document.querySelectorAll('[role="menuitem"], button, a')).filter(el => {
                    const t = (el.innerText || '').toLowerCase();
                    return t.includes('copy link') || t.includes('link') || t.includes('save') || t.includes('share');
                }).map(el => ({
                    tag: el.tagName,
                    text: el.innerText.trim(),
                    href: el.href || '',
                    dataAttrs: Array.from(el.attributes).map(a => `${a.name}=${a.value}`).slice(0, 5)
                }));
                return {
                    popovers: items,
                    matches: allButtonsAndLinks
                };
            }
            """)

            print(f"Popovers found: {len(menu_info['popovers'])}")
            for p in menu_info['popovers']:
                print("Popover text:\n", p['text'])
            print(f"Matching buttons/links found: {len(menu_info['matches'])}")
            for m in menu_info['matches']:
                print("Match:", m)
        else:
            print("No control menu button found!")

        await context.close()

if __name__ == "__main__":
    asyncio.run(run())
