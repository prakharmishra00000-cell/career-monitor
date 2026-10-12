import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
from core.browser import BrowserManager

async def check():
    b = BrowserManager(headless=False)
    await b.start()
    p = await b.get_page()
    await p.goto("https://web.whatsapp.com")
    await asyncio.sleep(6)
    link = p.locator("[data-testid='link_device_qr_phone_number_shortcut_link']").first
    await link.dispatch_event("click")
    await asyncio.sleep(3)
    
    # Check all elements with text
    buttons = await p.locator("button, div[role='button'], span").all()
    for btn in buttons:
        txt = (await btn.inner_text()).strip()
        if "United States" in txt or "+1" in txt or "Country" in txt:
            print("Found country element:", repr(txt))
            await btn.click()
            break
            
    await asyncio.sleep(2)
    inputs = await p.locator("input").all()
    for i in inputs:
        print("input:", await i.get_attribute("placeholder"), await i.get_attribute("type"))

    await b.close()

if __name__ == "__main__":
    asyncio.run(check())
