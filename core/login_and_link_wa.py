import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
from core.browser import BrowserManager, human_delay
from core.linkedin_actions import verify_linkedin_login
from core.live_monitor import record_live_event

async def login_both(email: str = "prakharmishra00000@gmail.com", password: str = "Prakhar@2026P", phone: str = "6372843175"):
    manager = BrowserManager(headless=False)
    context = await manager.start()
    page = await manager.get_page()

    print("[Auth] 1. Logging into LinkedIn with verified selectors...")
    record_live_event("LOGIN_ATTEMPT", "Attempting LinkedIn authentication for Prakhar Mishra")
    await page.goto("https://www.linkedin.com/login", timeout=45000)
    await human_delay(3, 5)

    # 1. Fill Email on visible input
    email_box = page.locator('input[type="email"]:visible, input#username:visible').first
    if await email_box.count() > 0:
        print(f"[Auth] Entering email: {email}")
        await email_box.fill(email)
        await human_delay(1, 2)
    else:
        # Fallback to any visible text input in the form
        fallback_input = page.locator('input[type="text"]:visible').first
        if await fallback_input.is_visible():
            print(f"[Auth] Entering email in fallback input: {email}")
            await fallback_input.fill(email)
            await human_delay(1, 2)

    # 2. Fill Password on visible input
    pwd_box = page.locator('input[type="password"]:visible').first
    if await pwd_box.count() > 0:
        print("[Auth] Entering password and submitting with Enter...")
        await pwd_box.fill(password)
        await human_delay(1, 2)
        await pwd_box.press("Enter")
        await human_delay(6, 10)

    try:
        await page.screenshot(path="logs/linkedin_auth_result.png", timeout=5000)
    except Exception:
        pass

    # Check LinkedIn Login Status
    li_ok = await verify_linkedin_login(page, expected_profile_id="prakhar-mishra-8aa426423")
    print(f"[Auth] LinkedIn Status: {'AUTHENTICATED' if li_ok else 'CHECK_SCREENSHOT'}")
    if li_ok:
        record_live_event("LINKEDIN_AUTHENTICATED", "LinkedIn profile prakhar-mishra-8aa426423 successfully verified!")

    # 4. Open WhatsApp Web to fetch pairing code for India (+91)
    print("\n[Auth] 2. Connecting WhatsApp Web for India (+91 " + phone + ")...")
    record_live_event("WHATSAPP_LINKING", f"Requesting pairing code for +91 {phone}")
    wa_page = await context.new_page()
    await wa_page.goto("https://web.whatsapp.com", timeout=50000)
    await human_delay(5, 7)

    # Click 'Link with phone number' using dispatch_event
    link_phone_btn = wa_page.locator('[data-testid="link_device_qr_phone_number_shortcut_link"], span:has-text("Link with phone number"), div[role="button"]:has-text("Link with phone number")').first
    pairing_code = None

    if await link_phone_btn.count() > 0:
        print("[Auth] Clicking 'Link with phone number' via dispatch_event...")
        await link_phone_btn.dispatch_event("click")
        await human_delay(3, 4)

        # Select Country if country selector button exists
        country_selector = wa_page.locator('button[aria-label*="Country"], div[role="button"]:has-text("+1")').first
        if await country_selector.is_visible():
            await country_selector.click()
            await human_delay(1, 2)
            search_country = wa_page.locator('input[placeholder*="Search"], input[aria-label*="Search"]').first
            if await search_country.is_visible():
                await search_country.fill("India")
                await human_delay(1, 2)
                india_opt = wa_page.locator('div[role="button"]:has-text("India"), span:has-text("India")').first
                if await india_opt.is_visible():
                    await india_opt.click()
                    await human_delay(1, 2)

        phone_input = wa_page.locator('input[aria-label*="phone number"], input[type="text"]').last
        if await phone_input.is_visible():
            print(f"[Auth] Entering phone number: {phone}")
            await phone_input.fill(phone)
            await human_delay(1, 2)

            next_btn = wa_page.locator('button:has-text("Next"), div[role="button"]:has-text("Next")').first
            if await next_btn.is_visible():
                await next_btn.click()
                await human_delay(5, 7)

                code_spans = wa_page.locator('div[data-testid*="pairing-code"] span, span[aria-label*="code"]')
                count = await code_spans.count()
                if count > 0:
                    code_parts = [await code_spans.nth(i).inner_text() for i in range(count)]
                    pairing_code = "".join(code_parts)
                    print(f"\n==========================================")
                    print(f"WHATSAPP PAIRING CODE FOR +91 {phone}: {pairing_code}")
                    print(f"==========================================\n")
                    record_live_event("WHATSAPP_CODE_READY", f"Pairing code for +91 {phone}: {pairing_code}")

    try:
        await wa_page.screenshot(path="logs/whatsapp_pairing.png", timeout=5000)
    except Exception:
        pass
    
    # Keep context open for 30s to allow user pairing if code exists
    if pairing_code:
        print("[Auth] Waiting 45 seconds for phone pairing...")
        await asyncio.sleep(45)

    await manager.close()
    return li_ok, pairing_code

if __name__ == "__main__":
    asyncio.run(login_both())
