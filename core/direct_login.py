import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
from core.browser import BrowserManager, human_delay
from core.linkedin_actions import verify_linkedin_login

async def perform_direct_login(password: str, identifier: str = "prakharmishra00000@gmail.com"):
    # Using msedge with long timeouts to handle poor connections
    manager = BrowserManager(headless=False)
    context = await manager.start()
    page = await manager.get_page()

    print(f"[Direct Login] Navigating to LinkedIn with extended timeout for slow network...")
    try:
        await page.goto("https://www.linkedin.com/login", timeout=60000)
    except Exception as e:
        print(f"[Direct Login] Network slow, retrying navigation: {e}")
        await page.goto("https://www.linkedin.com/login", timeout=90000)

    await human_delay(3, 5)

    # Fill username
    username_input = page.locator('input#username, input[name="session_key"]').first
    if await username_input.is_visible():
        print(f"[Direct Login] Entering username: {identifier}")
        await username_input.fill(identifier)
        await human_delay(1, 2)

    # Fill password
    pwd_input = page.locator('input#password, input[name="session_password"]').first
    if await pwd_input.is_visible():
        print(f"[Direct Login] Entering password...")
        await pwd_input.fill(password)
        await human_delay(1, 2)

    # Click Sign in
    submit_btn = page.locator('button[type="submit"]:has-text("Sign in"), button.btn__primary--large').first
    if await submit_btn.is_visible():
        print(f"[Direct Login] Submitting login form...")
        await submit_btn.click()
        await human_delay(6, 10)

    await page.screenshot(path="logs/linkedin_direct_login.png")

    # Verify session
    is_ok = await verify_linkedin_login(page, expected_profile_id="prakhar-mishra-8aa426423")
    print(f"[Direct Login] Verification Status: {'AUTHENTICATED' if is_ok else 'CHECK_SCREENSHOT'}")
    
    await manager.close()
    return is_ok

if __name__ == "__main__":
    if len(sys.argv) > 1:
        pwd = sys.argv[1]
        asyncio.run(perform_direct_login(pwd))
    else:
        print("Usage: python core/direct_login.py <password>")
