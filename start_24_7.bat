@echo off
title LinkedIn Career Agent 24-7 Auto-Start
cd /d "C:\Users\yasha\.gemini\antigravity\scratch\linkedin-job-automator"

echo [1/3] Starting Local Dashboard Server...
start /b python live_dashboard.py

echo [2/3] Starting Cloudflare Public Mobile Tunnel...
start /b "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://127.0.0.1:5000

echo [3/3] Starting 24/7 Watchdog Supervisor...
start /b python watchdog.py

echo System running 24/7 in background.
