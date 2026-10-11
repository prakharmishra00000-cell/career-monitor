import os
import sys
import asyncio
from typing import Optional
from playwright.async_api import Page
from core.browser import BrowserManager, human_delay
from core.linkedin_actions import verify_linkedin_login
from core.whatsapp_sender import verify_whatsapp_login

async def automated_linkedin_login(page: Page, email_or_phone: str, password: str, expected_id: str = "prakhar-mishra-8aa426423") -> bool:
    """Automates LinkedIn sign-in and handles checkpoints."""
    print(f"[LinkedIn Auth] Navigating to login page...")
    await page.goto("https://www.linkedin.com/login", timeout=40000)
    await human_delay(2, 4)

    # Fill username
    username_input = page.locator('input#username, input[name="session_key"]').first
    if await username_input.is_visible():
        await username_input.fill(email_or_phone)
        await human_delay(1, 2)

    # Fill password
    pwd_input = page.locator('input#password, input[name="session_password"]').first
    if await pwd_input.is_visible():
        await pwd_input.fill(password)
        await human_delay(1, 2)

    # Click submit
    submit_btn = page.locator('button[type="submit"]:has-text("Sign in"), button.btn__primary--large').first
    if await submit_btn.is_visible():
        await submit_btn.click()
        await human_delay(4, 7)

    # Check if 2FA or PIN checkpoint appears
    pin_input = page.locator('input#input__email_verification_pin, input[name="pin"]').first
    if await pin_input.is_visible():
        print("[LinkedIn 2FA] Verification code required.")
        return "2FA_REQUIRED"

    return await verify_linkedin_login(page, expected_profile_id=expected_id)

async def submit_linkedin_2fa(page: Page, otp_code: str, expected_id: str = "prakhar-mishra-8aa426423") -> bool:
    """Submits 2FA code if prompted by LinkedIn."""
    pin_input = page.locator('input#input__email_verification_pin, input[name="pin"]').first
    if await pin_input.is_visible():
        await pin_input.fill(otp_code.strip())
        await human_delay(1, 2)
        submit_btn = page.locator('button[type="submit"]:has-text("Submit"), button#email-pin-submit-button').first
        if await submit_btn.is_visible():
            await submit_btn.click()
            await human_delay(4, 7)
    return await verify_linkedin_login(page, expected_profile_id=expected_id)

async def request_whatsapp_pairing_code(page: Page, phone_number: str = "6372843175", country_code: str = "+91") -> Optional[str]:
    """
    Navigates to WhatsApp Web, selects 'Link with phone number',
    enters phone number, and retrieves the 8-character pairing code to show the user.
    """
    print("[WhatsApp Web] Opening WhatsApp Web...")
    await page.goto("https://web.whatsapp.com", timeout=45000)
    await human_delay(4, 6)

    # Look for "Link with phone number" link
    link_with_phone = page.locator('span:has-text("Link with phone number"), div[role="button"]:has-text("Link with phone number")').first
    if await link_with_phone.is_visible():
        await link_with_phone.click()
        await human_delay(2, 3)

        # Phone number input
        phone_input = page.locator('input[aria-label*="phone number"], input[type="text"]').last
        if await phone_input.is_visible():
            clean_digits = "".join(filter(str.isdigit, phone_number))
            if clean_digits.startswith("91") and len(clean_digits) == 12:
                clean_digits = clean_digits[2:]
            await phone_input.fill(clean_digits)
            await human_delay(1, 2)

            # Click next
            next_btn = page.locator('button:has-text("Next"), div[role="button"]:has-text("Next")').first
            if await next_btn.is_visible():
                await next_btn.click()
                await human_delay(3, 5)

                # Locate pairing code containers
                code_digits = page.locator('div[data-testid*="pairing-code"] span, span[aria-label*="code"]')
                if await code_digits.count() > 0:
                    code_parts = []
                    for i in range(await code_digits.count()):
                        code_parts.append(await code_digits.nth(i).inner_text())
                    return "".join(code_parts)

    return None
