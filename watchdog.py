import os
import sys
import time
import subprocess
from datetime import datetime
from rich.console import Console
from core.github_remote import GitHubRemoteManager

console = Console()

def run_supervisor():
    remote_mgr = GitHubRemoteManager()
    console.print("[bold green]=======================================================[/bold green]")
    console.print("[bold green]  24/7 Auto-Healing Supervisor & Watchdog Started     [/bold green]")
    console.print("[bold green]  Protected Profile: prakhar-mishra-8aa426423          [/bold green]")
    console.print("[bold green]  Remote Controlled by: prakharmishra00000-cell       [/bold green]")
    console.print("[bold green]=======================================================[/bold green]")

    restart_count = 0
    max_consecutive_failures = 10

    while True:
        # Check GitHub remote directives before launching
        directives = remote_mgr.get_remote_directives()
        if directives.get("kill_switch_active"):
            console.print("[bold yellow][GitHub Remote Alert] Kill-switch activated from GitHub. Pausing 24/7 worker...[/bold yellow]")
            remote_mgr.emit_heartbeat(status="PAUSED_BY_GITHUB", last_action="Remote kill-switch active", leads_discovered=0)
            time.sleep(120)
            continue

        stealth_cooldown = directives.get("stealth_cooldown_hours", 0)
        if stealth_cooldown > 0:
            console.print(f"[bold yellow][GitHub Remote Alert] Cooldown mode active ({stealth_cooldown}h). Sleeping...[/bold yellow]")
            time.sleep(stealth_cooldown * 3600)
            continue

        console.print(f"\n[cyan][{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Launching 24/7 Autonomous Bot (Instance #{restart_count + 1})...[/cyan]")
        remote_mgr.emit_heartbeat(status="RUNNING", last_action=f"Launched instance #{restart_count + 1}", leads_discovered=0)

        # Start main.py as a supervised subprocess
        cmd = [sys.executable, "main.py", "--run"]
        process = subprocess.Popen(cmd)

        try:
            return_code = process.wait()
            console.print(f"[yellow]Bot process exited with code: {return_code}[/yellow]")
            
            if return_code == 0:
                # Normal termination (e.g. user keyboard interrupt)
                console.print("[green]Process exited gracefully.[/green]")
                break
            else:
                restart_count += 1
                console.print(f"[bold red]Unexpected exit detected! Failure count: {restart_count}/{max_consecutive_failures}[/bold red]")
                
                # Check for anti-ban safety backoff
                backoff_seconds = min(300, 30 * restart_count)
                console.print(f"[yellow]Auto-recovering... Waiting {backoff_seconds} seconds before self-healing restart.[/yellow]")
                remote_mgr.emit_heartbeat(status="RECOVERING", last_action=f"Process crashed with code {return_code}, restarting in {backoff_seconds}s", leads_discovered=0)
                time.sleep(backoff_seconds)

        except KeyboardInterrupt:
            console.print("\n[yellow]Watchdog received stop command. Terminating child worker...[/yellow]")
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
            remote_mgr.emit_heartbeat(status="STOPPED", last_action="Manual operator shutdown", leads_discovered=0)
            break

if __name__ == "__main__":
    run_supervisor()
