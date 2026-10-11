import urllib.parse
import asyncio
import re
from typing import List, Dict, Any, Optional
from playwright.async_api import Page
from core.browser import human_delay
from core.database import (
    is_post_processed, insert_lead, update_lead_status, 
    update_comment_status, get_pending_connection_leads,
    get_daily_action_count, log_activity
)
from core.ai_evaluator import analyze_post

async def verify_linkedin_login(page: Page, expected_profile_id: str = "prakhar-mishra-8aa426423") -> bool:
    """
    Checks if the current session is logged in and verifies it strictly belongs to
    the authorized profile: prakhar-mishra-8aa426423.
    """
    try:
        await page.goto("https://www.linkedin.com/feed/", timeout=35000)
        await human_delay(3, 5)
        
        # Check basic authentication
        if "login" in page.url or "checkpoint" in page.url:
            print("[LinkedIn Auth] Not logged in.")
            return False

        # Navigate to /in/me/ to verify exact identity
        await page.goto("https://www.linkedin.com/in/me/", timeout=35000)
        await human_delay(3, 5)
        current_url = page.url.lower()

        if expected_profile_id.lower() in current_url:
            print(f"[LinkedIn Auth] Identity Verified: Authorized profile active ({expected_profile_id})")
            return True
        elif "/in/" in current_url:
            # Check if name is Prakhar Mishra on page
            body_text = await page.inner_text("body")
            if "prakhar mishra" in body_text.lower():
                print(f"[LinkedIn Auth] Identity Verified: Prakhar Mishra verified on profile page.")
                return True
            else:
                print(f"[SECURITY ALERT] Current logged-in account does NOT match authorized ID ({expected_profile_id}). Current URL: {current_url}")
                print(f"[SECURITY ALERT] Automation halted to protect other accounts.")
                return False

        # If redirection didn't complete but feed is accessible
        await page.goto("https://www.linkedin.com/feed/", timeout=30000)
        return True
    except Exception as e:
        print(f"[LinkedIn Check] Error checking login status: {e}")
        return False

async def search_and_ingest_posts(page: Page, query: str, max_posts: int = 10) -> List[Dict[str, Any]]:
    """Searches LinkedIn for recent posts matching target keywords."""
    encoded_q = urllib.parse.quote(query)
    search_url = f"https://www.linkedin.com/search/results/content/?keywords={encoded_q}&sortBy=%22date_posted%22"
    
    print(f"[Scanner] Searching LinkedIn: {query}")
    try:
        await page.goto(search_url, timeout=40000)
        await human_delay(3, 6)
    except Exception as e:
        print(f"[Scanner] Failed to load search URL: {e}")
        return []

    # Scroll down slightly to trigger lazy-loaded posts
    for _ in range(2):
        await page.mouse.wheel(0, 800)
        await human_delay(1.5, 3.0)

    # Find post cards
    post_locators = page.locator('div[data-urn*="urn:li:activity"], div.feed-shared-update-v2')
    count = await post_locators.count()
    print(f"[Scanner] Found {count} post elements on search page.")

    extracted_leads = []

    for i in range(min(count, max_posts)):
        try:
            post_card = post_locators.nth(i)
            
            # Extract post URN or ID
            urn_attr = await post_card.get_attribute("data-urn")
            post_id = urn_attr or f"post_{hash(await post_card.inner_text())}"
            
            if is_post_processed(post_id):
                continue # Already analyzed

            # Expand "see more" if truncated
            see_more = post_card.locator('button.feed-shared-inline-show-more-text__see-more-less-toggle, button:has-text("more")').first
            if await see_more.is_visible():
                try:
                    await see_more.click(timeout=1500)
                    await human_delay(0.5, 1.0)
                except Exception:
                    pass

            # Extract Post Text
            text_elem = post_card.locator('div.feed-shared-update-v2__description, span.break-words').first
            post_text = await text_elem.inner_text() if await text_elem.is_visible() else await post_card.inner_text()

            # Extract Recruiter Name and Profile URL
            recruiter_name = "Recruiter"
            recruiter_profile_url = ""
            author_link = post_card.locator('a.app-aware-link[href*="/in/"]').first
            if await author_link.is_visible():
                recruiter_profile_url = await author_link.get_attribute("href") or ""
                # Strip tracking parameters
                recruiter_profile_url = recruiter_profile_url.split("?")[0]
                recruiter_name = (await author_link.inner_text()).strip().split("\n")[0]

            # Construct Post URL
            post_url = f"https://www.linkedin.com/feed/update/{post_id}/" if "urn:li:activity" in post_id else page.url

            # Deep AI Evaluation of the Post
            analysis = analyze_post(post_text, recruiter_name=recruiter_name)
            
            # Check paid filter: ONLY PAID ROLES ALLOWED
            if not analysis.get("is_paid", True):
                print(f"[Filter] Discarding UNPAID post: {post_id} - '{recruiter_name}'")
                lead_data = {
                    "post_id": post_id,
                    "post_url": post_url,
                    "recruiter_name": recruiter_name,
                    "recruiter_profile_url": recruiter_profile_url,
                    "post_text": post_text,
                    "job_type": analysis.get("job_type", "job"),
                    "is_paid": 0,
                    "domain_detected": analysis.get("domain_detected", "Other"),
                    "relevance_score": analysis.get("relevance_score", 0.0),
                    "recruiter_instructions": analysis.get("recruiter_instructions", ""),
                    "whatsapp_number": analysis.get("whatsapp_number"),
                    "requires_comment": 0,
                    "comment_text": "",
                    "pitch_message": "",
                    "connection_note": "",
                    "whatsapp_pitch": "",
                    "status": "REJECTED_UNPAID",
                    "comment_status": "NONE",
                    "whatsapp_status": "NONE"
                }
                insert_lead(lead_data)
                continue

            if not analysis.get("is_relevant", False):
                print(f"[Filter] Discarding IRRELEVANT post: {post_id}")
                lead_data = {
                    "post_id": post_id,
                    "post_url": post_url,
                    "recruiter_name": recruiter_name,
                    "recruiter_profile_url": recruiter_profile_url,
                    "post_text": post_text,
                    "job_type": analysis.get("job_type", "job"),
                    "is_paid": 1,
                    "domain_detected": analysis.get("domain_detected", "Other"),
                    "relevance_score": analysis.get("relevance_score", 0.0),
                    "recruiter_instructions": "",
                    "whatsapp_number": None,
                    "requires_comment": 0,
                    "comment_text": "",
                    "pitch_message": "",
                    "connection_note": "",
                    "whatsapp_pitch": "",
                    "status": "REJECTED_IRRELEVANT",
                    "comment_status": "NONE",
                    "whatsapp_status": "NONE"
                }
                insert_lead(lead_data)
                continue

            # Qualified lead!
            comment_status = "PENDING" if analysis.get("requires_comment") else "NONE"
            whatsapp_status = "PENDING" if analysis.get("whatsapp_number") else "NONE"

            lead_record = {
                "post_id": post_id,
                "post_url": post_url,
                "recruiter_name": recruiter_name,
                "recruiter_profile_url": recruiter_profile_url,
                "post_text": post_text,
                "job_type": analysis.get("job_type", "job"),
                "is_paid": 1,
                "domain_detected": analysis.get("domain_detected", "UI/UX"),
                "relevance_score": analysis.get("relevance_score", 1.0),
                "recruiter_instructions": analysis.get("recruiter_instructions", ""),
                "whatsapp_number": analysis.get("whatsapp_number"),
                "requires_comment": 1 if analysis.get("requires_comment") else 0,
                "comment_text": analysis.get("comment_text", ""),
                "pitch_message": analysis.get("pitch_message", ""),
                "connection_note": analysis.get("connection_note", ""),
                "whatsapp_pitch": analysis.get("whatsapp_pitch", ""),
                "status": "DISCOVERED",
                "comment_status": comment_status,
                "whatsapp_status": whatsapp_status
            }

            lead_id = insert_lead(lead_record)
            lead_record["id"] = lead_id
            extracted_leads.append(lead_record)
            print(f"[Lead Qualified] ID: {lead_id} | Domain: {lead_record['domain_detected']} | Recruiter: {recruiter_name}")

        except Exception as e:
            print(f"[Scanner] Error processing card index {i}: {e}")

    return extracted_leads

async def send_profile_outreach(page: Page, lead: Dict[str, Any], max_dm_quota: int = 35, max_connect_quota: int = 20) -> str:
    """
    Visits the recruiter's profile:
    - If direct 'Message' button is unlocked, sends deep AI pitch message.
    - If locked, sends Connection Request with customized note.
    """
    profile_url = lead.get("recruiter_profile_url")
    if not profile_url:
        print(f"[Outreach] No profile URL for lead {lead.get('id')}")
        return "FAILED"

    lead_id = lead["id"]
    pitch_message = lead.get("pitch_message", "")
    connection_note = lead.get("connection_note", "")

    try:
        print(f"[Outreach] Visiting profile: {profile_url}")
        await page.goto(profile_url, timeout=35000)
        await human_delay(4, 7)

        # 1. Attempt Direct Message
        msg_button = page.locator('button.artdeco-button--primary:has-text("Message"), button:has-text("Message")').first
        if await msg_button.is_visible():
            if get_daily_action_count("DM") >= max_dm_quota:
                print("[Quota] Daily DM quota reached. Skipping DM.")
            else:
                print(f"[Outreach] Open Message button found! Sending direct pitch...")
                await msg_button.click()
                await human_delay(2, 4)
                
                chat_box = page.locator('div[role="textbox"][aria-label*="Write a message"], div.msg-form__contenteditable').first
                if await chat_box.is_visible():
                    await chat_box.click()
                    await chat_box.fill(pitch_message)
                    await human_delay(1.5, 3.0)
                    
                    send_btn = page.locator('button[type="submit"]:has-text("Send"), button.msg-form__send-button').first
                    if await send_btn.is_visible():
                        await send_btn.click()
                        await human_delay(2, 3)
                        update_lead_status(lead_id, "DM_SENT", details=f"Direct message sent to {lead.get('recruiter_name')}")
                        return "DM_SENT"

        # 2. Fallback: Connection Request
        if get_daily_action_count("CONNECTION_REQUEST") >= max_connect_quota:
            print("[Quota] Daily connection request limit reached. Skipping connect.")
            return "QUOTA_EXCEEDED"

        print(f"[Outreach] Direct DM not free/open. Sending connection request with note...")
        connect_btn = page.locator('button:has-text("Connect")').first
        if not await connect_btn.is_visible():
            # Check under 'More' actions dropdown
            more_btn = page.locator('button[aria-label="More actions"], button:has-text("More")').first
            if await more_btn.is_visible():
                await more_btn.click()
                await human_delay(1.5, 2.5)
                connect_btn = page.locator('div[role="button"]:has-text("Connect"), span:has-text("Connect")').first

        if await connect_btn.is_visible():
            await connect_btn.click()
            await human_delay(2, 3.5)

            # Check if "Add a note" modal appears
            add_note_btn = page.locator('button:has-text("Add a note")').first
            if await add_note_btn.is_visible():
                await add_note_btn.click()
                await human_delay(1, 2)
                
                textarea = page.locator('textarea[name="message"], textarea#custom-message').first
                if await textarea.is_visible():
                    await textarea.fill(connection_note[:280])
                    await human_delay(1.5, 2.5)
                
                send_invite = page.locator('button:has-text("Send")').first
                await send_invite.click()
            else:
                # Direct send without note
                send_direct = page.locator('button:has-text("Send without note"), button[aria-label="Send now"]').first
                if await send_direct.is_visible():
                    await send_direct.click()

            await human_delay(2, 4)
            update_lead_status(lead_id, "CONNECTION_REQUESTED", details="Connection request sent with note.")
            return "CONNECTION_REQUESTED"

        update_lead_status(lead_id, "FAILED", details="No accessible message or connect buttons found.")
        return "FAILED"

    except Exception as e:
        print(f"[Outreach] Error dispatching outreach to {profile_url}: {e}")
        update_lead_status(lead_id, "FAILED", details=str(e))
        return "FAILED"

async def post_recruiter_comment(page: Page, lead: Dict[str, Any]) -> bool:
    """Posts a tailored comment with portfolio link if recruiter requested comments."""
    post_url = lead.get("post_url")
    comment_text = lead.get("comment_text")
    lead_id = lead["id"]

    if not post_url or not comment_text:
        return False

    try:
        print(f"[Comment] Navigating to post to comment: {post_url}")
        await page.goto(post_url, timeout=35000)
        await human_delay(3, 5)

        # Find Comment button / box
        comment_action_btn = page.locator('button[aria-label*="Comment"], button:has-text("Comment")').first
        if await comment_action_btn.is_visible():
            await comment_action_btn.click()
            await human_delay(1.5, 3)

        editor = page.locator('div[role="textbox"][aria-label*="comment"], div.ql-editor').first
        if await editor.is_visible():
            await editor.click()
            await editor.fill(comment_text)
            await human_delay(2, 3)

            submit_btn = page.locator('button:has-text("Post"), button.comments-comment-box__submit-button').first
            if await submit_btn.is_visible():
                await submit_btn.click()
                await human_delay(2, 4)
                update_comment_status(lead_id, "COMMENTED", details="Tailored comment with portfolio posted.")
                print(f"[Comment] Successfully posted comment on lead {lead_id}!")
                return True

        update_comment_status(lead_id, "FAILED", details="Comment textbox or submit button not found.")
        return False

    except Exception as e:
        print(f"[Comment] Failed to post comment on {post_url}: {e}")
        update_comment_status(lead_id, "FAILED", details=str(e))
        return False

async def check_and_message_accepted_connections(page: Page) -> int:
    """
    Checks recent connections. If any lead with status 'CONNECTION_REQUESTED'
    has accepted, immediately sends the deep AI-generated pitch message.
    """
    pending_leads = get_pending_connection_leads()
    if not pending_leads:
        return 0

    print(f"[Connection Monitor] Checking {len(pending_leads)} pending connection requests...")
    try:
        await page.goto("https://www.linkedin.com/mynetwork/invite-connect/connections/", timeout=35000)
        await human_delay(4, 6)

        processed_count = 0
        for lead_row in pending_leads:
            lead = dict(lead_row)
            recruiter_name = lead["recruiter_name"]
            profile_url = lead["recruiter_profile_url"]
            pitch_message = lead["pitch_message"]
            lead_id = lead["id"]

            # Search recruiter name or match connection cards on current page
            matched_card = page.locator(f'li:has-text("{recruiter_name}")').first
            if await matched_card.is_visible():
                print(f"[Connection Monitor] Match found! {recruiter_name} accepted your request.")
                
                # Click 'Message' button on the connection card
                msg_btn = matched_card.locator('button:has-text("Message")').first
                if await msg_btn.is_visible():
                    await msg_btn.click()
                    await human_delay(2, 4)
                    
                    chat_box = page.locator('div[role="textbox"][aria-label*="Write a message"], div.msg-form__contenteditable').first
                    if await chat_box.is_visible():
                        await chat_box.fill(pitch_message)
                        await human_delay(1.5, 3)
                        
                        send_btn = page.locator('button[type="submit"]:has-text("Send"), button.msg-form__send-button').first
                        if await send_btn.is_visible():
                            await send_btn.click()
                            await human_delay(2, 3)
                            
                            update_lead_status(lead_id, "CONNECTED", details="Connection accepted and follow-up pitch sent!")
                            log_activity(lead_id, action_type="FOLLOWUP_DM", status="SUCCESS", details=f"Follow-up pitch delivered to {recruiter_name}")
                            processed_count += 1
                            print(f"[Connection Monitor] Instantly sent deep AI pitch to {recruiter_name}!")

        return processed_count

    except Exception as e:
        print(f"[Connection Monitor] Error checking accepted connections: {e}")
        return 0
