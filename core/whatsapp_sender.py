import urllib.parse
import asyncio
from typing import Dict, Any, Optional
from playwright.async_api import Page
from core.browser import human_delay
from core.database import (
    update_whatsapp_status, get_pending_whatsapp_leads,
    get_daily_action_count, log_activity
)
from core.live_monitor import record_live_event

async def verify_whatsapp_login(page: Page) -> bool:
    """Checks if WhatsApp Web is logged in."""
    try:
        await page.goto("https://web.whatsapp.com/", timeout=40000)
        await human_delay(4, 7)
        # Search panel or chats container indicates active session
        chat_list = page.locator('div[data-testid="chat-list"], div#pane-side, div[aria-label="Chat list"]').first
        if await chat_list.is_visible():
            return True
        return False
    except Exception as e:
        print(f"[WhatsApp] Error verifying session: {e}")
        return False

async def dispatch_whatsapp_message(page: Page, lead: Dict[str, Any], max_daily_wa: int = 20) -> bool:
    """Dispatches a professional job inquiry on WhatsApp."""
    phone = lead.get("whatsapp_number")
    pitch = lead.get("whatsapp_pitch")
    lead_id = lead["id"]
    recruiter_name = lead.get("recruiter_name", "Recruiter")

    if not phone or not pitch:
        update_whatsapp_status(lead_id, "FAILED", details="Missing phone number or message")
        return False

    if get_daily_action_count("WHATSAPP") >= max_daily_wa:
        print("[Quota] Daily WhatsApp outreach limit reached.")
        return False

    clean_digits = "".join(filter(str.isdigit, phone))
    # If standard 10 digit Indian number without country code, add 91
    if len(clean_digits) == 10:
        clean_digits = "91" + clean_digits

    encoded_text = urllib.parse.quote(pitch)
    url = f"https://web.whatsapp.com/send?phone={clean_digits}&text={encoded_text}"

    print(f"[WhatsApp] Sending outreach to {recruiter_name} at +{clean_digits}...")
    try:
        await page.goto(url, timeout=45000)
        await human_delay(6, 9)

        # Check for invalid number alert
        invalid_popup = page.locator('div:has-text("Phone number shared via url is invalid")').first
        if await invalid_popup.is_visible():
            print(f"[WhatsApp] Invalid phone number alert for {clean_digits}")
            update_whatsapp_status(lead_id, "FAILED", details=f"Invalid phone number {clean_digits}")
            return False

        # Wait for send button
        send_btn = page.locator('button[aria-label="Send"], span[data-icon="send"], button[data-tab="11"]').first
        await send_btn.wait_for(state="visible", timeout=25000)
        await human_delay(1, 2.5)
        await send_btn.click()
        await human_delay(3, 5)

        update_whatsapp_status(lead_id, "SENT", details=f"WhatsApp inquiry sent to +{clean_digits}")
        log_activity(lead_id, action_type="WHATSAPP", status="SUCCESS", details=f"Message delivered to {recruiter_name}")
        record_live_event("WHATSAPP_SENT", f"Delivered WhatsApp inquiry to {recruiter_name} (+{clean_digits})")
        print(f"[WhatsApp] Message successfully delivered to {recruiter_name}!")
        return True

    except Exception as e:
        print(f"[WhatsApp] Failed to dispatch message to +{clean_digits}: {e}")
        update_whatsapp_status(lead_id, "FAILED", details=str(e))
        return False

async def process_all_pending_whatsapp_leads(page: Page) -> int:
    pending = get_pending_whatsapp_leads()
    if not pending:
        return 0

    print(f"[WhatsApp] Processing {len(pending)} pending WhatsApp leads...")
    sent_count = 0
    for lead_row in pending:
        lead = dict(lead_row)
        success = await dispatch_whatsapp_message(page, lead)
        if success:
            sent_count += 1
            await human_delay(30, 60) # Anti-ban safety interval
    return sent_count
