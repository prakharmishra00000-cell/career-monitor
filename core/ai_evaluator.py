import json
import os
import re
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# Pre-compiled Regex for Phone/WhatsApp numbers
PHONE_REGEX = re.compile(
    r'(?:(?:\+|00)[1-9]\d{0,3}[\s\-\.]?)?(?:\(?\d{2,5}\)?[\s\-\.]?)?\d{3,5}[\s\-\.]?\d{3,5}'
)
WHATSAPP_KEYWORDS = ["whatsapp", "wa.me", "ping on", "reach out on", "contact on", "dm or wa", "text on"]

def load_profile() -> Dict[str, Any]:
    profile_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "portfolio_profile.json")
    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Warning] Failed to load profile: {e}")
        return {}

def extract_potential_phone_number(text: str) -> Optional[str]:
    """Extracts phone number, prioritizing proximity to WhatsApp keywords."""
    lowered = text.lower()
    for kw in WHATSAPP_KEYWORDS:
        if kw in lowered:
            idx = lowered.find(kw)
            chunk = text[max(0, idx - 20) : min(len(text), idx + 80)]
            matches = PHONE_REGEX.findall(chunk)
            for m in matches:
                clean_digits = re.sub(r'\D', '', m)
                if 10 <= len(clean_digits) <= 15:
                    return clean_digits

    # Fallback to general phone match
    matches = PHONE_REGEX.findall(text)
    for m in matches:
        clean_digits = re.sub(r'\D', '', m)
        if 10 <= len(clean_digits) <= 15:
            return clean_digits
    return None

def heuristic_check_paid(text: str) -> bool:
    """Fast heuristic check to detect unpaid markers."""
    lowered = text.lower()
    unpaid_markers = [
        "unpaid", "un-paid", "non-paid", "without stipend", "no stipend", 
        "free internship", "volunteer", "experience only", "equity only", "college credit only"
    ]
    for marker in unpaid_markers:
        if marker in lowered:
            return False
    return True

SYSTEM_PROMPT = """
You are an expert AI Job Evaluator and Career Agent.
Your job is to analyze recruitment posts on LinkedIn deeply and personalize high-converting outreach messages.

CANDIDATE PROFILE:
{profile_json}

CRITICAL ROLE-SPECIFIC RULE (STRICT ENFORCEMENT):
- Detect the EXACT single primary job role the recruiter is hiring for:
  • "UI/UX Designer" OR
  • "Prompt Engineer" OR
  • "Web Developer" OR
  • "Mechanical Engineer"
- ALL generated messages ("pitch_message", "connection_note", "comment_text", "whatsapp_pitch") MUST FOCUS 100% EXCLUSIVELY on that single role!
- ABSOLUTE PROHIBITION: NEVER list multiple unrelated roles together. 
  - If the role is for UI/UX Designer: Talk ONLY about UI/UX design, Figma, design systems, prototypes, and user interfaces.
  - If the role is for Prompt Engineer: Talk ONLY about prompt engineering, LLMs, structured outputs, agent workflows, and Gemini API.
  - If the role is for Web Developer: Talk ONLY about full-stack web development, rapid vibe coding, Next.js, React, and building production web applications.
  - If the role is for Mechanical Engineer: Talk ONLY about mechanical engineering, CAD/SolidWorks, product design, manufacturing fundamentals, and entry-level engineering.

RULES:
1. Target Domains:
   - UI/UX Design (Figma, UX research, Design systems, mobile/web interfaces)
   - Prompt Engineering & Generative AI (LLM workflows, agents, system prompt architecture)
   - Web Development / Vibe Coding (Fast, modern full-stack dev with Next.js, React, Tailwind)
   - Mechanical Engineering (Design, CAD, SolidWorks, Graduate Engineer Trainee, Manufacturing, R&D)
   If the post does NOT belong to any of these domains, mark is_relevant=false.

2. Experience & Seniority Filter:
   - TARGET CANDIDATE IS A FRESHER / 2027 BATCH / COLLEGE STUDENT / JUNIOR.
   - General roles: Reject posts requiring 3+ to 5+ years senior experience.

3. MECHANICAL 2027 BATCH STRICT ELIGIBILITY FILTER (ABSOLUTE ENFORCEMENT):
   - For all Mechanical Engineering posts:
     * MUST ALLOW ACTIVE BACKLOGS OR HAVE NO RESTRICTION ON BACKLOGS.
     * MUST NOT DEMAND A MINIMUM CGPA OR PERCENTAGE CUTOFF (e.g. Reject if post mentions "no active backlogs", "zero backlogs", "min 60%", "min 65%", "min 70%", "min 75%", "7.0 CGPA", "7.5 CGPA", "8.0 CGPA", etc.).
     * ABSOLUTE REJECTION: If a Mechanical post says "No backlogs allowed", "Strictly no active backlogs", "Minimum 60%/70%/75%", or "6.5+ CGPA required", you MUST set is_relevant=false!
     * ONLY ACCEPT if the recruiter explicitly states "active backlogs allowed", "backlogs allowed", "no percentage criteria", "no CGPA criteria", "evaluated purely on technical test/skills", OR has zero criteria on marks/backlogs.

4. Compensation Filter:
   - Must be PAID (paid full-time/part-time job OR paid internship).
   - If the post states "unpaid", "no stipend", "free", or lacks any compensation for an internship, mark is_paid=false.

3. Recruiter Instructions Detection:
   - Check if recruiter explicitly asked readers to comment (e.g. "Comment 'Interested' below", "Comment with your portfolio link", "Drop your resume in comments").
   - If yes, set requires_comment=true.

4. Contact Extraction:
   - Extract any WhatsApp or phone number explicitly provided for candidates to reach out.

5. Personalized Messages to Generate (Role Specific):
   - "pitch_message": High-impact, tailored pitch focusing ONLY on the specific role requested.
   - "connection_note": Short, punchy connection request note under 280 characters focusing ONLY on the specific role requested.
   - "comment_text": If requires_comment is true, write a polished comment highlighting candidate's expertise in THAT specific role and attaching portfolio ({portfolio_url}).
   - "whatsapp_pitch": If a WhatsApp number is found, write a crisp, professional WhatsApp chat message referencing THAT specific job opening and portfolio link.

Return strictly valid JSON matching this schema:
{{
  "is_relevant": true|false,
  "domain_detected": "UI/UX Designer" | "Prompt Engineer" | "Web Developer" | "Mechanical Engineer" | "Other",
  "relevance_score": 0.0 to 1.0,
  "job_type": "job" | "internship" | "freelance" | "trainee",
  "is_paid": true|false,
  "recruiter_instructions": "string or none",
  "whatsapp_number": "string or null",
  "requires_comment": true|false,
  "pitch_message": "string",
  "connection_note": "string (under 280 chars)",
  "comment_text": "string",
  "whatsapp_pitch": "string"
}}
"""

def analyze_post(post_text: str, recruiter_name: str = "") -> Dict[str, Any]:
    profile = load_profile()
    portfolio_url = profile.get("portfolio_url", "https://yashportfolio.dev")
    extracted_wa = extract_potential_phone_number(post_text)

    # First check API key
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and api_key != "your_gemini_api_key_here":
        try:
            # Check modern google-genai SDK
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                formatted_prompt = SYSTEM_PROMPT.format(
                    profile_json=json.dumps(profile, indent=2),
                    portfolio_url=portfolio_url
                )
                user_content = f"RECRUITER NAME: {recruiter_name}\n\nPOST CONTENT:\n{post_text}"
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[formatted_prompt, user_content],
                    config={"response_mime_type": "application/json"}
                )
                result = json.loads(response.text)
                if not result.get("whatsapp_number") and extracted_wa:
                    result["whatsapp_number"] = extracted_wa
                return result
            except ImportError:
                # Try google.generativeai legacy package
                import google.generativeai as gai
                gai.configure(api_key=api_key)
                model = gai.GenerativeModel("gemini-1.5-flash")
                formatted_prompt = SYSTEM_PROMPT.format(
                    profile_json=json.dumps(profile, indent=2),
                    portfolio_url=portfolio_url
                )
                user_content = f"RECRUITER NAME: {recruiter_name}\n\nPOST CONTENT:\n{post_text}"
                resp = model.generate_content([formatted_prompt, user_content])
                clean_text = resp.text.strip()
                if clean_text.startswith("```"):
                    clean_text = clean_text.split("\n", 1)[1].rsplit("\n", 1)[0]
                result = json.loads(clean_text)
                if not result.get("whatsapp_number") and extracted_wa:
                    result["whatsapp_number"] = extracted_wa
                return result
        except Exception as e:
            print(f"[AI Evaluator] Gemini API error, falling back to local heuristic evaluator: {e}")

    # Robust Local Heuristic Evaluator (runs even if no API key is provided)
    is_paid = heuristic_check_paid(post_text)
    lowered = post_text.lower()

    # Strict single-domain detection
    domain = "Other"
    relevance_score = 0.0
    if any(k in lowered for k in ["ui/ux", "ui ux", "product designer", "figma", "user experience", "ux designer", "ui designer"]):
        domain = "UI/UX Designer"
        relevance_score = 0.95
    elif any(k in lowered for k in ["prompt engineer", "prompt engineering", "generative ai", "llm", "ai agent"]):
        domain = "Prompt Engineer"
        relevance_score = 0.95
    elif any(k in lowered for k in ["vibe coding", "web develop", "frontend", "full stack", "fullstack", "react", "next.js", "software engineer"]):
        domain = "Web Developer"
        relevance_score = 0.90
    elif any(k in lowered for k in ["mechanical engineer", "mechanical engineering", "cad", "solidworks", "get mechanical", "graduate engineer trainee", "mechanical fresher", "autocad"]):
        # Check strict negative criteria for Mechanical:
        # If post explicitly demands no backlogs or minimum percentage, reject immediately!
        no_backlog_markers = ["no active backlogs", "no backlogs", "zero backlogs", "without backlogs", "cleared all backlogs"]
        min_cgpa_markers = ["min 60%", "min 65%", "min 70%", "min 75%", "minimum 60%", "minimum 65%", "minimum 70%", "minimum 75%", "6.0 cgpa", "6.5 cgpa", "7.0 cgpa", "7.5 cgpa", "8.0 cgpa", "60% throughout", "70% throughout", "75% throughout"]

        has_no_backlog_rule = any(m in lowered for m in no_backlog_markers)
        has_min_cgpa_rule = any(m in lowered for m in min_cgpa_markers)

        if has_no_backlog_rule or has_min_cgpa_rule:
            domain = "Other"
            relevance_score = 0.0
        else:
            domain = "Mechanical Engineer"
            relevance_score = 0.95

    is_relevant = relevance_score >= 0.8
    is_internship = any(k in lowered for k in ["intern", "internship", "trainee", "stipend"])
    job_type = "internship" if is_internship else "job"

    # Comment requirement
    requires_comment = any(k in lowered for k in [
        "comment below", "comment 'interested'", "drop your portfolio", 
        "drop portfolio", "drop resume", "comment your email", "comment below with"
    ])

    greeting_name = recruiter_name.split()[0] if recruiter_name else "there"
    my_name = profile.get("full_name", "Prakhar Mishra")

    # Generate strictly role-specific messages
    if domain == "Mechanical Engineer":
        pitch = (
            f"Hi {greeting_name},\n\n"
            f"I came across your post for the Mechanical Engineering {job_type} opportunity and wanted to reach out. "
            f"I have a strong foundation in mechanical design, CAD modeling, and engineering problem-solving.\n\n"
            f"Key competencies:\n"
            f"• 3D CAD modeling, drafting, and tolerance analysis using SolidWorks & AutoCAD\n"
            f"• Core fundamentals in design analysis, materials, and manufacturing processes\n"
            f"• Eager to contribute directly in hands-on engineering, product development, or manufacturing operations\n\n"
            f"I am available to join and contribute immediately. Would you be open to connecting for a quick discussion?"
        )
        connection_note = (
            f"Hi {greeting_name}, saw your Mechanical Engineering opening! Strong foundation in CAD design, SolidWorks, and core engineering principles. Eager to contribute immediately. Would love to connect!"
        )[:280]
        comment = (
            f"Hi {greeting_name}, very interested in this Mechanical Engineering {job_type}! Solid foundation in CAD modeling and mechanical design principles. Looking forward to connecting and sharing my resume."
        )
        wa_pitch = (
            f"Hello {greeting_name}, I saw your LinkedIn post for the Mechanical Engineering {job_type}. "
            f"I specialize in CAD modeling, SolidWorks, and mechanical design. Best regards, {my_name} (+91 6372843175)"
        )
    elif domain == "UI/UX Designer":
        pitch = (
            f"Hi {greeting_name},\n\n"
            f"I came across your post for the UI/UX Designer {job_type} and was immediately drawn to the role. "
            f"As a UI/UX and Product Designer, I focus on crafting clean, intuitive, and accessible user experiences that convert.\n\n"
            f"My work centers on:\n"
            f"• Designing comprehensive Figma design systems, wireframes, and interactive prototypes\n"
            f"• Structuring responsive layouts with slick micro-interactions and friction-free user journeys\n"
            f"• Turning complex product requirements into elegant, usable digital interfaces\n\n"
            f"You can explore my design systems, prototypes, and case studies on my live portfolio: {portfolio_url}\n\n"
            f"I would love to bring high-velocity design execution to your team. Are you open to a brief chat?"
        )
        connection_note = (
            f"Hi {greeting_name}, noticed your UI/UX Designer {job_type} opening! I specialize in Figma design systems, user flows & intuitive web/mobile UI. Portfolio: {portfolio_url}. Would love to connect and discuss!"
        )[:280]
        comment = (
            f"Hi {greeting_name}, strongly interested in this UI/UX Designer {job_type}! I specialize in Figma design systems, modern interface design, and friction-free user experiences. Explore my design portfolio here: {portfolio_url}. Looking forward to connecting!"
        )
        wa_pitch = (
            f"Hello {greeting_name}, I saw your LinkedIn post for the UI/UX Designer {job_type} opening. "
            f"I specialize in UI/UX design, Figma design systems, and responsive user interfaces. "
            f"Here is my live portfolio: {portfolio_url}. Best regards, {my_name} (+91 6372843175)"
        )
    elif domain == "Prompt Engineer":
        pitch = (
            f"Hi {greeting_name},\n\n"
            f"I came across your post for the Prompt Engineer {job_type} and resonated with your requirements. "
            f"I specialize in prompt engineering, LLM orchestration, and architecting production-grade generative AI workflows.\n\n"
            f"My focus areas include:\n"
            f"• Crafting resilient system prompts, structured JSON outputs, and multi-step reasoning chains\n"
            f"• Integrating Google Gemini and OpenAI models into autonomous agent workflows\n"
            f"• Building AI intelligence systems (like ExamIntel, an analytical platform with 17 Gemini-powered AI features)\n\n"
            f"You can review my AI implementations and live projects on my portfolio: {portfolio_url}\n\n"
            f"I'd love to discuss how I can help optimize your AI pipelines. Would you be open to a quick conversation?"
        )
        connection_note = (
            f"Hi {greeting_name}, saw your Prompt Engineer {job_type} opening! I build resilient system prompts, structured outputs & multi-agent architectures (Gemini/OpenAI). Portfolio: {portfolio_url}. Would love to connect!"
        )[:280]
        comment = (
            f"Hi {greeting_name}, very interested in this Prompt Engineer {job_type}! I specialize in structured prompt engineering, LLM agent pipelines, and Gemini API integration. Check out my live AI projects here: {portfolio_url}. Looking forward to connecting!"
        )
        wa_pitch = (
            f"Hello {greeting_name}, I saw your LinkedIn post regarding the Prompt Engineer {job_type} opening. "
            f"I specialize in prompt optimization, LLM agents, and structured outputs. "
            f"Live portfolio: {portfolio_url}. Best regards, {my_name} (+91 6372843175)"
        )
    else:  # Web Developer
        pitch = (
            f"Hi {greeting_name},\n\n"
            f"I saw your post for the Web Developer {job_type} and wanted to reach out. "
            f"I'm a Full-Stack Web Developer specialized in rapid vibe coding, shipping production-grade web applications at speed.\n\n"
            f"My technical stack & recent work:\n"
            f"• Building fast, responsive applications using Next.js, React, TypeScript, and Tailwind CSS\n"
            f"• Architecting robust APIs, seamless state management, and continuous Vercel deployments\n"
            f"• Developed CareerHub AI, a real-time discovery engine indexing 50K+ live opportunities across 9+ sources\n\n"
            f"You can explore my live applications, case studies, and GitHub code at: {portfolio_url}\n\n"
            f"I'd love to deliver fast, scalable solutions for your codebase. Are you available for a quick chat?"
        )
        connection_note = (
            f"Hi {greeting_name}, noticed your Web Developer {job_type} opening! I build fast, production-ready web apps via rapid vibe coding in Next.js & React. Live projects & code: {portfolio_url}. Would love to connect!"
        )[:280]
        comment = (
            f"Hi {greeting_name}, strongly interested in this Web Developer {job_type}! I build production-grade web applications using Next.js, React, and rapid vibe coding. Explore CareerHub AI and my live projects at: {portfolio_url}. Looking forward to discussing!"
        )
        wa_pitch = (
            f"Hello {greeting_name}, I saw your LinkedIn post for the Web Developer {job_type} opening. "
            f"I build modern full-stack web applications using Next.js, React, and rapid vibe coding. "
            f"Live portfolio & GitHub: {portfolio_url}. Best regards, {my_name} (+91 6372843175)"
        )

    return {
        "is_relevant": is_relevant,
        "domain_detected": domain,
        "relevance_score": relevance_score,
        "job_type": job_type,
        "is_paid": is_paid,
        "recruiter_instructions": "Comment or direct reach out requested" if requires_comment else "Direct reach out",
        "whatsapp_number": extracted_wa,
        "requires_comment": requires_comment,
        "pitch_message": pitch,
        "connection_note": connection_note,
        "comment_text": comment,
        "whatsapp_pitch": wa_pitch
    }
