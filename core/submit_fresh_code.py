import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
from core.browser import BrowserManager, human_delay
from core.linkedin_actions import verify_linkedin_login

async def submit_fresh_code(pin_code: str = "774726", identifier: str = "prakharmishra00000@gmail.com", new_password: str = "Prakhar@Career2026!"):
    manager = BrowserManager(headless=False)
    context = await manager.start()
    page = await manager.get_page()

    print("[LinkedIn Auth] Navigating to password reset page...")
    await page.goto("https://www.linkedin.com/checkpoint/rp/request-password-reset", timeout=40000)
    await human_delay(3, 5)

    # Check if we are on the initial username input page
    username_input = page.locator('input#username').first
    if await username_input.is_visible():
        print(f"[LinkedIn Auth] Entering email: {identifier}")
        await username_input.fill(identifier)
        await human_delay(1, 2)
        submit_btn = page.locator('button#reset-password-submit-button').first
        if await submit_btn.is_visible():
            await submit_btn.click()
            await human_delay(4, 6)

    # Now we are on the 6-digit code page
    print(f"[LinkedIn Auth] Locating 6-digit PIN input...")
    # Target specific PIN input box
    pin_input = page.locator('input#input__email_verification_pin, input[name="pin"], input.form__input--text').first
    if not await pin_input.is_visible():
        # Fallback locator for the code field
        pin_input = page.locator('main input, div[role="main"] input').first

    if await pin_input.is_visible():
        print(f"[LinkedIn Auth] Typing code: {pin_code}")
        await pin_input.click()
        await human_delay(0.5, 1)
        await pin_input.fill(pin_code.strip())
        await human_delay(1, 2)

        submit_btn = page.locator('button#email-pin-submit-button, button[type="submit"]:has-text("Submit")').first
        if not await submit_btn.is_visible():
            submit_btn = page.locator('button:has-text("Submit")').first

        if await submit_btn.is_visible():
            await submit_btn.click()
            await human_delay(5, 8)
            print("[LinkedIn Auth] Code submitted. Processing response...")

    await page.screenshot(path="logs/linkedin_after_code_submit.png")

    # Check for new password fields
    pwd_field = page.locator('input#newPassword, input[name="newPassword"]').first
    if await pwd_field.is_visible():
        print(f"[LinkedIn Auth] New password prompt detected. Setting password to establish session...")
        await pwd_field.fill(new_password)
        await human_delay(1, 2)
        confirm_field = page.locator('input#confirmPassword, input[name="confirmPassword"]').first
        if await confirm_field.is_visible():
            await confirm_field.fill(new_password)
            await human_delay(1, 2)
        save_btn = page.locator('button#reset-password-submit-button, button[type="submit"]:has-text("Submit")').first
        if await save_btn.is_visible():
            await save_btn.click()
            await human_delay(5, 8)

    await page.screenshot(path="logs/linkedin_final_screen.png")

    # Verify session
    is_ok = await verify_linkedin_login(page, expected_profile_id="prakhar-mishra-8aa426423")
    print(f"[LinkedIn Auth] Verification Result: {'AUTHENTICATED' if is_ok else 'PENDING'}")
    
    await manager.close()
    return is_ok

if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else "774726"
    asyncio.run(submit_fresh_code(code))
