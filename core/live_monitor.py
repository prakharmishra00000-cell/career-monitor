import os
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from core.database import get_connection, get_stats, get_daily_action_count

STATUS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "live_status.json")

def record_live_event(stage: str, message: str, extra: Optional[Dict[str, Any]] = None):
    """
    Saves authentic real-time execution state to logs/live_status.json.
    Guaranteed zero mock data.
    """
    os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
    
    current_data = {}
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                current_data = json.load(f)
        except Exception:
            pass

    history: List[Dict[str, Any]] = current_data.get("recent_events", [])
    new_event = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stage": stage,
        "message": message,
        "extra": extra or {}
    }
    history.insert(0, new_event)
    history = history[:50] # Keep last 50 authentic events

    payload = {
        "bot_name": "Prakhar Mishra Career Agent",
        "authorized_profile": "prakhar-mishra-8aa426423",
        "current_stage": stage,
        "last_active": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status_message": message,
        "extra": extra or {},
        "recent_events": history
    }

    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as e:
        print(f"[Live Monitor] Error saving status: {e}")

def get_recent_leads(limit: int = 10) -> List[Dict[str, Any]]:
    """Fetches real authentic lead entries from the SQLite database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, recruiter_name, domain_detected, job_type, is_paid, status, comment_status, whatsapp_status, created_at
            FROM leads
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

def render_realtime_terminal():
    """Renders authentic real-time dashboard to the console."""
    console = Console()
    stats = get_stats()
    leads = get_recent_leads(limit=8)

    # 1. Header Panel
    status_data = {}
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                status_data = json.load(f)
        except Exception:
            pass

    current_stage = status_data.get("current_stage", "IDLE")
    status_msg = status_data.get("status_message", "Awaiting execution")
    last_seen = status_data.get("last_active", "N/A")

    console.print(Panel(
        f"[bold cyan]PRAKHAR MISHRA - 24/7 AUTONOMOUS OUTREACH LIVE MONITOR[/bold cyan]\n"
        f"[green]Profile:[/green] prakhar-mishra-8aa426423 | [green]Phone/WA:[/green] +91 6372843175\n"
        f"[yellow]Current Stage:[/yellow] [bold]{current_stage}[/bold] | [yellow]Status:[/yellow] {status_msg}\n"
        f"[dim]Last Activity: {last_seen}[/dim]",
        border_style="cyan"
    ))

    # 2. Activity / Quotas Table
    quota_table = Table(title="[bold green]Authentic Daily Action Quotas[/bold green]")
    quota_table.add_column("Channel", style="cyan")
    quota_table.add_column("Actions Today", style="yellow")
    quota_table.add_column("Safe Limit", style="green")

    quota_table.add_row("Direct Messages", str(get_daily_action_count("DM")), "35")
    quota_table.add_row("Connection Invites", str(get_daily_action_count("CONNECTION_REQUEST")), "20")
    quota_table.add_row("Follow-up DMs (Accepted)", str(get_daily_action_count("FOLLOWUP_DM")), "Unlimited")
    quota_table.add_row("Comments", str(get_daily_action_count("COMMENT")), "25")
    quota_table.add_row("WhatsApp Messages", str(get_daily_action_count("WHATSAPP")), "20")
    console.print(quota_table)

    # 3. Authentic Leads Stream Table
    leads_table = Table(title="[bold blue]Live Detected Opportunities (Real Data Only)[/bold blue]")
    leads_table.add_column("ID", style="dim", width=4)
    leads_table.add_column("Recruiter", style="bold")
    leads_table.add_column("Domain", style="cyan")
    leads_table.add_column("Type", style="magenta")
    leads_table.add_column("Paid?", style="green")
    leads_table.add_column("Outreach Status", style="yellow")
    leads_table.add_column("WhatsApp", style="blue")
    leads_table.add_column("Timestamp", style="dim")

    if not leads:
        leads_table.add_row("-", "No opportunities recorded yet", "-", "-", "-", "-", "-", "-")
    else:
        for ld in leads:
            is_paid_str = "[bold green]PAID[/bold green]" if ld["is_paid"] else "[bold red]UNPAID[/bold red]"
            leads_table.add_row(
                str(ld["id"]),
                str(ld["recruiter_name"]),
                str(ld["domain_detected"]),
                str(ld["job_type"]).capitalize(),
                is_paid_str,
                str(ld["status"]),
                str(ld["whatsapp_status"]),
                str(ld["created_at"])
            )

    console.print(leads_table)
