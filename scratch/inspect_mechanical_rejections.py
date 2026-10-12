import sqlite3

conn = sqlite3.connect('automator.db')
c = conn.cursor()
c.execute("""
    SELECT id, status, post_text 
    FROM leads 
    WHERE post_text LIKE '%mechanical%' OR post_text LIKE '%get%' OR post_text LIKE '%cad%' 
    ORDER BY id DESC LIMIT 10
""")
rows = c.fetchall()
print(f"Found {len(rows)} Mechanical-related scraped posts:")
for r in rows:
    lead_id, status, text = r
    clean_text = text[:300].replace('\n', ' ')
    safe_text = clean_text.encode('ascii', 'ignore').decode('ascii')
    print(f"\n[ID #{lead_id}] Status: {status}")
    print(f"Text snippet: {safe_text}")
