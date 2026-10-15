import sqlite3

conn = sqlite3.connect('automator.db')
c = conn.cursor()

c.execute("SELECT id, domain_detected, recruiter_name, post_text, post_url FROM leads WHERE whatsapp_number IS NOT NULL AND length(whatsapp_number) >= 8")
rows = c.fetchall()

updated = 0
for r in rows:
    lid, current_domain, recruiter, text, url = r
    full = f"{recruiter} {text} {url}".lower()

    # Disqualify generic sales / voice BPO / telecalling
    is_sales_bpo = any(b in full for b in [
        'voice process', 'customer support', 'bpo', 'telecaller', 'telesales',
        'field sales', 'business development executive', 'insurance advisor',
        'sales representative', 'customer care'
    ])
    
    if is_sales_bpo:
        c.execute("UPDATE leads SET domain_detected='Other', status='REJECTED_IRRELEVANT' WHERE id=?", (lid,))
        updated += 1
        continue

    # Re-evaluate proper domain
    is_mech = any(m in full for m in ['mechanical', 'autocad', 'solidworks', 'get', 'trainee engineer', 'maintenance engineer', 'quality engineer', 'production engineer', 'draftsman', 'automobile', 'catia'])
    is_uiux = any(u in full for u in ['ui/ux', 'ui designer', 'ux designer', 'product designer', 'figma', 'user interface', 'user experience', 'visual designer', 'graphic designer'])
    is_web = any(w in full for w in ['web developer', 'frontend', 'backend', 'full stack', 'react', 'laravel', 'wordpress', 'php developer', 'software developer', 'typescript', 'javascript', 'html', 'next.js', 'django'])
    is_ai = any(a in full for a in ['prompt engineer', 'generative ai', 'machine learning', 'data science', 'ai developer', 'artificial intelligence', 'nlp', 'computer vision', 'deep learning', 'llm'])

    new_domain = current_domain
    if is_mech:
        new_domain = 'Mechanical Engineer'
    elif is_uiux:
        new_domain = 'UI/UX Designer'
    elif is_web:
        new_domain = 'Web Developer'
    elif is_ai:
        new_domain = 'Prompt Engineer'
    
    if new_domain != current_domain:
        c.execute("UPDATE leads SET domain_detected=? WHERE id=?", (new_domain, lid))
        updated += 1

conn.commit()
print(f"Domain classifications cleaned up. Updated {updated} leads.")

# Print breakdown of verified leads with WhatsApp
print("\n--- Current Verified WhatsApp Leads by Domain ---")
c.execute("""
    SELECT domain_detected, count(*) FROM leads 
    WHERE domain_detected IN ('UI/UX Designer', 'Prompt Engineer', 'Web Developer', 'Mechanical Engineer')
      AND whatsapp_number IS NOT NULL AND length(whatsapp_number) >= 8
      AND status NOT LIKE 'REJECTED%'
    GROUP BY domain_detected
""")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")

total_clean = c.execute("""
    SELECT count(*) FROM leads 
    WHERE domain_detected IN ('UI/UX Designer', 'Prompt Engineer', 'Web Developer', 'Mechanical Engineer')
      AND whatsapp_number IS NOT NULL AND length(whatsapp_number) >= 8
      AND status NOT LIKE 'REJECTED%'
""").fetchone()[0]
print(f"Total qualified leads with WhatsApp: {total_clean}")
