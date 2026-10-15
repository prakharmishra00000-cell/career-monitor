import sqlite3

conn = sqlite3.connect('automator.db')
c = conn.cursor()

total = c.execute("SELECT count(*) FROM leads").fetchone()[0]
with_wa = c.execute("SELECT count(*) FROM leads WHERE whatsapp_number IS NOT NULL AND length(whatsapp_number) > 5").fetchone()[0]
with_wa_and_direct_url = c.execute("""
    SELECT count(*) FROM leads 
    WHERE whatsapp_number IS NOT NULL AND length(whatsapp_number) > 5
      AND (post_url LIKE '%/jobs/view/%' OR post_url LIKE '%/feed/update/%' OR post_url LIKE '%/posts/%')
""").fetchone()[0]

print(f"Total leads: {total}")
print(f"Leads with WhatsApp number: {with_wa}")
print(f"Leads with WhatsApp number & direct link: {with_wa_and_direct_url}")

print("\nBreakdown by domain (with WhatsApp):")
for r in c.execute("""
    SELECT domain_detected, count(*) FROM leads
    WHERE whatsapp_number IS NOT NULL AND length(whatsapp_number) > 5
    GROUP BY domain_detected
""").fetchall():
    print(f"  {r[0]}: {r[1]}")
