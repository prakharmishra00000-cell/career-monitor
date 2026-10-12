import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
from core.browser import BrowserManager, human_delay
from core.whatsapp_sender import verify_whatsapp_login
from core.live_monitor import record_live_event

async def generate_india_pairing_code(phone: str = "6372843175"):
    manager = BrowserManager(headless=False)
    context = await manager.start()
    page = await manager.get_page()

    print("[WhatsApp] Navigating to web.whatsapp.com...")
    await page.goto("https://web.whatsapp.com", timeout=60000)
    await human_delay(6, 9)

    # 1. Check if already logged in
    if await verify_whatsapp_login(page):
        print("[WhatsApp] SUCCESS: WhatsApp Web is ALREADY logged in!")
        await manager.close()
        return True, "ALREADY_LOGGED_IN"

    # 2. Click 'Link with phone number'
    print("[WhatsApp] Clicking 'Link with phone number'...")
    link_btn = page.locator('[data-testid="link_device_qr_phone_number_shortcut_link"], span:has-text("Link with phone number"), div[role="button"]:has-text("Link with phone number")').first
    await link_btn.wait_for(state="visible", timeout=30000)
    await link_btn.dispatch_event("click")
    await human_delay(3, 5)

    # 3. Target Country Dropdown (currently showing Philippines or United States)
    print("[WhatsApp] Setting country to India (+91)...")
    country_box = page.locator('div:has-text("Philippines"), button:has-text("Philippines"), div:has-text("United States"), button:has-text("United States"), div[role="combobox"]').first
    if await country_box.is_visible():
        await country_box.click()
        await human_delay(2, 3)

        search_country = page.locator('input[placeholder*="Search"], input[aria-label*="Search"]').first
        if await search_country.is_visible():
            await search_country.fill("India")
            await human_delay(1.5, 2.5)

            india_item = page.locator('div[role="listitem"]:has-text("India"), div[role="button"]:has-text("India"), li:has-text("India"), span:has-text("India")').first
            if await india_item.is_visible():
                await india_item.click()
                await human_delay(2, 3)

    # 4. Fill 10-digit Phone Number
    print(f"[WhatsApp] Entering phone number: {phone}...")
    phone_input = page.locator('input[aria-label*="phone number"], input[type="tel"], input[type="text"]:visible').last
    if await phone_input.is_visible():
        await phone_input.click()
        await phone_input.fill("")
        await human_delay(0.5, 1)
        await phone_input.fill(phone)
        await human_delay(1, 2)

        # 5. Click Next
        next_btn = page.locator('button:has-text("Next"), div[role="button"]:has-text("Next")').first
        if await next_btn.is_visible():
            await next_btn.click()
            await human_delay(5, 8)

            # 6. Extract Code
            code_boxes = page.locator('div[data-testid*="pairing-code"] span, span[aria-label*="code"]')
            count = await code_boxes.count()
            if count > 0:
                parts = [await code_boxes.nth(i).inner_text() for i in range(count)]
                code = "".join(parts)
                print(f"\n==========================================")
                print(f"WHATSAPP PAIRING CODE FOR +91 {phone}: {code}")
                print(f"==========================================\n")
                record_live_event("WHATSAPP_CODE_READY", f"Pairing code for +91 {phone}: {code}")
                
                try:
                    await page.screenshot(path="logs/whatsapp_india_pairing.png", timeout=5000)
                except Exception:
                    pass

                print("[WhatsApp] Browser is open and waiting 180s for pairing...")
                for remaining in range(180, 0, -5):
                    if await verify_whatsapp_login(page):
                        print("\n[WhatsApp] SUCCESS: Phone paired! WhatsApp session saved!\n")
                        record_live_event("WHATSAPP_AUTHENTICATED", "WhatsApp Web successfully paired!")
                        await manager.close()
                        return True, code
                    await asyncio.sleep(5)

                await manager.close()
                return False, code

    try:
        await page.screenshot(path="logs/whatsapp_india_pairing.png", timeout=5000)
    except Exception:
        pass
    await manager.close()
    return False, None

if __name__ == "__main__":
    asyncio.run(generate_india_pairing_code())
