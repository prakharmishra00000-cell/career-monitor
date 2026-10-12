import sqlite3

conn = sqlite3.connect('automator.db')
c = conn.cursor()
c.execute("SELECT domain_detected, COUNT(id) FROM leads WHERE status NOT LIKE 'REJECTED%' GROUP BY domain_detected")
for row in c.fetchall():
    print(f"{row[0]}: {row[1]}")
