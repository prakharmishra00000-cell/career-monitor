import sys
import os
import argparse
import asyncio
import time
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core.database import init_db, get_stats, get_daily_action_count
from core.browser import BrowserManager, human_delay, load_settings
from core.linkedin_actions import (
    verify_linkedin_login, search_and_ingest_posts,
    send_profile_outreach, post_recruiter_comment,
    check_and_message_accepted_connections
)
from core.whatsapp_sender import verify_whatsapp_login, process_all_pending_whatsapp_leads
from core.ai_evaluator import analyze_post
from core.github_remote import GitHubRemoteManager

console = Console()

async def interactive_login_mode():
    """Opens a visible browser so the user can log into LinkedIn and WhatsApp Web once."""
    console.print(Panel.fit("[bold cyan]Session Setup & Login Helper[/bold cyan]\n"
                            "This will launch a Chrome window with session persistence.\n"
                            "1. Log into your LinkedIn account.\n"
                            "2. Open WhatsApp Web (web.whatsapp.com) and scan the QR code.\n"
                            "3. When finished, press ENTER here in the terminal to save your session.",
                            border_style="cyan"))

    manager = BrowserManager(headless=False)
    context = await manager.start()
    page = await manager.get_page()

    await page.goto("https://www.linkedin.com/login")
    
    # Open second tab for WhatsApp Web
    wa_page = await context.new_page()
    await wa_page.goto("https://web.whatsapp.com")

    input("\n>>> Press ENTER here once you have successfully logged into both LinkedIn and WhatsApp Web... ")

    console.print("[green]Verifying sessions...[/green]")
    li_ok = await verify_linkedin_login(page)
    wa_ok = await verify_whatsapp_login(wa_page)

    console.print(f"LinkedIn Session: {'[bold green]AUTHENTICATED[/bold green]' if li_ok else '[bold yellow]NOT LOGGED IN[/bold yellow]'}")
    console.print(f"WhatsApp Web Session: {'[bold green]AUTHENTICATED[/bold green]' if wa_ok else '[bold yellow]NOT LOGGED IN[/bold yellow]'}")

    await manager.close()
    console.print("[bold green]Browser session saved successfully in browser_data/chrome_profile![/bold green]")

def display_stats():
    """Prints current database statistics and daily action counts."""
    init_db()
    stats = get_stats()
    
    table = Table(title="[bold blue]Autonomous Career Bot - Lead Statistics[/bold blue]")
    table.add_column("Status / Category", style="cyan", no_wrap=True)
    table.add_column("Count", style="magenta")

    table.add_row("Total Leads Processed", str(stats.get("total_leads", 0)))
    table.add_section()
    for status, count in stats.get("status_breakdown", {}).items():
        table.add_row(f"Status: {status}", str(count))

    console.print(table)

    # Daily Quotas Table
    quota_table = Table(title="[bold green]Today's Action Counts vs. Daily Limits[/bold green]")
    quota_table.add_column("Action", style="cyan")
    quota_table.add_column("Executed Today", style="yellow")
    quota_table.add_column("Safe Daily Max", style="green")

    settings = load_settings().get("rate_limits", {})
    quota_table.add_row("Direct Messages", str(get_daily_action_count("DM")), str(settings.get("max_direct_messages_per_day", 35)))
    quota_table.add_row("Connection Invites", str(get_daily_action_count("CONNECTION_REQUEST")), str(settings.get("max_connection_requests_per_day", 20)))
    quota_table.add_row("Comments", str(get_daily_action_count("COMMENT")), str(settings.get("max_comments_per_day", 25)))
    quota_table.add_row("WhatsApp Messages", str(get_daily_action_count("WHATSAPP")), str(settings.get("max_whatsapp_messages_per_day", 20)))

    console.print(quota_table)

def test_ai_module():
    """Tests the AI evaluator with mock job posts."""
    sample_paid_post = """
    We are looking for a UI/UX Designer and Web Developer for our fast-growing startup!
    Must have experience with Figma, design systems, and rapid vibe coding in Next.js & React.
    This is a paid full-time internship/job with a competitive monthly stipend of $1200 / 40,000 INR.
    Drop your portfolio in the comments below or reach out on WhatsApp at +91 98765 43210!
    """

    sample_unpaid_post = """
    Hiring UI/UX intern! Unpaid internship for college students. Great learning experience and certificate of completion. No stipend provided.
    """

    console.print("[bold yellow]Testing AI Evaluator on Paid Job Post...[/bold yellow]")
    res1 = analyze_post(sample_paid_post, recruiter_name="Alex Smith")
    console.print(res1)

    console.print("\n[bold yellow]Testing AI Evaluator on Unpaid Job Post (Should be Rejected)...[/bold yellow]")
    res2 = analyze_post(sample_unpaid_post, recruiter_name="John Doe")
    console.print(res2)

async def run_autonomous_loop():
    """The 24/7 background worker loop."""
    init_db()
    settings = load_settings()
    rate_limits = settings.get("rate_limits", {})
    check_interval_mins = settings.get("bot", {}).get("check_interval_minutes", 10)
    conn_check_mins = settings.get("bot", {}).get("check_connections_interval_minutes", 15)

    console.print(Panel.fit("[bold green]STARTING 24/7 AUTONOMOUS OUTREACH BOT[/bold green]\n"
                            "Target Domains: UI/UX Design, Prompt Engineering, Web Development (Vibe Coding)\n"
                            "Mode: Paid Jobs & Paid Internships Only (Unpaid Strictly Filtered)\n"
                            "Channels: LinkedIn DM, Connection Requests, Instant Follow-ups, Comments, WhatsApp",
                            border_style="green"))

    manager = BrowserManager()
    await manager.start()
    page = await manager.get_page()

    remote_mgr = GitHubRemoteManager()
    is_logged = await verify_linkedin_login(page, expected_profile_id="prakhar-mishra-8aa426423")
    if not is_logged:
        console.print("[bold red]LinkedIn authentication failed or unauthorized profile detected![/bold red]")
        console.print("[bold yellow]This automation is strictly locked to Prakhar Mishra (prakhar-mishra-8aa426423).[/bold yellow]")
        console.print("[cyan]Please run 'python main.py --login' to sign into the authorized account.[/cyan]")
        await manager.close()
        return

    last_conn_check_time = 0

    try:
        while True:
            # Sync live directives from GitHub (prakharmishra00000-cell)
            directives = remote_mgr.get_remote_directives()
            if directives.get("kill_switch_active"):
                console.print("[bold yellow][GitHub Remote] Bot paused via GitHub kill-switch. Waiting 120s...[/bold yellow]")
                remote_mgr.emit_heartbeat(status="PAUSED", last_action="Remote kill-switch active", leads_discovered=0)
                await asyncio.sleep(120)
                continue

            delay_multiplier = directives.get("dynamic_delay_multiplier", 1.0)
            remote_queries = directives.get("custom_search_queries")
            active_queries = remote_queries if remote_queries else settings.get("search_queries", [])

            cycle_start = time.time()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            console.print(f"\n[bold blue][{now_str}] Starting Scanning & Outreach Cycle (Synced with GitHub)...[/bold blue]")
            remote_mgr.emit_heartbeat(status="SCANNING", last_action=f"Cycle started at {now_str}", leads_discovered=0)

            # 1. Check for Accepted Connections & Instantly Dispatch Deep AI Pitch
            if (time.time() - last_conn_check_time) >= (conn_check_mins * 60):
                console.print("[cyan]Checking for newly accepted connection requests...[/cyan]")
                sent_followups = await check_and_message_accepted_connections(page)
                if sent_followups > 0:
                    console.print(f"[bold green]Delivered {sent_followups} instant follow-up pitches to new connections![/bold green]")
                last_conn_check_time = time.time()

            # 2. Search & Ingest Matching Posts
            queries = settings.get("search_queries", [])
            for query in queries:
                try:
                    leads = await search_and_ingest_posts(page, query=query, max_posts=5)
                    for lead in leads:
                        # Outreach Dispatch
                        if settings.get("channels", {}).get("enable_linkedin_dm", True):
                            outreach_result = await send_profile_outreach(
                                page, lead,
                                max_dm_quota=rate_limits.get("max_direct_messages_per_day", 35),
                                max_connect_quota=rate_limits.get("max_connection_requests_per_day", 20)
                            )
                            console.print(f"[Lead {lead['id']}] Outreach result: {outreach_result}")
                            await human_delay(
                                rate_limits.get("min_delay_between_actions_seconds", 35),
                                rate_limits.get("max_delay_between_actions_seconds", 90)
                            )

                        # Comment Dispatch (if requested by recruiter)
                        if lead.get("requires_comment") and settings.get("channels", {}).get("enable_linkedin_comment", True):
                            await post_recruiter_comment(page, lead)
                            await human_delay(20, 45)

                except Exception as e:
                    console.print(f"[red]Error during query '{query}': {e}[/red]")
                    await human_delay(10, 20)

            # 3. Process Pending WhatsApp Inquiries
            if settings.get("channels", {}).get("enable_whatsapp", True):
                try:
                    wa_sent = await process_all_pending_whatsapp_leads(page)
                    if wa_sent > 0:
                        console.print(f"[bold green]Dispatched {wa_sent} WhatsApp inquiries![/bold green]")
                except Exception as e:
                    console.print(f"[red]Error processing WhatsApp queue: {e}[/red]")

            # Cycle finished; sleep until next cycle
            sleep_duration = check_interval_mins * 60
            console.print(f"[bold yellow]Cycle complete. Sleeping for {check_interval_mins} minutes before next sweep...[/bold yellow]")
            await asyncio.sleep(sleep_duration)

    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping autonomous worker gracefully...[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Fatal error in worker daemon: {e}[/bold red]")
    finally:
        await manager.close()
        console.print("[green]Browser context closed safely.[/green]")

def main():
    parser = argparse.ArgumentParser(description="LinkedIn & WhatsApp Autonomous Job Outreach Bot")
    parser.add_argument("--login", action="store_true", help="Launch browser to log in to LinkedIn & WhatsApp once")
    parser.add_argument("--run", action="store_true", help="Run 24/7 autonomous monitoring & outreach daemon")
    parser.add_argument("--stats", action="store_true", help="Display stats and activity logs")
    parser.add_argument("--test-ai", action="store_true", help="Run AI evaluator test on sample job posts")

    args = parser.parse_args()

    if args.login:
        asyncio.run(interactive_login_mode())
    elif args.run:
        asyncio.run(run_autonomous_loop())
    elif args.stats:
        display_stats()
    elif args.test_ai:
        test_ai_module()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
