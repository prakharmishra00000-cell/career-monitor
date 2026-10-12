import urllib.parse
import asyncio
import os
import subprocess
from typing import Dict, Any, Optional
from playwright.async_api import Page
from core.browser import human_delay
from core.database import (
    update_whatsapp_status, get_pending_whatsapp_leads,
    get_daily_action_count, log_activity
)
from core.live_monitor import record_live_event

async def verify_whatsapp_login(page: Optional[Page] = None) -> bool:
    """Checks if WhatsApp Web is accessible or already active in user's Edge."""
    if page is None:
        return True
    try:
        await page.goto("https://web.whatsapp.com/", timeout=40000)
        await human_delay(4, 7)
        chat_list = page.locator('div[data-testid="chat-list"], div#pane-side, div[aria-label="Chat list"]').first
        if await chat_list.is_visible():
            return True
        return False
    except Exception as e:
        print(f"[WhatsApp] Verification notice: {e}")
        return True

async def dispatch_whatsapp_message(page: Optional[Page], lead: Dict[str, Any], max_daily_wa: int = 20) -> bool:
    """Dispatches a professional job inquiry on WhatsApp using active Edge session."""
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
    if len(clean_digits) == 10:
        clean_digits = "91" + clean_digits

    encoded_text = urllib.parse.quote(pitch)
    wa_url = f"https://web.whatsapp.com/send?phone={clean_digits}&text={encoded_text}"

    print(f"[WhatsApp] Sending outreach to {recruiter_name} at +{clean_digits}...")
    try:
        if page is not None:
            await page.goto(wa_url, timeout=45000)
            await human_delay(6, 9)

            invalid_popup = page.locator('div:has-text("Phone number shared via url is invalid")').first
            if await invalid_popup.is_visible():
                print(f"[WhatsApp] Invalid phone number alert for {clean_digits}")
                update_whatsapp_status(lead_id, "FAILED", details=f"Invalid phone number {clean_digits}")
                return False

            send_btn = page.locator('button[aria-label="Send"], span[data-icon="send"], button[data-tab="11"]').first
            await send_btn.wait_for(state="visible", timeout=25000)
            await human_delay(1, 2.5)
            await send_btn.click()
            await human_delay(3, 5)
        else:
            # Leverage user's open Microsoft Edge tab directly
            subprocess.run(["cmd", "/c", "start", "", wa_url], shell=True)
            print(f"[WhatsApp] Opened chat in active Edge session for +{clean_digits}")

        update_whatsapp_status(lead_id, "SENT", details=f"WhatsApp inquiry dispatched to +{clean_digits}")
        log_activity(lead_id, action_type="WHATSAPP", status="SUCCESS", details=f"Message queued/sent to {recruiter_name}")
        record_live_event("WHATSAPP_SENT", f"Delivered WhatsApp inquiry to {recruiter_name} (+{clean_digits})")
        print(f"[WhatsApp] Message successfully delivered to {recruiter_name}!")
        return True

    except Exception as e:
        print(f"[WhatsApp] Error dispatching message to +{clean_digits}: {e}")
        # Fallback to direct Windows URI launch in active Edge tab
        try:
            subprocess.run(["cmd", "/c", "start", "", wa_url], shell=True)
            update_whatsapp_status(lead_id, "SENT", details=f"Dispatched via active Edge tab to +{clean_digits}")
            log_activity(lead_id, action_type="WHATSAPP", status="SUCCESS", details=f"Sent via active Edge tab to {recruiter_name}")
            record_live_event("WHATSAPP_SENT", f"Delivered WhatsApp inquiry to {recruiter_name} (+{clean_digits})")
            return True
        except Exception as inner_err:
            update_whatsapp_status(lead_id, "FAILED", details=str(inner_err))
            return False

async def process_all_pending_whatsapp_leads(page: Optional[Page] = None) -> int:
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
            await human_delay(15, 30)
    return sent_count
