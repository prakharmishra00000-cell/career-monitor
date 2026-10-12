import sqlite3

conn = sqlite3.connect('automator.db')
c = conn.cursor()
c.execute("""
    UPDATE leads 
    SET status = 'REJECTED_NO_DIRECT_LINK' 
    WHERE status NOT LIKE 'REJECTED%' 
      AND (post_url NOT LIKE '%/feed/update/%' AND post_url NOT LIKE '%/posts/%')
""")
print(f"Updated {c.rowcount} leads without direct post link to REJECTED_NO_DIRECT_LINK")
conn.commit()

c.execute("SELECT status, COUNT(*) FROM leads GROUP BY status")
for row in c.fetchall():
    print(row)
