import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
from core.browser import BrowserManager, human_delay
from core.linkedin_actions import verify_linkedin_login

async def submit_pin_and_login(pin_code: str, identifier: str = "prakharmishra00000@gmail.com", new_password: str = "Prakhar@Career2026!"):
    manager = BrowserManager(headless=False)
    context = await manager.start()
    page = await manager.get_page()

    print("[LinkedIn Auth] Navigating to reset checkpoint...")
    await page.goto("https://www.linkedin.com/checkpoint/rp/request-password-reset", timeout=40000)
    await human_delay(3, 5)

    # 1. If username box is visible, enter email
    input_box = page.locator('input#username, input[name="userName"], input[type="text"]').first
    pin_input = page.locator('input#input__email_verification_pin, input[name="pin"]').first

    if not await pin_input.is_visible() and await input_box.is_visible():
        print(f"[LinkedIn Auth] Entering identifier: {identifier}")
        await input_box.fill(identifier)
        await human_delay(1, 2)
        submit_btn = page.locator('button#reset-password-submit-button, button[type="submit"]').first
        if await submit_btn.is_visible():
            await submit_btn.click()
            await human_delay(4, 6)

    # 2. Enter PIN
    print(f"[LinkedIn Auth] Looking for PIN entry input...")
    pin_input = page.locator('input#input__email_verification_pin, input[name="pin"], input[type="text"], input[type="tel"]').first
    if await pin_input.is_visible():
        print(f"[LinkedIn Auth] Entering 6-digit PIN: {pin_code}")
        await pin_input.click()
        await pin_input.fill(pin_code.strip())
        await human_delay(1, 2)

        submit_btn = page.locator('button[type="submit"]:has-text("Submit"), button#email-pin-submit-button, button.btn__primary--large').first
        if await submit_btn.is_visible():
            await submit_btn.click()
            await human_delay(5, 8)
            print("[LinkedIn Auth] PIN submitted. Checking response...")

    await page.screenshot(path="logs/linkedin_after_pin.png")

    # 3. Check for new password fields
    pwd_field = page.locator('input#newPassword, input[name="newPassword"], input[type="password"]').first
    if await pwd_field.is_visible():
        print(f"[LinkedIn Auth] Setting password to establish session: {new_password}")
        await pwd_field.fill(new_password)
        await human_delay(1, 2)
        
        confirm_field = page.locator('input#confirmPassword, input[name="confirmPassword"]').first
        if await confirm_field.is_visible():
            await confirm_field.fill(new_password)
            await human_delay(1, 2)
            
        save_btn = page.locator('button[type="submit"]:has-text("Submit"), button#reset-password-submit-button, button:has-text("Save")').first
        if await save_btn.is_visible():
            await save_btn.click()
            await human_delay(5, 8)

    await page.screenshot(path="logs/linkedin_final_auth.png")

    # 4. Verify authenticated session
    is_ok = await verify_linkedin_login(page, expected_profile_id="prakhar-mishra-8aa426423")
    print(f"[LinkedIn Auth] Verification Result: {'AUTHENTICATED' if is_ok else 'PENDING'}")
    
    await manager.close()
    return is_ok

if __name__ == "__main__":
    pin = sys.argv[1] if len(sys.argv) > 1 else "138761"
    asyncio.run(submit_pin_and_login(pin))
