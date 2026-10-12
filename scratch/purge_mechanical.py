import sqlite3

def purge_mechanical():
    conn = sqlite3.connect('automator.db')
    c = conn.cursor()
    c.execute("DELETE FROM activity_log WHERE lead_id IN (SELECT id FROM leads WHERE domain_detected = 'Mechanical Engineer')")
    c.execute("DELETE FROM leads WHERE domain_detected = 'Mechanical Engineer'")
    conn.commit()
    print(f"Purged all Mechanical Engineer leads. Rows deleted: {c.rowcount}")

if __name__ == '__main__':
    purge_mechanical()
