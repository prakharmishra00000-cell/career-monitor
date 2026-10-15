import urllib.request
import urllib.parse
import re
import time
import sys
sys.path.append('.')
from bs4 import BeautifulSoup
from core.database import insert_lead, is_post_processed, get_connection

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
}

PHONE_REGEX = re.compile(r'(?:(?:\+?91[\s\-]?)?|0?)[6789]\d{2}[\s\-]?\d{3}[\s\-]?\d{4}')

SCALE_QUERIES = [
    # Mechanical
    ("Mechanical Engineer", "Mechanical Fresher WhatsApp", "India"),
    ("Mechanical Engineer", "AutoCAD Fresher WhatsApp", "India"),
    ("Mechanical Engineer", "GET Mechanical WhatsApp", "India"),
    ("Mechanical Engineer", "Mechanical Trainee WhatsApp", "Pune"),
    ("Mechanical Engineer", "Mechanical Design Fresher WhatsApp", "Bangalore"),
    ("Mechanical Engineer", "Mechanical Fresher WhatsApp", "Chennai"),
    ("Mechanical Engineer", "Mechanical Engineer Fresher WhatsApp", "Ahmedabad"),
    ("Mechanical Engineer", "Production Engineer Fresher WhatsApp", "India"),
    ("Mechanical Engineer", "Quality Engineer Fresher WhatsApp", "India"),
    ("Mechanical Engineer", "Junior Mechanical Engineer WhatsApp", "Delhi"),

    # UI/UX Designer
    ("UI/UX Designer", "UI UX Fresher WhatsApp", "India"),
    ("UI/UX Designer", "UI UX Intern WhatsApp", "Bangalore"),
    ("UI/UX Designer", "Figma Designer Fresher WhatsApp", "India"),
    ("UI/UX Designer", "Product Designer Fresher WhatsApp", "India"),
    ("UI/UX Designer", "UI UX Trainee WhatsApp", "Mumbai"),
    ("UI/UX Designer", "UI UX Designer WhatsApp", "Pune"),
    ("UI/UX Designer", "Graphic and UI Designer Fresher WhatsApp", "India"),
    ("UI/UX Designer", "UI UX Designer Intern WhatsApp", "Delhi"),
    ("UI/UX Designer", "Junior UX Designer WhatsApp", "India"),
    ("UI/UX Designer", "UI Designer Fresher WhatsApp", "Hyderabad"),

    # Web Developer
    ("Web Developer", "Web Developer Fresher WhatsApp", "India"),
    ("Web Developer", "Frontend Developer Fresher WhatsApp", "Bangalore"),
    ("Web Developer", "React Developer Fresher WhatsApp", "India"),
    ("Web Developer", "Full Stack Fresher WhatsApp", "India"),
    ("Web Developer", "Python Developer Fresher WhatsApp", "Pune"),
    ("Web Developer", "Web Development Intern WhatsApp", "India"),
    ("Web Developer", "Frontend Intern WhatsApp", "Noida"),
    ("Web Developer", "Next JS Developer Fresher WhatsApp", "India"),
    ("Web Developer", "Junior Web Developer WhatsApp", "Mumbai"),
    ("Web Developer", "WordPress Developer Fresher WhatsApp", "India"),

    # Prompt Engineer / Generative AI
    ("Prompt Engineer", "Prompt Engineer Fresher WhatsApp", "India"),
    ("Prompt Engineer", "Generative AI Fresher WhatsApp", "India"),
    ("Prompt Engineer", "AI Intern WhatsApp", "India"),
    ("Prompt Engineer", "Machine Learning Fresher WhatsApp", "Bangalore"),
    ("Prompt Engineer", "AI ML Intern WhatsApp", "Hyderabad"),
    ("Prompt Engineer", "Data Science Fresher WhatsApp", "India"),
    ("Prompt Engineer", "Python AI Intern WhatsApp", "Pune"),
    ("Prompt Engineer", "LLM Fresher WhatsApp", "India"),
    ("Prompt Engineer", "Artificial Intelligence Fresher WhatsApp", "India"),
    ("Prompt Engineer", "AI Trainee WhatsApp", "Noida")
]

def search_jobs(keywords, location="India", start=0):
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={urllib.parse.quote(keywords)}&location={urllib.parse.quote(location)}&start={start}"
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

def get_desc(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            desc = soup.find('div', class_='show-more-less-html__markup')
            return desc.get_text('\n', strip=True) if desc else soup.get_text('\n', strip=True)
    except Exception:
        return ""

def clean_phone(raw):
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

def scale_harvest(target_total: int = 105):
    with get_connection() as conn:
        c = conn.cursor()
        current = c.execute("SELECT count(*) FROM leads WHERE whatsapp_number IS NOT NULL AND length(whatsapp_number) >= 10").fetchone()[0]

    print(f"[Scale Harvester] Starting scale run. Current WhatsApp leads: {current} | Target: {target_total}", flush=True)
    if current >= target_total:
        print(f"[Scale Harvester] Already reached target ({current} >= {target_total})", flush=True)
        return

    fresher_cues = ["fresher", "freshers", "intern", "internship", "trainee", "entry level", "student", "college", "2026", "2027", "2028", "junior", "campus", "get", "0-1", "0-2", "0 year", "apprentice"]
    senior_disqualifiers = ["3+ year", "4+ year", "5+ year", "6+ year", "7+ year", "8+ year", "10+ year", "lead architect", "senior architect", "principal", "manager"]

    for domain, query, loc in SCALE_QUERIES:
        print(f"\n[Scale Harvester] Searching '{query}' in {loc} ({domain})...", flush=True)
        for page_start in [0, 10, 20]:
            jobs = search_jobs(query, location=loc, start=page_start)
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

                desc = get_desc(job_url)
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

                wa_cand = clean_phone(phones[0])
                if len(wa_cand) != 10 or not wa_cand[0] in ['6', '7', '8', '9']:
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
                    "recruiter_instructions": f"Direct Recruiter WhatsApp: +91 {wa_cand}",
                    "whatsapp_number": wa_cand,
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
                    print(f"  [+] #{current}: {domain} | {company} | WA: +91 {wa_cand} | {job_url}", flush=True)

                time.sleep(1.0)
                if current >= target_total:
                    print(f"\n[TARGET REACHED] Reached {current} verified WhatsApp leads!", flush=True)
                    return

            time.sleep(1.2)

    print(f"\n[Scale Harvester] Sweep completed. Total leads with WhatsApp: {current}", flush=True)

if __name__ == '__main__':
    scale_harvest(target_total=105)
