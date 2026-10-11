# LinkedIn & WhatsApp Autonomous Career Outreach Agent

An enterprise-grade, 24/7 background automation system that detects job & internship postings on LinkedIn, rigorously filters for **paid** opportunities in **UI/UX Design**, **Prompt Engineering**, and **Web Development (Vibe Coding)**, and executes personalized multi-channel outreach via:
- Direct Messages (DMs) to job posters
- Smart Connection Requests with tailored notes
- Instant follow-up DMs as soon as connections are accepted
- Contextual portfolio comments on posts (when recruiters ask to comment)
- Professional WhatsApp outreach (when a contact number is provided)

---

## Architecture Overview

```
LinkedIn Search / Feeds
       │
       ▼
Post Ingestion & Deduplication (SQLite)
       │
       ▼
AI Deep Post Analysis (Gemini / Heuristic Engine)
  ├─ Domain Verification: UI/UX, Prompt Engineering, Vibe Coding
  ├─ Strict Paid Filter (Rejects unpaid internships / no-stipend posts)
  ├─ Recruiter CTAs (e.g. "Comment below with portfolio")
  └─ Contact Extraction (Phone / WhatsApp number extraction)
       │
       ├─────────────────────────┬─────────────────────────┐
       ▼                         ▼                         ▼
Direct Message (Open DM)   Connection Request        Post Comment
       │                   (Wait for acceptance)     (Portfolio attached)
       │                         │
       │                         ▼
       │                   Accepted Connection Poller
       │                   (Instant deep pitch follow-up)
       │                         │
       └─────────────────────────┼─────────────────────────┘
                                 │
                                 ▼
                     WhatsApp Web Automation
                     (Direct message to recruiter's WA)
```

---

## Directory Structure

```
linkedin-job-automator/
├── config/
│   ├── portfolio_profile.json  # Your portfolio, projects, bio & links
│   └── settings.yaml           # Queries, anti-ban rate limits, intervals
├── core/
│   ├── ai_evaluator.py         # Deep post analyzer & personalized pitch generator
│   ├── browser.py              # Stealth persistent browser context manager
│   ├── database.py             # SQLite state store, quotas, & activity tracker
│   ├── linkedin_actions.py     # Feed parser, DM, connect, comment, & poller
│   └── whatsapp_sender.py      # WhatsApp Web automated dispatcher
├── main.py                     # CLI & 24/7 autonomous worker daemon
├── requirements.txt            # Python dependencies
├── setup.bat                   # 1-click environment installer
├── login.bat                   # 1-click interactive login launcher
├── run_24_7.bat                # 1-click 24/7 daemon launcher
└── stats.bat                   # 1-click status dashboard
```

---

## Quick Start Guide

### Step 1: Install Dependencies
Run `setup.bat` or in your terminal:
```bash
pip install -r requirements.txt
playwright install chromium
```

### Step 2: Configure Your Profile
Edit [`config/portfolio_profile.json`](config/portfolio_profile.json):
- Replace `full_name`, `portfolio_url`, `github_url`, `email`, and `phone` with your real details.
- Add your specific featured projects and case study links.

*(Optional)* Add your Gemini API key in `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```
*(Note: If no API key is provided, the system automatically falls back to its built-in rule-based evaluation engine so it never stops working!)*

### Step 3: One-Time Account Login
Run:
```bash
python main.py --login
# or double-click login.bat
```
1. A Chrome window will open.
2. Sign in to your **LinkedIn** account.
3. In the second tab, scan the QR code on **WhatsApp Web** (`web.whatsapp.com`).
4. Press **ENTER** in your terminal. Your session cookies and login tokens are permanently saved in `browser_data/chrome_profile`. You do not need to log in again.

### Step 4: Launch 24/7 Autonomous Agent
Run:
```bash
python main.py --run
# or double-click run_24_7.bat
```
The agent will run continuously in the background, performing periodic sweeps every 10–15 minutes, evaluating new posts, and executing outreach safely.

---

## Monitoring & Stats
To check how many leads were found, DMs sent, and actions performed:
```bash
python main.py --stats
# or double-click stats.bat
```

---

## Anti-Ban & Safety Protections
To ensure your LinkedIn and WhatsApp accounts remain 100% in good standing:
1. **Daily Action Quotas**: Defaults to max 20 connection requests/day and 35 DMs/day (customizable in `config/settings.yaml`).
2. **Human Jitter**: Natural random delays (35s – 90s) between actions.
3. **Session Persistence**: Reuses authentic browser cookies instead of creating new browser fingerprints.
