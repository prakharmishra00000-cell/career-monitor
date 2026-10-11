@echo off
echo ===============================================================
echo Starting Authentic Real-Time Live Monitor (No Mock Data)...
echo Opening: http://127.0.0.1:5000
echo ===============================================================
start http://127.0.0.1:5000
python live_dashboard.py
pause
