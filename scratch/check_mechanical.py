import sqlite3

def check_mechanical():
    conn = sqlite3.connect('automator.db')
    c = conn.cursor()
    c.execute("SELECT id, domain_detected, status, post_url, post_text FROM leads WHERE domain_detected = 'Mechanical Engineer'")
    rows = c.fetchall()
    print(f"Total Mechanical leads in DB: {len(rows)}")
    for r in rows:
        lead_id, domain, status, post_url, text = r
        safe_text = clean_text.encode('ascii', 'ignore').decode('ascii')
        print(f"ID #{lead_id} | Status: {status} | URL: {post_url} | Text: {safe_text}")

if __name__ == '__main__':
    check_mechanical()
