import sqlite3

conn = sqlite3.connect('automator.db')
c = conn.cursor()
c.execute("DELETE FROM leads WHERE status = 'REJECTED_NO_DIRECT_LINK'")
print(f"Deleted {c.rowcount} stale no-link records to allow fresh scan with link resolver.")
conn.commit()

c.execute("SELECT status, COUNT(*) FROM leads GROUP BY status")
print("Remaining in DB:")
for r in c.fetchall():
    print(r)
