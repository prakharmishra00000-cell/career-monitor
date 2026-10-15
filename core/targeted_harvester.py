import sys
sys.path.append('.')
from core.harvester import search_guest_jobs, fetch_job_details, clean_phone_number, PHONE_REGEX
from core.database import insert_lead, is_post_processed, get_connection
import re
import time

TARGET_QUERIES = [
    # Mechanical
    ("Mechanical Engineer", "Mechanical Engineer Fresher walk in"),
    ("Mechanical Engineer", "Diploma Mechanical Fresher contact"),
    ("Mechanical Engineer", "BE Mechanical Fresher WhatsApp"),
    ("Mechanical Engineer", "Mechanical Site Engineer Fresher contact"),
    ("Mechanical Engineer", "SolidWorks Mechanical Fresher contact"),
    ("Mechanical Engineer", "CAD Engineer Fresher contact"),
    ("Mechanical Engineer", "Mechanical Maintenance Fresher WhatsApp"),
    ("Mechanical Engineer", "Mechanical Engineer Fresher placement"),
    ("Mechanical Engineer", "HVAC Fresher Mechanical contact"),
    ("Mechanical Engineer", "Automobile Mechanical Fresher contact"),

    # UI/UX
    ("UI/UX Designer", "UI UX Designer Fresher hiring"),
    ("UI/UX Designer", "UI Designer Fresher contact"),
    ("UI/UX Designer", "Web and Graphic Designer Fresher WhatsApp"),
    ("UI/UX Designer", "Junior UI Designer Fresher contact"),
    ("UI/UX Designer", "UI UX Intern walk in"),
    ("UI/UX Designer", "Figma UI UX Fresher contact"),
    ("UI/UX Designer", "Product Designer Intern contact"),
    ("UI/UX Designer", "User Experience Designer Fresher WhatsApp"),
    ("UI/UX Designer", "Visual Designer Fresher WhatsApp"),
    ("UI/UX Designer", "UI Developer Fresher contact"),

    # Web Dev
    ("Web Developer", "Frontend Fresher contact"),
    ("Web Developer", "HTML CSS Fresher contact"),
    ("Web Developer", "JavaScript Fresher WhatsApp"),
    ("Web Developer", "Junior Web Developer Fresher contact"),
    ("Web Developer", "Full Stack Intern WhatsApp"),
    ("Web Developer", "Web Developer Trainee contact"),
    ("Web Developer", "React JS Fresher contact"),
    ("Web Developer", "Node JS Developer Fresher contact"),
    ("Web Developer", "Software Developer Fresher contact"),
    ("Web Developer", "Python Intern contact WhatsApp"),

    # Prompt Engineer / AI
    ("Prompt Engineer", "AI Prompt Engineer Fresher"),
    ("Prompt Engineer", "Generative AI Trainee contact"),
    ("Prompt Engineer", "Junior AI Engineer Fresher"),
    ("Prompt Engineer", "Machine Learning Fresher contact"),
    ("Prompt Engineer", "Data Science Trainee WhatsApp"),
    ("Prompt Engineer", "Python AI Fresher contact"),
    ("Prompt Engineer", "Deep Learning Intern WhatsApp"),
    ("Prompt Engineer", "Computer Vision Intern contact"),
    ("Prompt Engineer", "NLP Fresher contact"),
    ("Prompt Engineer", "Artificial Intelligence Intern contact")
]

fresher_cues = ["fresher", "freshers", "intern", "internship", "trainee", "entry level", "student", "college", "2026", "2027", "2028", "junior", "campus", "get", "0-1", "0-2", "0 year", "apprentice"]
senior_disqualifiers = ["3+ year", "4+ year", "5+ year", "6+ year", "7+ year", "8+ year", "10+ year", "lead architect", "senior architect", "principal", "manager"]

def run_targeted_harvest(target_total_wa: int = 105):
    with get_connection() as conn:
        c = conn.cursor()
        current = c.execute("SELECT count(*) FROM leads WHERE whatsapp_number IS NOT NULL AND length(whatsapp_number) > 5").fetchone()[0]

    print(f"Current leads with WhatsApp: {current} | Goal: {target_total_wa}", flush=True)
    if current >= target_total_wa:
        print("Goal already reached!", flush=True)
        return

    for domain, query in TARGET_QUERIES:
        print(f"\nQuerying: '{query}' ({domain})...", flush=True)
        for start_idx in [0, 10, 20]:
            jobs = search_guest_jobs(query, location="India", start=start_idx)
            if not jobs:
                break

            for j in jobs:
                job_url = j['url']
                job_title = j['title']
                company = j['company']

                post_id_match = re.search(r'-(\d+)$', job_url) or re.search(r'/jobs/view/.*?(\d+)', job_url)
                post_id = f"job_{post_id_match.group(1)}" if post_id_match else f"job_{abs(hash(job_url))}"

                if is_post_processed(post_id):
                    continue

                desc = fetch_job_details(job_url)
                if not desc:
                    continue

                full_content = f"{job_title}\n{company}\n{desc}"
                full_lower = full_content.lower()

                # Fresher gate
                if not any(f in full_lower for f in fresher_cues) or any(s in full_lower for s in senior_disqualifiers):
                    continue

                # Phone extraction
                phones = PHONE_REGEX.findall(desc) or PHONE_REGEX.findall(full_content)
                if not phones:
                    continue

                # Filter out pure requisition IDs (Apple/Amazon internal numbers that don't look like phone numbers)
                wa_candidate = clean_phone_number(phones[0])
                if len(wa_candidate) != 10 or not wa_candidate[0] in ['6', '7', '8', '9']:
                    continue

                wa_pitch = (
                    f"Hi {company} Hiring Team! I saw your {job_title} opening on LinkedIn ({job_url}). "
                    f"I am Prakhar Mishra, specialized in {domain} (Portfolio: https://prakharmishra.dev). "
                    f"I would love to apply for this fresher role. Thank you!"
                )

                lead_data = {
                    "post_id": post_id,
                    "post_url": job_url,
                    "recruiter_name": company,
                    "recruiter_profile_url": "", # Strictly NO profile link
                    "post_text": desc[:1500],
                    "job_type": "internship" if "intern" in full_lower else "job",
                    "is_paid": 0 if ("unpaid" in full_lower or "no stipend" in full_lower) else 1,
                    "domain_detected": domain,
                    "relevance_score": 0.98,
                    "recruiter_instructions": f"Direct Recruiter WhatsApp: +91 {wa_candidate}",
                    "whatsapp_number": wa_candidate,
                    "requires_comment": 0,
                    "comment_text": "",
                    "pitch_message": wa_pitch,
                    "connection_note": f"Hi, interested in {job_title} at {company}!",
                    "whatsapp_pitch": wa_pitch,
                    "status": "DISCOVERED",
                    "comment_status": "NONE",
                    "whatsapp_status": "PENDING"
                }

                if insert_lead(lead_data):
                    current += 1
                    print(f"  [+] #{current}: {domain} | {company} | WA: +91 {wa_candidate} | {job_url}", flush=True)

                time.sleep(1.0)
                if current >= target_total_wa:
                    print(f"\n[TARGET REACHED] Reached {current} verified WhatsApp leads!", flush=True)
                    return

            time.sleep(1.2)

    print(f"\nHarvest finished. Total leads with WhatsApp: {current}", flush=True)

if __name__ == '__main__':
    run_targeted_harvest(target_total_wa=105)
