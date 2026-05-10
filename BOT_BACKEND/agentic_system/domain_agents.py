from .crawling_agent import fetch_multiple_urls
from .knowledge_store import ensure_knowledge_store_ready, load_runtime_knowledge_chunks, search_knowledge_store
import os
import asyncio
import time
import re
import json
import unicodedata
from pathlib import Path
from groq import Groq
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

def get_llm_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in .env")
    return Groq(api_key=api_key)

GROQ_MODELS_CASCADE = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "mixtral-8x7b-32768",
    "llama3-70b-8192"
]

async def call_groq_with_retry(messages, model="llama-3.3-70b-versatile", max_tokens=2048, temperature=0.1):
    """Async Groq caller with smart retry and model cascade fallback."""
    client = get_llm_client()
    
    model_cascade = [model] + [m for m in GROQ_MODELS_CASCADE if m != model]
    model_cascade = list(dict.fromkeys(model_cascade))  # deduplicate, preserve order
    
    last_exception = None
    for attempt_model in model_cascade:
        for retry_num in range(2):
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda m=attempt_model: client.chat.completions.create(
                        messages=messages,
                        model=m,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                last_exception = e
                err_str = str(e).lower()
                if "rate_limit" in err_str or "429" in err_str or "rate limit" in err_str:
                    wait_time = 1.5 ** retry_num  # Faster retries
                    print(f"[GROQ RATE LIMIT] Model {attempt_model} hit rate limit. Waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"[GROQ ERROR] Model {attempt_model}: {e}")
                    break  # Non-rate-limit error, try next model
    
    # ---------------------------------------------------------
    # FALLBACK TO GEMINI IF ALL GROQ MODELS FAIL
    # ---------------------------------------------------------
    gemini_key = os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        print(f"[ORCHESTRATOR] Groq failed. Attempting Gemini fallback (Key: {gemini_key[:5]}...)")
        try:
            genai.configure(api_key=gemini_key)
            model_gemini = genai.GenerativeModel("gemini-2.5-flash")
            
            # Format messages for Gemini (Role: user/model)
            gemini_history = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                if msg["role"] == "system":
                    continue # handled below
                gemini_history.append({"role": role, "parts": [msg["content"]]})
            
            # If system msg exists, prepend to first user message
            if messages and messages[0]["role"] == "system":
                # Find first user message or create one
                user_msg_found = False
                for i in range(len(gemini_history)):
                    if gemini_history[i]["role"] == "user":
                        gemini_history[i]["parts"][0] = f"SYSTEM INSTRUCTIONS: {messages[0]['content']}\n\nUSER QUESTION: {gemini_history[i]['parts'][0]}"
                        user_msg_found = True
                        break
                if not user_msg_found:
                    gemini_history.insert(0, {"role": "user", "parts": [f"SYSTEM INSTRUCTIONS: {messages[0]['content']}"]})
            
            response = await asyncio.to_thread(
                model_gemini.generate_content,
                gemini_history
            )
            return response.text.strip()
        except Exception as ge:
            print(f"[GEMINI CRITICAL FAIL] {ge}")
            import traceback
            print(traceback.format_exc())
            
    print(f"[FINAL ORCHESTRATION ERROR] Both Groq and Gemini failed. Last Groq Error: {last_exception}")
    raise last_exception or Exception("All LLM providers (Groq & Gemini) failed. Please try again.")

# The 12 Domains and their mapping to URLs on SVSU website
DOMAIN_MAPPING = {
    "Home": ["https://svsu.ac.in/"],
    "About": ["https://svsu.ac.in/about-us", "https://svsu.ac.in/vision-mission", "https://svsu.ac.in/vice-chancellor"],
    "Academics": ["https://svsu.ac.in/academics", "https://svsu.ac.in/skill-faculty"],
    "Administration": ["https://svsu.ac.in/administration", "https://svsu.ac.in/vice-chancellor", "https://svsu.ac.in/registrar"],
    "Admission": ["https://svsu.ac.in/admission", "https://svsu.ac.in/how-to-apply", "https://svsu.ac.in/admission-schedule", "https://svsu.ac.in/eligibility-norms"],
    "Research": ["https://svsu.ac.in/research", "https://svsu.ac.in/projects"],
    "Student Programs": ["https://svsu.ac.in/student-corner", "https://svsu.ac.in/clubs"],
    "Examination": ["https://svsu.ac.in/examination"],
    "Notices": ["https://svsu.ac.in/tender-notice", "https://svsu.ac.in/office-orders"],
    "Library": ["https://svsu.ac.in/library"],
    "Contact": ["https://svsu.ac.in/contact-us"],
    "Updates": ["https://svsu.ac.in/news-events", "https://svsu.ac.in/announcements"],
}

# Provide slightly different personas for specific domains
AGENT_ROLES = {
    "Admission": "SVSU Admission Verification Specialist. You verify programs, fees, seats, eligibility, and admission rules strictly against official SVSU data. You never guess, rename, or invent unavailable courses.",
    "About": "SVSU Institutional Facts Specialist. You explain the university's identity, leadership, campuses, history, and vision strictly from verified SVSU context.",
    "Updates": "SVSU Dynamic Updates Agent. You continuously monitor recent notices and news to answer the user.",
    "Examination": "SVSU Examination Agent. You handle queries regarding exams, rules, calendars, and result announcements.",
    "Home": "SVSU Universal Knowledge Specialist for 'Others Query' section. You handle general SVSU queries across campus life, leadership, facilities, administration, and university policies strictly from the provided official context."
}

OFFICIAL_CURRENT_PROGRAMS = [
    "B.Tech Electrical Engineering",
    "B.Tech Computer Science & Engineering (AI/ML)",
    "B.Tech Computer Engineering",
    "B.Tech Mechanical and Smart Manufacturing",
    "BCA / BCA (Honours / Honours with Research)",
    "BCA - MCA (Integrated)",
    "BCA",
    "MCA",
    "B.Voc Robotics and Automation",
    "B.Voc Mechatronics",
    "B.Voc Mechanical Manufacturing",
    "B.Voc Solar Technology",
    "B.Voc Management-BPM and Analytics",
    "B.Voc Public Services",
    "B.Voc Medical Laboratory Technology",
    "B.Voc Production-Tool and Die Manufacturing",
    "B.Voc Agriculture",
    "B.Voc Management-Financial Services",
    "B.Voc (Medical Laboratory Technology) Honours with Research",
    "B.Voc (MLT) Honours with Research",
    "BBA",
    "BBA (General)",
    "BBA (Airlines and Airport Management)",
    "BBA - BPM and Analytics (Hons. / Hons. with Research)",
    "BBA in Retail Management",
    "B.Com (Hons. / Hons. with Research)",
    "B.Com (Honors/Research)",
    "B.Sc. Clinical Psychology",
    "B.Sc. (Yoga & Spiritual Science)",
    "B.Sc. Mathematics and Computing (Hons. with Research)",
    "B.Sc. in Mathematics and Computing",
    "Bachelor of Hotel Management",
    "Bachelor in Hotel Management",
    "MBA",
    "MBA (Business Analytics)",
    "MBA (Working Professional)",
    "M.Tech Robotics and Automation",
    "M.Sc. Clinical Psychology",
    "M.Sc Clinical Psychology",
    "M.Sc. MLT (Microbiology)",
    "M.Sc MLT (Microbiology)",
    "M.Sc. Geo-informatics",
    "M.Sc Geo-Informatics",
    "M.A. English",
    "M.Voc Agriculture",
    "M.Voc Entrepreneurship",
    "M.Voc Management Banking & Finance",
    "M.Voc Management-HRM",
    "M.Voc Public Health",
    "PG Diploma in Semiconductor Device Packaging (PGDSDP)",
    "PG Diploma Criminal Forensics",
    "PG Diploma in Airport Operations and Management",
    "PG Diploma Public Policy",
    "Diploma Computer Science and Engineering",
    "Diploma in Computer Science & Engineering",
    "Diploma Computer Generative AI / Cyber Security",
    "Diploma Computer (Generative AI/Cyber Security)",
    "D.Voc Draughtmanship (Civil)",
    "D.Voc Horticulture",
    "D.Voc Mechanical Manufacturing",
    "D.Voc Industrial Electronics",
    "Diploma in Mechanical Engineering",
    "D.Voc Office Management",
    "Undergraduate Diploma in Interior Design",
    "Undergraduate Diploma in Airlines Management",
    "Undergraduate Diploma in Japanese Language",
    "Undergraduate Diploma in German Language",
    "Diploma in Yoga",
    "Diploma in Folk Art Banchari",
    "Diploma in English Language",
    "Undergraduate Certificate in Animation, Multimedia and Graphics",
    "UG Certificate in Animation, Multimedia and Graphics",
    "Undergraduate Certificate in Music (Folk Art - Banchari / Instrumental / Vocal)",
    "UG Certificate in Music (Folk Art)",
    "Undergraduate Certificate in Food Production & Traditional Sweets",
    "Certificate in Housekeeping Associate",
    "Certificate in Loss Prevention",
    "Certificate in Food and Beverages Server"
]

PROGRAM_AVAILABILITY_GUARDRAILS = [
    "Do not claim a standalone B.Tech in Cyber Security unless it explicitly appears in official SVSU data.",
    "Do not claim a standalone B.Voc in Cyber Security unless it explicitly appears in official SVSU data.",
    "Do not claim a standalone B.Tech in Artificial Intelligence and Data Science. The official current B.Tech option is B.Tech Computer Science & Engineering (AI/ML).",
    "Do not claim a standalone B.Voc in Digital Marketing unless it explicitly appears in official SVSU data.",
    "Cyber Security may appear in official SVSU data as a minor/Hons option or inside Diploma Computer (Generative AI/Cyber Security). Do not present that as a standalone B.Tech or B.Voc degree.",
    "For 'best course' questions, never invent courses and never claim one universal best course. Recommend only from the official catalog based on the student's goals.",
]

HINGLISH_HINTS = {
    "kya", "hai", "bhai", "kaunsa", "kon", "konsa", "mein", "kr",
    "bta", "bata", "chahiye", "nhi", "nahin", "acha", "haan"
}

BASE_SOURCE_PRIORITIES = {
    "CUSTOM_FACTS": 260,
    "CORE_FACTS": 230,
    "DEPARTMENTS": 210,
    "ABOUT": 190,
    "ADMINISTRATION": 190,
    "ACADEMICS": 185,
    "ADMISSION": 180,
    "EXAMINATION": 175,
    "STUDENTS": 170,
    "FACILITIES": 170,
    "SVSU_ALL_PROGRAMS_LIST": 165,
    "PDF": 120,
}

DOMAIN_SOURCE_BOOSTS = {
    "Home": {
        "CUSTOM_FACTS": 140,
        "CORE_FACTS": 120,
        "DEPARTMENTS": 135,
        "ABOUT": 105,
        "ADMINISTRATION": 100,
        "ACADEMICS": 95,
        "STUDENTS": 95,
        "FACILITIES": 125,
        "ADMISSION": 75,
        "EXAMINATION": 75,
        "PDF": 25,
        "ADMISSION_RULES_MANUAL_2025": 180,
        "PROSPECTUS_2025_EXTRA_PAGES": 170,
        "PROSPECTUS_2025_PAGES_5_17": 170,
        "UNIVERSITY_FACILITIES_MANUAL_2025": 185,
        "DSW_SCHOLARSHIPS_MANUAL_2025": 180,
        "ACADEMIC_ORDINANCES_2024": 175,
        "EXAMINATION_ORDINANCE": 175,
        "CONSULTANCY_POLICY": 160,
        "RECRUITMENT_RULES_NON_TEACHING": 165,
        "PHD_REGULATIONS": 170,
        "PHD_ORDINANCE": 170,
        "RESEARCH_NEW": 165,
        "DSW_COMMITTEES_NOTIFICATION": 175,
        "GUEST_HOUSE_COE_EXTENDED_2025": 180,
        "UNIVERSITY_POLICIES_CULTURE_2025": 185,
        "RESEARCH_INTEGRITY_RECRUITMENT_2024_2025": 190,
        "UNIVERSITY_ADMIN_COMMITTEES_2025": 195,
    },
    "About": {
        "CUSTOM_FACTS": 150,
        "CORE_FACTS": 130,
        "DEPARTMENTS": 120,
        "ABOUT": 130,
        "ADMINISTRATION": 95,
        "PDF": 20,
    },
    "Administration": {
        "CUSTOM_FACTS": 150,
        "CORE_FACTS": 125,
        "DEPARTMENTS": 135,
        "ADMINISTRATION": 135,
        "ABOUT": 90,
        "PDF": 20,
    },
    "Academics": {
        "CUSTOM_FACTS": 140,
        "CORE_FACTS": 110,
        "DEPARTMENTS": 145,
        "ACADEMICS": 135,
        "SVSU_ALL_PROGRAMS_LIST": 120,
        "PDF": 25,
    },
    "Admission": {
        "CUSTOM_FACTS": 140,
        "CORE_FACTS": 115,
        "ADMISSION": 135,
        "SVSU_ALL_PROGRAMS_LIST": 130,
        "PDF": 30,
        "ADMISSION_RULES_MANUAL_2025": -1000,
        "PROSPECTUS_2025_EXTRA_PAGES": -1000,
        "PROSPECTUS_2025_PAGES_5_17": -1000,
        "UNIVERSITY_FACILITIES_MANUAL_2025": -1000,
        "DSW_SCHOLARSHIPS_MANUAL_2025": -1000,
        "ACADEMIC_ORDINANCES_2024": -1000,
        "EXAMINATION_ORDINANCE": -1000,
        "CONSULTANCY_POLICY": -1000,
        "RECRUITMENT_RULES_NON_TEACHING": -1000,
        "PHD_REGULATIONS": -1000,
        "PHD_ORDINANCE": -1000,
        "RESEARCH_NEW": -1000,
        "DSW_COMMITTEES_NOTIFICATION": -1000,
        "GUEST_HOUSE_COE_EXTENDED_2025": -1000,
        "UNIVERSITY_POLICIES_CULTURE_2025": -1000,
        "RESEARCH_INTEGRITY_RECRUITMENT_2024_2025": -1000,
        "UNIVERSITY_ADMIN_COMMITTEES_2025": -1000,
    },
    "Student Programs": {
        "CUSTOM_FACTS": 140,
        "CORE_FACTS": 105,
        "DEPARTMENTS": 110,
        "STUDENTS": 135,
        "FACILITIES": 125,
        "PDF": 20,
    },
    "Examination": {
        "CUSTOM_FACTS": 135,
        "CORE_FACTS": 105,
        "EXAMINATION": 140,
        "PDF": 25,
    },
    "Library": {
        "CUSTOM_FACTS": 130,
        "CORE_FACTS": 110,
        "FACILITIES": 130,
        "PDF": 20,
    },
    "Contact": {
        "CUSTOM_FACTS": 150,
        "CORE_FACTS": 135,
        "DEPARTMENTS": 120,
        "ABOUT": 80,
        "ADMINISTRATION": 80,
    },
    "Research": {
        "CUSTOM_FACTS": 130,
        "CORE_FACTS": 100,
        "ACADEMICS": 85,
        "PDF": 40,
    },
    "Updates": {
        "CUSTOM_FACTS": 130,
        "CORE_FACTS": 95,
        "PDF": 30,
    },
    "Notices": {
        "CUSTOM_FACTS": 130,
        "CORE_FACTS": 95,
        "PDF": 30,
    },
}

QUERY_SYNONYM_EXPANSIONS = {
    "vc": ["vice chancellor", "leadership", "administration"],
    "vice chancellor": ["vc", "leadership", "administration"],
    "registrar": ["administration", "office", "contact"],
    "cs it": ["computer science", "information technology", "computer department", "cs it department"],
    "cs department": ["computer science", "cs it department", "computer department"],
    "it department": ["information technology", "cs it department", "computer department"],
    "hostel": ["accommodation", "mess", "rooms", "student facilities"],
    "library": ["books", "reading room", "e resources", "e granthalaya"],
    "club": ["clubs", "society", "student programs", "nss", "ncc"],
    "clubs": ["club", "society", "student programs", "nss", "ncc"],
    "canteen": ["student facilities", "campus facilities"],
    "transport": ["bus", "student facilities"],
    "health": ["health centre", "medical", "student welfare"],
    "exam": ["examination", "result", "dmc", "re evaluation"],
    "result": ["exam", "examination", "dmc", "re evaluation"],
    "faculty": ["department", "academic", "school"],
    "department": ["faculty", "academic", "school"],
    "placements": ["career", "industrial relations", "training and placement"],
    "placement": ["career", "industrial relations", "training and placement"],
    "contact": ["phone", "email", "address"],
}

HOME_QUERY_URL_HINTS = [
    (
        {"vc", "vice chancellor", "registrar", "administration", "office", "leadership"},
        [
            "https://svsu.ac.in/about-us",
            "https://svsu.ac.in/vice-chancellor",
            "https://svsu.ac.in/registrar",
            "https://svsu.ac.in/administration",
        ],
    ),
    (
        {"department", "faculty", "academic", "school", "program", "course", "cs", "it", "computer"},
        [
            "https://svsu.ac.in/academics",
            "https://svsu.ac.in/skill-faculty",
        ],
    ),
    (
        {"hostel", "club", "clubs", "nss", "ncc", "canteen", "transport", "health", "student"},
        [
            "https://svsu.ac.in/student-corner",
            "https://svsu.ac.in/clubs",
        ],
    ),
    (
        {"library", "books", "reading", "journal"},
        [
            "https://svsu.ac.in/library",
        ],
    ),
    (
        {"exam", "result", "dmc", "reappear", "supplementary"},
        [
            "https://svsu.ac.in/examination",
        ],
    ),
    (
        {"notice", "news", "latest", "update", "announcement", "tender"},
        [
            "https://svsu.ac.in/news-events",
            "https://svsu.ac.in/announcements",
            "https://svsu.ac.in/office-orders",
        ],
    ),
    (
        {"contact", "phone", "email", "address", "location", "map"},
        [
            "https://svsu.ac.in/contact-us",
        ],
    ),
]

def normalize_catalog_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    normalized = normalized.replace("ﬁ", "fi").replace("ﬀ", "ff").replace("&", " and ")
    normalized = normalized.lower()
    replacements = {
        "b. tech": "btech",
        "b tech": "btech",
        "b.tech": "btech",
        "m. tech": "mtech",
        "m tech": "mtech",
        "m.tech": "mtech",
        "b. voc": "bvoc",
        "b voc": "bvoc",
        "b.voc": "bvoc",
        "m. voc": "mvoc",
        "m voc": "mvoc",
        "m.voc": "mvoc",
        "d. voc": "dvoc",
        "d voc": "dvoc",
        "d.voc": "dvoc",
        "ai/ml": "ai ml",
        "ai&ml": "ai ml",
        "ai and ml": "ai ml",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()

def looks_hinglish(text: str) -> bool:
    tokens = set(normalize_catalog_text(text).split())
    return any(token in HINGLISH_HINTS for token in tokens)

def select_language_reply(question: str, english: str, hinglish: str) -> str:
    return hinglish if looks_hinglish(question) else english

def has_any_query_term(query: str, terms) -> bool:
    return any(term in query for term in terms)

def query_token_set(query: str):
    return set(normalize_catalog_text(query).split())

def has_query_phrase(query: str, phrase: str) -> bool:
    normalized_query = normalize_catalog_text(query)
    normalized_phrase = normalize_catalog_text(phrase)
    if not normalized_query or not normalized_phrase:
        return False
    if " " in normalized_phrase:
        return f" {normalized_phrase} " in f" {normalized_query} "
    return normalized_phrase in normalized_query.split()

def has_any_query_phrase(query: str, phrases) -> bool:
    return any(has_query_phrase(query, phrase) for phrase in phrases)

def get_official_program_catalog_context() -> str:
    return "\n".join(f"- {program}" for program in OFFICIAL_CURRENT_PROGRAMS)

def get_program_guardrail_notes() -> str:
    return "\n".join(f"- {note}" for note in PROGRAM_AVAILABILITY_GUARDRAILS)

def get_program_availability_guardrail(question: str, domain: str) -> str:
    if domain not in {"Admission", "Academics", "Home"}:
        return ""

    q = normalize_catalog_text(question)

    direct_rules = [
        (
            all(term in q for term in ["btech", "cyber", "security"]),
            "I could not verify any standalone **B.Tech in Cyber Security** in SVSU's current official program list, so I should not confirm it. What I can verify is: **B.Tech Electrical Engineering** has an official minor/Hons context in Cyber Security, and **Diploma Computer (Generative AI/Cyber Security)** is an official diploma-level option.",
            "Main SVSU ke current official program list me koi standalone **B.Tech in Cyber Security** verify nahi kar pa raha, isliye main ise confirm nahi karunga. Jo official cheezein verify hoti hain wo yeh hain: **B.Tech Electrical Engineering** me Cyber Security ka minor/Hons context milta hai, aur **Diploma Computer (Generative AI/Cyber Security)** diploma level par available hai."
        ),
        (
            all(term in q for term in ["bvoc", "cyber", "security"]),
            "I could not verify any standalone **B.Voc in Cyber Security** in SVSU's current official program list, so I should not confirm it.",
            "Main SVSU ke current official program list me koi standalone **B.Voc in Cyber Security** verify nahi kar pa raha, isliye main ise confirm nahi karunga."
        ),
        (
            all(term in q for term in ["btech", "artificial", "intelligence", "data", "science"]),
            "I could not verify any standalone **B.Tech in Artificial Intelligence and Data Science** in SVSU's current official program list. The official current B.Tech program I can verify is **B.Tech Computer Science & Engineering (AI/ML)**.",
            "Main SVSU ke current official program list me koi standalone **B.Tech in Artificial Intelligence and Data Science** verify nahi kar pa raha. Jo official B.Tech option verify hota hai wo **B.Tech Computer Science & Engineering (AI/ML)** hai."
        ),
        (
            all(term in q for term in ["bvoc", "digital", "marketing"]),
            "I could not verify any standalone **B.Voc in Digital Marketing** in SVSU's current official program list, so I should not confirm it.",
            "Main SVSU ke current official program list me koi standalone **B.Voc in Digital Marketing** verify nahi kar pa raha, isliye main ise confirm nahi karunga."
        ),
    ]

    for condition, english, hinglish in direct_rules:
        if condition:
            return select_language_reply(question, english, hinglish)

    if "cyber" in q and "security" in q and not any(term in q for term in ["diploma", "minor", "electrical"]):
        english = "I should be careful here: I could not verify a standalone **Cyber Security degree** in SVSU's current official catalog. The related official options I can verify are **Diploma Computer (Generative AI/Cyber Security)** and a Cyber Security minor/Hons context with **B.Tech Electrical Engineering**."
        hinglish = "Yahan mujhe careful rehna chahiye: main SVSU ke current official catalog me koi standalone **Cyber Security degree** verify nahi kar pa raha. Jo related official options verify hote hain wo **Diploma Computer (Generative AI/Cyber Security)** aur **B.Tech Electrical Engineering** ke saath Cyber Security minor/Hons context hain."
        return select_language_reply(question, english, hinglish)

    return ""

PROGRAM_SEARCH_ALIASES = {
    "BCA": [
        "BCA",
        "Bachelor of Computer Applications",
        "Bachelor in Computer Applications",
    ],
    "BCA - MCA (Integrated)": [
        "BCA - MCA (Integrated)",
        "Integrated BCA-MCA",
        "Integrated BCA MCA",
        "BCA-MCA",
        "BCA MCA",
    ],
    "Bachelor in Hotel Management": [
        "Bachelor in Hotel Management",
        "Bachelor of Hotel Management",
        "BHM",
    ],
    "B.Tech Computer Science & Engineering (AI/ML)": [
        "B.Tech Computer Science & Engineering (AI/ML)",
        "B. Tech. Computer Science and Engineering (Artificial Intelligence and Machine Learning)",
        "B Tech Computer Science and Engineering Artificial Intelligence and Machine Learning",
        "B.Tech CSE (AI/ML)",
    ],
    "B.Tech Computer Engineering": [
        "B.Tech Computer Engineering",
        "B.Tech in Computer Engineering",
        "B. Tech. in Computer Engineering",
    ],
    "B.Tech Mechanical and Smart Manufacturing": [
        "B.Tech Mechanical and Smart Manufacturing",
        "B.Tech. Mechanical and Smart Manufacturing",
    ],
    "BBA in Retail Management": [
        "BBA in Retail Management",
        "BBA Retail Management",
    ],
    "B.Com (Honors/Research)": [
        "B.Com (Honors/Research)",
        "B.Com Honors Research",
        "B.Com Hons with Research",
    ],
}

PROGRAM_DETAIL_INTENT_HINTS = [
    "detail", "details", "jankari", "bata", "information", "info", "tell me",
    "seats", "intake", "duration", "eligibility", "industry partner", "fees",
    "industry partners", "ncrf", "overview", "about the program",
    "brief program overview", "full details", "program details", "bataye", "btaye",
    "program_selected:", "exact_program:", "details of"
]

PROGRAM_CATALOG_CACHE = None
PROGRAM_SOURCE_DOCUMENTS = None
STRUCTURED_PROGRAM_CATALOG_CACHE = None
PROGRAM_PROFILE_CACHE = {}
PROGRAM_MATCH_STOPWORDS = {
    "and", "or", "of", "the", "in", "with", "for", "program", "course",
    "general", "approved", "research", "honors", "honours", "management",
}

def get_program_search_aliases(program_name: str):
    aliases = [program_name]
    aliases.extend(PROGRAM_SEARCH_ALIASES.get(program_name, []))
    if " in " in program_name:
        aliases.append(program_name.replace(" in ", " of "))
    if " of " in program_name:
        aliases.append(program_name.replace(" of ", " in "))
    if "&" in program_name:
        aliases.append(program_name.replace("&", "and"))
    if "and" in program_name:
        aliases.append(program_name.replace("and", "&"))
    aliases.append(re.sub(r"\s*\((.*?)\)", r" \1", program_name).replace("  ", " ").strip())
    aliases.append(re.sub(r"\s*\((.*?)\)", "", program_name).replace("  ", " ").strip())
    aliases.append(program_name.replace("/", " ").replace("-", " ").strip())
    aliases.append(program_name.replace("Honors", "Honours"))
    aliases.append(program_name.replace("Honours", "Honors"))
    aliases.append(program_name.replace("(General)", "General"))
    aliases.append(program_name.replace("(Honors/Research)", "(Honours/Honours with Research)"))
    aliases.append(program_name.replace("(Honors/Research)", "Honours with Research"))
    aliases.append(program_name.replace("(Honors/Research)", "Honours"))

    if program_name.startswith("UG Certificate in "):
        rest = program_name.replace("UG Certificate in ", "", 1).strip()
        aliases.extend([
            f"Undergraduate Certificate in {rest}",
            f"UG Certificate in {rest}",
        ])
    if program_name.startswith("Undergraduate Certificate in "):
        rest = program_name.replace("Undergraduate Certificate in ", "", 1).strip()
        aliases.extend([
            f"UG Certificate in {rest}",
            f"Undergraduate Certificate in {rest}",
        ])
    if program_name.startswith("Undergraduate Diploma in "):
        rest = program_name.replace("Undergraduate Diploma in ", "", 1).strip()
        aliases.extend([
            f"UG Diploma in {rest}",
            f"Undergraduate Diploma in {rest}",
        ])
    if program_name.startswith("Diploma in "):
        rest = program_name.replace("Diploma in ", "", 1).strip()
        aliases.extend([
            f"Undergraduate Diploma in {rest}",
            f"Diploma {rest}",
        ])
    if program_name.startswith("Certificate in "):
        rest = program_name.replace("Certificate in ", "", 1).strip()
        aliases.extend([
            f"Undergraduate Certificate in {rest}",
            f"UG Certificate in {rest}",
        ])
    if program_name.startswith("PG Diploma in "):
        rest = program_name.replace("PG Diploma in ", "", 1).strip()
        aliases.extend([
            f"PG Diploma {rest}",
            f"Post Graduate Diploma in {rest}",
        ])
    if program_name.startswith("B.Voc "):
        rest = program_name.replace("B.Voc ", "", 1).strip()
        aliases.extend([
            f"B.Voc. {rest}",
            f"B.Voc. ({rest})",
            f"Bachelor of Vocation (B.Voc.) {rest}",
            f"Bachelor of Vocation (B. Voc.) {rest}",
        ])
    if program_name.startswith("M.Voc "):
        rest = program_name.replace("M.Voc ", "", 1).strip()
        aliases.extend([
            f"M.Voc. {rest}",
            f"M.Voc. ({rest})",
            f"Master of Vocation (M.Voc.) {rest}",
            f"Master of Vocation (M. Voc.) {rest}",
        ])
    if program_name.startswith("D.Voc "):
        rest = program_name.replace("D.Voc ", "", 1).strip()
        aliases.extend([
            f"D.Voc. {rest}",
            f"D.Voc. ({rest})",
            f"Diploma of Vocation (D.Voc.) {rest}",
            f"Diploma of Vocation (D. Voc.) {rest}",
        ])
    if program_name.startswith("B.Tech "):
        rest = program_name.replace("B.Tech ", "", 1).strip()
        aliases.extend([
            f"B.Tech. {rest}",
            f"B.Tech. in {rest}",
            f"B.Tech in {rest}",
            f"Bachelor of Technology (B.Tech.) in {rest}",
            f"Bachelor of Technology (B.Tech.) {rest}",
        ])
    if program_name.startswith("M.Tech "):
        rest = program_name.replace("M.Tech ", "", 1).strip()
        aliases.extend([
            f"M.Tech. {rest}",
            f"M.Tech. in {rest}",
            f"Master of Technology (M.Tech.) {rest}",
            f"Master of Technology (M.Tech.) in {rest}",
        ])
    if program_name.startswith("B.Sc. "):
        rest = program_name.replace("B.Sc. ", "", 1).strip()
        aliases.extend([
            f"B.Sc. ({rest})",
            f"B.Sc {rest}",
        ])
    if program_name.startswith("M.Sc "):
        rest = program_name.replace("M.Sc ", "", 1).strip()
        aliases.extend([
            f"M.Sc. ({rest})",
            f"M.Sc. {rest}",
        ])

    return dedupe_preserve_order([alias.strip(" #-") for alias in aliases if alias and alias.strip(" #-")])

def get_program_signature_tokens(text: str):
    tokens = [
        token for token in normalize_catalog_text(text).split()
        if len(token) >= 2 and token not in PROGRAM_MATCH_STOPWORDS
    ]
    return dedupe_preserve_order(tokens)

def alias_is_too_broad_for_target(target_program: str, alias: str) -> bool:
    target_tokens = set(get_program_signature_tokens(target_program))
    alias_tokens = set(get_program_signature_tokens(alias))
    if not target_tokens or not alias_tokens:
        return False
    if alias_tokens == target_tokens:
        return False
    return alias_tokens < target_tokens and len(target_tokens - alias_tokens) >= 1

def normalize_program_field_value(field_name: str, value: str) -> str:
    value = " ".join(str(value or "").split())
    if not value:
        return ""
    normalized = normalize_catalog_text(value)
    if field_name in {"seats", "seat", "intake"}:
        digits = re.findall(r"\d+", normalized)
        return digits[0] if digits else normalized
    if field_name == "duration":
        digits = re.findall(r"\d+(?:\.\d+)?", normalized)
        if digits:
            return digits[0]
    if field_name == "ncrf_level":
        digits = re.findall(r"\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?", normalized)
        if digits:
            return digits[0]
    return normalized

def get_repo_root_dir() -> Path:
    return Path(__file__).resolve().parents[2]

def get_program_data_paths():
    repo_root = get_repo_root_dir()
    backend_data_dir = repo_root / "BOT_BACKEND" / "data"
    structured_dir = repo_root / "SVSU_KNOWLEDGE" / "Structured_Data"
    text_dir = repo_root / "SVSU_KNOWLEDGE" / "Text_Knowledge"
    return {
        "structured_catalog_json": [
            backend_data_dir / "official_admission_program_catalog_2025_26.json",
            structured_dir / "official_admission_program_catalog_2025_26.json",
        ],
        "program_list_txt": [
            backend_data_dir / "svsu_all_programs_list.txt",
            structured_dir / "svsu_all_programs_list.txt",
        ],
        "pdf_knowledge_txt": [
            backend_data_dir / "pdf_knowledge.txt",
            text_dir / "pdf_knowledge.txt",
        ],
        "admission_knowledge_txt": [
            backend_data_dir / "admission_knowledge.txt",
            text_dir / "admission_knowledge.txt",
        ],
    }

def read_first_existing_text(paths):
    for path in paths:
        try:
            if path.exists():
                return path.read_text(encoding="utf-8", errors="ignore"), path
        except Exception:
            continue
    return "", None

def build_structured_catalog_record(raw_record: dict):
    if not isinstance(raw_record, dict):
        return None

    display_title = " ".join(str(raw_record.get("display_title", "")).split()).strip()
    canonical_title = " ".join(str(raw_record.get("canonical_title", "")).split()).strip()
    legacy_catalog_title = " ".join(str(raw_record.get("legacy_catalog_title", "")).split()).strip()
    aliases = []
    for candidate in [display_title, canonical_title, legacy_catalog_title]:
        if candidate:
            aliases.append(candidate)
    aliases.extend(
        " ".join(str(alias or "").split()).strip()
        for alias in raw_record.get("aliases", [])
        if str(alias or "").strip()
    )
    aliases = dedupe_preserve_order([alias for alias in aliases if alias])

    return {
        "program": display_title or canonical_title,
        "display_title": display_title or canonical_title,
        "canonical_title": canonical_title or display_title,
        "legacy_catalog_title": legacy_catalog_title,
        "aliases": aliases,
        "faculty": " ".join(str(raw_record.get("faculty", "")).split()),
        "industry_partner": " ".join(str(raw_record.get("industry_partner", "")).split()),
        "eligibility": " ".join(str(raw_record.get("eligibility", "")).split()),
        "intake": " ".join(str(raw_record.get("intake", "")).split()),
        "seats": " ".join(str(raw_record.get("intake", "") or raw_record.get("seats", "")).split()),
        "duration": " ".join(str(raw_record.get("duration", "")).split()),
        "ncrf_level": " ".join(str(raw_record.get("ncrf_level", "")).split()),
        "session": " ".join(str(raw_record.get("session", "")).split()),
        "menu_level": " ".join(str(raw_record.get("menu_level", "")).split()),
        "menu_category": " ".join(str(raw_record.get("menu_category", "")).split()),
        "source_url": " ".join(str(raw_record.get("source_url", "")).split()),
    }

def load_structured_program_catalog():
    global STRUCTURED_PROGRAM_CATALOG_CACHE
    if STRUCTURED_PROGRAM_CATALOG_CACHE is not None:
        return STRUCTURED_PROGRAM_CATALOG_CACHE

    paths = get_program_data_paths()["structured_catalog_json"]
    structured_catalog = []
    for path in paths:
        try:
            if not path.exists():
                continue
            payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            for raw_record in payload.get("programs", []):
                record = build_structured_catalog_record(raw_record)
                if record and record.get("program"):
                    structured_catalog.append(record)
            if structured_catalog:
                break
        except Exception:
            continue

    STRUCTURED_PROGRAM_CATALOG_CACHE = structured_catalog
    return STRUCTURED_PROGRAM_CATALOG_CACHE

def load_program_source_documents():
    global PROGRAM_SOURCE_DOCUMENTS
    if PROGRAM_SOURCE_DOCUMENTS is not None:
        return PROGRAM_SOURCE_DOCUMENTS

    candidate_files = [
        ("PDF", get_program_data_paths()["pdf_knowledge_txt"]),
        ("SVSU_ALL_PROGRAMS_LIST", get_program_data_paths()["program_list_txt"]),
        ("ADMISSION", get_program_data_paths()["admission_knowledge_txt"]),
    ]

    documents = []
    for source, path_options in candidate_files:
        text, resolved_path = read_first_existing_text(path_options)
        if not text or not resolved_path:
            continue
        documents.append({
            "source": source,
            "path": str(resolved_path),
            "text": text,
            "lines": text.splitlines(),
        })

    PROGRAM_SOURCE_DOCUMENTS = documents
    return PROGRAM_SOURCE_DOCUMENTS

def extract_explicit_program_selection(question: str) -> str:
    text = str(question or "")
    patterns = [
        r"PROGRAM_SELECTED\s*:\s*(.+?)(?:\n|$)",
        r"EXACT_PROGRAM\s*:\s*(.+?)(?:\n|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            selection = match.group(1).strip(" .:-")
            if selection:
                return selection
    return ""

def load_program_catalog_cache():
    global PROGRAM_CATALOG_CACHE
    if PROGRAM_CATALOG_CACHE is not None:
        return PROGRAM_CATALOG_CACHE

    cache = {}

    for record in load_structured_program_catalog():
        cache_key_candidates = [record.get("program", ""), record.get("display_title", ""), record.get("canonical_title", "")]
        cache_key_candidates.extend(record.get("aliases", []))
        for alias in dedupe_preserve_order([candidate for candidate in cache_key_candidates if candidate]):
            normalized_alias = normalize_catalog_text(alias)
            if normalized_alias and normalized_alias not in cache:
                cache[normalized_alias] = dict(record)

    content, _ = read_first_existing_text(get_program_data_paths()["program_list_txt"])
    if content:
        block_pattern = re.compile(
            r"PROGRAM:\s*(.*?)\s*ID:\s*(.*?)\s*NCrF Level:\s*(.*?)\s*Duration:\s*(.*?)\s*Seats:\s*(.*?)\s*(?=---|$)",
            flags=re.IGNORECASE | re.DOTALL,
        )
        for match in block_pattern.finditer(content):
            program = " ".join(match.group(1).split())
            record = {
                "program": program,
                "display_title": program,
                "canonical_title": program,
                "aliases": get_program_search_aliases(program),
                "id": " ".join(match.group(2).split()),
                "ncrf_level": " ".join(match.group(3).split()),
                "duration": " ".join(match.group(4).split()),
                "seats": " ".join(match.group(5).split()),
                "intake": " ".join(match.group(5).split()),
            }
            for alias in dedupe_preserve_order([program] + record["aliases"]):
                normalized_alias = normalize_catalog_text(alias)
                if not normalized_alias:
                    continue
                existing = cache.get(normalized_alias, {})
                merged = dict(record)
                merged.update({k: v for k, v in existing.items() if v})
                cache[normalized_alias] = merged

    PROGRAM_CATALOG_CACHE = cache
    return PROGRAM_CATALOG_CACHE

def find_catalog_program_record(program_name: str):
    catalog = load_program_catalog_cache()
    for alias in get_program_search_aliases(program_name):
        if alias_is_too_broad_for_target(program_name, alias):
            continue
        record = catalog.get(normalize_catalog_text(alias))
        if record:
            return record

    target_tokens = set(get_program_signature_tokens(program_name))
    if not target_tokens:
        return None

    best_record = None
    best_score = 0
    for record in catalog.values():
        record_tokens = set(get_program_signature_tokens(record.get("program", "")))
        overlap = len(target_tokens & record_tokens)
        if overlap < max(2, min(len(target_tokens), 3)):
            continue
        coverage = overlap / max(len(target_tokens), 1)
        if coverage < 0.75:
            continue
        score = (overlap * 10) - abs(len(record_tokens) - len(target_tokens))
        if overlap == len(target_tokens):
            score += 15
        if score > best_score:
            best_score = score
            best_record = record
    if best_score >= 24:
        return best_record
    return None

def find_exact_official_program(question: str):
    programs_by_length = sorted(OFFICIAL_CURRENT_PROGRAMS, key=lambda item: len(normalize_catalog_text(item)), reverse=True)
    search_targets = []

    explicit_program = extract_explicit_program_selection(question)
    if explicit_program:
        search_targets.append(explicit_program)
    search_targets.append(question)

    for search_target in dedupe_preserve_order(search_targets):
        normalized_question = normalize_catalog_text(search_target)
        if not normalized_question:
            continue
        
        # Priority 1: Match against entire OFFICIAL_CURRENT_PROGRAMS list via aliases
        for program in programs_by_length:
            aliases = get_program_search_aliases(program)
            for alias in aliases:
                # Use word boundaries for better precision
                if re.search(rf"\b{re.escape(normalize_catalog_text(alias))}\b", normalized_question):
                    return program
                    
    # Priority 2: Match against catalog records directly
    catalog = load_program_catalog_cache()
    for normalized_alias, record in catalog.items():
        if re.search(rf"\b{re.escape(normalized_alias)}\b", normalize_catalog_text(question)):
            return record.get("program", "")

    return ""

def extract_program_field(text: str, label_patterns: list, stop_patterns: list):
    if not text:
        return ""

    label_regex = "|".join(label_patterns)
    stop_regex = "|".join(stop_patterns)
    match = re.search(
        rf"(?:{label_regex})\s*[:\-]?\s*(.+?)(?=(?:{stop_regex})\s*[:\-]?|$)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return ""

    value = " ".join(match.group(1).replace("\r", " ").replace("\n", " ").split())
    return value.strip(" -:")

def get_best_program_local_context(text: str, aliases):
    raw_text = str(text or "")
    if not raw_text.strip():
        return ""

    candidates = []
    lowered_text = raw_text.lower()
    for alias in aliases:
        alias_text = str(alias or "").strip()
        if not alias_text:
            continue
        idx = lowered_text.find(alias_text.lower())
        if idx == -1:
            continue
        start = max(0, idx - 900)
        end = min(len(raw_text), idx + 2600)
        window = raw_text[start:end]
        lower_window = window.lower()
        score = sum(
            keyword in lower_window
            for keyword in ["eligibility", "ncrf level", "industry partner", "industry partners", "about the program"]
        )
        candidates.append((score, -abs(idx), window))

    if not candidates:
        return raw_text

    candidates.sort(reverse=True)
    return candidates[0][2]

def get_program_source_contexts(program_name: str, aliases, limit: int = 3):
    documents = load_program_source_documents()
    candidates = []
    seen_windows = set()

    for document in documents:
        lines = document["lines"]
        normalized_lines = [normalize_catalog_text(line) for line in lines]
        for idx, normalized_line in enumerate(normalized_lines):
            if not normalized_line:
                continue
            for alias in aliases:
                normalized_alias = normalize_catalog_text(alias)
                if not normalized_alias or not has_query_phrase(normalized_line, normalized_alias):
                    continue

                start = max(0, idx - 14)
                end = min(len(lines) - 1, idx + 42)
                window = "\n".join(lines[start:end + 1]).strip()
                if not window or window in seen_windows:
                    continue

                normalized_window = normalize_catalog_text(window)
                label_score = sum(
                    keyword in normalized_window
                    for keyword in ["eligibility", "ncrf level", "industry partner", "industry partners", "duration", "seats", "about the program"]
                )
                alias_strength = len(normalized_alias.split()) * 12 + min(len(normalized_alias), 30)
                program_name_bonus = 20 if has_query_phrase(normalized_window, program_name) else 0
                source_bonus = {"PDF": 45, "SVSU_ALL_PROGRAMS_LIST": 30, "ADMISSION": 15}.get(document["source"], 0)
                score = alias_strength + (label_score * 18) + program_name_bonus + source_bonus

                if program_name == "BCA" and "integrated bca mca" in normalized_window:
                    score -= 35
                if program_name == "BCA - MCA (Integrated)" and "integrated bca mca" in normalized_window:
                    score += 40

                candidates.append((score, -idx, document["source"], window))
                seen_windows.add(window)
                break

    candidates.sort(reverse=True)
    return [window for _, _, _, window in candidates[:limit]]

PROGRAM_FIELD_PATTERNS = {
    "eligibility": re.compile(r"^\s*eligibility(?:\s+criteria)?\s*[:\-]?\s*(.*)$", flags=re.IGNORECASE),
    "ncrf_level": re.compile(r"^\s*ncrf\s*level\s*[:\-]?\s*(.*)$", flags=re.IGNORECASE),
    "industry_partner": re.compile(r"^\s*industry\s*partners?\s*[:\-]?\s*(.*)$", flags=re.IGNORECASE),
    "duration": re.compile(r"^\s*duration\s*[:\-]?\s*(.*)$", flags=re.IGNORECASE),
    "seats": re.compile(r"^\s*(?:seats?|intake)\s*[:\-]?\s*(.*)$", flags=re.IGNORECASE),
    "about_program": re.compile(r"^\s*about the program\b\s*[:\-]?\s*(.*)$", flags=re.IGNORECASE),
}

def get_program_source_windows(program_name: str, aliases, limit: int = 6):
    documents = load_program_source_documents()
    candidates = []
    seen_keys = set()

    for document in documents:
        lines = document["lines"]
        normalized_lines = [normalize_catalog_text(line) for line in lines]
        for idx, normalized_line in enumerate(normalized_lines):
            if not normalized_line:
                continue
            for alias in aliases:
                normalized_alias = normalize_catalog_text(alias)
                if not normalized_alias or not has_query_phrase(normalized_line, normalized_alias):
                    continue

                start = max(0, idx - 60)
                end = min(len(lines) - 1, idx + 45)
                key = (document["source"], start, end)
                if key in seen_keys:
                    continue

                window_lines = lines[start:end + 1]
                window_text = "\n".join(window_lines).strip()
                normalized_window = normalize_catalog_text(window_text)
                label_score = sum(
                    keyword in normalized_window
                    for keyword in ["eligibility", "ncrf level", "industry partner", "industry partners", "duration", "seats", "about the program"]
                )
                alias_strength = len(normalized_alias.split()) * 12 + min(len(normalized_alias), 30)
                program_name_bonus = 20 if has_query_phrase(normalized_window, program_name) else 0
                source_bonus = {"PDF": 45, "SVSU_ALL_PROGRAMS_LIST": 30, "ADMISSION": 15}.get(document["source"], 0)
                score = alias_strength + (label_score * 18) + program_name_bonus + source_bonus

                if program_name == "BCA" and "integrated bca mca" in normalized_window:
                    score -= 35
                if program_name == "BCA - MCA (Integrated)" and "integrated bca mca" in normalized_window:
                    score += 40

                candidates.append({
                    "score": score,
                    "source": document["source"],
                    "alias": alias,
                    "alias_index": idx - start,
                    "lines": window_lines,
                    "text": window_text,
                })
                seen_keys.add(key)
                break

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[:limit]

def is_program_source_boundary_line(line: str, aliases) -> bool:
    normalized_line = normalize_catalog_text(line)
    if not normalized_line:
        return False
    if normalized_line.isdigit():
        return True
    if any(
        normalized_line.startswith(prefix)
        for prefix in [
            "eligibility",
            "ncrf level",
            "industry partner",
            "industry partners",
            "duration",
            "seat",
            "seats",
            "intake",
            "about the program",
            "about the programs",
            "program:",
            "program highlights",
            "minor degree options",
            "detail data",
            "skill department",
            "guidelines for registration",
            "distribution and reservation of seats",
        ]
    ):
        return True
    if any(normalized_line == normalize_catalog_text(alias) for alias in aliases if len(normalize_catalog_text(alias)) > 4):
        return True
    return False

def extract_program_field_from_source_windows(windows, field_name: str, program_name: str, aliases):
    pattern = PROGRAM_FIELD_PATTERNS.get(field_name)
    if not pattern:
        return ""

    candidates = []
    for window in windows:
        lines = window["lines"]
        alias_index = window["alias_index"]
        for idx, raw_line in enumerate(lines):
            match = pattern.match(raw_line.strip())
            if not match:
                continue

            value_parts = []
            first_value = (match.group(1) or "").strip()
            if first_value:
                value_parts.append(first_value)

            for follow_idx in range(idx + 1, len(lines)):
                follow_line = lines[follow_idx].strip()
                if not follow_line:
                    if field_name == "about_program" and value_parts:
                        break
                    continue
                if is_program_source_boundary_line(follow_line, aliases):
                    break
                value_parts.append(follow_line)

            value = " ".join(part for part in value_parts if part).strip(" -:")
            if not value:
                continue

            value_norm = normalize_catalog_text(value)
            neighborhood_text = " ".join(lines[max(0, idx - 3): min(len(lines), idx + 4)])
            neighborhood_norm = normalize_catalog_text(neighborhood_text)

            score = 260 - (abs(idx - alias_index) * 4)
            if idx >= alias_index:
                score += 25
            if any(
                has_query_phrase(value_norm, alias) or has_query_phrase(neighborhood_norm, alias)
                for alias in aliases
                if len(normalize_catalog_text(alias)) > 2
            ):
                score += 120
            if has_query_phrase(value_norm, program_name) or has_query_phrase(neighborhood_norm, program_name):
                score += 160
            if field_name == "about_program":
                if len(value.split()) < 10:
                    score -= 180
                if "about the programs" in value_norm:
                    score -= 180
            if program_name == "BCA" and "integrated bca mca" in f"{value_norm} {neighborhood_norm}":
                score -= 180
            if program_name == "BCA - MCA (Integrated)" and "integrated bca mca" in f"{value_norm} {neighborhood_norm}":
                score += 120

            candidates.append((score, value))

    if not candidates:
        return ""

    candidates.sort(reverse=True)
    return candidates[0][1]

def get_first_program_field_value(text_candidates, label_patterns: list, stop_patterns: list):
    for text in text_candidates:
        value = extract_program_field(text, label_patterns, stop_patterns)
        if value:
            return value
    return ""

def trim_program_overview(text: str, max_sentences: int = 3, max_chars: int = 650):
    cleaned = " ".join(str(text or "").split())
    if not cleaned:
        return ""
    sentence_parts = re.split(r"(?<=[.!?])\s+", cleaned)
    trimmed = " ".join(sentence_parts[:max_sentences]).strip()
    if len(trimmed) > max_chars:
        trimmed = trimmed[:max_chars].rsplit(" ", 1)[0].strip() + "..."
    return trimmed

def program_overview_confident_for_program(program_name: str, overview: str) -> bool:
    overview_text = str(overview or "").strip()
    if not overview_text:
        return False

    normalized_overview = normalize_catalog_text(overview_text)
    if any(term in normalized_overview for term in ["airlines", "aviation", "airport management"]):
        program_tokens = set(get_program_signature_tokens(program_name))
        if not {"airlines", "airport", "aviation"} & program_tokens:
            return False

    signature_tokens = [
        token for token in get_program_signature_tokens(program_name)
        if len(token) >= 4 and token not in {"certificate", "diploma", "undergraduate", "postgraduate"}
    ]
    if not signature_tokens:
        return True

    overlap = sum(token in normalized_overview for token in signature_tokens)
    return overlap >= min(2, len(signature_tokens))

def build_explicit_program_gap_answer(question: str, program_name: str, catalog_record: dict | None):
    if not program_name:
        return ""

    english_lines = [
        f"I could not safely extract a **full verified profile** for **{program_name}** from the current SVSU knowledge sources, so I should not guess the missing details.",
        "",
        "**What I can verify right now:**",
    ]
    hinglish_lines = [
        f"Main current SVSU knowledge sources se **{program_name}** ka **full verified profile** safely extract nahi kar pa raha, isliye main missing details guess nahi karunga.",
        "",
        "**Jo main abhi verify kar pa raha hoon:**",
    ]

    if catalog_record:
        if catalog_record.get("seats"):
            english_lines.append(f"- **Seats / Intake:** {catalog_record['seats']}")
            hinglish_lines.append(f"- **Seats / Intake:** {catalog_record['seats']}")
        if catalog_record.get("duration"):
            english_lines.append(f"- **Duration:** {catalog_record['duration']}")
            hinglish_lines.append(f"- **Duration:** {catalog_record['duration']}")
        if catalog_record.get("ncrf_level"):
            english_lines.append(f"- **NCrF Level:** {catalog_record['ncrf_level']}")
            hinglish_lines.append(f"- **NCrF Level:** {catalog_record['ncrf_level']}")
    else:
        english_lines.append("- I could not verify the structured catalog fields for this exact title either.")
        hinglish_lines.append("- Main is exact title ke structured catalog fields bhi verify nahi kar pa raha.")

    english_lines.extend([
        "",
        "**Note:** To ensure accuracy, I am only using verified records. For official confirmation, feel free to reach out to our team at **admissions@svsu.ac.in** or call **1800-1800-147**.",
    ])
    hinglish_lines.extend([
        "",
        "**Note:** Sahi jaankari ke liye main sirf verified records use kar raha hoon. Official confirmation ke liye aap **admissions@svsu.ac.in** ya **1800-1800-147** par sampark kar sakte hain.",
    ])
    return select_language_reply(question, "\n".join(english_lines), "\n".join(hinglish_lines))

def build_exact_program_detail_answer(question: str, domain: str) -> str:
    if domain not in {"Admission", "Academics", "Home"}:
        return ""

    q = normalize_catalog_text(question)
    explicit_selection = extract_explicit_program_selection(question)
    is_detail_intended = any(hint in q for hint in PROGRAM_DETAIL_INTENT_HINTS) or explicit_selection
    
    if not is_detail_intended:
        return ""

    program_name = find_exact_official_program(question)
    if not program_name:
        return ""

    catalog_record = find_catalog_program_record(program_name)
    if catalog_record and catalog_record.get("display_title"):
        program_name = catalog_record["display_title"]
    aliases = get_program_search_aliases(program_name)
    question_tokens = query_token_set(question)
    retrieval_aliases = [
        alias for alias in aliases
        if len(normalize_catalog_text(alias)) > 4 or normalize_catalog_text(alias) in question_tokens
    ]
    candidate_queries = retrieval_aliases + [program_name, f"{program_name} eligibility industry partner about the program"]

    snippets = []
    seen_pairs = set()
    for candidate_query in candidate_queries:
        for snippet in perform_hybrid_retrieval(candidate_query, "Admission", top_n=8):
            snippet_text_normalized = normalize_catalog_text(snippet["text"])
            snippet_title_normalized = normalize_catalog_text(snippet.get("title", ""))
            if retrieval_aliases and not any(
                has_query_phrase(snippet_text_normalized, alias) or has_query_phrase(snippet_title_normalized, alias)
                for alias in retrieval_aliases
            ):
                continue
            key = (snippet["source"], snippet["text"][:240])
            if key not in seen_pairs:
                seen_pairs.add(key)
                snippets.append(snippet)

    combined_text = "\n\n".join(snippet["text"] for snippet in snippets)
    flattened_text = " ".join(combined_text.replace("\r", " ").replace("\n", " ").split())
    local_text = get_best_program_local_context(combined_text, retrieval_aliases or aliases)
    local_flattened_text = " ".join(local_text.replace("\r", " ").replace("\n", " ").split())
    source_windows = get_program_source_windows(program_name, retrieval_aliases or aliases, limit=6)
    source_contexts = [window["text"] for window in source_windows]
    source_flattened_texts = [
        " ".join(source_context.replace("\r", " ").replace("\n", " ").split())
        for source_context in source_contexts
        if source_context.strip()
    ]
    text_candidates = source_flattened_texts + [local_flattened_text, flattened_text]
    text_candidates = [candidate for candidate in text_candidates if candidate]
    alias_stop_patterns = [re.escape(alias) for alias in aliases if len(normalize_catalog_text(alias)) > 5]

    source_seats = extract_program_field_from_source_windows(source_windows, "seats", program_name, aliases)
    source_duration = extract_program_field_from_source_windows(source_windows, "duration", program_name, aliases)
    source_eligibility = extract_program_field_from_source_windows(source_windows, "eligibility", program_name, aliases)
    source_ncrf_level = extract_program_field_from_source_windows(source_windows, "ncrf_level", program_name, aliases)
    source_industry_partner = extract_program_field_from_source_windows(source_windows, "industry_partner", program_name, aliases)
    source_about_program = extract_program_field_from_source_windows(source_windows, "about_program", program_name, aliases)

    conflict_fields = []
    if catalog_record:
        for field_name, catalog_key in [("seats", "seats"), ("duration", "duration"), ("ncrf_level", "ncrf_level")]:
            catalog_value = normalize_program_field_value(field_name, (catalog_record or {}).get(catalog_key, ""))
            source_value = normalize_program_field_value(field_name, locals().get(f"source_{field_name}", ""))
            if catalog_value and source_value and catalog_value != source_value:
                conflict_fields.append(field_name)

    source_block_conflicted = len(conflict_fields) >= 2
    if source_block_conflicted:
        source_eligibility = ""
        source_industry_partner = ""
        source_about_program = ""
    safe_detail_candidates = [] if source_block_conflicted else text_candidates

    seats = (catalog_record or {}).get("intake", "") or (catalog_record or {}).get("seats", "") or source_seats or get_first_program_field_value(
        text_candidates,
        [r"Seats?", r"Seat", r"Intake"],
        [r"Eligibility Criteria", r"Eligibility", r"NCrF Level", r"Industry Partners?", r"Duration", r"About the Program", r"Program Fee Details", r"Fee Structure"],
    )
    duration = (catalog_record or {}).get("duration", "") or source_duration or get_first_program_field_value(
        text_candidates,
        [r"Duration"],
        [r"Eligibility Criteria", r"Eligibility", r"NCrF Level", r"Industry Partners?", r"Seats?", r"Seat", r"Intake", r"About the Program", r"Program Fee Details", r"Fee Structure"],
    )
    eligibility = source_eligibility or get_first_program_field_value(
        safe_detail_candidates,
        [r"Eligibility Criteria", r"Eligibility"],
        [r"NCrF Level", r"Industry Partners?", r"Duration", r"Seats?", r"Seat", r"Intake", r"About the Program", r"Program Fee Details", r"Fee Structure"],
    )
    ncrf_level = (catalog_record or {}).get("ncrf_level", "") or source_ncrf_level or get_first_program_field_value(
        text_candidates,
        [r"NCrF Level", r"NCrF level"],
        [r"Eligibility Criteria", r"Eligibility", r"Industry Partners?", r"Duration", r"Seats?", r"Seat", r"Intake", r"About the Program", r"Program Fee Details", r"Fee Structure"],
    )
    industry_partner = source_industry_partner or get_first_program_field_value(
        safe_detail_candidates,
        [r"Industry Partners?", r"Industry Partner"],
        [r"Duration", r"Seats?", r"Seat", r"Intake", r"Eligibility", r"NCrF Level", r"About the Program", r"Program Fee Details", r"Fee Structure"],
    )
    about_program = source_about_program or get_first_program_field_value(
        safe_detail_candidates,
        [r"About the Program\b"],
        [
            r"Job Roles aligned",
            r"Program Fee Details",
            r"Fee Structure",
            r"Guidelines for Registration",
            r"Distribution and Reservation of Seats",
            r"Eligibility Criteria",
            r"Eligibility",
            r"About the Programs",
            r"Skill Department",
            r"PROGRAM",
            *alias_stop_patterns,
        ],
    )
    about_program = trim_program_overview(about_program)
    if about_program and not program_overview_confident_for_program(program_name, about_program):
        about_program = ""

    faculty = (catalog_record or {}).get("faculty", "")
    menu_level = (catalog_record or {}).get("menu_level", "")
    session = (catalog_record or {}).get("session", "")
    source_url = (catalog_record or {}).get("source_url", "")

    if not any([seats, duration, eligibility, ncrf_level, industry_partner, about_program, faculty, menu_level]):
        return ""

    english_lines = [f"Here are the **verified admission details** for **{program_name}**:", ""]
    hinglish_lines = [f"Yahan **{program_name}** ki verified admission details di ja rahi hain:", ""]

    if faculty:
        english_lines.append(f"- **Faculty / School:** {faculty}")
        hinglish_lines.append(f"- **Faculty / School:** {faculty}")
    if menu_level:
        english_lines.append(f"- **Programme Level:** {menu_level}")
        hinglish_lines.append(f"- **Programme Level:** {menu_level}")
    if seats:
        english_lines.append(f"- **Seats / Intake:** {seats}")
        hinglish_lines.append(f"- **Seats / Intake:** {seats}")
    if duration:
        english_lines.append(f"- **Duration:** {duration}")
        hinglish_lines.append(f"- **Duration:** {duration}")
    if eligibility:
        english_lines.append(f"- **Eligibility:** {eligibility}")
        hinglish_lines.append(f"- **Eligibility:** {eligibility}")
    if ncrf_level:
        english_lines.append(f"- **NCrF Level:** {ncrf_level}")
        hinglish_lines.append(f"- **NCrF Level:** {ncrf_level}")
    if industry_partner:
        english_lines.append(f"- **Industry Partner:** {industry_partner}")
        hinglish_lines.append(f"- **Industry Partner:** {industry_partner}")
    if about_program:
        english_lines.extend(["", "**Program Overview:**", about_program])
        hinglish_lines.extend(["", "**Program Overview:**", about_program])
    if session:
        english_lines.append(f"- **Admission Session:** {session}")
        hinglish_lines.append(f"- **Admission Session:** {session}")

    english_lines.extend([
        "",
        "If you need more details about the **fee structure, admission route, or application guidance** for this program, just let me know!",
    ])
    hinglish_lines.extend([
        "",
        "Agar aapko is program ki **fee structure, admission route, ya application guidance** chahiye, toh zaroor batayein!",
    ])
    if source_url:
        english_lines.append(f"- **Official Source:** {source_url}")
        hinglish_lines.append(f"- **Official Source:** {source_url}")
    if source_block_conflicted:
        english_lines.append("- Some detailed source blocks for this program appear internally conflicting, so I kept only the safer verified fields.")
        hinglish_lines.append("- Is program ke kuch detailed source blocks internally conflicting lag rahe the, isliye maine sirf safer verified fields hi rakhe.")

    return select_language_reply(question, "\n".join(english_lines), "\n".join(hinglish_lines))

def get_verified_program_recommendation(question: str, domain: str) -> str:
    if domain not in {"Admission", "Academics", "Home"}:
        return ""

    q = normalize_catalog_text(question)
    explicit_program = extract_explicit_program_selection(question)

    exact_program_answer = build_exact_program_detail_answer(question, domain)
    if exact_program_answer:
        return exact_program_answer
    if explicit_program:
        return build_explicit_program_gap_answer(question, find_exact_official_program(question) or explicit_program, find_catalog_program_record(find_exact_official_program(question) or explicit_program))

    best_course_hints = ["best", "ebst", "acha", "achha", "recommend", "suggest", "kaunsa", "konsa"]
    if "course" in q and any(hint in q for hint in best_course_hints):
        english = """There is no single universal **best course** at SVSU. The right choice depends on your career goal. Based on the current official SVSU catalog, these are strong options:

- **For software / AI careers**: B.Tech Computer Science & Engineering (AI/ML), B.Tech in Computer Engineering, BCA, BCA - MCA (Integrated)
- **For core engineering + industry exposure**: B.Tech Electrical Engineering, B.Tech Mechanical and Smart Manufacturing
- **For skill-based industry pathways**: B.Voc Robotics and Automation, B.Voc Mechatronics, B.Voc Mechanical Manufacturing
- **For management**: BBA (General), BBA (Airlines and Airport Management), MBA, MBA (Business Analytics)

If you want, tell me your goal like **software jobs, AI, government job, management, core engineering, or diploma path**, and I will suggest the most suitable verified SVSU course only."""
        hinglish = """SVSU me ek hi universal **best course** nahi hota. Best course aapke career goal par depend karta hai. Current official SVSU catalog ke hisaab se ye strong options hain:

- **Software / AI career ke liye**: B.Tech Computer Science & Engineering (AI/ML), B.Tech in Computer Engineering, BCA, BCA - MCA (Integrated)
- **Core engineering + industry exposure ke liye**: B.Tech Electrical Engineering, B.Tech Mechanical and Smart Manufacturing
- **Skill-based industry pathway ke liye**: B.Voc Robotics and Automation, B.Voc Mechatronics, B.Voc Mechanical Manufacturing
- **Management ke liye**: BBA (General), BBA (Airlines and Airport Management), MBA, MBA (Business Analytics)

Agar aap apna goal bata do, jaise **software job, AI, government job, management, core engineering, ya diploma path**, to main sirf verified SVSU options me se best suggest kar dunga."""
        return select_language_reply(question, english, hinglish)

    cs_it_terms = ["cs it", "cs", "it", "computer department", "cs department", "it department", "computer science department"]
    cs_it_detail_terms = ["department", "about", "tell", "detail", "details", "bat", "bta", "department in svsu"]
    if has_any_query_phrase(q, cs_it_terms) and has_any_query_phrase(q, cs_it_detail_terms):
        english = """For the **CS/IT department side at SVSU**, these are the current officially verifiable details:

- It operates under the **Skill Faculty of Engineering & Technology (SFET)**
- The officially listed **CS/IT department chairperson** is **Prof. (Dr.) Usha Batra**
- The department focus areas include **AI, Data Science, Cybersecurity, Cloud Computing, and Software Development**

The current officially verifiable CS/IT-related programs are:

- **B.Tech Computer Science & Engineering (AI/ML)**
- **B.Tech in Computer Engineering**
- **BCA**
- **BCA - MCA (Integrated)**
- **Diploma Computer Science and Engineering**
- **Diploma Computer (Generative AI/Cyber Security)**

Important accuracy note:
- I could **not** verify any standalone **B.Tech in Cyber Security**
- I could **not** verify any standalone **B.Voc in Cyber Security**
- I could **not** verify any standalone **B.Tech in Artificial Intelligence and Data Science**

So if you want CS/IT at SVSU, the most relevant verified options are **B.Tech CSE (AI/ML)**, **B.Tech Computer Engineering**, **BCA**, and the two diploma/computer pathways above."""
        hinglish = """SVSU ke **CS/IT department side** me current official aur verify hone wali details ye hain:

- Yeh **Skill Faculty of Engineering & Technology (SFET)** ke under aata hai
- Officially listed **CS/IT department chairperson** **Prof. (Dr.) Usha Batra** hain
- Department ke focus areas me **AI, Data Science, Cybersecurity, Cloud Computing, aur Software Development** aate hain

Current official aur verify hone wale CS/IT-related programs ye hain:

- **B.Tech Computer Science & Engineering (AI/ML)**
- **B.Tech in Computer Engineering**
- **BCA**
- **BCA - MCA (Integrated)**
- **Diploma Computer Science and Engineering**
- **Diploma Computer (Generative AI/Cyber Security)**

Important accuracy note:
- main koi standalone **B.Tech in Cyber Security** verify nahi kar pa raha
- main koi standalone **B.Voc in Cyber Security** verify nahi kar pa raha
- main koi standalone **B.Tech in Artificial Intelligence and Data Science** verify nahi kar pa raha

Isliye agar aap SVSU me CS/IT options dekh rahe ho, to sabse relevant verified options **B.Tech CSE (AI/ML)**, **B.Tech Computer Engineering**, **BCA**, aur upar wale diploma/computer pathways hain."""
        return select_language_reply(question, english, hinglish)

    return ""

def get_verified_department_directory_info(question: str, domain: str) -> str:
    if domain not in {"Academics", "Administration", "Home", "Contact", "Student Programs"}:
        return ""

    q = normalize_catalog_text(question)

    full_directory_terms = [
        "all departments", "all department", "all faculties", "all faculty",
        "department list", "faculty list", "all branches", "all offices",
        "full structure", "full university structure", "sabhi department",
        "sabhi departments", "sabhi faculty", "sabhi faculties", "department names",
        "faculties in svsu", "departments in svsu", "svsu structure", "complete structure"
    ]
    if not has_any_query_term(q, full_directory_terms):
        return ""

    english = """Here is the **full verified SVSU structure overview** from the current curated data.

**Academic Faculties:**
- **SFET**: Automotive Studies, Construction Management and Technology, Green Technology, CS/IT, Industry 4.0, Plastic Technology
- **SFASH**: Language and Culture, Life Science and Health Care, Psychology and Behavioral Sciences, Science and Computation, Sports and Yoga, Pharmacy
- **SFMSR**: Management Studies, Banking and Finance, Tourism and Hospitality
- **SFA**: Agriculture and Horticulture

**Academic Support Units:**
- **IQAC**
- **Research and Development Cell**
- **Controller of Examination (COE) Office**
- **Central Library**

**Student Support and Campus Units:**
- **Dean Student Welfare (DSW)**
- **Career Counselling and Placement Cell**
- **Health Centre**
- **Hostel system**
- **Clubs / NSS / NCC / student-activity network**
- **Transport and Security Branch**

**Administrative Offices and Branches:**
- **Accounts Section**
- **Purchase and Central Store**
- **Infrastructure Development Cell (IDC)**
- **Industrial Relations and Alumni Affairs (IRAA)**
- **Proctorial Board**
- **General Branch**
- **Digital Innovation Cell (DIC)**
- **SVSU Skill Innovators Foundation**
- **Cultural Cell**
- **Minority Cell / SC-ST-OBC Cell**

**Key Leadership Contacts:**
- VC: **Prof. (Dr.) Dinesh Kumar**
- Registrar: **Prof. (Dr.) Jyoti Rana**
- Dean Academics: **Prof. (Dr.) Vikram Singh**
- Dean DSW: **Prof. (Dr.) Kulwant Singh**

If you want, I can now give the **full detailed breakdown of any one faculty, department, office, or cell** with chairperson, focus area, and available contacts."""
    hinglish = """Yahan current curated data ke hisaab se **SVSU ka full verified structure overview** diya gaya hai.

**Academic Faculties:**
- **SFET**: Automotive Studies, Construction Management and Technology, Green Technology, CS/IT, Industry 4.0, Plastic Technology
- **SFASH**: Language and Culture, Life Science and Health Care, Psychology and Behavioral Sciences, Science and Computation, Sports and Yoga, Pharmacy
- **SFMSR**: Management Studies, Banking and Finance, Tourism and Hospitality
- **SFA**: Agriculture aur Horticulture

**Academic Support Units:**
- **IQAC**
- **Research and Development Cell**
- **Controller of Examination (COE) Office**
- **Central Library**

**Student Support aur Campus Units:**
- **Dean Student Welfare (DSW)**
- **Career Counselling and Placement Cell**
- **Health Centre**
- **Hostel system**
- **Clubs / NSS / NCC / student-activity network**
- **Transport and Security Branch**

**Administrative Offices aur Branches:**
- **Accounts Section**
- **Purchase and Central Store**
- **Infrastructure Development Cell (IDC)**
- **Industrial Relations and Alumni Affairs (IRAA)**
- **Proctorial Board**
- **General Branch**
- **Digital Innovation Cell (DIC)**
- **SVSU Skill Innovators Foundation**
- **Cultural Cell**
- **Minority Cell / SC-ST-OBC Cell**

**Key Leadership Contacts:**
- VC: **Prof. (Dr.) Dinesh Kumar**
- Registrar: **Prof. (Dr.) Jyoti Rana**
- Dean Academics: **Prof. (Dr.) Vikram Singh**
- Dean DSW: **Prof. (Dr.) Kulwant Singh**

Agar chaho to main ab **kisi bhi ek faculty, department, office, ya cell ka full detailed breakdown** bhi de sakta hoon, jisme chairperson, focus area, aur available contacts honge."""
    return select_language_reply(question, english, hinglish)

def get_verified_general_info(question: str, domain: str) -> str:
    q = normalize_catalog_text(question)

    if domain in {"Student Programs", "Home"} and "hostel" in q:
        english = """**SVSU Hostel Facility (verified details):**

- Separate hostel facilities are available for **boys and girls**
- The hostel buildings are described as **six-storey buildings**
- Room types include **4-seater, 3-seater, and single-seater rooms**
- Amenities include **Wi-Fi, RO water, study/reading rooms, LED TV common rooms, and indoor/outdoor games**
- Security includes **24/7 guards and CCTV surveillance**

**Eligibility and rules:**
- Boys living within **30 km** and girls living within **15 km** of the hostel campus are generally not eligible
- Hostel application is done **online through the university website**

**Fee snapshot from the available SVSU data:**
- Hostel security: **Rs 5,000 refundable**
- Mess security: **Rs 5,000 refundable**
- Hostel charges: **Rs 11,000 per semester**
- Total at admission: **Rs 21,000** excluding mess charges

**Hostel contacts in the available SVSU data:**
- Boys Hostel (Kailash Bhawan): **Mr. Satish**, **9896269975**, **hsb@svsu.ac.in**
- Girls Hostel (Himadri Bhawan): **Dr. Sonia**, **9899849058**, **hsg@svsu.ac.in**"""
        hinglish = """**SVSU Hostel Facility (verified details):**

- SVSU me **boys aur girls dono ke liye separate hostel facility** available hai
- Hostel buildings **six-storey** batayi gayi hain
- Room types me **4-seater, 3-seater, aur single-seater rooms** aate hain
- Facilities me **Wi-Fi, RO water, study/reading rooms, LED TV common rooms, aur indoor/outdoor games** diye gaye hain
- Security ke liye **24/7 guards aur CCTV surveillance** hai

**Eligibility aur rules:**
- Jo boys **30 km** ke andar rehte hain aur girls **15 km** ke andar rehti hain, unhe generally hostel eligibility nahi hoti
- Hostel application **university website par online** hoti hai

**Available SVSU data ke hisaab se fee snapshot:**
- Hostel security: **Rs 5,000 refundable**
- Mess security: **Rs 5,000 refundable**
- Hostel charges: **Rs 11,000 per semester**
- Admission ke time total: **Rs 21,000** (mess charges alag)

**Hostel contacts:**
- Boys Hostel (Kailash Bhawan): **Mr. Satish**, **9896269975**, **hsb@svsu.ac.in**
- Girls Hostel (Himadri Bhawan): **Dr. Sonia**, **9899849058**, **hsg@svsu.ac.in**"""
        return select_language_reply(question, english, hinglish)

    if domain in {"Library", "Home"} and "library" in q:
        english = """**SVSU Central Library (verified details):**

- Library timing: **9:00 AM to 6:00 PM on working days**
- Reading room: **24/7**
- Available collection in the curated SVSU data:
  - **15,000+ printed books**
  - **20,000+ e-books**
  - **15,000+ e-journals**
- Library system: **e-Granthalaya**

**Borrowing limits listed in the available SVSU data:**
- Faculty: **10 books**
- PG students: **5 books**
- UG/Diploma students: **3 books**"""
        hinglish = """**SVSU Central Library (verified details):**

- Library timing: **working days me 9:00 AM se 6:00 PM**
- Reading room: **24/7**
- Curated SVSU data ke hisaab se collection:
  - **15,000+ printed books**
  - **20,000+ e-books**
  - **15,000+ e-journals**
- Library system: **e-Granthalaya**

**Available SVSU data me borrowing limits:**
- Faculty: **10 books**
- PG students: **5 books**
- UG/Diploma students: **3 books**"""
        return select_language_reply(question, english, hinglish)

    if domain in {"Student Programs", "Home"} and has_any_query_term(q, [
        "club", "clubs", "society", "societies", "student activity", "student activities",
        "extracurricular", "extra curricular", "nss", "ncc", "yrc"
    ]):
        english = """SVSU has a structured **student club and activity ecosystem** under student-welfare support.

- The curated SVSU student data lists **17 student clubs/cells/committees**, including **NSS, Youth Red Cross, NCC, and the Cell for Differently Abled**
- Major club options include **Technical Club, Sports and Adventure Club, Yoga Club, Literary Club, Cultural/Dramatics Club, Photography Club, Eco Club, Legal Literacy Club, Competitive Exam Club, Fine Arts Club, Psychological Guidance Club, and Drug Prevention Club**
- For joining, students should **contact the faculty coordinators** of the relevant club.
- Dean Student Welfare: **Prof. (Dr.) Kulwant Singh** (dean.dsw@svsu.ac.in)

For the latest schedules or activity calendars, please confirm with the **Dean DSW or club coordinators** directly as event dates may vary."""
        hinglish = """SVSU me **student clubs aur activities ka structured system** available hai, jo student-welfare side se supported hai.

- Curated SVSU student data me **17 student clubs/cells/committees** listed hain, jinme **NSS, Youth Red Cross, NCC, aur Cell for Differently Abled** bhi shamil hain
- Major options me **Technical Club, Sports and Adventure Club, Yoga Club, Literary Club, Cultural/Dramatics Club, Photography Club, Eco Club, Legal Literacy Club, Competitive Exam Club, Fine Arts Club, Psychological Guidance Club, aur Drug Prevention Club** listed hain
- Join karne ke liye student ko **relevant club ke faculty coordinators** se contact karna chahiye
- Dean Student Welfare: **Prof. (Dr.) Kulwant Singh** (dean.dsw@svsu.ac.in)

Latest schedule ya activity calendar ke liye **Dean DSW / relevant club coordinators** se confirm karna behtar rahega, kyunki events change ho sakte hain."""
        return select_language_reply(question, english, hinglish)

    if domain in {"Student Programs", "Administration", "Home"} and has_any_query_term(q, [
        "health centre", "health center", "medical", "doctor", "clinic", "nurse", "pharmacist"
    ]):
        english = """Yes, SVSU has a **University Health Centre** dedicated to student and staff welfare.

- The health centre looks after the medical needs of **students, staff, and their families**.
- Services include **first aid, blood pressure/temperature/blood sugar monitoring, doctor consultations, medicines, nebulizer facility, wheelchair support, and health camps**.
- Medical staff: **Ms. Jyoti Attri (Staff Nurse)** and **Mr. Hari Om (Pharmacist)**.
- Staff contacts: **9911001039** and **9050987172**.

For doctor availability or emergency support timings, it is best to check with the health-centre staff directly."""
        hinglish = """Haan, SVSU me ek dedicated **University Health Centre** hai.

- Health centre **students, staff, aur unke families** ki medical needs ka dhyan rakhta hai.
- Services me **first aid, blood pressure/sugar monitoring, doctor consultations, medicines, nebulizer, wheelchair support, aur health camps** shamil hain.
- Medical staff: **Ms. Jyoti Attri (Staff Nurse)** aur **Mr. Hari Om (Pharmacist)**.
- Contacts: **9911001039** aur **9050987172**.

Doctor ki availability ya emergency timing ke liye ek baar health-centre staff se direct confirm kar lena behtar rahega."""
        return select_language_reply(question, english, hinglish)

    if domain in {"Administration", "Student Programs", "Home"} and has_any_query_term(q, [
        "transport", "bus", "security", "transport and security"
    ]):
        english = """SVSU has a dedicated **Transport and Security Branch** to manage campus logistics.

- **Branch Head:** Mr. Parveen Kumar (Assistant Registrar).
- **Contact:** 0124-2746800
- **Email:** parveen.kumar78@svsu.ac.in

For specific route-wise bus timings or pickup points, please reach out to the transport branch directly as schedules are updated periodically."""
        hinglish = """SVSU me campus logistics ke liye ek dedicated **Transport and Security Branch** hai.

- **Branch Head:** Mr. Parveen Kumar (Assistant Registrar).
- **Contact:** 0124-2746800
- **Email:** parveen.kumar78@svsu.ac.in

Bus routes aur timings ki detailed information ke liye aap transport branch se direct sampark kar sakte hain."""
        return select_language_reply(question, english, hinglish)

    if domain in {"Administration", "Student Programs", "Home"} and has_any_query_term(q, [
        "placement", "placements", "career counselling", "career counseling", "career", "training and placement", "job"
    ]):
        english = """SVSU has a very active **Career Counselling and Placement Cell** that focuses on making students job-ready.

- The cell supports students in **soft skills development, career awareness, job readiness, and final placements**.
- Key members include **Dr. Ravinder Kumar, Dr. Preeti, and Dr. Lalit Kumar**.
- The university also has an **Industrial Relations & Alumni Affairs (IRAA)** wing led by **Dr. Vikas Singh Bhadoria** (Deputy TPO).

SVSU follows a strong industry-integrated model, ensuring high placement rates across vocational programs."""
        hinglish = """SVSU me ek bahut active **Career Counselling and Placement Cell** hai jo students ko job-ready banane par focus karta hai.

- Ye cell **soft skills, career awareness, aur placement support** provide karta hai.
- Team members: **Dr. Ravinder Kumar, Dr. Preeti, aur Dr. Lalit Kumar**.
- SVSU me **Industrial Relations & Alumni Affairs (IRAA)** wing bhi hai, jiske Deputy TPO **Dr. Vikas Singh Bhadoria** hain.

SVSU ka industry-integrated model vocational programs me behtareen placement ensure karta hai."""
        return select_language_reply(question, english, hinglish)

    if domain in {"Administration", "Student Programs", "Home"} and has_any_query_term(q, [
        "canteen", "cafeteria", "food court", "mess"
    ]) and "hostel" not in q:
        english = """SVSU provides canteen and cafeteria facilities for students and staff.

- Canteen-related records and notices are available in the university data.
- For current daily menus, pricing, or operational timings, it is best to check directly at the campus food court or contact the university helpline.

Official contacts: **info@svsu.ac.in** or **1800-1800-147**."""
        hinglish = """SVSU me students aur staff ke liye canteen aur cafeteria facilities available hain.

- University data me canteen-related notices aur records present hain.
- Aaj ke menu, pricing, ya timing ke liye campus food court me check karna ya helpline par contact karna sabse sahi rahega.

Official contacts: **info@svsu.ac.in** ya **1800-1800-147**."""
        return select_language_reply(question, english, hinglish)

    if domain in {"Admission", "Academics", "Home"} and has_any_query_term(q, [
        "fee", "fees", "tuition", "semester fee", "course fee", "fee structure"
    ]) and "hostel" not in q:
        english = """SVSU program fees are structured based on the specific course, level, and academic session.

- The official SVSU data contains the detailed **fee structure for the 2025-26 session**.
- Fee categories include **Diploma, B.Voc, B.Tech, BCA, BBA, MBA, PG Diploma, and others**.
- Hostel charges are separate from academic program fees.

Please specify the **exact course name** and **session** for precise fee details. For official confirmation, you can email **admissions@svsu.ac.in**."""
        hinglish = """SVSU ke programs ki fees unke course, level, aur academic session par depend karti hai.

- Official data me **session 2025-26 ki detailed fee structure** available hai.
- Isme **Diploma, B.Voc, B.Tech, BCA, BBA, MBA, PG Diploma** jaise sabhi programs ki list hai.
- Hostel fees academic fees se alag hoti hai.

Sahi jaankari ke liye please **exact course name** aur **session** batayein, ya **admissions@svsu.ac.in** par mail karein."""
        return select_language_reply(question, english, hinglish)

    if domain in {"Administration", "About", "Home"} and "registrar" in q:
        english = "The current officially verifiable **Registrar of SVSU** is **Prof. (Dr.) Jyoti Rana**. The available SVSU data also lists the registrar email as **registrar@svsu.ac.in**."
        hinglish = "Current officially verifiable **Registrar of SVSU** **Prof. (Dr.) Jyoti Rana** hain. Available SVSU data me registrar email **registrar@svsu.ac.in** listed hai."
        return select_language_reply(question, english, hinglish)

    if domain in {"Administration", "Student Programs", "Home"} and has_any_query_term(q, [
        "dean dsw", "dsw", "student welfare", "student wellfare", "scholarship"
    ]):
        english = """The **Dean Student Welfare (DSW)** at SVSU is **Prof. (Dr.) Kulwant Singh**.

- The DSW office handles **student welfare, scholarships, travel allowances, and extracurricular activities**.
- Contact Email: **dean.dsw@svsu.ac.in**.

If you need specific guidance on scholarships or student clubs, feel free to ask!"""
        hinglish = """SVSU me **Dean Student Welfare (DSW)** **Prof. (Dr.) Kulwant Singh** hain.

- DSW office **student welfare, scholarships, travel allowances, aur extracurricular activities** ko manage karta hai.
- Contact Email: **dean.dsw@svsu.ac.in**.

Agar aapko scholarship ya clubs ke baare me kuch aur poochna hai, toh batayein!"""
        return select_language_reply(question, english, hinglish)

    if domain in {"Administration", "About", "Home"} and ("vice chancellor" in q or re.search(r"\bvc\b", q)):
        english = "The current officially verifiable **Vice Chancellor of SVSU** is **Professor (Dr.) Dinesh Kumar**. According to the available SVSU data, he assumed charge on **May 26, 2025**, and the VC office email listed in the data is **vcoffice@svsu.ac.in**."
        hinglish = "Current officially verifiable **Vice Chancellor of SVSU** **Professor (Dr.) Dinesh Kumar** hain. Available SVSU data ke hisaab se unhone **May 26, 2025** ko charge assume kiya tha, aur listed VC office email **vcoffice@svsu.ac.in** hai."
        return select_language_reply(question, english, hinglish)

    if domain in {"Administration", "About", "Contact", "Home", "Admission"} and has_any_query_term(q, [
        "contact", "phone", "email", "helpline", "address", "location", "where is", "campus", "office"
    ]):
        english = """Here are the core **SVSU contact details** for your reference:

- **Admission Helpline:** 1800-1800-147
- **Admission Email:** admissions@svsu.ac.in
- **General Support:** info@svsu.ac.in
- **Main Campus:** Village Dudhola, District Palwal, Haryana.
- **Transit Campus:** 2nd and 3rd Floor, Plot No. 147, Sector-44, Gurugram, Haryana.
- **Landline:** 0124-2746800

If you need the contact for a specific department (like DSW, Registrar, or VC office), please let me know."""
        hinglish = """Aapki help ke liye **SVSU ke core contact details** yahan diye gaye hain:

- **Admission Helpline:** 1800-1800-147
- **Admission Email:** admissions@svsu.ac.in
- **General Support:** info@svsu.ac.in
- **Main Campus:** Village Dudhola, District Palwal, Haryana.
- **Transit Campus:** Plot No. 147, Sector-44, Gurugram, Haryana.
- **Landline:** 0124-2746800

Agar aapko kisi specific department (jaise DSW ya Registrar office) ka contact chahiye, toh bataiye."""
        return select_language_reply(question, english, hinglish)

    return ""

def extract_user_request_text(question: str) -> str:
    text = str(question or "")
    if "USER REQUEST:" in text:
        return text.rsplit("USER REQUEST:", 1)[-1].strip()
    return text.strip()

def dedupe_preserve_order(items):
    deduped = []
    seen = set()
    for item in items:
        if item and item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped

def chunk_text_for_retrieval(text: str, max_chars: int = 1400):
    chunks = []
    current_lines = []
    current_len = 0

    def flush_current():
        nonlocal current_lines, current_len
        chunk = "\n".join(current_lines).strip()
        if chunk:
            chunks.append(chunk)
        current_lines = []
        current_len = 0

    for raw_line in str(text or "").replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            if current_lines and current_lines[-1] != "":
                current_lines.append("")
            continue

        is_heading = line.startswith("===") or line.startswith("---") or line.upper().startswith("DOCUMENT:")
        line_len = len(line) + 1

        if is_heading and current_lines:
            flush_current()

        if current_len and current_len + line_len > max_chars:
            flush_current()

        current_lines.append(line)
        current_len += line_len

    flush_current()
    return chunks

def extract_query_signals(question: str, domain: str):
    normalized_question = normalize_catalog_text(question)
    if not normalized_question:
        return "", [], []

    stop_words = {
        "this", "that", "what", "where", "when", "how", "who", "is", "are",
        "the", "a", "an", "tell", "about", "please", "give", "me", "of",
        "for", "in", "on", "to", "and", "do", "does", "with", "there",
        "any", "can", "you", "svsu", "university", "detail", "details",
    }

    keywords = [token for token in normalized_question.split() if len(token) >= 3 and token not in stop_words]
    expanded_keywords = list(keywords)

    for trigger, related_terms in QUERY_SYNONYM_EXPANSIONS.items():
        if trigger in normalized_question:
            for related in related_terms:
                expanded_keywords.extend(
                    token for token in normalize_catalog_text(related).split()
                    if len(token) >= 2 and token not in stop_words
                )

    deduped_keywords = dedupe_preserve_order(expanded_keywords)

    phrases = []
    meaningful_tokens = [token for token in normalized_question.split() if token not in stop_words]
    if len(meaningful_tokens) >= 2:
        phrases.append(" ".join(meaningful_tokens[: min(len(meaningful_tokens), 6)]))
        for i in range(len(meaningful_tokens) - 1):
            phrase = f"{meaningful_tokens[i]} {meaningful_tokens[i + 1]}"
            if len(phrase) >= 6:
                phrases.append(phrase)

    return normalized_question, dedupe_preserve_order(deduped_keywords), dedupe_preserve_order(phrases)

def get_live_context_urls(domain: str, question: str):
    if domain != "Home":
        return DOMAIN_MAPPING.get(domain, DOMAIN_MAPPING["Home"])

    normalized_question = normalize_catalog_text(question)
    selected_urls = [
        "https://svsu.ac.in/",
        "https://svsu.ac.in/about-us",
        "https://svsu.ac.in/contact-us",
    ]

    for triggers, urls in HOME_QUERY_URL_HINTS:
        if any(trigger in normalized_question for trigger in triggers):
            selected_urls.extend(urls)

    if len(selected_urls) <= 3:
        selected_urls.extend([
            "https://svsu.ac.in/academics",
            "https://svsu.ac.in/student-corner",
            "https://svsu.ac.in/administration",
        ])

    return dedupe_preserve_order(selected_urls)[:6]

def build_retrieved_context_sections(snippets: list):
    if not snippets:
        return "", ""

    priority_sources = {"CUSTOM_FACTS", "CORE_FACTS"}
    priority_blocks = []
    supporting_blocks = []

    for snippet in snippets:
        block = f"SOURCE: {snippet['source']}\n{snippet['text'][:2400].strip()}"
        if snippet["source"] in priority_sources:
            priority_blocks.append(block)
        else:
            supporting_blocks.append(block)

    priority_context = "\n\n---\n\n".join(priority_blocks)
    supporting_context = "\n\n---\n\n".join(supporting_blocks)
    return priority_context, supporting_context

def get_answer_format_guidance(question: str, domain: str) -> str:
    q = normalize_catalog_text(question)
    
    if any(token in q for token in ["to the point", "short", "direct", "brevity", "pointwise", "to-the-point"]):
        return (
            "CRITICAL FORMAT RULE: Your response must be extremely brief and 'to the point'. "
            "Maximum 2-3 sentences total. No headers. No 'Verified Details'. No fluff. "
            "Just the answer."
        )

    if any(token in q for token in ["club", "clubs", "society", "transport", "health", "medical", "placement", "career", "canteen", "cafeteria"]):
        return (
            "FORMAT RULE: Start with a clear answer. Then add a clean bulleted list "
            "of verified details. Keep it professional."
        )

    if any(token in q for token in ["who", "kya", "kaun", "vice chancellor", "registrar", "contact", "phone", "email"]):
        return (
            "FORMAT RULE: Provide a direct answer followed by a short bulleted list of details if needed."
        )

    if any(token in q for token in ["fee", "fees", "hostel", "library", "timing", "time", "eligibility", "seat", "seats", "duration"]):
        return (
            "FORMAT RULE: Start with a short answer, then give a clean bullet list "
            "of the verified values. Prefer exact numbers, dates, timings, and contacts."
        )

    if any(token in q for token in ["best", "compare", "difference", "overview", "about", "department", "tell"]):
        return (
            "FORMAT RULE: Provide a concise overview followed by specific verified points in bullets."
        )

    if domain in {"Home", "About", "Administration", "Student Programs", "Library", "Research"}:
        return (
            "FORMAT RULE: Give a concise direct answer first, then add a compact contextual "
            "section with only the most relevant verified supporting points."
        )

    return (
        "FORMAT RULE: Answer directly in the first 1-2 lines. Use short sections or bullets "
        "only when they improve clarity."
    )

def build_grounded_fallback_context(core_facts: str, priority_context: str, supporting_context: str, crawled_context: str) -> str:
    parts = []
    if priority_context:
        parts.append("[PRIORITY KNOWLEDGE]\n" + priority_context[:5000])
    if supporting_context:
        parts.append("[SUPPORTING KNOWLEDGE]\n" + supporting_context[:5000])
    if crawled_context:
        parts.append("[LIVE WEBSITE CONTEXT]\n" + crawled_context[:3500])
    if core_facts:
        parts.append("[CORE FACTS]\n" + core_facts[:2500])
    return "\n\n".join(part for part in parts if part).strip()

# --- GLOBAL KNOWLEDGE CACHE (Optimized for Advanced Agent performance) ---
KNOWLEDGE_CHUNKS = []
LAST_CACHE_UPDATE = 0
CACHE_TTL = 3600 # 1 hour

def refresh_knowledge_cache(force: bool = False):
    global KNOWLEDGE_CHUNKS, LAST_CACHE_UPDATE, PROGRAM_SOURCE_DOCUMENTS, PROGRAM_CATALOG_CACHE, STRUCTURED_PROGRAM_CATALOG_CACHE
    current_time = time.time()
    if not force and KNOWLEDGE_CHUNKS and (current_time - LAST_CACHE_UPDATE < CACHE_TTL):
        return

    if force:
        PROGRAM_SOURCE_DOCUMENTS = None
        PROGRAM_CATALOG_CACHE = None
        STRUCTURED_PROGRAM_CATALOG_CACHE = None
    
    print("[CACHE] Refreshing Advanced Knowledge Base...")
    try:
        ensure_knowledge_store_ready(force=False)
    except Exception as e:
        print(f"[CACHE] Structured knowledge store check skipped: {e}")

    db_chunks = load_runtime_knowledge_chunks()
    if db_chunks:
        KNOWLEDGE_CHUNKS = db_chunks
        LAST_CACHE_UPDATE = current_time
        print(f"[CACHE] Loaded {len(db_chunks)} chunks from structured knowledge store.")
        return

    new_chunks = []
    seen_chunk_keys = set()

    base_dir = os.path.dirname(__file__)
    candidate_data_dirs = dedupe_preserve_order([
        os.path.normpath(os.path.join(base_dir, "..", "data")),
        os.path.normpath(os.path.join(base_dir, "..", "..", "data")),
    ])

    candidate_paths = []
    for data_dir in candidate_data_dirs:
        if not os.path.exists(data_dir):
            continue
        for filename in sorted(os.listdir(data_dir)):
            if filename.endswith("_knowledge.txt") or filename in {"svsu_all_programs_list.txt", "custom_facts.txt"}:
                path = os.path.join(data_dir, filename)
                source = filename.replace("_knowledge.txt", "").replace(".txt", "").upper()
                candidate_paths.append((path, source))

    core_facts_path = os.path.normpath(os.path.join(base_dir, "..", "core_facts.txt"))
    if os.path.exists(core_facts_path):
        candidate_paths.append((core_facts_path, "CORE_FACTS"))

    for path, source in candidate_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        for chunk_text in chunk_text_for_retrieval(content):
            title = next((line.strip() for line in chunk_text.splitlines() if line.strip()), "")[:160]
            chunk_key = (source, normalize_catalog_text(title), normalize_catalog_text(chunk_text[:220]))
            if chunk_key in seen_chunk_keys:
                continue
            seen_chunk_keys.add(chunk_key)
            new_chunks.append({
                "text": chunk_text,
                "source": source,
                "lower": normalize_catalog_text(chunk_text),
                "title": title,
                "title_lower": normalize_catalog_text(title),
                "priority": BASE_SOURCE_PRIORITIES.get(source, 100),
            })
    
    KNOWLEDGE_CHUNKS = new_chunks
    LAST_CACHE_UPDATE = current_time

def perform_hybrid_retrieval(question: str, domain: str, top_n: int = 15):
    """Deep Hybrid Search: Combines FTS5 Database ranking with CPU-intensive local heuristic scoring."""
    normalized_question, keywords, phrases = extract_query_signals(question, domain)
    if not keywords and not normalized_question:
        return []

    # 1. DATABASE FTS5 SEARCH (High Authority)
    db_results = []
    try:
        # Get up to 25 raw matches from FTS index
        db_results = search_knowledge_store(question, limit=25)
    except Exception as e:
        print(f"[RETRIEVAL] DB Search Error: {e}")

    # Map chunk_ids to their FTS5 rank scores for boosting
    fts_chunk_ids = {r['chunk_id']: r['rank_score'] for r in db_results if 'chunk_id' in r}

    domain_boosts = DOMAIN_SOURCE_BOOSTS.get(domain, {})
    scored_snippets = []

    for chunk in KNOWLEDGE_CHUNKS:
        chunk_id = chunk.get("chunk_id", "")
        # Note: chunk_id in KNOWLEDGE_CHUNKS is built from:
        # hashlib.sha1(f"{doc['source_key']}|{chunk_index}|{normalized_content[:500]}".encode("utf-8")).hexdigest()
        # This matches what is in the DB.
        
        section_lower = chunk["lower"]
        title_lower = chunk.get("title_lower", "")
        
        # Base score from DB Rank or default
        score = chunk.get("priority", 0) + domain_boosts.get(chunk["source"], 0)
        
        # FTS5 Boost (BM25 rank score is usually negative, smaller is better)
        if chunk_id in fts_chunk_ids:
            # We convert negative rank to positive boost
            rank_val = fts_chunk_ids[chunk_id]
            boost = max(50, 200 - (rank_val * 10)) # Heuristic boost
            score += boost
            # print(f"[FTS BOOST] Applied {boost} to chunk {chunk_id[:8]}")

        matched_keywords = set()
        matched_phrases = 0

        if normalized_question and normalized_question in section_lower:
            score += 150 # Significant direct match boost

        for phrase in phrases:
            if phrase and phrase in section_lower:
                matched_phrases += 1
                score += 40
                if phrase in title_lower:
                    score += 30

        for kw in keywords:
            # Use regex for word boundaries to avoid partial matches (e.g. 'art' matching 'part')
            word_matches = re.findall(rf'\b{re.escape(kw)}\b', section_lower)
            if word_matches:
                matched_keywords.add(kw)
                score += 20 + (min(len(word_matches), 10) * 5)
                if kw in title_lower:
                    score += 25

        if not matched_keywords and not matched_phrases and chunk_id not in fts_chunk_ids and not (normalized_question and normalized_question in section_lower):
            continue

        # Penalize general PDF snippets if they are just page numbers or generic footers
        if chunk["source"] == "PDF" and len(section_lower) < 150:
            score -= 40

        final_score = score + (len(matched_keywords) * 20) + (matched_phrases * 15)
        
        scored_snippets.append({
            "text": chunk["text"],
            "score": final_score,
            "source": chunk["source"],
            "title": chunk.get("title", ""),
        })
    
    scored_snippets.sort(key=lambda x: x["score"], reverse=True)
    
    unique_texts = set()
    top_final_snippets = []
    for item in scored_snippets:
        # Fuzzy deduplication by first 120 chars
        text_hash = normalize_catalog_text(item["text"][:120])
        if text_hash not in unique_texts:
            unique_texts.add(text_hash)
            top_final_snippets.append(item)
        if len(top_final_snippets) >= top_n:
            break
    return top_final_snippets

async def execute_domain_agent(domain: str, question: str, history: list = None, mode: str = "intelligent") -> str:
    """Advanced Domain Agent with Thread-Safe Hybrid Retrieval and Deep Synthesis."""
    refresh_knowledge_cache()
    
    print(f"[ADVANCED AGENT] '{domain}' Agent triggered | Mode: {mode}")
    raw_user_question = extract_user_request_text(question)

    direct_guardrail = get_program_availability_guardrail(raw_user_question, domain)
    if direct_guardrail:
        print(f"[PROGRAM GUARDRAIL] Direct verified response returned for domain '{domain}'")
        return direct_guardrail

    direct_verified_answer = get_verified_program_recommendation(raw_user_question, domain)
    if direct_verified_answer:
        print(f"[PROGRAM GUIDE] Direct verified recommendation returned for domain '{domain}'")
        return direct_verified_answer

    direct_department_answer = get_verified_department_directory_info(raw_user_question, domain)
    if direct_department_answer:
        print(f"[DEPARTMENT GUIDE] Direct verified directory response returned for domain '{domain}'")
        return direct_department_answer

    direct_general_answer = get_verified_general_info(raw_user_question, domain)
    if direct_general_answer:
        print(f"[GENERAL GUIDE] Direct verified response returned for domain '{domain}'")
        return direct_general_answer
    
    # --- STRICT ADMISSION GATEKEEPER ---
    if domain == "Admission":
        admission_keywords = {
            "fee", "fees", "admission", "apply", "form", "eligibility", "date", "dates", "seat", "seats", "intake", 
            "counselor", "counselling", "scholarship", "course", "program", "programmes", "detail", "details", "jankari", "bata"
        }
        q_tokens = set(normalize_catalog_text(raw_user_question).split())
        is_admission_topic = any(kw in q_tokens for kw in admission_keywords) or find_exact_official_program(raw_user_question)
        
        if not is_admission_topic:
            print(f"[ADMISSION GATE] Off-topic query detected in Admission domain. Redirecting...")
            english = "You are currently in the **Admission Query** section. For general university information, VC details, administration, or other queries, please click the **Menu (hamburger icon)** at the top right and switch to the **'Others Query'** section.\n\nFor official admission help, you can contact: **admissions@svsu.ac.in** or call **1800-1800-147**."
            hinglish = "Aap abhi **Admission Query** section mein hain. University ki baaki jaankari (VC details, admin, etc.) ke liye kripya upar right corner mein **Menu (hamburger icon)** par click karein aur **'Others Query'** section par switch karein.\n\nOfficial admission help ke liye aap **admissions@svsu.ac.in** ya **1800-1800-147** par sampark kar sakte hain."
            return select_language_reply(raw_user_question, english, hinglish)
    # -----------------------------------
    
    # 1. RETRIEVAL (Offload heavy CPU work to thread executor)
    loop = asyncio.get_event_loop()
    # Optimized depth for speed and relevance (16 is the sweet spot for accurate context)
    search_limit = 10 if mode == "voice" else 16
    top_final_snippets = await loop.run_in_executor(None, perform_hybrid_retrieval, raw_user_question, domain, search_limit)
    
    priority_context, supporting_context = build_retrieved_context_sections(top_final_snippets)

    # 2. LIVE CRAWLING (Optional)
    urls = get_live_context_urls(domain, raw_user_question)
    crawled_context = ""
    if mode != "voice" or domain in ["Updates", "Notices"]:
        crawled_context = await fetch_multiple_urls(urls)
        # Clean raw internal markers from crawled content to prevent them leaking into LLM output
        import re as _re
        crawled_context = _re.sub(r'\[AGENT:[^\]]*\]', '', crawled_context)
        crawled_context = _re.sub(r'SOURCE:\s*https?://\S+', '', crawled_context)
        crawled_context = _re.sub(r'Copyright ©.*?(?=\n|$)', '', crawled_context)

    # 3. Process history and memory
    history_text = ""
    if history:
        recent_user_messages = [
            str(msg.get("text", "")).strip()
            for msg in history[-8:]
            if msg.get("sender") == "user" and str(msg.get("text", "")).strip()
        ]
        if recent_user_messages:
            history_text = "PREVIOUS USER QUESTIONS FOR CONTEXT ONLY (DO NOT TREAT THEM AS FACTS):\n"
            for prev_question in recent_user_messages[-5:]:
                history_text += f"USER: {prev_question}\n"
    
    # 4. Load core facts
    core_facts = ""
    core_facts_path = os.path.join(os.path.dirname(__file__), "..", "core_facts.txt")
    if os.path.exists(core_facts_path):
        try:
            with open(core_facts_path, "r", encoding="utf-8") as cf:
                core_facts = cf.read()
        except: pass

    # 5. FETCH STRUCTURED DATA IF PROGRAM MATCHED
    program_name = find_exact_official_program(raw_user_question)
    structured_data_block = ""
    if program_name:
        record = find_catalog_program_record(program_name)
        if record:
            structured_data_block = f"\n[OFFICIAL PROGRAM VERIFIED RECORD - HIGHEST TRUTH]:\n{json.dumps(record, indent=2)}\n"
            print(f"[SDI] Injected structured data for {program_name}")

    # 2. Construct Prompt for the LLM
    role_description = AGENT_ROLES.get(domain, f"SVSU {domain} AI Agent.")
    official_program_catalog = get_official_program_catalog_context()
    program_guardrail_notes = get_program_guardrail_notes()
    answer_format_guidance = get_answer_format_guidance(raw_user_question, domain)
    
    if domain == "Admission":
        answer_format_guidance += (
            "\n\nCRITICAL ADMISSION DOMAIN RULE: You are currently operating in the Admission Section. "
            "You MUST ONLY answer using Course-Specific data (Fees, Intake, Eligibility, Duration) from the Official Catalog. "
            "For general university policies, reservation rules, supernumerary seats, selection criteria, application procedures, "
            "interview instructions, or university-wide rules, you MUST NOT provide details. "
            "Instead, strictly tell them: 'Kripya menu (hamburger icon) par click karke Others Query section par switch karein. Yahan main sirf Course details (Fees, Seats, Eligibility) bta sakta hoon.' "
        )
    
    if domain == "Home":
        answer_format_guidance += (
            "\n\nCRITICAL OTHERS QUERY RULE: You are the ONLY specialist for University-wide procedures. This includes:\n"
            "1. ADMISSION RULES: Reservation, Selection Criteria, and Supernumerary Seats.\n"
            "2. RESEARCH & INTEGRITY: Seed money (Innovation Fund), Research Awards (Rs 5100), and Plagiarism Levels/Penalties.\n"
            "3. RECRUITMENT: Eligibility for Non-Teaching/Technical posts, pay scales, and promotion quotas (Seniority-cum-Merit).\n"
            "4. ADMINISTRATION: Details of EC/Court/Finance Committees, Registrar/Dean offices, IT Cell, and departmental directories.\n"
            "5. INNOVATION (SUPER 30): 6-month EDP program with SIDBI, incubation support, and success stories of current student startups.\n"
            "6. DAKSH: Specialized competitive exam coaching (UPSC/SSC) with scholarships up to 90% and guidance by IAS/IPS officers.\n"
            "7. INTERNATIONAL: 5% seat reservation, AIU equivalence, and Visa requirements.\n"
            "Always identify the specific faculty member or officer (e.g., Registrar, Dean, Proctor, IT Incharge) mentioned in the snippets so the student knows exactly whom to contact."
        )

    system_prompt = f"""You are the {role_description}. You are the Senior AI Counselor for SVSU (Shri Vishwakarma Skill University), powered by a Deep Reasoning engine.

### THE THINKING PROTOCOL (THINK BEFORE YOU SPEAK):
1. **DEEP SCAN**: Analyze the user's query against ALL provided knowledge snippets (Research, Recruitment, Admin, DAKSH, Super 30, etc.).
2. **SOURCE SYNTHESIS**: If a query touches multiple areas (e.g., 'How to get a job and do research?'), synthesize answers from both 'RECRUITMENT' and 'RESEARCH' snippets.
3. **IDENTIFY STAKEHOLDERS**: Always identify the specific official (Registrar, Dean, Nodal Officer) responsible for the queried area to ensure the student has a physical point of contact.
4. **REASONING CHAIN**: Formulate a step-by-step logic in your "mind" before writing. For example: "The user is asking about plagiarism. Level 1 is up to 40%. Penalty is X. I should also mention the Nodal Officer."

### CORE OPERATING PRINCIPLES:
1. **UNDERSTAND & ANALYZE**: Do not just dump data. Acknowledge the user's specific context. Provide a coherent, expert-led response that feels like a mentor speaking to a student.
2. **EASY & TO-THE-POINT**: Your answers must be **Easy to Understand** and **Directly to the Point**. Avoid unnecessary filler text. If a procedure has steps, list them clearly (1, 2, 3).
3. **PREMIUM FORMATTING**: Use **Bold Text** for key terms, dates, and names. Use Bullet Points for lists to make the answer scannable and professional.
4. **TRUTH HIERARCHY**: [OFFICIAL PROGRAM VERIFIED RECORD] is your ABSOLUTE HIGHEST SOURCE OF TRUTH. Use it over anything else.
5. **ZERO HALLUCINATION**: If the information is not in the 'SVSU_KNOWLEDGE' snippets provided below, DO NOT guess. Use the official fallback.
6. **LANGUAGE MIRRORING**: Default to professional English. For Hindi/Hinglish queries, respond in warm, professional Hinglish.
7. **BRAND ADVOCACY**: SVSU is India's FIRST Government Skill University. Highlight its industry-linkage, practical 'Dual Education' model, and world-class infrastructure.
8. **PROACTIVE COUNSELING**: If someone asks about DAKSH, also mention the scholarship opportunity. If someone asks about Recruitment, mention the 'Seniority-cum-Merit' principle if applicable.
9. **OTHERS QUERY FALLBACK**: If the answer is NOT in context, professionally inform the user: 'The specific information is currently unavailable in my records. You may visit the university campus to physically meet the respective Dean or Chairperson of the department for detailed clarification.'

[QUESTION-SPECIFIC RESPONSE FORMAT]:
{answer_format_guidance}

UNIVERSITY CORE KNOWLEDGE:
{core_facts if core_facts else '- Admission Helpline: 1800-1800-147'}

{structured_data_block}

[OFFICIAL CURRENT PROGRAM CATALOG]:
{official_program_catalog}

[PROGRAM AVAILABILITY GUARDRAILS]:
{program_guardrail_notes}

### DATA CONNECTIVITY:
You are directly connected to the 'SVSU_KNOWLEDGE' engine which indexes all University PDFs, CSVs, and structured JSONs. Always look for specific details in the snippets provided below.

[PRIORITY SVSU KNOWLEDGE]:
{priority_context[:8000] if priority_context else 'No extra priority manual knowledge found for this query.'}

[SVSU KNOWLEDGE BANK SNIPPETS]:
{supporting_context[:12000] if supporting_context else 'No additional domain snippets found for this query.'}

[LIVE WEBSITE CONTEXT]:
{crawled_context[:5000]}

[ACTIVE CONVERSATION MEMORY]:
{history_text}
"""
    try:
        # Use 3.3-70b for maximum reasoning quality as requested by user ("acche ans. de rha tha")
        primary_model = "llama-3.1-8b-instant"
        max_tokens_val = 256 if mode == "voice" else 1500 # Optimized for speed
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"USER REQUEST: {raw_user_question}"}
        ]
        
        # Increase timeout back to 25s for 70b model + large context
        return await asyncio.wait_for(
            call_groq_with_retry(messages, model=primary_model, max_tokens=max_tokens_val),
            timeout=25
        )
    except asyncio.TimeoutError:
        print(f"[TIMEOUT] Domain Agent '{domain}' timed out after 25s. Attempting quick fallback...")
    except Exception as e:
        print(f"[ERROR] LLM Request failed in {domain} Agent: {e}")

    # ─── EMERGENCY FALLBACK: Quick direct answer with only core facts ───
    try:
        grounded_fallback_context = build_grounded_fallback_context(
            core_facts=core_facts,
            priority_context=priority_context,
            supporting_context=supporting_context,
            crawled_context=crawled_context,
        )
        fallback_messages = [
            {
                "role": "system",
                "content": (
                    "You are SVSU AI. Answer only from the grounded official context below. "
                    "Provide a clear, direct answer in the first line, followed by bulleted details if useful. "
                    "Do not use internal labels like 'Direct Answer' or 'Verified Details'. "
                    "If a detail is not verifiable, say you could not verify it and provide contact: admissions@svsu.ac.in.\n\n"
                    f"{grounded_fallback_context}"
                ),
            },
            {"role": "user", "content": raw_user_question}
        ]
        print(f"[FALLBACK] Attempting fast direct Groq call for '{domain}'...")
        return await asyncio.wait_for(
            call_groq_with_retry(fallback_messages, model="llama-3.1-8b-instant", max_tokens=512),
            timeout=10
        )
    except Exception as fe:
        print(f"[FALLBACK FAILED] {fe}")
        return "\u26a0️ I am unable to fetch a response right now. For university queries, please contact **SVSU Helpdesk: 1800-1800-147** or email **admissions@svsu.ac.in**."
