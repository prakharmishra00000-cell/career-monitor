import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
from core.browser import BrowserManager, human_delay

async def trigger_linkedin_reset(identifier: str = "prakharmishra00000@gmail.com"):
    manager = BrowserManager(headless=False)
    context = await manager.start()
    page = await manager.get_page()

    print("[LinkedIn Reset] Navigating to password reset page...")
    await page.goto("https://www.linkedin.com/checkpoint/rp/request-password-reset", timeout=40000)
    await human_delay(3, 5)

    # Find email or phone input
    input_box = page.locator('input#username, input[name="userName"], input[type="text"]').first
    if await input_box.is_visible():
        print(f"[LinkedIn Reset] Entering identifier: {identifier}")
        await input_box.fill(identifier)
        await human_delay(1, 2)

        # Click Find Account / Reset password button
        submit_btn = page.locator('button#reset-password-submit-button, button[type="submit"]').first
        if await submit_btn.is_visible():
            await submit_btn.click()
            await human_delay(4, 7)
            print("[LinkedIn Reset] Form submitted. Checking page response...")

            # Take screenshot to verify
            await page.screenshot(path="logs/linkedin_reset_screen.png")

            # Check if PIN input is visible
            pin_input = page.locator('input#input__email_verification_pin, input[name="pin"]').first
            if await pin_input.is_visible():
                print("[LinkedIn Reset] SUCCESS: 6-digit PIN has been sent by LinkedIn!")
                return True
            else:
                print(f"[LinkedIn Reset] Current URL: {page.url}")
                page_text = await page.inner_text("body")
                print(f"[LinkedIn Reset] Page snippet: {page_text[:300]}")
                return True

    print("[LinkedIn Reset] Input box not found. Check logs/linkedin_reset_screen.png")
    await page.screenshot(path="logs/linkedin_reset_screen.png")
    return False

if __name__ == "__main__":
    asyncio.run(trigger_linkedin_reset())
