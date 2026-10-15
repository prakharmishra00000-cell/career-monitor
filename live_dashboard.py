import os
import json
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
from core.database import get_connection, get_stats, get_daily_action_count

STATUS_FILE = os.path.join(os.path.dirname(__file__), "logs", "live_status.json")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Prakhar Mishra | 24/7 Career Agent Live Monitor</title>
    <style>
        :root {
            --bg: #090d16;
            --card-bg: #111827;
            --border: #1f2937;
            --accent: #3b82f6;
            --text-main: #f9fafb;
            --text-muted: #9ca3af;
            --green: #10b981;
            --yellow: #f59e0b;
            --red: #ef4444;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        body { background: var(--bg); color: var(--text-main); padding: 24px; }
        .container { max-width: 1200px; margin: 0 auto; }
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid var(--border); }
        .badge { padding: 4px 12px; border-radius: 9999px; font-size: 13px; font-weight: 600; display: inline-flex; align-items: center; gap: 6px; }
        .badge-live { background: rgba(16, 185, 129, 0.15); color: var(--green); border: 1px solid var(--green); }
        .pulse { width: 8px; height: 8px; background: var(--green); border-radius: 50%; animation: pulse 1.5s infinite; }
        @keyframes pulse { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
        .card-label { font-size: 13px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
        .card-value { font-size: 28px; font-weight: 700; color: var(--text-main); }
        .card-sub { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
        .section-title { font-size: 18px; font-weight: 600; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; }
        table { width: 100%; border-collapse: collapse; background: var(--card-bg); border-radius: 12px; overflow: hidden; border: 1px solid var(--border); }
        th, td { padding: 12px 16px; text-align: left; font-size: 14px; border-bottom: 1px solid var(--border); }
        th { background: #1a2234; color: var(--text-muted); font-weight: 600; font-size: 12px; text-transform: uppercase; }
        tr:hover { background: #162032; }
        .tag { padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
        .tag-paid { background: rgba(16, 185, 129, 0.2); color: var(--green); }
        .tag-unpaid { background: rgba(239, 68, 68, 0.2); color: var(--red); }
        .tag-status { background: rgba(59, 130, 246, 0.2); color: var(--accent); }
        .console-box { background: #000; border: 1px solid var(--border); border-radius: 8px; padding: 16px; font-family: monospace; font-size: 13px; height: 180px; overflow-y: auto; color: #a3e635; margin-top: 24px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>Prakhar Mishra | Career Agent Live Monitor</h1>
                <p style="color: var(--text-muted); font-size: 14px; margin-top: 4px;">Profile: prakhar-mishra-8aa426423 | WhatsApp: +91 6372843175</p>
            </div>
            <div class="badge badge-live">
                <span class="pulse"></span> REAL-TIME ENGINE ACTIVE
            </div>
        </header>

        <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));">
            <div class="card">
                <div class="card-label">Scanner Status</div>
                <div class="card-value" id="currentStage" style="color: var(--accent);">INITIALIZING</div>
                <div class="card-sub" id="lastActive">Checking...</div>
            </div>
            <div class="card">
                <div class="card-label">Verified Opportunities (Recruiter WhatsApp & Direct Links)</div>
                <div class="card-value" id="totalLeads">0</div>
                <div class="card-sub">Mechanical (2026-2028 Freshers) • UI/UX • AI/Prompt • Web Dev</div>
            </div>
        </div>

        <div class="section-title">
            <span>Authentic Detected Opportunities (WhatsApp & Direct Links)</span>
            <span style="font-size: 12px; color: var(--text-muted);">Auto-refreshes live every 3s</span>
        </div>

        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Role</th>
                    <th>Target Level</th>
                    <th>Direct Post Link</th>
                    <th>Recruiter WhatsApp / Contact</th>
                    <th>Compensation</th>
                    <th>Status</th>
                    <th>Time</th>
                </tr>
            </thead>
            <tbody id="leadsTableBody">
                <tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 24px;">Loading live opportunities...</td></tr>
            </tbody>
        </table>

        <div class="console-box" id="consoleLogs">
            [System] Live telemetry streaming initialized...
        </div>
    </div>

    <script>
        async function refreshData() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();

                document.getElementById('currentStage').innerText = data.current_stage || 'IDLE';
                document.getElementById('lastActive').innerText = 'Last Event: ' + (data.last_active || 'Just now');
                document.getElementById('totalLeads').innerText = data.stats.total_leads || 0;

                const tbody = document.getElementById('leadsTableBody');
                const validLeads = data.leads || [];
                if (validLeads.length > 0) {
                    tbody.innerHTML = validLeads.map(ld => {
                        let targetLevelBadge = '';
                        if (ld.domain_detected === 'Mechanical Engineer') {
                            targetLevelBadge = `<span style="background:rgba(245,158,11,0.2); color:#fbbf24; padding:3px 8px; border-radius:4px; font-size:11px; font-weight:700; border:1px solid #d97706; display:inline-block;">⚡ Freshers / Trainees (2026-2028)</span>`;
                        } else {
                            const levelText = (ld.job_type === 'internship') ? 'Fresher / Intern' : 'Fresher / Junior';
                            targetLevelBadge = `<span style="background:rgba(99,102,241,0.2); color:#a5b4fc; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:600;">${levelText}</span>`;
                        }

                        let postLink = '';
                        if (ld.post_url && (ld.post_url.includes('/feed/update/') || ld.post_url.includes('/posts/') || ld.post_url.includes('/jobs/view/'))) {
                            postLink = `<a href="${ld.post_url}" target="_blank" style="display:inline-block; color:#34d399; text-decoration:none; font-weight:700; font-size:12px; background:rgba(52,211,153,0.18); padding:5px 12px; border-radius:6px; border:1px solid #10b981;">🔗 Direct Post Link</a>`;
                        } else {
                            postLink = `<span style="color:#f59e0b; font-size:12px; font-weight:600; background:rgba(245,158,11,0.15); padding:4px 8px; border-radius:4px; border:1px solid #d97706;">Direct Post Link Pending</span>`;
                        }

                        let waContact = '';
                        if (ld.whatsapp_number) {
                            const cleanNum = ld.whatsapp_number.replace(/[^0-9]/g, '');
                            const chatNum = cleanNum.startsWith('91') && cleanNum.length === 12 ? cleanNum : (cleanNum.length === 10 ? '91' + cleanNum : cleanNum);
                            waContact = `<a href="https://wa.me/${chatNum}" target="_blank" style="display:inline-flex; align-items:center; gap:4px; background:rgba(16,185,129,0.2); color:#10b981; padding:4px 10px; border-radius:6px; font-weight:700; font-size:12px; text-decoration:none; border:1px solid #10b981;">💬 +${chatNum}</a>`;
                        } else {
                            waContact = `<span style="color:#6b7280; font-size:12px;">Contact on WhatsApp</span>`;
                        }

                        return `
                        <tr>
                            <td>#${ld.id}</td>
                            <td><strong style="color:#f3f4f6;">${ld.domain_detected}</strong></td>
                            <td>${targetLevelBadge}</td>
                            <td>${postLink}</td>
                            <td>${waContact}</td>
                            <td><span class="tag ${ld.is_paid ? 'tag-paid' : 'tag-unpaid'}">${ld.is_paid ? 'PAID' : 'UNPAID'}</span></td>
                            <td><span class="tag tag-status">${ld.status}</span></td>
                            <td style="color: var(--text-muted); font-size: 12px;">${ld.created_at}</td>
                        </tr>
                        `;
                    }).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding: 28px; color: var(--text-muted); font-size: 14px;">No verified post opportunities found yet. Continuous live scout active...</td></tr>';
                }

                if (data.recent_events && data.recent_events.length > 0) {
                    const logsBox = document.getElementById('consoleLogs');
                    logsBox.innerHTML = data.recent_events.map(ev => `[${ev.timestamp}] [${ev.stage}] ${ev.message}`).join('<br>');
                }
            } catch (err) {
                console.error("Telemetry fetch error:", err);
            }
        }

        setInterval(refreshData, 3000);
        refreshData();
    </script>
</body>
</html>
"""

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            # Read live state
            live_data = {}
            if os.path.exists(STATUS_FILE):
                try:
                    with open(STATUS_FILE, "r", encoding="utf-8") as f:
                        live_data = json.load(f)
                except Exception:
                    pass

            # Query real leads from DB: Strictly direct post links only (/feed/update/, /posts/, /jobs/view/)
            leads = []
            verified_count = 0
            try:
                with get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT id, recruiter_name, recruiter_profile_url, post_url, domain_detected, job_type, is_paid, status, whatsapp_number, whatsapp_status, created_at
                        FROM leads 
                        WHERE domain_detected IN ('UI/UX Designer', 'Prompt Engineer', 'Web Developer', 'Mechanical Engineer')
                          AND whatsapp_number IS NOT NULL 
                          AND length(whatsapp_number) >= 8
                        ORDER BY id DESC LIMIT 250
                    """)
                    leads = [dict(r) for r in cursor.fetchall()]

                    cursor.execute("""
                        SELECT COUNT(*) FROM leads 
                        WHERE domain_detected IN ('UI/UX Designer', 'Prompt Engineer', 'Web Developer', 'Mechanical Engineer')
                          AND whatsapp_number IS NOT NULL 
                          AND length(whatsapp_number) >= 8
                    """)
                    verified_count = cursor.fetchone()[0]
            except Exception:
                pass

            response_payload = {
                "current_stage": live_data.get("current_stage", "IDLE"),
                "last_active": live_data.get("last_active", ""),
                "status_message": live_data.get("status_message", ""),
                "stats": {
                    "total_leads": verified_count,
                    "status_breakdown": get_stats().get("status_breakdown", {})
                },
                "quotas": {
                    "dm": get_daily_action_count("DM"),
                    "connect": get_daily_action_count("CONNECTION_REQUEST"),
                    "comment": get_daily_action_count("COMMENT"),
                    "whatsapp": get_daily_action_count("WHATSAPP")
                },
                "leads": leads,
                "recent_events": live_data.get("recent_events", [])
            }
            self.wfile.write(json.dumps(response_payload).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

def run_dashboard_server(port: int = 5000):
    server = ThreadingHTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"\n[Live Dashboard] Multi-threaded server running on all interfaces at port {port}")
    server.serve_forever()

if __name__ == "__main__":
    run_dashboard_server()
