import os
import random
import asyncio
import yaml
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, BrowserContext, Page

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "settings.yaml")

def load_settings():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

async def human_delay(min_sec: float = 2.0, max_sec: float = 5.0):
    """Introduces human-like jitter delay between actions."""
    delay = random.uniform(min_sec, max_sec)
    await asyncio.sleep(delay)

class BrowserManager:
    def __init__(self, headless: Optional[bool] = None):
        self.settings = load_settings()
        self.playwright = None
        self.context: Optional[BrowserContext] = None
        
        # Determine headless
        if headless is not None:
            self.headless = headless
        else:
            self.headless = self.settings.get("browser", {}).get("headless", False)
            
        base_dir = os.path.dirname(os.path.dirname(__file__))
        data_dir_rel = self.settings.get("browser", {}).get("user_data_dir", "browser_data/chrome_profile")
        self.user_data_dir = os.path.join(base_dir, data_dir_rel)
        Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)

    async def start(self) -> BrowserContext:
        """Launches persistent browser context preserving LinkedIn and WhatsApp login sessions."""
        self.playwright = await async_playwright().start()
        
        # Chromium flags for stealth and stability
        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--disable-popup-blocking",
            "--start-maximized"
        ]

        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            channel="chrome", # Will use installed Google Chrome or bundled chromium
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            args=args,
            slow_mo=self.settings.get("browser", {}).get("slow_mo_ms", 50)
        )

        # Inject stealth evasions
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.chrome = {
                runtime: {}
            };
        """)

        return self.context

    async def get_page(self) -> Page:
        if not self.context:
            await self.start()
        if len(self.context.pages) > 0:
            return self.context.pages[0]
        return await self.context.new_page()

    async def close(self):
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
