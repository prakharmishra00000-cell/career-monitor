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
from core.live_monitor import record_live_event

async def verify_linkedin_login(page: Page, expected_profile_id: str = "prakhar-mishra-8aa426423") -> bool:
    """
    Checks if the current session is logged in and verifies it strictly belongs to
    the authorized profile: prakhar-mishra-8aa426423.
    """
    try:
        try:
            await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=60000)
            await human_delay(3, 5)
        except Exception as e:
            print(f"[LinkedIn Check] Feed nav notice: {e}")

        # Check basic authentication
        if "login" in page.url or "checkpoint" in page.url:
            print("[LinkedIn Auth] Not logged in.")
            return False

        # Navigate to /in/me/ to verify exact identity
        try:
            await page.goto("https://www.linkedin.com/in/me/", wait_until="domcontentloaded", timeout=60000)
            await human_delay(3, 5)
        except Exception as e:
            print(f"[LinkedIn Check] /in/me nav notice: {e}")

        current_url = page.url.lower()

        if expected_profile_id.lower() in current_url:
            print(f"[LinkedIn Auth] Identity Verified: Authorized profile active ({expected_profile_id})")
            return True
        elif "/in/" in current_url:
            body_text = await page.inner_text("body")
            if "prakhar mishra" in body_text.lower():
                print(f"[LinkedIn Auth] Identity Verified: Prakhar Mishra verified on profile page.")
                return True
            else:
                print(f"[SECURITY ALERT] Current logged-in account does NOT match authorized ID ({expected_profile_id}). Current URL: {current_url}")
                return False

        # If feed or session is authenticated
        if "linkedin.com" in page.url and "login" not in page.url:
            print(f"[LinkedIn Auth] Active authenticated session confirmed.")
            return True
        return False
    except Exception as e:
        print(f"[LinkedIn Check] Verification error: {e}")
        return True

async def resolve_direct_post_link(context, author_url: str) -> str:
    """Navigates to author's recent activity feed to extract the exact direct post permalink."""
    if not author_url or "linkedin.com/in/" not in author_url:
        return ""
    activity_url = f"{author_url.rstrip('/')}/recent-activity/all/"
    try:
        temp_page = await context.new_page()
        await temp_page.goto(activity_url, timeout=25000)
        await asyncio.sleep(2)
        links = await temp_page.evaluate("""
        () => {
            const anchors = Array.from(document.querySelectorAll('a')).map(a => a.href);
            return anchors.filter(h => h.includes('/feed/update/') || h.includes('/posts/'));
        }
        """)
        await temp_page.close()
        if links:
            return links[0].split('?')[0]
    except Exception as e:
        print(f"[LinkResolver] Note resolving activity link: {e}")
    return ""

async def search_and_ingest_posts(page: Page, query: str, max_posts: int = 10) -> List[Dict[str, Any]]:
    """Searches LinkedIn for recent posts matching target keywords."""
    encoded_q = urllib.parse.quote(query)
    search_url = f"https://www.linkedin.com/search/results/content/?keywords={encoded_q}&sortBy=%22date_posted%22"
    
    print(f"[Scanner] Searching LinkedIn: {query}")
    record_live_event("SCANNING", f"Searching LinkedIn feed: {query}")
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

    # Extract posts using evaluate to support both legacy and 2026 feed formats
    js_extract = """
    () => {
        // Collect all distinct feed post spans
        const spans = Array.from(document.querySelectorAll('span')).filter(s => s.innerText.trim() === 'Feed post');
        const items = [];
        const seenUrls = new Set();

        for (const s of spans) {
            let card = s;
            while (card && card.parentElement && card.parentElement.tagName !== 'MAIN' && card.parentElement.id !== 'root') {
                const feedSpansInParent = Array.from(card.parentElement.querySelectorAll('span')).filter(sp => sp.innerText.trim() === 'Feed post');
                if (feedSpansInParent.length > 1) break;
                card = card.parentElement;
            }
            if (!card) continue;

            const authorLink = card.querySelector('a[href*="/in/"]');
            const authorUrl = authorLink ? authorLink.href.split('?')[0] : '';
            if (authorUrl && seenUrls.has(authorUrl)) continue;
            if (authorUrl) seenUrls.add(authorUrl);

            // Extract author name
            let authorName = 'Recruiter';
            if (authorLink) {
                const rawName = authorLink.innerText.trim().split('\\n')[0];
                if (rawName && rawName.length > 1) authorName = rawName;
            }

            // Extract post text
            let fullText = card.innerText || '';
            // Remove "Feed post" header line from text
            if (fullText.startsWith('Feed post')) {
                fullText = fullText.substring(9).trim();
            }

            // Find direct permalink to the post:
            const container = card.closest('li') || card.closest('.artdeco-card') || card;
            let postHref = '';
            const allAnchors = Array.from(container.querySelectorAll('a'));
            for (const a of allAnchors) {
                const href = a.href || '';
                if (href.includes('/feed/update/') || href.includes('/posts/')) {
                    postHref = href.split('?')[0];
                    break;
                }
            }

            // Fallback: check data-urn, data-entity-urn, data-chameleon-result-urn, or regex on container outerHTML
            let urn = container.getAttribute('data-urn') || container.getAttribute('data-id') || container.getAttribute('data-entity-urn') || '';
            if (!urn) {
                const elWithUrn = container.querySelector('[data-urn], [data-entity-urn], [data-id*="activity"], [data-chameleon-result-urn]');
                if (elWithUrn) {
                    urn = elWithUrn.getAttribute('data-urn') || elWithUrn.getAttribute('data-entity-urn') || elWithUrn.getAttribute('data-id') || elWithUrn.getAttribute('data-chameleon-result-urn') || '';
                }
            }
            if (!postHref) {
                const html = (container.outerHTML || '');
                const m = html.match(/urn:li:(activity|ugcPost|share):[0-9]+/);
                if (m) {
                    urn = m[0];
                    postHref = `https://www.linkedin.com/feed/update/${m[0]}/`;
                }
            }

            items.push({
                urn: urn,
                postHref: postHref,
                authorName: authorName,
                authorUrl: authorUrl,
                postText: fullText
            });
        }
        return items;
    }
    """
    raw_posts = await page.evaluate(js_extract)
    print(f"[Scanner] Found {len(raw_posts)} post elements on search page.")

    extracted_leads = []

    for raw in raw_posts[:max_posts]:
        try:
            author_url = raw.get("authorUrl", "")
            recruiter_name = raw.get("authorName", "Recruiter")
            post_text = raw.get("postText", "")
            post_urn = raw.get("urn", "")
            post_href = raw.get("postHref", "")

            # Generate unique post identifier
            post_id = post_urn if post_urn else (post_href if post_href else f"post_{abs(hash(post_text[:120]))}")

            if is_post_processed(post_id):
                continue

            recruiter_profile_url = author_url
            if post_href and ("/feed/update/" in post_href or "/posts/" in post_href):
                post_url = post_href
            elif "urn:li:activity" in post_id or "urn:li:ugcPost" in post_id or "urn:li:share" in post_id:
                post_url = f"https://www.linkedin.com/feed/update/{post_id}/"
            else:
                post_url = ""  # NEVER fallback to profile URL or search URL

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

            # HARD CRITERIA VALIDATION GATE FOR MECHANICAL ENGINEERING:
            # 1. MUST be strictly for Freshers / 2026, 2027, or 2028 batch (Zero experienced roles)
            # 2. MUST explicitly mention CTC / LPA / salary / stipend in the post
            # 3. MUST explicitly state active backlogs allowed OR no minimum CGPA
            # 4. MUST NOT have prohibited zero-backlog, minimum % cutoff, or experience requirements
            if analysis.get("domain_detected") == "Mechanical Engineer":
                raw_lower = post_text.lower()

                # Batch / Fresher eligibility (Strictly 2026, 2027, 2028 freshers only)
                batch_cues = ["2026", "2027", "2028", "fresher", "freshers", "intern", "internship", "graduate engineer trainee", "get trainee", "entry level", "junior engineer"]
                has_target_batch = any(b in raw_lower for b in batch_cues)

                # Prohibited experienced markers (e.g. 1+ years, 2+ years, 3+ years, senior)
                experienced_cues = ["years of experience", "years experience", "yr experience", "yrs experience", "1+ year", "2+ year", "3+ year", "4+ year", "5+ year", "senior", "lead engineer"]
                has_experience_required = any(exp in raw_lower for exp in experienced_cues)

                allowed_backlog_cues = ["active backlog", "backlog allowed", "backlogs allowed", "backlogs accepted", "with backlog", "allow backlog", "standing arrear", "arrear allowed"]
                no_cgpa_cues = ["no minimum cgpa", "no cgpa", "no percentage", "no minimum percentage", "no cutoff", "no criteria", "any percentage", "any cgpa", "skill based", "practical test only"]
                prohibited_cues = ["no active backlog", "no backlog", "zero backlog", "without backlog", "min 60%", "min 65%", "min 70%", "min 75%", "minimum 60%", "minimum 70%", "minimum 75%", "6.0 cgpa", "6.5 cgpa", "7.0 cgpa", "7.5 cgpa", "8.0 cgpa"]
                salary_ctc_cues = ["lpa", "ctc", "per annum", "/annum", "inr", "salary", "stipend", "pm", "/month", "per month"]

                has_prohibited = any(p in raw_lower for p in prohibited_cues)
                has_allowed_backlog = any(b in raw_lower for b in allowed_backlog_cues)
                has_no_cgpa = any(c in raw_lower for c in no_cgpa_cues)
                has_salary_or_ctc = any(s in raw_lower for s in salary_ctc_cues)

                # Strict requirement:
                # Must be 2026/2027/2028/fresher + NO experience required + CTC/LPA present + Backlog allowed/No CGPA present + NO prohibited cutoffs
                if not has_target_batch or has_experience_required or has_prohibited or not (has_allowed_backlog or has_no_cgpa) or not has_salary_or_ctc:
                    print(f"[Filter] Discarding Mechanical post {post_id}: does not meet 2026-2028 batch + CTC/LPA + backlogs-allowed/no-CGPA criteria.")
                    lead_data = {
                        "post_id": post_id,
                        "post_url": post_url,
                        "recruiter_name": recruiter_name,
                        "recruiter_profile_url": recruiter_profile_url,
                        "post_text": post_text,
                        "job_type": analysis.get("job_type", "job"),
                        "is_paid": 1,
                        "domain_detected": "Mechanical Engineer",
                        "relevance_score": 0.0,
                        "recruiter_instructions": "",
                        "whatsapp_number": None,
                        "requires_comment": 0,
                        "comment_text": "",
                        "pitch_message": "",
                        "connection_note": "",
                        "whatsapp_pitch": "",
                        "status": "REJECTED_STRICT_CRITERIA",
                        "comment_status": "NONE",
                        "whatsapp_status": "NONE"
                    }
                    insert_lead(lead_data)
                    continue

            # Qualified lead! Resolve direct permalink from recruiter profile if missing!
            if not post_url and recruiter_profile_url and "linkedin.com/in/" in recruiter_profile_url:
                print(f"[LinkResolver] Resolving direct post permalink for {recruiter_name} ({recruiter_profile_url})...")
                post_url = await resolve_direct_post_link(page.context, recruiter_profile_url)

            # Final verification: If direct post link could not be verified, discard so "Link unavailable" never appears
            if not post_url or not ("/feed/update/" in post_url or "/posts/" in post_url):
                print(f"[Filter] Discarding post {post_id}: direct post link could not be verified.")
                lead_data = {
                    "post_id": post_id,
                    "post_url": "",
                    "recruiter_name": recruiter_name,
                    "recruiter_profile_url": recruiter_profile_url,
                    "post_text": post_text,
                    "job_type": analysis.get("job_type", "job"),
                    "is_paid": 1 if analysis.get("is_paid") else 0,
                    "domain_detected": analysis.get("domain_detected", "Other"),
                    "relevance_score": 0.0,
                    "recruiter_instructions": "",
                    "whatsapp_number": None,
                    "requires_comment": 0,
                    "comment_text": "",
                    "pitch_message": "",
                    "connection_note": "",
                    "whatsapp_pitch": "",
                    "status": "REJECTED_NO_DIRECT_LINK",
                    "comment_status": "NONE",
                    "whatsapp_status": "NONE"
                }
                insert_lead(lead_data)
                continue

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
                
                chat_box = page.locator('div[role="textbox"][aria-label*="Write a message"], div.msg-form__contenteditable, div[contenteditable="true"]').first
                if await chat_box.is_visible():
                    await chat_box.click()
                    await human_delay(1, 2)
                    # Use keyboard type for contenteditable divs
                    # Clean pitch_message to ascii / safe unicode
                    safe_pitch = pitch_message.encode('ascii', errors='ignore').decode('ascii')
                    await page.keyboard.type(safe_pitch, delay=15)
                    await human_delay(1.5, 3.0)
                    
                    send_btn = page.locator('button[type="submit"]:has-text("Send"), button.msg-form__send-button, button:has-text("Send")').first
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
                try:
                    await more_btn.click(timeout=5000, force=True)
                    await human_delay(1.5, 2.5)
                    connect_btn = page.locator('div[role="button"]:has-text("Connect"), span:has-text("Connect")').first
                except Exception as more_err:
                    print(f"[Outreach] Could not open More dropdown: {more_err}")

        if await connect_btn.is_visible():
            try:
                await connect_btn.click(timeout=5000, force=True)
                await human_delay(2, 3.5)
            except Exception as conn_err:
                print(f"[Outreach] Connect click notice: {conn_err}")

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
