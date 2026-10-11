@echo off
echo =======================================================
echo Setting up LinkedIn & WhatsApp Job Automator Environment
echo =======================================================
pip install -r requirements.txt
playwright install chromium
echo.
echo Setup completed! Next, run login.bat to log in to your accounts.
pause
