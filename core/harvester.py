import urllib.request
import urllib.parse
import re
import time
import sys
sys.path.append('.')
from bs4 import BeautifulSoup
from core.database import insert_lead, is_post_processed, get_connection

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
}

# Matches +91 9876543210, +91-98765-43210, 98765 43210, 9876543210, 09876543210
PHONE_REGEX = re.compile(r'(?:(?:\+?91[\s\-]?)?|0?)[6789]\d{2}[\s\-]?\d{3}[\s\-]?\d{4}')

EXPANDED_QUERIES = [
    # Mechanical Engineer (Freshers / Trainees / GET)
    {"domain": "Mechanical Engineer", "query": "Mechanical Fresher WhatsApp", "location": "India"},
    {"domain": "Mechanical Engineer", "query": "Mechanical Trainee WhatsApp", "location": "India"},
    {"domain": "Mechanical Engineer", "query": "Graduate Engineer Trainee Mechanical WhatsApp", "location": "India"},
    {"domain": "Mechanical Engineer", "query": "Mechanical Fresher Walk-in WhatsApp", "location": "Pune"},
    {"domain": "Mechanical Engineer", "query": "Mechanical Fresher HR phone", "location": "Chennai"},
    {"domain": "Mechanical Engineer", "query": "GET Mechanical Fresher contact", "location": "India"},
    {"domain": "Mechanical Engineer", "query": "Mechanical Quality Fresher WhatsApp", "location": "India"},
    {"domain": "Mechanical Engineer", "query": "Mechanical Production Trainee WhatsApp", "location": "Ahmedabad"},
    {"domain": "Mechanical Engineer", "query": "Mechanical Design Fresher WhatsApp", "location": "India"},
    {"domain": "Mechanical Engineer", "query": "AutoCAD Mechanical Fresher contact", "location": "India"},
    {"domain": "Mechanical Engineer", "query": "Junior Mechanical Engineer WhatsApp", "location": "Mumbai"},

    # UI/UX Designer (Freshers / Interns / Trainees)
    {"domain": "UI/UX Designer", "query": "UI UX Fresher WhatsApp", "location": "India"},
    {"domain": "UI/UX Designer", "query": "UI UX Designer Intern WhatsApp", "location": "India"},
    {"domain": "UI/UX Designer", "query": "UI UX Trainee WhatsApp", "location": "India"},
    {"domain": "UI/UX Designer", "query": "UI UX Fresher hiring WhatsApp", "location": "Bangalore"},
    {"domain": "UI/UX Designer", "query": "Figma Fresher WhatsApp", "location": "India"},
    {"domain": "UI/UX Designer", "query": "Product Design Intern WhatsApp", "location": "India"},
    {"domain": "UI/UX Designer", "query": "Junior UI Designer contact WhatsApp", "location": "Delhi"},
    {"domain": "UI/UX Designer", "query": "Graphic UI Fresher WhatsApp", "location": "India"},
    {"domain": "UI/UX Designer", "query": "UI UX Intern phone", "location": "Mumbai"},
    {"domain": "UI/UX Designer", "query": "UI UX Designer Fresher walk in", "location": "India"},

    # Web Developer (Freshers / Interns / Trainees)
    {"domain": "Web Developer", "query": "Web Developer Fresher WhatsApp", "location": "India"},
    {"domain": "Web Developer", "query": "Frontend Developer Fresher WhatsApp", "location": "India"},
    {"domain": "Web Developer", "query": "Frontend Intern WhatsApp", "location": "Bangalore"},
    {"domain": "Web Developer", "query": "React Developer Fresher WhatsApp", "location": "India"},
    {"domain": "Web Developer", "query": "Full Stack Fresher WhatsApp", "location": "Noida"},
    {"domain": "Web Developer", "query": "Python Developer Fresher WhatsApp", "location": "India"},
    {"domain": "Web Developer", "query": "Web Developer Intern contact WhatsApp", "location": "Pune"},
    {"domain": "Web Developer", "query": "Junior Web Developer WhatsApp", "location": "India"},
    {"domain": "Web Developer", "query": "PHP Developer Fresher WhatsApp", "location": "Ahmedabad"},
    {"domain": "Web Developer", "query": "HTML CSS Developer Fresher WhatsApp", "location": "India"},

    # Prompt Engineer / Generative AI / ML Interns
    {"domain": "Prompt Engineer", "query": "Prompt Engineer Fresher WhatsApp", "location": "India"},
    {"domain": "Prompt Engineer", "query": "Generative AI Intern WhatsApp", "location": "India"},
    {"domain": "Prompt Engineer", "query": "AI Intern WhatsApp", "location": "Bangalore"},
    {"domain": "Prompt Engineer", "query": "AI ML Fresher WhatsApp", "location": "India"},
    {"domain": "Prompt Engineer", "query": "Machine Learning Intern WhatsApp", "location": "India"},
    {"domain": "Prompt Engineer", "query": "AI Trainee WhatsApp", "location": "Hyderabad"},
    {"domain": "Prompt Engineer", "query": "Data Science Fresher WhatsApp", "location": "India"},
    {"domain": "Prompt Engineer", "query": "AI Engineer Fresher contact", "location": "India"},
    {"domain": "Prompt Engineer", "query": "LLM Intern WhatsApp", "location": "India"},
    {"domain": "Prompt Engineer", "query": "Data Analyst Fresher WhatsApp", "location": "India"}
]

def search_guest_jobs(keyword, location="India", start=0):
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={urllib.parse.quote(keyword)}&location={urllib.parse.quote(location)}&start={start}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            jobs = []
            for li in soup.find_all('li'):
                link = li.find('a', class_='base-card__full-link')
                title = li.find('h3', class_='base-search-card__title')
                comp = li.find('h4', class_='base-search-card__subtitle')
                if link and title:
                    href = link.get('href', '').split('?')[0]
                    t = title.get_text(strip=True)
                    c = comp.get_text(strip=True) if comp else 'Recruiter'
                    jobs.append({'title': t, 'company': c, 'url': href})
            return jobs
    except Exception:
        return []

def fetch_job_details(job_url):
    req = urllib.request.Request(job_url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            desc = soup.find('div', class_='show-more-less-html__markup')
            text = desc.get_text('\n', strip=True) if desc else soup.get_text('\n', strip=True)
            return text
    except Exception:
        return ""

def clean_phone_number(raw: str) -> str:
    digits = re.sub(r'[^0-9]', '', raw)
    if digits.startswith('91') and len(digits) == 12:
        return digits[2:]
    if len(digits) == 11 and digits.startswith('0'):
        return digits[1:]
    if len(digits) == 10:
        return digits
    if len(digits) > 10:
        return digits[-10:]
    return raw

def harvest_until_target(target_total_with_wa: int = 105):
    with get_connection() as conn:
        c = conn.cursor()
        current_count = c.execute("SELECT count(*) FROM leads WHERE whatsapp_number IS NOT NULL AND length(whatsapp_number) > 5").fetchone()[0]

    print(f"[Harvester] Current leads with WhatsApp: {current_count} | Target: {target_total_with_wa}", flush=True)
    if current_count >= target_total_with_wa:
        print(f"[Harvester] Target already reached! ({current_count} >= {target_total_with_wa})", flush=True)
        return

    fresher_cues = ["fresher", "freshers", "intern", "internship", "trainee", "entry level", "student", "college", "2026", "2027", "2028", "junior", "campus", "get", "0-1", "0-2", "0 year", "apprentice"]
    senior_disqualifiers = ["3+ year", "4+ year", "5+ year", "6+ year", "7+ year", "8+ year", "10+ year", "lead architect", "senior architect", "principal", "manager"]

    new_saved = 0
    for target in EXPANDED_QUERIES:
        domain = target["domain"]
        query = target["query"]
        loc = target.get("location", "India")
        print(f"\n[Harvester] Searching: '{query}' in {loc} ({domain})...", flush=True)

        for page_start in [0, 10, 20, 30]:
            jobs = search_guest_jobs(query, location=loc, start=page_start)
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

                # Check freshers eligibility
                is_fresher = any(f in full_lower for f in fresher_cues)
                is_senior = any(s in full_lower for s in senior_disqualifiers)
                if not is_fresher or is_senior:
                    continue

                # Extract phone / WhatsApp
                phones = PHONE_REGEX.findall(desc)
                if not phones:
                    # Also check title or header
                    phones = PHONE_REGEX.findall(full_content)
                if not phones:
                    continue

                whatsapp_num = clean_phone_number(phones[0])
                if len(whatsapp_num) < 10:
                    continue

                job_type = "internship" if "intern" in full_lower else "job"
                is_paid = 0 if ("unpaid" in full_lower or "no stipend" in full_lower) else 1

                wa_pitch = (
                    f"Hi {company} Hiring Team! I saw your {job_title} opening on LinkedIn ({job_url}). "
                    f"I am Prakhar Mishra, specialized in {domain} (Portfolio: https://prakharmishra.dev). "
                    f"I would love to submit my profile for this fresher position. Thank you!"
                )

                lead_data = {
                    "post_id": post_id,
                    "post_url": job_url,
                    "recruiter_name": company,
                    "recruiter_profile_url": "", # Zero profile links
                    "post_text": desc[:1500],
                    "job_type": job_type,
                    "is_paid": is_paid,
                    "domain_detected": domain,
                    "relevance_score": 0.96,
                    "recruiter_instructions": f"Direct Recruiter WhatsApp: +91 {whatsapp_num}",
                    "whatsapp_number": whatsapp_num,
                    "requires_comment": 0,
                    "comment_text": "",
                    "pitch_message": wa_pitch,
                    "connection_note": f"Hi, interested in the {job_title} opportunity at {company}!",
                    "whatsapp_pitch": wa_pitch,
                    "status": "DISCOVERED",
                    "comment_status": "NONE",
                    "whatsapp_status": "PENDING"
                }

                if insert_lead(lead_data):
                    new_saved += 1
                    current_count += 1
                    print(f"  [+] #{current_count}: {domain} | {company} | WA: +91 {whatsapp_num} | {job_url}", flush=True)

                time.sleep(1.0)

                if current_count >= target_total_with_wa:
                    print(f"\n[Harvester] SUCCESS! Reached target of {current_count} verified WhatsApp leads!", flush=True)
                    return

            time.sleep(1.2)

    print(f"\n[Harvester] Completed sweep. Total with WhatsApp: {current_count}", flush=True)

if __name__ == '__main__':
    harvest_until_target(target_total_with_wa=105)
