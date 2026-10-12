import sqlite3

conn = sqlite3.connect('automator.db')
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM leads")
total = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM leads WHERE post_url LIKE '%/feed/update/%' OR post_url LIKE '%/posts/%'")
verified = c.fetchone()[0]

c.execute("SELECT id, domain_detected, recruiter_name, post_url, created_at FROM leads WHERE post_url LIKE '%/feed/update/%' OR post_url LIKE '%/posts/%'")
verified_rows = c.fetchall()

print(f"Total leads: {total} | Verified with Direct Link: {verified}")
for r in verified_rows:
    print(r)
