import sqlite3

conn = sqlite3.connect('automator.db')
c = conn.cursor()
c.execute("SELECT id, domain_detected, post_id, post_url, recruiter_name, post_text FROM leads WHERE id IN (471, 478)")
for r in c.fetchall():
    print("ID:", r[0], "Domain:", r[1], "Post ID:", r[2], "URL:", r[3], "Recruiter:", r[4])
    print("Text snippet:", repr(r[5][:100]))
