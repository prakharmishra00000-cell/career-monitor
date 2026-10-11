import os
import json
import time
import requests
from typing import Dict, Any, Optional

class GitHubRemoteManager:
    """
    Manages remote control, watchdog signals, and dynamic configuration
    synchronized via GitHub (prakharmishra00000-cell) so the 24/7 bot
    never gets permanently disabled or banned.
    """
    def __init__(self, github_username: str = "prakharmishra00000-cell", repo_name: str = "linkedin-automator-control"):
        self.username = github_username
        self.repo = repo_name
        self.raw_config_url = f"https://raw.githubusercontent.com/{self.username}/{self.repo}/main/bot_control.json"
        self.local_cache_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "remote_control_cache.json")
        self.last_fetch_time = 0
        self.fetch_interval_seconds = 180 # Check GitHub remote config every 3 minutes

    def get_remote_directives(self) -> Dict[str, Any]:
        """
        Fetches live instructions from your GitHub repository.
        If offline or repo not yet published, uses safe local defaults.
        """
        current_time = time.time()
        if (current_time - self.last_fetch_time) < self.fetch_interval_seconds:
            return self._load_cached_directives()

        try:
            response = requests.get(self.raw_config_url, timeout=5)
            if response.status_code == 200:
                directives = response.json()
                self._cache_directives(directives)
                self.last_fetch_time = current_time
                print(f"[GitHub Remote] Synced live directives from {self.username}/{self.repo}")
                return directives
        except Exception as e:
            # Fallback to local cache if network drops
            pass

        return self._load_cached_directives()

    def _load_cached_directives(self) -> Dict[str, Any]:
        if os.path.exists(self.local_cache_path):
            try:
                with open(self.local_cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Default safe directives
        return {
            "kill_switch_active": False,
            "stealth_cooldown_hours": 0,
            "dynamic_delay_multiplier": 1.0,
            "circuit_breaker_triggered": False,
            "status_message": "Operating normally",
            "channels": {
                "direct_message": True,
                "connection_request": True,
                "comments": True,
                "whatsapp": True
            }
        }

    def _cache_directives(self, directives: Dict[str, Any]):
        try:
            with open(self.local_cache_path, "w", encoding="utf-8") as f:
                json.dump(directives, f, indent=2)
        except Exception:
            pass

    def emit_heartbeat(self, status: str, last_action: str, leads_discovered: int):
        """
        Logs local and remote telemetry state so you can inspect
        your bot's 24/7 health remotely at any time.
        """
        heartbeat_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "owner": self.username,
            "authorized_profile": "prakhar-mishra-8aa426423",
            "bot_status": status,
            "last_action": last_action,
            "leads_discovered": leads_discovered,
            "health": "OPTIMAL"
        }
        heartbeat_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "heartbeat.json")
        try:
            with open(heartbeat_file, "w", encoding="utf-8") as f:
                json.dump(heartbeat_data, f, indent=2)
        except Exception:
            pass
