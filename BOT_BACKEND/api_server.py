import os
import json
import base64
import uuid
import smtplib
import re
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, File, UploadFile, BackgroundTasks, Request

from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import mimetypes
import pandas as pd
# Heavy imports (edge_tts, groq) will be imported locally inside functions

mimetypes.add_type('model/gltf-binary', '.glb')
mimetypes.add_type('model/gltf+json', '.gltf')

# Standardized Project Path Logic
if "TRANSFORMERS_OFFLINE" in os.environ:
    del os.environ["TRANSFORMERS_OFFLINE"]
if "HF_HUB_OFFLINE" in os.environ:
    del os.environ["HF_HUB_OFFLINE"]

CURRENT_FILE_PATH = os.path.abspath(__file__)
BASE_DIR = os.path.dirname(CURRENT_FILE_PATH)
print(f"DEBUG: CURRENT_FILE_PATH={CURRENT_FILE_PATH}")
print(f"DEBUG: BASE_DIR={BASE_DIR}")

# Detect if in BOT_BACKEND folder
if "BOT_BACKEND" in BASE_DIR:
    ROOT_DIR = os.path.dirname(BASE_DIR)
else:
    ROOT_DIR = BASE_DIR

print(f"DEBUG: ROOT_DIR={ROOT_DIR}")

# Load .env
env_path = os.path.join(ROOT_DIR, ".env")
load_dotenv(env_path) if os.path.exists(env_path) else load_dotenv()

app = FastAPI()

@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/admin_panel/chatbot.html?v=cloudfix-20260416")

@app.get("/chatbot")
async def chatbot_redirect():
    return RedirectResponse(url="/admin_panel/chatbot.html")

@app.get("/widget")
async def widget_mode():
    return FileResponse("assets/avatar.html")

NO_CACHE_PATHS = {
    "/admin",
    "/talk",
    "/admin_panel/chatbot.html",
    "/admin_panel/admin.html",
    "/admin_panel/admin_dashboard.html",
    "/admin_panel/talk.html",
    "/assets/widget.js",
}

@app.middleware("http")
async def disable_cache_for_ui(request: Request, call_next):
    response = await call_next(request)
    if request.url.path in NO_CACHE_PATHS:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

try:
    from agentic_system.monitoring_agent import start_monitoring
    from agentic_system.evolution_agent import evolution_process
    from agentic_system.domain_agents import refresh_knowledge_cache
    from agentic_system.knowledge_store import (
        ensure_knowledge_store_ready,
        get_knowledge_store_overview,
        search_knowledge_store,
        get_knowledge_document_details,
        get_knowledge_db_path,
    )
    import asyncio

    @app.on_event("startup")
    async def startup_event():
        start_monitoring()
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, ensure_knowledge_store_ready)
        loop.run_in_executor(None, refresh_knowledge_cache)
        print("[SERVER] Advanced Knowledge Base Initialized.")
except ImportError as e:
    print(f"Monitoring/Domain Agent not available: {e}")
    # Fallback if evolution_process also fails to import
    try:
        from agentic_system.evolution_agent import evolution_process
        from agentic_system.domain_agents import refresh_knowledge_cache
        from agentic_system.knowledge_store import (
            ensure_knowledge_store_ready,
            get_custom_facts_text,
            upsert_custom_facts,
            get_knowledge_store_overview,
            search_knowledge_store,
            get_knowledge_document_details,
            get_knowledge_db_path,
        )
    except:
        async def evolution_process(*args, **kwargs): pass
        def refresh_knowledge_cache(*args, **kwargs): return None
        def ensure_knowledge_store_ready(*args, **kwargs): return {}
        def get_custom_facts_text(): return ""
        def upsert_custom_facts(*args, **kwargs): return None
        def get_knowledge_store_overview(): return {}
        def search_knowledge_store(*args, **kwargs): return []
        def get_knowledge_document_details(*args, **kwargs): return None
        def get_knowledge_db_path(): return ""
else:
    from agentic_system.knowledge_store import (
        get_custom_facts_text,
        upsert_custom_facts,
        get_knowledge_store_overview,
        search_knowledge_store,
        get_knowledge_document_details,
        get_knowledge_db_path,
    )

ADMIN_DIR = os.path.join(ROOT_DIR, "admin_panel")
ASSETS_DIR = os.path.join(ROOT_DIR, "assets")
OPERATIONAL_DIR = os.path.join(ROOT_DIR, "SVSU_KNOWLEDGE", "Operational")

print(f"DEBUG: ADMIN_DIR={ADMIN_DIR}")
print(f"DEBUG: ASSETS_DIR={ASSETS_DIR}")
print(f"DEBUG: OPERATIONAL_DIR={OPERATIONAL_DIR}")

# Robust fallback for mounted directories
if not os.path.exists(ADMIN_DIR):
    ADMIN_DIR = os.path.join(BASE_DIR, "admin_panel")

print(f"STITCH LOG: ROOT_DIR is {ROOT_DIR}")
print(f"STITCH LOG: ADMIN_DIR is {ADMIN_DIR}")

if not os.path.exists(ADMIN_DIR):
    os.makedirs(ADMIN_DIR, exist_ok=True)
if not os.path.exists(ASSETS_DIR):
    os.makedirs(ASSETS_DIR, exist_ok=True)
if not os.path.exists(OPERATIONAL_DIR):
    os.makedirs(OPERATIONAL_DIR, exist_ok=True)

app.mount("/admin_panel", StaticFiles(directory=ADMIN_DIR), name="admin_panel")
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# Create temp directories for audio processing
if not os.path.exists("data"): os.makedirs("data")
if not os.path.exists("temp_audio"): os.makedirs("temp_audio")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Groq Client Initialization
groq_client = None

def get_groq_client():
    from groq import Groq

    global groq_client
    if groq_client is None:
        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return groq_client

# SVSU Agentic Framework Initialization
import sys
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

LEADS_FILE = os.path.join(OPERATIONAL_DIR, "leads.csv")
APPLICATIONS_FILE = os.path.join(OPERATIONAL_DIR, "applications.csv")
ENGAGEMENTS_FILE = os.path.join(OPERATIONAL_DIR, "engagements.csv")
LEAD_COLUMNS = [
    "lead_id", "name", "email", "mobile", "designation", "purpose", "bot_type",
    "timestamp", "created_at", "updated_at", "stage", "latest_course",
    "application_count", "last_application_at"
]
APPLICATION_COLUMNS = [
    "app_id", "lead_id", "name", "email", "mobile", "state", "city", "course", "qualification",
    "passing_year", "percentage", "user_query", "timestamp", "source_bot", "purpose"
]
ENGAGEMENT_COLUMNS = [
    "event_id", "lead_id", "email", "mobile", "bot_type", "purpose", "timestamp"
]

class LeadData(BaseModel):
    lead_id: str = ""
    name: str
    email: str
    mobile: str
    designation: str = ""
    purpose: str
    bot_type: str = "intelligent"

class ApplicationData(BaseModel):
    lead_id: str = ""
    name: str
    email: str
    mobile: str
    state: str = ""
    city: str
    course: str
    qualification: str
    passing_year: str
    percentage: str = ""
    user_query: str = ""
    timestamp: str = ""
    source_bot: str = ""
    purpose: str = "admission"

class NotifyResultData(BaseModel):
    name: str
    email: str
    program: str
    semester: str

class ChatRequest(BaseModel):
    question: str
    mode: str = "general"
    history: list = []
    user_id: str = None
    selected_program: str | None = None

class TrafficLog(BaseModel):
    bot_type: str = "general"
    client_id: str = ""
    page_url: str = ""


class CustomEmailRequest(BaseModel):
    to_email: str
    subject: str
    body: str
class KnowledgeData(BaseModel):
    facts: str

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}$")
ADMISSION_CONTACT_EMAIL = "admissions@svsu.ac.in"
ADMISSION_CONTACT_HELPLINE = "1800-1800-147"
ADMISSION_LEVEL_ORDER = ["Diploma", "UG Certificate", "Undergraduate", "Postgraduate"]
ADMISSION_CATALOG_PATHS = [
    os.path.join(ROOT_DIR, "SVSU_KNOWLEDGE", "Structured_Data", "official_admission_program_catalog_2025_26.json"),
    os.path.join(ROOT_DIR, "BOT_BACKEND", "data", "official_admission_program_catalog_2025_26.json"),
    os.path.join(BASE_DIR, "data", "official_admission_program_catalog_2025_26.json"),
]
PROGRAM_DATA_COVERAGE_PATHS = [
    os.path.join(ROOT_DIR, "SVSU_KNOWLEDGE", "Structured_Data", "program_data_coverage_report.json"),
    os.path.join(BASE_DIR, "data", "program_data_coverage_report.json"),
]
_ADMISSION_CATALOG_CACHE = {"path": "", "mtime": 0.0, "payload": None}
_PROGRAM_DATA_COVERAGE_CACHE = {"path": "", "mtime": 0.0, "payload": None}

CHATS_COUNT_FILE = os.path.join(OPERATIONAL_DIR, "chats_count.txt")
TRAFFIC_FILE = os.path.join(OPERATIONAL_DIR, "traffic.csv")
TRAFFIC_COLUMNS = ["bot_type", "timestamp", "client_id", "ip", "user_agent", "page_url"]
TRAFFIC_DEDUP_SECONDS = max(0, int(os.getenv("TRAFFIC_DEDUP_SECONDS", "120")))
TRAFFIC_CACHE_MAX_KEYS = max(2000, int(os.getenv("TRAFFIC_CACHE_MAX_KEYS", "5000")))
_TRAFFIC_HIT_CACHE = {}
ADMISSION_MATCH_STOPWORDS = {
    "the", "for", "and", "with", "from", "that", "this", "please", "about", "info",
    "information", "details", "detail", "program", "programs", "course", "courses",
    "admission", "query", "show", "list", "menu", "give", "tell", "need", "want",
    "fees", "fee", "eligibility", "process", "source", "current", "session",
}

def compact_text(value: str) -> str:
    return " ".join(str(value or "").split()).strip()

def normalize_lookup_text(value: str) -> str:
    text = compact_text(value).lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def meaningful_match_tokens(value: str) -> list[str]:
    return [
        tok
        for tok in normalize_lookup_text(value).split()
        if len(tok) >= 3 and tok not in ADMISSION_MATCH_STOPWORDS
    ]

def should_use_hindi(text: str) -> bool:
    """Detect if text contains Devanagari or common Hinglish markers."""
    if not text:
        return False
    # Devanagari check
    if any('\u0900' <= c <= '\u097f' for c in text):
        return True
    # Hinglish tokens
    hinglish_tokens = {
        "kya", "hai", "kaise", "kab", "kahan", "kitna", "bhai", "batao", 
        "btavo", "btau", "kar", "kr", "rha", "raha", "hun", "hoon", "aap", "apna"
    }
    q_tokens = set(str(text).lower().split())
    return not q_tokens.isdisjoint(hinglish_tokens)


def get_client_ip(request: Request) -> str:
    x_forwarded_for = (request.headers.get("x-forwarded-for") or "").strip()
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    x_real_ip = (request.headers.get("x-real-ip") or "").strip()
    if x_real_ip:
        return x_real_ip
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


SOURCE_LINE_HINT_RE = re.compile(r"\b(source|sources|citation|citations|reference|references)\b", re.IGNORECASE)
YEAR_2025_RE = re.compile(r"\b2025\b")
ACADEMIC_2025_RANGE_RE = re.compile(r"\b(?:20\d{2}\s*[-/]\s*2025|2025\s*[-/]\s*(?:20)?\d{2})\b")


def enforce_response_policy(answer: str) -> str:
    """
    Output policy for user-facing chatbot responses:
    1) Never expose source/citation lines.
    2) Never show academic year 2025 explicitly.
    """
    if not answer:
        return ""

    text = str(answer).replace("\r\n", "\n")
    filtered_lines = []

    for raw_line in text.split("\n"):
        compact_line = compact_text(raw_line)
        lower_line = compact_line.lower()

        if lower_line and ("http://" in lower_line or "https://" in lower_line):
            continue

        if SOURCE_LINE_HINT_RE.search(lower_line):
            if (
                ":" in lower_line
                or lower_line.startswith(("-", "*", "•"))
                or "official bulletin" in lower_line
                or "verified from" in lower_line
            ):
                continue

        filtered_lines.append(raw_line)

    text = "\n".join(filtered_lines)
    text = ACADEMIC_2025_RANGE_RE.sub("current academic session", text)
    text = YEAR_2025_RE.sub("current academic session", text)
    text = re.sub(r"\bsources\b", "official records", text, flags=re.IGNORECASE)
    text = re.sub(r"\bsource\b", "official record", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcitations?\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\breferences?\b", "", text, flags=re.IGNORECASE)
    text = re.sub(
        r"(current academic session)(?:\s*[-/]\s*current academic session)+",
        r"\1",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"/\s*(official record|official records)", r" \1", text, flags=re.IGNORECASE)

    cleaned_lines = [re.sub(r"[ \t]{2,}", " ", line).rstrip() for line in text.split("\n")]
    text = "\n".join(cleaned_lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text

def slugify_text(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", normalize_lookup_text(value))
    slug = slug.strip("-")
    return slug or f"program-{uuid.uuid4().hex[:8]}"

def format_catalog_source_label(value) -> str:
    if isinstance(value, dict):
        return compact_text(value.get("title") or value.get("url") or value.get("pdf_path"))
    return compact_text(value)

def format_catalog_source_url(value) -> str:
    if isinstance(value, dict):
        return compact_text(value.get("url"))
    return compact_text(value)

def normalize_menu_level(level: str) -> str:
    normalized = normalize_lookup_text(level)
    if not normalized:
        return ""
    if "certificate" in normalized:
        return "UG Certificate"
    if "postgraduate" in normalized or normalized == "pg" or normalized.startswith("pg "):
        return "Postgraduate"
    if "undergraduate" in normalized or normalized == "ug" or normalized.startswith("ug "):
        return "Undergraduate"
    if "diploma" in normalized or "d voc" in normalized or "dvoc" in normalized:
        return "Diploma"
    return compact_text(level)

def find_admission_catalog_path() -> str:
    for path in ADMISSION_CATALOG_PATHS:
        if os.path.exists(path):
            return path
    return ""


def find_program_data_coverage_path() -> str:
    for path in PROGRAM_DATA_COVERAGE_PATHS:
        if os.path.exists(path):
            return path
    return ""


def load_program_data_coverage_report(force: bool = False) -> dict:
    path = find_program_data_coverage_path()
    if not path:
        return {}

    mtime = os.path.getmtime(path)
    if (
        not force
        and _PROGRAM_DATA_COVERAGE_CACHE["payload"] is not None
        and _PROGRAM_DATA_COVERAGE_CACHE["path"] == path
        and _PROGRAM_DATA_COVERAGE_CACHE["mtime"] == mtime
    ):
        return _PROGRAM_DATA_COVERAGE_CACHE["payload"]

    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    _PROGRAM_DATA_COVERAGE_CACHE["path"] = path
    _PROGRAM_DATA_COVERAGE_CACHE["mtime"] = mtime
    _PROGRAM_DATA_COVERAGE_CACHE["payload"] = payload
    return payload

def prepare_admission_program_rows(raw_rows: list) -> list:
    if not isinstance(raw_rows, list):
        return []

    rows = []
    used_program_ids = set()
    for item in raw_rows:
        if not isinstance(item, dict):
            continue

        display_title = compact_text(item.get("display_title") or item.get("canonical_title") or item.get("program"))
        canonical_title = compact_text(item.get("canonical_title") or display_title)
        if not display_title:
            continue

        aliases = []
        for alias in item.get("aliases", []) if isinstance(item.get("aliases"), list) else []:
            cleaned = compact_text(alias)
            if cleaned:
                aliases.append(cleaned)
        aliases = list(dict.fromkeys(aliases))
        verified_sources = []
        for source in item.get("verified_sources", []) if isinstance(item.get("verified_sources"), list) else []:
            cleaned = compact_text(source)
            if cleaned:
                verified_sources.append(cleaned)
        verified_sources = list(dict.fromkeys(verified_sources))

        menu_level = normalize_menu_level(item.get("menu_level", ""))
        program_id = slugify_text(display_title)
        if program_id in used_program_ids:
            suffix = 2
            while f"{program_id}-{suffix}" in used_program_ids:
                suffix += 1
            program_id = f"{program_id}-{suffix}"
        used_program_ids.add(program_id)

        rows.append({
            "program_id": program_id,
            "serial_no": compact_text(item.get("serial_no")),
            "display_title": display_title,
            "canonical_title": canonical_title,
            "faculty": compact_text(item.get("faculty")),
            "industry_partner": compact_text(item.get("industry_partner")),
            "eligibility": compact_text(item.get("eligibility")),
            "intake": compact_text(item.get("intake")),
            "duration": compact_text(item.get("duration")),
            "ncrf_level": compact_text(item.get("ncrf_level")),
            "legacy_catalog_title": compact_text(item.get("legacy_catalog_title")),
            "menu_level": menu_level,
            "menu_category": compact_text(item.get("menu_category")),
            "aliases": aliases,
            "session": compact_text(item.get("session")),
            "source_url": compact_text(item.get("source_url")),
            "fees": compact_text(item.get("fees")),
            "fee_source": compact_text(item.get("fee_source")),
            "admission_process": compact_text(item.get("admission_process")),
            "admission_source": compact_text(item.get("admission_source")),
            "placement": compact_text(item.get("placement")),
            "placement_source": compact_text(item.get("placement_source")),
            "scholarship": compact_text(item.get("scholarship")),
            "scholarship_source": compact_text(item.get("scholarship_source")),
            "career_scope": compact_text(item.get("career_scope")),
            "career_scope_source": compact_text(item.get("career_scope_source")),
            "program_brief": compact_text(item.get("program_brief")),
            "program_brief_source": compact_text(item.get("program_brief_source")),
            "program_brief_source_mode": compact_text(item.get("program_brief_source_mode")),
            "ncrf_level_source": compact_text(item.get("ncrf_level_source")),
            "industry_partner_source": compact_text(item.get("industry_partner_source")),
            "verified_sources": verified_sources,
        })

    level_rank = {lvl: idx for idx, lvl in enumerate(ADMISSION_LEVEL_ORDER)}
    rows.sort(key=lambda row: (level_rank.get(row.get("menu_level", ""), 99), normalize_lookup_text(row.get("display_title", ""))))
    return rows

def compute_admission_levels(programs: list) -> list:
    level_counts = {}
    for row in programs:
        level = row.get("menu_level", "")
        if not level:
            continue
        level_counts[level] = level_counts.get(level, 0) + 1

    ordered = []
    for level in ADMISSION_LEVEL_ORDER:
        if level in level_counts:
            ordered.append({"level": level, "count": level_counts[level]})
    for level, count in sorted(level_counts.items()):
        if level not in ADMISSION_LEVEL_ORDER:
            ordered.append({"level": level, "count": count})
    return ordered

def load_admission_catalog_payload(force: bool = False) -> dict:
    path = find_admission_catalog_path()
    if not path:
        return {
            "status": "error",
            "message": "Official admission catalog file not found.",
            "session": "",
            "source": "",
            "source_url": "",
            "total_programs": 0,
            "levels": [],
            "programs": [],
        }

    mtime = os.path.getmtime(path)
    if (
        not force
        and _ADMISSION_CATALOG_CACHE["payload"] is not None
        and _ADMISSION_CATALOG_CACHE["path"] == path
        and _ADMISSION_CATALOG_CACHE["mtime"] == mtime
    ):
        return _ADMISSION_CATALOG_CACHE["payload"]

    with open(path, "r", encoding="utf-8") as f:
        raw_payload = json.load(f)

    programs = prepare_admission_program_rows(raw_payload.get("programs", []))
    coverage_report = load_program_data_coverage_report()
    session = compact_text(raw_payload.get("session"))
    source = format_catalog_source_label(raw_payload.get("source"))
    source_url = format_catalog_source_url(raw_payload.get("source_url"))
    if not source_url:
        source_url = format_catalog_source_url(raw_payload.get("source"))
    if not source_url and programs:
        source_url = next((row.get("source_url", "") for row in programs if row.get("source_url")), "")

    payload = {
        "status": "success",
        "session": session,
        "source": source,
        "source_url": source_url,
        "catalog_path": path,
        "total_programs": len(programs),
        "levels": compute_admission_levels(programs),
        "programs": programs,
        "program_count_views": coverage_report.get("program_count_views", {}),
        "pdf_ingestion_summary": coverage_report.get("pdf_inventory_summary", {}),
        "program_data_quality": coverage_report.get("field_coverage_after", {}),
    }

    _ADMISSION_CATALOG_CACHE["path"] = path
    _ADMISSION_CATALOG_CACHE["mtime"] = mtime
    _ADMISSION_CATALOG_CACHE["payload"] = payload
    return payload

def search_admission_programs(programs: list, query: str) -> list:
    q_norm = normalize_lookup_text(query)
    if not q_norm:
        return programs

    tokens = meaningful_match_tokens(q_norm)
    ranked = []
    for row in programs:
        searchable = " ".join([
            row.get("display_title", ""),
            row.get("canonical_title", ""),
            row.get("legacy_catalog_title", ""),
            row.get("faculty", ""),
            row.get("menu_level", ""),
            row.get("menu_category", ""),
            " ".join(row.get("aliases", [])),
        ])
        hay = normalize_lookup_text(searchable)
        if not hay:
            continue

        score = 0
        if q_norm == normalize_lookup_text(row.get("display_title", "")):
            score += 120
        if q_norm in hay:
            score += 60
        if tokens and all(tok in hay for tok in tokens):
            score += 30
        for tok in tokens:
            if tok in hay:
                score += 2

        if score > 0:
            ranked.append((score, row))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in ranked]

def clean_mobile_number(mobile: str) -> str:
    digits = re.sub(r"\D", "", str(mobile or ""))
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    return digits

def is_valid_mobile_number(mobile: str) -> bool:
    return bool(re.fullmatch(r"[6-9]\d{9}", clean_mobile_number(mobile)))

def normalize_email_address(email: str) -> str:
    return str(email or "").strip().lower()

def is_valid_email_address(email: str) -> bool:
    return bool(EMAIL_PATTERN.fullmatch(normalize_email_address(email)))

def normalize_person_name(name: str) -> str:
    return " ".join(str(name or "").strip().split())

def generate_lead_id() -> str:
    return f"lead_{datetime.now().strftime('%y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"

ADMISSION_TOPIC_KEYWORDS = {
    "fees": [
        "fee", "fees", "tuition", "cost", "price", "amount", "payment",
        "semester fee", "yearly fee", "admission fee",
        "fes", "fess", "feez", "fue",  # misspellings
    ],
    "admission_process": [
        "admission process", "application process", "how to apply", "apply",
        "admission procedure", "admission steps", "documents required",
        "document", "counselling", "counseling", "last date", "important date",
        "admision", "addmission", "admissoin",  # misspellings
    ],
    "placement": [
        "placement", "placements", "package", "lpa", "job", "jobs", "recruiter",
        "placment", "plcement", "plcmnt", "placements",  # misspellings
    ],
    "scholarship": [
        "scholarship", "scholarships", "financial aid", "financial assistance",
        "fee waiver", "concession", "stipend",
        "scholorship", "scollarship", "scholarshp", "scholarship",  # misspellings
    ],
    "eligibility": [
        "eligibility", "eligible", "criteria", "qualification", "minimum marks",
        "who can apply",
        # Common misspellings of eligibility:
        "elisiblity", "eligiblity", "eligblity", "eligbility", "elgibility",
        "eligibiltiy", "eligiblty", "eligiblity", "elgibality", "eligibilty",
        "elibility", "eligibiliy", "eligibilty", "eligability",
    ],
    "career_scope": [
        "career scope", "career", "future scope", "job role", "job roles",
        "career options", "what after",
        "carrer", "carreer", "scop", "scope",  # misspellings
    ],
    "faculty": [
        "faculty", "department", "school",
        "faculy", "factuly", "facultey",  # misspellings
    ],
    "intake": [
        "intake", "seat", "seats",
        "itake", "intke", "intak",  # misspellings
    ],
    "duration": [
        "duration", "course length", "years", "semesters",
        "duraton", "duation", "durtion",  # misspellings
    ],
    "ncrf_level": [
        "ncrf", "ncrf level",
    ],
}

ADMISSION_TOPIC_ORDER = [
    "fees",
    "admission_process",
    "placement",
    "scholarship",
    "eligibility",
    "career_scope",
    "faculty",
    "intake",
    "duration",
    "ncrf_level",
]

ADMISSION_TOPIC_LABELS = {
    "fees": "fee details",
    "admission_process": "admission process",
    "placement": "placement details",
    "scholarship": "scholarship details",
    "eligibility": "eligibility",
    "career_scope": "career scope",
    "faculty": "faculty",
    "intake": "intake/seats",
    "duration": "duration",
    "ncrf_level": "NCrF level",
}

def strip_program_selected_prefix(text: str) -> str:
    lines = []
    for line in str(text or "").splitlines():
        if line.strip().lower().startswith("program_selected:"):
            continue
        lines.append(line.strip())
    return " ".join([ln for ln in lines if ln]).strip()

def unique_in_order(items: list) -> list:
    output = []
    seen = set()
    for item in items:
        cleaned = compact_text(item)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(cleaned)
    return output

def format_human_list(items: list) -> str:
    clean_items = unique_in_order(items)
    if not clean_items:
        return ""
    if len(clean_items) == 1:
        return clean_items[0]
    if len(clean_items) == 2:
        return f"{clean_items[0]} and {clean_items[1]}"
    return f"{', '.join(clean_items[:-1])}, and {clean_items[-1]}"

def extract_admission_topics(text: str) -> list:
    q = normalize_lookup_text(strip_program_selected_prefix(text))
    if not q:
        return []

    detected = []
    for topic in ADMISSION_TOPIC_ORDER:
        for keyword in ADMISSION_TOPIC_KEYWORDS.get(topic, []):
            if keyword in q:
                detected.append(topic)
                break
    return unique_in_order(detected)


def clean_program_field(value: str) -> str:
    """Strip raw crawler markers and junk from stored program data fields."""
    import re
    if not value:
        return value
    # Remove [AGENT: ...] tags
    value = re.sub(r'\[AGENT:[^\]]*\]', '', value)
    # Remove SOURCE: URL patterns
    value = re.sub(r'---?\s*SOURCE:\s*https?://\S+', '', value)
    value = re.sub(r'SOURCE:\s*https?://\S+', '', value)
    # Remove standalone --- separators
    value = re.sub(r'\s*---+\s*', ' ', value)
    # Remove copyright notices
    value = re.sub(r'Copyright\s*©.*?(?=\n|$|\Z)', '', value, flags=re.IGNORECASE)
    # Remove "Shri Vishwakarma Skill University..." boilerplate text  
    value = re.sub(r'Shri Vishwakarma Skill University[^.]*?\.', '', value)
    # Clean up extra whitespace
    value = re.sub(r'\s{2,}', ' ', value).strip()
    return value


def get_program_lookup_names(row: dict) -> list:
    names = [
        row.get("display_title", ""),
        row.get("canonical_title", ""),
        row.get("legacy_catalog_title", ""),
    ]
    aliases = row.get("aliases", [])
    if isinstance(aliases, list):
        names.extend(aliases)
    return unique_in_order(names)

def resolve_admission_program_record(programs: list, selected_program: str = "", question: str = "") -> dict | None:
    if not programs:
        return None

    # 1. First, check if the question itself contains a very strong match for a program.
    # This allows users to switch context even if a program was previously selected.
    q_norm = normalize_lookup_text(strip_program_selected_prefix(question))
    if q_norm and len(q_norm) > 4:
        for row in programs:
            for name in get_program_lookup_names(row):
                name_norm = normalize_lookup_text(name)
                # Exact or very strong containment match in question
                if name_norm and (name_norm == q_norm or (len(name_norm) > 10 and name_norm in q_norm)):
                    return row

    # 2. If no strong match in question, use the selected_program if available.
    if selected_program:
        sel_norm = normalize_lookup_text(selected_program)
        for row in programs:
            for name in get_program_lookup_names(row):
                if normalize_lookup_text(name) == sel_norm:
                    return row

    # 3. Fallback to fuzzy search on question if nothing else matched
    if q_norm:
        ranked = search_admission_programs(programs, q_norm)
        if ranked:
            top = ranked[0]
            top_names = get_program_lookup_names(top)

            # Strong phrase check first
            for name in top_names:
                name_norm = normalize_lookup_text(name)
                if name_norm and len(name_norm) >= 8 and name_norm in q_norm:
                    return top

            # Token overlap check to avoid accidental/random program mapping
            q_tokens = set(meaningful_match_tokens(q_norm))
            top_tokens = set()
            for name in top_names:
                top_tokens.update(meaningful_match_tokens(name))

            overlap = q_tokens.intersection(top_tokens)
            if len(overlap) >= 2:
                return top
            if len(overlap) == 1:
                token = next(iter(overlap))
                if len(token) >= 6:
                    return top

    return None

def get_program_brief_text(program: dict) -> str:
    explicit = compact_text(program.get("program_brief"))
    if explicit:
        # Strip redundant metadata keywords
        keywords = ["Eligibility:", "NCrF Level:", "Duration:", "Seat:", "Industry Partner:", "About the Program:", "Faculty:", "Intake:"]
        earliest = len(explicit)
        for kw in keywords:
            idx = explicit.find(kw)
            if idx != -1 and idx < earliest:
                earliest = idx
        explicit = explicit[:earliest].strip()
        if explicit:
            return explicit

    title = compact_text(program.get("display_title"))
    level = compact_text(program.get("menu_level")).lower()
    if title and level:
        return f"{title} is an SVSU {level} programme with practical, industry-linked learning."
    if title:
        return f"{title} is an SVSU programme with practical, industry-linked learning."
    return "This is an SVSU programme with practical, industry-linked learning."


def get_program_verified_sources(program: dict) -> list:
    sources = []
    for key in (
        "program_brief_source",
        "ncrf_level_source",
        "industry_partner_source",
        "fee_source",
        "admission_source",
        "placement_source",
        "scholarship_source",
        "career_scope_source",
        "source",
    ):
        value = compact_text(program.get(key))
        if value:
            sources.append(value)

    for value in program.get("verified_sources", []) if isinstance(program.get("verified_sources"), list) else []:
        cleaned = compact_text(value)
        if cleaned:
            sources.append(cleaned)

    output = []
    seen = set()
    for source in sources:
        key = source.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(source)
    return output


def is_program_count_query(text: str) -> bool:
    q = normalize_lookup_text(strip_program_selected_prefix(text))
    if not q:
        return False
    patterns = [
        "how many program",
        "how many course",
        "total program",
        "total course",
        "program offered",
        "programs offered",
        "courses offered",
        "course offered",
        "kitne program",
        "kitne course",
        "kitne programme",
        "program count",
        "course count",
        "offer kar",
        "offer karti",
        "offer krti",
    ]
    return any(pattern in q for pattern in patterns)


def build_program_count_answer(payload: dict) -> str:
    session = compact_text(payload.get("session")) or "current session"
    total_programs = payload.get("total_programs", len(payload.get("programs", [])))
    count_views = payload.get("program_count_views", {}) if isinstance(payload.get("program_count_views"), dict) else {}
    short_term_count = count_views.get("short_term_program_calendar_entries")
    source_label = compact_text(payload.get("source")) or "official admission catalog"

    lines = [
        f"For the official **{session}** admission data currently loaded in the bot, SVSU has **{total_programs} programmes**.",
    ]

    if short_term_count:
        lines.append(
            f"- **Separate short-term booklet/calendar view:** {short_term_count} short-term programmes."
        )

    count_note = compact_text(count_views.get("count_note"))
    if count_note:
        lines.extend([
            "",
            count_note,
        ])

    lines.extend([
        "",
        "If you want, I can also give the exact breakup by UG, PG, Diploma and UG Certificate from the same official record.",
    ])
    return "\n".join(lines)

def build_admission_topic_answer(program: dict, topics: list) -> str:
    program_name = compact_text(program.get("display_title")) or "this program"
    lines = [
        f"Thank you for your question. Here are verified details for **{program_name}**:",
        "",
    ]
    missing_topics = []

    for topic in topics:
        if topic == "fees":
            fee_text = clean_program_field(compact_text(program.get("fees") or program.get("fee_structure")))
            if fee_text:
                # Better formatting for fee text blocks
                f_text = fee_text.replace(". ", ".\n- ").replace("One-time fees:", "\n- **One-time fees:**").replace("Semester fee:", "\n- **Semester fee:**").replace("Industry-sponsored candidate option:", "\n- **Industry-sponsored option:**")
                lines.append(f"- **Fees:**\n{f_text}")
            else:
                lines.append("- **Fees:** Program-wise fee amount is not available in the currently loaded official structured record.")
                missing_topics.append(ADMISSION_TOPIC_LABELS[topic])
            continue

        if topic == "admission_process":
            process_text = compact_text(program.get("admission_process"))
            if process_text:
                lines.append(f"- **Admission Process:** {process_text}")
            else:
                lines.append("- **Admission Process:** Please apply through the official SVSU admission portal and follow current document verification/merit-counselling instructions from the latest admission bulletin.")
                missing_topics.append("program-specific admission process timeline")
            continue

        if topic == "placement":
            placement_text = compact_text(program.get("placement") or program.get("placement_info"))
            if placement_text:
                lines.append(f"- **Placement:** {placement_text}")
            else:
                lines.append("- **Placement:** Program-wise placement statistics are not explicitly available in the current official structured record.")
                missing_topics.append(ADMISSION_TOPIC_LABELS[topic])
            continue

        if topic == "scholarship":
            scholarship_text = compact_text(program.get("scholarship") or program.get("scholarship_info"))
            if scholarship_text:
                lines.append(f"- **Scholarship:** {scholarship_text}")
            else:
                lines.append("- **Scholarship:** Program-wise scholarship details are not explicitly available in the current official structured record.")
                missing_topics.append(ADMISSION_TOPIC_LABELS[topic])
            continue

        if topic == "eligibility":
            eligibility_text = clean_program_field(compact_text(program.get("eligibility")))
            if eligibility_text:
                lines.append(f"- **Eligibility:** {eligibility_text}")
            else:
                lines.append("- **Eligibility:** Not listed in current official structured record.")
                missing_topics.append(ADMISSION_TOPIC_LABELS[topic])
            continue

        if topic == "career_scope":
            career_text = clean_program_field(compact_text(program.get("career_scope")))
            if career_text:
                lines.append(f"- **Career Scope:** {career_text}")
            else:
                industry_partner = clean_program_field(compact_text(program.get("industry_partner")))
                if industry_partner:
                    lines.append(f"- **Career Scope:** Industry-linked exposure is indicated through listed partner(s): {industry_partner}.")
                    lines.append("- **Career Note:** Exact role-wise outcome/package data is not explicitly listed in this structured record.")
                else:
                    lines.append("- **Career Scope:** Detailed role-wise career outcomes are not explicitly listed in this structured record.")
                missing_topics.append("official role-wise career outcome details")
            continue

        if topic == "faculty":
            faculty_text = compact_text(program.get("faculty"))
            if faculty_text:
                lines.append(f"- **Faculty:** {faculty_text}")
            else:
                lines.append("- **Faculty:** Not listed in current official structured record.")
                missing_topics.append(ADMISSION_TOPIC_LABELS[topic])
            continue

        if topic == "intake":
            intake_text = clean_program_field(compact_text(program.get("intake")))
            if intake_text:
                lines.append(f"- **Intake/Seats:** {intake_text}")
            else:
                lines.append("- **Intake/Seats:** Not listed in current official structured record.")
                missing_topics.append(ADMISSION_TOPIC_LABELS[topic])
            continue

        if topic == "duration":
            duration_text = compact_text(program.get("duration"))
            if duration_text:
                lines.append(f"- **Duration:** {duration_text}")
            else:
                lines.append("- **Duration:** Not listed in current official structured record.")
                missing_topics.append(ADMISSION_TOPIC_LABELS[topic])
            continue

        if topic == "ncrf_level":
            ncrf_text = compact_text(program.get("ncrf_level"))
            if ncrf_text:
                lines.append(f"- **NCrF Level:** {ncrf_text}")
            else:
                lines.append("- **NCrF Level:** NCrF value is not explicitly listed for this program in current structured data.")
                missing_topics.append(ADMISSION_TOPIC_LABELS[topic])
            continue

    missing_text = format_human_list(missing_topics)
    brief_mode = compact_text(program.get("program_brief_source_mode"))

    if missing_topics:
        # Return partial answer with a helpful note, instead of None which causes master agent mixing
        if len(lines) > 2:  # We have at least some data
            lines.append("")
            lines.append(
                f"For more details on {missing_text}, please contact our Admission Experts:\n"
                f"- **Email:** {ADMISSION_CONTACT_EMAIL}\n"
                f"- **Helpline:** {ADMISSION_CONTACT_HELPLINE}"
            )
            return "\n".join(lines)
        return None

    return "\n".join(lines)

def get_structured_admission_answer(question: str, selected_program: str = "") -> str | None:
    if is_program_count_query(question):
        payload = load_admission_catalog_payload()
        if payload.get("status") != "success":
            return build_admission_support_fallback(reason="your admission query")
        return build_program_count_answer(payload)

    topics = extract_admission_topics(question)
    if not topics:
        return None

    payload = load_admission_catalog_payload()
    if payload.get("status") != "success":
        return build_admission_support_fallback(reason="your admission query")

    programs = payload.get("programs", [])
    program = resolve_admission_program_record(programs, selected_program=selected_program, question=question)
    if program:
        return build_admission_topic_answer(program, topics)

    topic_labels = [ADMISSION_TOPIC_LABELS.get(topic, topic) for topic in topics]
    # If program is not resolved, let the Master Agent try to resolve it via reasoning/history
    return None

def is_fee_or_financial_query(text: str) -> bool:
    q = normalize_lookup_text(text)
    if not q:
        return False
    keywords = [
        "fee", "fees", "tuition", "scholarship", "cost", "price", "amount",
        "semester fee", "yearly fee", "admission fee", "payment"
    ]
    return any(k in q for k in keywords)

def answer_has_fee_signal(answer: str) -> bool:
    a = normalize_lookup_text(answer)
    if not a:
        return False
    fee_signals = [
        "fee", "fees", "tuition", "scholarship", "inr", "rs", "rupee", "payment",
        "semester", "yearly", "contact admissions"
    ]
    if "₹" in (answer or ""):
        return True
    return any(signal in a for signal in fee_signals)

def answer_mentions_program(answer: str, program_name: str) -> bool:
    a = normalize_lookup_text(answer)
    p = normalize_lookup_text(program_name)
    if not a or not p:
        return False
    return p in a

def fee_answer_looks_generic(answer: str) -> bool:
    a = normalize_lookup_text(answer)
    if not a:
        return True
    generic_markers = [
        "for program fee questions",
        "i should not guess",
        "depends on the exact course",
        "depends on exact course",
        "tell me the exact course name",
        "exact course name",
    ]
    return any(marker in a for marker in generic_markers)

def answer_looks_uncertain(answer: str) -> bool:
    a = normalize_lookup_text(answer)
    if not a:
        return True
    uncertain_markers = [
        "could not verify", "cannot verify", "cant verify", "unable to verify",
        "not sure", "not available in the provided", "unable to fetch",
        "connectivity issue", "try again", "don't know", "do not know",
        "no information", "information not available", "not listed",
        "sorry", "apologize", "couldn't find"
    ]
    return any(marker in a for marker in uncertain_markers)

def build_admission_support_fallback(program_name: str = "", reason: str = "", question_context: str = "") -> str:
    program_line = f" for **{program_name}**" if program_name else ""
    reason_line = f" regarding **{reason}**" if reason else ""
    
    if should_use_hindi(question_context):
        return (
            f"Mujhe maaf karein, main is Admission section mein{reason_line}{program_line} ki puri jaankari verify nahi kar pa raha hoon.\n\n"
            "**Note:** Main yaha sirf **Admission Related** sawalon (fees, eligibility, placement etc.) ke jawab de sakta hoon.\n\n"
            "SVSU ki baaki jaankari ke liye please menu se **'Others Query'** select karein ya Admission Team se sampark karein:\n"
            "- **Phone:** 9306095464, 9253364547, 9253224547\n"
            "- **Toll Free:** 18001800147\n"
            "- **Email:** admissions@svsu.ac.in"
        )
    
    return (
        f"I apologize, but I couldn't safely verify the exact details{reason_line}{program_line} in this Admission section.\n\n"
        "**Note:** I can only handle **Admission Related** queries (fees, process, placement, etc.) here.\n\n"
        "For all other SVSU information, please use **'Others Query'** from the menu or contact our Admission Team:\n"
        "- **Phone:** 9306095464, 9253364547, 9253224547, 9253394547\n"
        "- **Toll Free:** 18001800147\n"
        "- **Email:** admissions@svsu.ac.in"
    )

def load_csv_df(path: str, columns: list) -> pd.DataFrame:
    if os.path.exists(path):
        try:
            df = pd.read_csv(path, on_bad_lines='skip').fillna("")
        except Exception:
            df = pd.DataFrame(columns=columns)
    else:
        df = pd.DataFrame(columns=columns)

    for col in columns:
        if col not in df.columns:
            df[col] = ""

    return df

def normalize_traffic_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in TRAFFIC_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df["bot_type"] = df["bot_type"].astype(str).fillna("").str.strip().str.lower().replace("", "intelligent")
    df["timestamp"] = df["timestamp"].astype(str).fillna("").str.strip()
    df["client_id"] = df["client_id"].astype(str).fillna("").str.strip()
    df["ip"] = df["ip"].astype(str).fillna("").str.strip()
    df["user_agent"] = df["user_agent"].astype(str).fillna("").str.strip()
    df["page_url"] = df["page_url"].astype(str).fillna("").str.strip()
    return df

def load_traffic_df() -> pd.DataFrame:
    return normalize_traffic_df(load_csv_df(TRAFFIC_FILE, TRAFFIC_COLUMNS))

def save_traffic_df(df: pd.DataFrame) -> None:
    df = normalize_traffic_df(df)
    df = df[TRAFFIC_COLUMNS]
    df.to_csv(TRAFFIC_FILE, index=False)

def make_traffic_identity_key(bot_type: str, client_id: str = "", ip: str = "", user_agent: str = "") -> str:
    bot = compact_text(bot_type).lower() or "intelligent"
    cid = compact_text(client_id)
    if cid:
        return f"client:{cid}|bot:{bot}"

    clean_ip = compact_text(ip)
    clean_ua = compact_text(user_agent)[:120]
    if clean_ip and clean_ua:
        return f"ipua:{clean_ip}|ua:{clean_ua}|bot:{bot}"
    if clean_ip:
        return f"ip:{clean_ip}|bot:{bot}"
    return ""

def prune_traffic_hit_cache(now_dt: datetime) -> None:
    if not _TRAFFIC_HIT_CACHE:
        return
    cutoff = now_dt - timedelta(seconds=max(TRAFFIC_DEDUP_SECONDS * 2, 300))
    stale_keys = [key for key, seen_dt in _TRAFFIC_HIT_CACHE.items() if seen_dt < cutoff]
    for key in stale_keys:
        _TRAFFIC_HIT_CACHE.pop(key, None)
    if len(_TRAFFIC_HIT_CACHE) > TRAFFIC_CACHE_MAX_KEYS:
        for key, _ in sorted(_TRAFFIC_HIT_CACHE.items(), key=lambda item: item[1])[:len(_TRAFFIC_HIT_CACHE) - TRAFFIC_CACHE_MAX_KEYS]:
            _TRAFFIC_HIT_CACHE.pop(key, None)

def deduplicate_traffic_df(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_traffic_df(df)
    if df.empty:
        return df

    work = df.copy()
    work["_dt"] = pd.to_datetime(work["timestamp"], errors="coerce")
    work = work.dropna(subset=["_dt"]).sort_values("_dt").copy()
    if work.empty:
        return work.drop(columns=["_dt"], errors="ignore")

    work["_traffic_key"] = work.apply(
        lambda row: make_traffic_identity_key(
            row.get("bot_type", ""),
            row.get("client_id", ""),
            row.get("ip", ""),
            row.get("user_agent", ""),
        ),
        axis=1,
    )

    if TRAFFIC_DEDUP_SECONDS <= 0:
        return work.drop(columns=["_dt", "_traffic_key"], errors="ignore")

    keep_mask = []
    last_seen_by_key = {}
    for _, row in work.iterrows():
        identity_key = row["_traffic_key"]
        event_dt = row["_dt"]
        # Older traffic rows had only bot_type/timestamp and no visit fingerprint.
        # Those rows cannot be trusted for analytics, so skip them instead of
        # letting historical noise permanently inflate admin stats.
        if not identity_key:
            has_page_url = bool(compact_text(row.get("page_url", "")))
            has_client_id = bool(compact_text(row.get("client_id", "")))
            has_ip = bool(compact_text(row.get("ip", "")))
            has_user_agent = bool(compact_text(row.get("user_agent", "")))
            keep_mask.append(has_page_url or has_client_id or has_ip or has_user_agent)
            continue

        last_seen = last_seen_by_key.get(identity_key)
        if last_seen is not None and (event_dt - last_seen).total_seconds() < TRAFFIC_DEDUP_SECONDS:
            keep_mask.append(False)
            continue

        last_seen_by_key[identity_key] = event_dt
        keep_mask.append(True)

    deduped = work.loc[keep_mask].drop(columns=["_dt", "_traffic_key"], errors="ignore")
    return deduped.reset_index(drop=True)

def normalize_leads_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in LEAD_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df["lead_id"] = df["lead_id"].astype(str).fillna("").str.strip()
    df["email"] = df["email"].astype(str).fillna("").map(normalize_email_address)
    df["mobile"] = df["mobile"].astype(str).fillna("").map(clean_mobile_number)
    df["bot_type"] = df["bot_type"].astype(str).fillna("").str.strip().str.lower().replace("", "intelligent")
    df["purpose"] = df["purpose"].astype(str).fillna("").str.strip()

    df["created_at"] = df["created_at"].astype(str).fillna("")
    df["updated_at"] = df["updated_at"].astype(str).fillna("")
    df["timestamp"] = df["timestamp"].astype(str).fillna("")

    missing_created = df["created_at"].eq("")
    df.loc[missing_created, "created_at"] = df.loc[missing_created, "timestamp"]

    missing_timestamp = df["timestamp"].eq("")
    df.loc[missing_timestamp, "timestamp"] = df.loc[missing_timestamp, "created_at"]

    missing_updated = df["updated_at"].eq("")
    df.loc[missing_updated, "updated_at"] = df.loc[missing_updated, "timestamp"]

    df["application_count"] = pd.to_numeric(df["application_count"], errors="coerce").fillna(0).astype(int)
    df["latest_course"] = df["latest_course"].astype(str).fillna("").str.strip()
    df["last_application_at"] = df["last_application_at"].astype(str).fillna("")

    if "stage" not in df.columns:
        df["stage"] = ""
    df["stage"] = df["stage"].astype(str).fillna("").str.strip()

    pending_mask = df["stage"].eq("") & df["purpose"].str.lower().str.startswith("pending")
    df.loc[pending_mask, "stage"] = "lead_captured"

    lead_mask = df["stage"].eq("") & ~df["purpose"].eq("")
    df.loc[lead_mask, "stage"] = "purpose_selected"

    app_mask = (df["application_count"] > 0) | (df["latest_course"] != "")
    df.loc[app_mask, "stage"] = "application_submitted"

    if not df.empty:
        df["_sort_dt"] = pd.to_datetime(df["updated_at"], errors="coerce")
        df["_sort_dt"] = df["_sort_dt"].fillna(pd.to_datetime(df["timestamp"], errors="coerce"))
        df["_identity_key"] = df.apply(get_engagement_identity_key, axis=1)
        df = df.sort_values("_sort_dt", na_position="last").drop_duplicates(subset=["_identity_key"], keep="last")
        df = df.drop(columns=["_sort_dt", "_identity_key"], errors="ignore")

    return df

def load_leads_df() -> pd.DataFrame:
    return normalize_leads_df(load_csv_df(LEADS_FILE, LEAD_COLUMNS))

def save_leads_df(df: pd.DataFrame) -> None:
    df = normalize_leads_df(df)
    df.to_csv(LEADS_FILE, index=False)

def normalize_applications_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in APPLICATION_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df["lead_id"] = df["lead_id"].astype(str).fillna("").str.strip()
    df["email"] = df["email"].astype(str).fillna("").map(normalize_email_address)
    df["mobile"] = df["mobile"].astype(str).fillna("").map(clean_mobile_number)
    df["course"] = df["course"].astype(str).fillna("").str.strip()
    df["timestamp"] = df["timestamp"].astype(str).fillna("")
    df["source_bot"] = df["source_bot"].astype(str).fillna("").str.strip().str.lower()
    df["purpose"] = df["purpose"].astype(str).fillna("").str.strip().str.lower()
    return df

def load_applications_df() -> pd.DataFrame:
    return normalize_applications_df(load_csv_df(APPLICATIONS_FILE, APPLICATION_COLUMNS))

def save_applications_df(df: pd.DataFrame) -> None:
    df = normalize_applications_df(df)
    # Ensure strict column order for CSV consistency
    df = df[APPLICATION_COLUMNS]
    df.to_csv(APPLICATIONS_FILE, index=False)

def load_engagements_df() -> pd.DataFrame:
    df = load_csv_df(ENGAGEMENTS_FILE, ENGAGEMENT_COLUMNS)
    for col in ENGAGEMENT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df["lead_id"] = df["lead_id"].astype(str).fillna("").str.strip()
    df["email"] = df["email"].astype(str).fillna("").map(normalize_email_address)
    df["mobile"] = df["mobile"].astype(str).fillna("").map(clean_mobile_number)
    df["bot_type"] = df["bot_type"].astype(str).fillna("").str.strip().str.lower()
    df["purpose"] = df["purpose"].astype(str).fillna("").str.strip().str.lower()
    df["timestamp"] = df["timestamp"].astype(str).fillna("")
    return df

def save_engagements_df(df: pd.DataFrame) -> None:
    df = load_engagements_df() if df is None else df
    df.to_csv(ENGAGEMENTS_FILE, index=False)

def append_engagement_event(lead_id: str, email: str, mobile: str, bot_type: str, purpose: str, timestamp: str) -> None:
    lead_id = str(lead_id or "").strip()
    timestamp = str(timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")).strip()
    if not lead_id:
        return
    df = load_engagements_df()
    if not df.empty:
        same_lead_mask = df["lead_id"].astype(str).str.strip() == lead_id
        if same_lead_mask.any():
            event_dt = pd.to_datetime(timestamp, errors="coerce")
            if pd.notna(event_dt):
                existing_days = pd.to_datetime(df.loc[same_lead_mask, "timestamp"], errors="coerce").dt.date
                if (existing_days == event_dt.date()).any():
                    return
            else:
                if (df.loc[same_lead_mask, "timestamp"].astype(str).str.strip() == timestamp).any():
                    return
    event = {
        "event_id": f"ENG-{uuid.uuid4().hex[:8].upper()}",
        "lead_id": lead_id,
        "email": normalize_email_address(email),
        "mobile": clean_mobile_number(mobile),
        "bot_type": (bot_type or "intelligent").strip().lower(),
        "purpose": (purpose or "").strip().lower(),
        "timestamp": timestamp
    }
    df = pd.concat([df, pd.DataFrame([event])], ignore_index=True) if not df.empty else pd.DataFrame([event])
    df.to_csv(ENGAGEMENTS_FILE, index=False)

def get_engagement_identity_key(row) -> str:
    lead_id = str(row.get("lead_id", "")).strip()
    email = normalize_email_address(row.get("email", ""))
    mobile = clean_mobile_number(row.get("mobile", ""))
    if email and mobile:
        return f"{email}|{mobile}"
    if mobile:
        return f"mobile:{mobile}"
    if email:
        return f"email:{email}"
    if lead_id:
        return f"lead:{lead_id}"
    return f"row:{row.name}"

def get_chats_count():
    if not os.path.exists(CHATS_COUNT_FILE):
        return 0
    with open(CHATS_COUNT_FILE, "r") as f:
        try:
            val = f.read().strip()
            return int(val) if val else 0
        except:
            return 0

def increment_chats_count():
    count = get_chats_count()
    with open(CHATS_COUNT_FILE, "w") as f:
        f.write(str(count + 1))

@app.get("/login")
async def login_page():
    return RedirectResponse(url="/admin_panel/admin_login.html")

@app.get("/dashboard")
async def dashboard_redirect():
    return RedirectResponse(url="/admin_panel/admin.html")

@app.get("/admin")
async def admin_portal():
    return RedirectResponse(url="/admin_panel/admin.html")

@app.get("/api/leads")
async def get_leads():
    try:
        df = load_leads_df()
        if not df.empty:
            df['dt'] = pd.to_datetime(df['updated_at'], errors='coerce')
            fallback_dt = pd.to_datetime(df['timestamp'], errors='coerce')
            df['dt'] = df['dt'].fillna(fallback_dt)
            df = df.sort_values(by='dt', ascending=False, na_position='last').drop(columns=['dt'])
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"Error fetching leads: {e}")
        return []

@app.post("/api/log-traffic")
async def log_traffic(data: TrafficLog, request: Request):
    try:
        now_dt = datetime.now()
        now_ts = now_dt.strftime("%Y-%m-%d %H:%M:%S")
        bot_type = compact_text(data.bot_type).lower() or "intelligent"
        client_id = compact_text(data.client_id)[:120]
        page_url = compact_text(data.page_url)[:300]
        client_ip = get_client_ip(request)
        user_agent = compact_text(request.headers.get("user-agent", ""))[:220]
        traffic_key = make_traffic_identity_key(
            bot_type=bot_type,
            client_id=client_id,
            ip=client_ip,
            user_agent=user_agent,
        )

        prune_traffic_hit_cache(now_dt)
        if traffic_key:
            last_seen = _TRAFFIC_HIT_CACHE.get(traffic_key)
            if last_seen and (now_dt - last_seen).total_seconds() < TRAFFIC_DEDUP_SECONDS:
                return {"status": "skipped", "reason": "dedup-cache"}

        df = load_traffic_df()
        if traffic_key and not df.empty:
            check_df = df.copy()
            check_df["_dt"] = pd.to_datetime(check_df["timestamp"], errors="coerce")
            check_df = check_df.dropna(subset=["_dt"])
            if not check_df.empty:
                check_df["_traffic_key"] = check_df.apply(
                    lambda row: make_traffic_identity_key(
                        row.get("bot_type", ""),
                        row.get("client_id", ""),
                        row.get("ip", ""),
                        row.get("user_agent", ""),
                    ),
                    axis=1,
                )
                same_key = check_df[check_df["_traffic_key"] == traffic_key]
                if not same_key.empty:
                    last_file_dt = same_key["_dt"].max()
                    if pd.notna(last_file_dt) and (now_dt - last_file_dt.to_pydatetime()).total_seconds() < TRAFFIC_DEDUP_SECONDS:
                        _TRAFFIC_HIT_CACHE[traffic_key] = now_dt
                        return {"status": "skipped", "reason": "dedup-file"}

        new_row = pd.DataFrame([{
            "bot_type": bot_type,
            "timestamp": now_ts,
            "client_id": client_id,
            "ip": client_ip,
            "user_agent": user_agent,
            "page_url": page_url,
        }])
        df = pd.concat([df, new_row], ignore_index=True) if not df.empty else new_row
        save_traffic_df(df)

        if traffic_key:
            _TRAFFIC_HIT_CACHE[traffic_key] = now_dt
        return {"status": "success"}
    except Exception as e:
        print(f"Traffic Log Error: {e}")
        return {"status": "error"}

@app.get("/api/traffic-analytics")
async def get_traffic_analytics(range_type: str = "7days", start_date: str = None, end_date: str = None):
    try:
        from datetime import timedelta, datetime
        df = pd.DataFrame(columns=["dt"])

        if os.path.exists(TRAFFIC_FILE):
            try:
                df_t = deduplicate_traffic_df(load_traffic_df())
                if not df_t.empty:
                    df_t["dt"] = pd.to_datetime(df_t["timestamp"], errors="coerce")
                    df = df_t[["dt"]].dropna(subset=["dt"]).copy()
            except Exception as traffic_err:
                print(f"Traffic Analytics Log Parse Error: {traffic_err}")

        if df.empty and os.path.exists(LEADS_FILE):
            try:
                df_l = load_leads_df()
                if not df_l.empty:
                    df_l["dt"] = pd.to_datetime(df_l["created_at"].where(df_l["created_at"] != "", df_l["timestamp"]), errors="coerce")
                    df = df_l[["dt"]].dropna(subset=["dt"]).copy()
            except Exception as lead_err:
                print(f"Traffic Analytics Lead Fallback Error: {lead_err}")

        if df.empty:
            return {"labels": [], "data": [], "summary": {"today": 0, "total": 0}}

        now = datetime.now()
        
        today_count = len(df[df['dt'].dt.date == now.date()])
        total_count = len(df)
        
        labels = []
        counts = []
        
        if range_type == "custom" and start_date and end_date:
            try:
                s_dt = datetime.strptime(start_date, "%Y-%m-%d")
                e_dt = datetime.strptime(end_date, "%Y-%m-%d")
            except:
                s_dt = now - timedelta(days=7); e_dt = now
                
            mask = (df['dt'].dt.date >= s_dt.date()) & (df['dt'].dt.date <= e_dt.date())
            df_filtered = df[mask]
            for i in range((e_dt - s_dt).days + 1):
                day = s_dt + timedelta(days=i)
                labels.append(day.strftime("%b %d"))
                counts.append(len(df_filtered[df_filtered['dt'].dt.date == day.date()]))
        else:
            days = 7 if range_type == "7days" else 30
            for i in range(days-1, -1, -1):
                target = now - timedelta(days=i)
                labels.append(target.strftime("%b %d"))
                counts.append(len(df[df['dt'].dt.date == target.date()]))
            
        return {
            "labels": labels,
            "data": counts,
            "summary": {
                "today": today_count,
                "yesterday": len(df[df['dt'].dt.date == (now - timedelta(days=1)).date()]),
                "total": total_count,
                "last_7_days": len(df[df['dt'] > (now - timedelta(days=7))]),
                "last_30_days": len(df[df['dt'] > (now - timedelta(days=30))])
            }
        }
    except Exception as e:
        print(f"Traffic Analytics Error: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/talk")
async def talk_mode():
    return FileResponse(os.path.join(ADMIN_DIR, "talk.html"))

@app.get("/api/admission/catalog")
async def admission_catalog(level: str = "", q: str = "", include_programs: bool = True):
    payload = load_admission_catalog_payload()
    if payload.get("status") != "success":
        return payload

    programs = list(payload.get("programs", []))
    if level:
        target_level = normalize_menu_level(level)
        programs = [row for row in programs if normalize_menu_level(row.get("menu_level", "")) == target_level]
    if q:
        programs = search_admission_programs(programs, q)

    response = {
        "status": "success",
        "session": payload.get("session", ""),
        "source": payload.get("source", ""),
        "source_url": payload.get("source_url", ""),
        "total_programs": payload.get("total_programs", len(payload.get("programs", []))),
        "filtered_count": len(programs),
        "levels": compute_admission_levels(programs if (level or q) else payload.get("programs", [])),
        "program_count_views": payload.get("program_count_views", {}),
        "pdf_ingestion_summary": payload.get("pdf_ingestion_summary", {}),
        "program_data_quality": payload.get("program_data_quality", {}),
        "programs": programs if include_programs else [],
    }
    return response

@app.get("/api/admission/coverage-report")
async def admission_coverage_report():
    report = load_program_data_coverage_report()
    if not report:
        return {"status": "error", "message": "Program data coverage report not found."}
    return {"status": "success", "report": report}

@app.post("/api/lead")
async def register_lead(data: LeadData):
    try:
        import pandas as pd
        df = load_leads_df()
        
        email_norm = normalize_email_address(data.email)
        mobile_clean = clean_mobile_number(data.mobile)
        
        # Check if lead exists by email or mobile
        mask = (df['email'] == email_norm) | (df['mobile'] == mobile_clean)
        
        lead_id = data.lead_id
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if mask.any():
            # Update existing lead
            idx = df.index[mask][0]
            lead_id = df.at[idx, 'lead_id']
            df.at[idx, 'name'] = data.name
            df.at[idx, 'email'] = email_norm
            df.at[idx, 'mobile'] = mobile_clean
            df.at[idx, 'purpose'] = data.purpose
            df.at[idx, 'bot_type'] = data.bot_type
            df.at[idx, 'updated_at'] = now_ts
        else:
            # Create new lead
            if not lead_id:
                lead_id = generate_lead_id()
            
            new_lead_dict = data.dict()
            new_lead_dict.update({
                'lead_id': lead_id,
                'email': email_norm,
                'mobile': mobile_clean,
                'timestamp': now_ts,
                'created_at': now_ts,
                'updated_at': now_ts,
                'application_count': 0,
                'latest_course': '',
                'last_application_at': ''
            })
            df = pd.concat([df, pd.DataFrame([new_lead_dict])], ignore_index=True)
            
        save_leads_df(df)
        
        # Log Engagement for Dashboard Analytics
        try:
            append_engagement_event(
                lead_id=lead_id,
                email=email_norm,
                mobile=mobile_clean,
                bot_type=data.bot_type,
                purpose=data.purpose,
                timestamp=now_ts
            )
        except Exception as e:
            print(f"Engagement Log Warning (Lead): {e}")
            
        return {"status": "success", "lead_id": lead_id}
    except Exception as e:
        print(f"Lead Registration Error: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/delete-lead")
async def delete_lead(data: dict):
    try:
        lead_id = data.get("lead_id")
        if not lead_id: return {"status": "error", "message": "No lead_id"}
        df = load_leads_df()
        df = df[df["lead_id"].astype(str) != str(lead_id)]
        save_leads_df(df)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/delete-application")
async def delete_application(data: dict):
    try:
        email = data.get("email")
        mobile = data.get("mobile")
        if not email and not mobile: return {"status": "error", "message": "No identifiers"}
        df = load_applications_df()
        if email: df = df[df["email"].astype(str) != str(email)]
        if mobile: df = df[df["mobile"].astype(str) != str(mobile)]
        save_applications_df(df)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/admission/program/{program_id}")
async def admission_program_details(program_id: str):
    payload = load_admission_catalog_payload()
    if payload.get("status") != "success":
        return payload
    
    programs = payload.get("programs", [])
    for row in programs:
        if row.get("program_id") == program_id:
            return {"status": "success", "program": row}
            
    return {"status": "error", "message": "Program not found."}

@app.post("/api/application")
async def register_application(data: ApplicationData, background_tasks: BackgroundTasks):
    try:
        import pandas as pd
        df = load_applications_df()
        
        # Enrich application data
        app_dict = data.dict()
        app_dict['app_id'] = f"APP-{uuid.uuid4().hex[:8].upper()}"
        app_dict['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Map lead if possible
        lead_id = data.lead_id
        if not lead_id:
            df_leads = load_leads_df()
            mask = (df_leads['email'] == normalize_email_address(data.email)) | (df_leads['mobile'] == clean_mobile_number(data.mobile))
            if mask.any():
                lead_id = df_leads.loc[mask, 'lead_id'].iloc[0]
        
        app_dict['lead_id'] = lead_id
        
        df = pd.concat([df, pd.DataFrame([app_dict])], ignore_index=True)
        save_applications_df(df)
        
        # Log Engagement for Dashboard Analytics
        try:
            append_engagement_event(
                lead_id=lead_id or "app-guest",
                email=data.email,
                mobile=data.mobile,
                bot_type="admission",
                purpose=f"Applied for {data.course}",
                timestamp=app_dict['timestamp']
            )
        except Exception as e:
            print(f"Engagement Log Warning (App): {e}")
        
        # Send confirmation email
        subject = f"Admission Interest Registered: {data.course} | SVSU"
        html_content = f"""
        <div style="color: #1e293b; font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;">

            <!-- Greeting -->
            <p style="font-size: 22px; font-weight: 800; color: #0f172a; margin-bottom: 8px;">Hello {data.name}! 👋</p>
            <p style="font-size: 15px; line-height: 1.7; color: #334155;">Thank you for using <b style="color: #c0392b;">SVSU Intelligent</b>! Your interest in the <b>{data.course}</b> program has been successfully received.</p>

            <!-- SVSU Highlight Box -->
            <div style="background: linear-gradient(135deg, #c0392b 0%, #a93226 100%); border-radius: 16px; padding: 25px 30px; margin: 25px 0; color: white;">
                <p style="margin: 0 0 8px; font-size: 13px; text-transform: uppercase; letter-spacing: 2px; opacity: 0.85;">Welcome to</p>
                <p style="margin: 0 0 5px; font-size: 22px; font-weight: 800;">India's 1st Government Skill University</p>
                <p style="margin: 0; font-size: 14px; opacity: 0.9; line-height: 1.6;">SVSU bridges the gap between education &amp; industry with its unique <b>Earn-While-You-Learn</b> and <b>Dual Education</b> model. Learn skills, earn certificates, and get placed in top companies!</p>
            </            <!-- Admission Process Image -->
            <div style="margin: 30px 0; text-align: center;">
                <img src="https://github.com/anujak7/svsu-intelligent/blob/main/assets/admission-process.png.png?raw=true" alt="Admission Process" style="width: 100%; max-width: 550px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);" onerror="this.style.display='none'">
                <p style="font-size: 12px; color: #94a3b8; margin-top: 8px;">Step-by-step procedure to join our learning community.</p>
            </div>

            <!-- Main CTA Button -->
            <div style="text-align: center; margin: 40px 0 30px;">
                <a href="https://admission.svsu.ac.in/" style="background: linear-gradient(135deg, #c0392b 0%, #e74c3c 100%); color: #ffffff; padding: 20px 50px; text-decoration: none; border-radius: 16px; font-weight: 800; font-size: 18px; display: inline-block; box-shadow: 0 12px 30px rgba(192,57,43,0.35); letter-spacing: 0.5px;">
                    APPLY FOR ADMISSION NOW
                </a>
                <p style="font-size: 12px; color: #94a3b8; margin-top: 12px;">Official Admission Portal: admission.svsu.ac.in</p>
            </div>

            <!-- Colorful Resource Buttons -->
            <div style="margin: 40px 0; padding: 30px; background-color: #f8fafc; border-radius: 24px; border: 1px solid #e2e8f0;">
                <p style="text-align: center; font-weight: 800; color: #0f172a; margin-bottom: 25px; font-size: 16px; text-transform: uppercase; letter-spacing: 1px;">Quick Access Resources</p>
                <table border="0" cellpadding="0" cellspacing="0" width="100%">
                    <tr>
                        <td width="50%" style="padding: 0 8px 15px 0;">
                            <a href="https://coe.svsu.ac.in/" style="display: block; background: linear-gradient(135deg, #2563eb, #3b82f6); color: #ffffff; padding: 15px; text-decoration: none; border-radius: 12px; text-align: center; font-weight: 700; font-size: 14px; box-shadow: 0 4px 6px rgba(59,130,246,0.3);"> Examination (COE)</a>
                        </td>
                        <td width="50%" style="padding: 0 0 15px 8px;">
                            <a href="https://www.svsulibrary.in/" style="display: block; background: linear-gradient(135deg, #059669, #10b981); color: #ffffff; padding: 15px; text-decoration: none; border-radius: 12px; text-align: center; font-weight: 700; font-size: 14px; box-shadow: 0 4px 6px rgba(16,185,129,0.3);"> Central Library</a>
                        </td>
                    </tr>
                    <tr>
                        <td width="50%" style="padding: 0 8px 0 0;">
                            <a href="https://rnd.svsu.ac.in/" style="display: block; background: linear-gradient(135deg, #7c3aed, #8b5cf6); color: #ffffff; padding: 15px; text-decoration: none; border-radius: 12px; text-align: center; font-weight: 700; font-size: 14px; box-shadow: 0 4px 6px rgba(139,92,246,0.3);"> Research (R&D)</a>
                        </td>
                        <td width="50%" style="padding: 0 0 0 8px;">
                            <a href="https://digitalojtdiary.svsu.ac.in/" style="display: block; background: linear-gradient(135deg, #ea580c, #f97316); color: #ffffff; padding: 15px; text-decoration: none; border-radius: 12px; text-align: center; font-weight: 700; font-size: 14px; box-shadow: 0 4px 6px rgba(249,115,22,0.3);"> OJT Portal</a>
                        </td>
                    </tr>
                </table>
            </div>

            <!-- Value Proposition Image -->
            <div style="margin: 40px 0; background-color: #f1f5f9; padding: 25px; border-radius: 20px;">
                <p style="text-align: center; font-weight: 800; color: #0f172a; margin-bottom: 20px; font-size: 18px;">Why SVSU is the Right Choice for You</p>
                <img src="https://github.com/anujak7/svsu-intelligent/blob/main/assets/top-10-reasons.png.png?raw=true" alt="Top 10 Reasons" style="width: 100%; border-radius: 10px;" onerror="this.style.display='none'">
                
                <div style="margin-top: 30px; padding-top: 30px; border-top: 1px solid #e2e8f0;">
                    <p style="text-align: center; font-weight: 800; color: #0f172a; margin-bottom: 20px; font-size: 18px;">Our Industry Partners & Recruiters</p>
                    <img src="https://github.com/anujak7/svsu-intelligent/blob/main/assets/companies-hiring.png.png?raw=true" alt="Companies Hiring" style="width: 100%; border-radius: 10px;" onerror="this.style.display='none'">yle.display='none'">
                    <p style="text-align: center; font-size: 13px; color: #64748b; margin-top: 15px;">Join the elite list of professionals hired by top global brands.</p>
                </div>
            </div>

            <!-- Contact Details -->
            <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 16px; padding: 20px 25px; margin: 30px 0;">
                <p style="margin: 0 0 12px; font-weight: 800; color: #166534; font-size: 15px;">📞 Need Help? Contact Us Directly</p>
                <p style="margin: 6px 0; font-size: 13px; color: #1e293b;"><b>Admission Helpline:</b> <a href="tel:9306095464" style="color: #c0392b; text-decoration: none; font-weight: 600;">9306095464</a>, <a href="tel:9253364547" style="color: #c0392b; text-decoration: none; font-weight: 600;">9253364547</a>, <a href="tel:9253224547" style="color: #c0392b; text-decoration: none; font-weight: 600;">9253224547</a>, <a href="tel:9253394547" style="color: #c0392b; text-decoration: none; font-weight: 600;">9253394547</a></p>
                <p style="margin: 6px 0; font-size: 13px; color: #1e293b;"><b>Toll Free:</b> <a href="tel:18001800147" style="color: #c0392b; text-decoration: none; font-weight: 600;">1800-1800-147</a></p>
                <p style="margin: 6px 0; font-size: 13px; color: #1e293b;"><b>Email:</b> <a href="mailto:admissions@svsu.ac.in" style="color: #c0392b; text-decoration: none; font-weight: 600;">admissions@svsu.ac.in</a></p>
                <p style="margin: 6px 0; font-size: 13px; color: #1e293b;"><b>Campus:</b> Village Dudhola, Palwal, Haryana - 121102</p>
            </div>

            <div style="background-color: #fff7ed; border-left: 4px solid #f97316; padding: 20px; margin: 30px 0; border-radius: 0 12px 12px 0;">
                <p style="margin: 0; color: #9a3412; font-weight: 700;">Academic Counseling:</p>
                <p style="margin: 5px 0 0; font-size: 14px; color: #c2410c;">Our team will call you within 24 hours to help you choose the best specialization and guide you through the document verification process.</p>
            </div>

            <p style="margin-top: 40px; font-weight: 700; color: #1e293b; font-size: 15px;">Warm Regards,</p>
            <p style="margin-top: 5px; color: #64748b; font-size: 14px;"><b>Admission Desk</b><br>Shri Vishwakarma Skill University<br><i>India's 1st Government Skill University</i></p>
        </div>
        """
        # Send in background
        background_tasks.add_task(send_professional_email, data.email, subject, html_content)
        
        print(f"Professional application registered for {data.course} for {data.name}")
        return {"status": "success", "message": "Application registered"}
    except Exception as e:
        print(f"Application Submission Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notify-result")
async def notify_result(data: NotifyResultData, background_tasks: BackgroundTasks):
    try:
        import pandas as pd
        notify_file = "data/result_notifications.csv"
        notify_dict = data.dict()
        notify_dict['timestamp'] = datetime.now().isoformat()
        file_exists = os.path.isfile(notify_file)
        df = pd.DataFrame([notify_dict])
        df.to_csv(notify_file, mode='a', index=False, header=not file_exists)
        
        # Send a confirmation email for notification request in background
        subject = f"Notification Set for {data.program} Exam Result"
        html = f"Hello {data.name},<br><br>We have received your request to be notified when the <b>{data.program} {data.semester} Sem</b> result is declared. We will send you an email as soon as it is available on our portal."
        background_tasks.add_task(send_professional_email, data.email, subject, html)
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/send-custom-email")
async def send_custom_email(req: CustomEmailRequest, background_tasks: BackgroundTasks):
    try:
        formatted_body = req.body.replace('\n', '<br>')
        html_content = f"""
        <div style="color: #1e293b; line-height: 1.6;">
            <p>{formatted_body}</p>
        </div>
        """
        background_tasks.add_task(send_professional_email, req.to_email, req.subject, html_content)
        return {"status": "success", "message": "Email queued for sending"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def send_professional_email(to_email, subject, content_html):
    # Premium responsive email template
    try:
        sender_email = os.getenv("SMTP_USER")
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT", 465))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")

        if not smtp_user:
            print("Email skipped: SMTP credentials not set")
            return

        current_year = datetime.now().year
        full_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
            </style>
        </head>
        <body style="font-family: 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif; margin: 0; padding: 0; background-color: #f8fafc; -webkit-font-smoothing: antialiased;">
            <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f8fafc; padding: 40px 10px;">
                <tr>
                    <td align="center">
                        <table border="0" cellpadding="0" cellspacing="0" width="600" style="background-color: #ffffff; border-radius: 24px; overflow: hidden; box-shadow: 0 20px 50px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;">
                            <!-- Header Banner -->
                            <tr>
                                <td style="background: linear-gradient(135deg, #c0392b 0%, #a93226 100%); padding: 40px 30px; text-align: center;">
                                    <img src="https://svsu.ac.in/assets/images/logo.png" alt="SVSU Logo" style="height: 90px; filter: drop-shadow(0 4px 6px rgba(0,0,0,0.1));">
                                    <div style="margin-top: 20px;">
                                        <h1 style="color: #ffffff; margin: 0; font-size: 24px; letter-spacing: -0.5px; font-weight: 800; text-shadow: 0 2px 4px rgba(0,0,0,0.1);">SHRI VISHWAKARMA</h1>
                                        <h2 style="color: #ffd7d7; margin: 2px 0 0; font-size: 16px; font-weight: bold; letter-spacing: 3px; text-transform: uppercase;">Skill University</h2>
                                    </div>
                                </td>
                            </tr>
                            
                            <!-- Body Content -->
                            <tr>
                                <td style="padding: 50px 45px 40px; background-color: #ffffff;">
                                    <div style="font-size: 16px; color: #334155; line-height: 1.8;">
                                        __CONTENT_HTML__
                                    </div>
                                </td>
                            </tr>
                            
                            <!-- Premium Divider -->
                            <tr>
                                <td style="padding: 0 45px;">
                                    <div style="height: 1px; background: linear-gradient(to right, transparent, #e2e8f0, transparent);"></div>
                                </td>
                            </tr>

                            <!-- Professional Footer -->
                            <tr>
                                <td style="padding: 40px 45px; background-color: #fbfcfd; border-top: 1px solid #f1f5f9;">
                                    <table border="0" cellpadding="0" cellspacing="0" width="100%">
                                        <tr>
                                            <td style="text-align: center;">
                                                <img src="https://svsu.ac.in/assets/images/logo.png" alt="SVSU Footer Logo" style="height: 60px; margin-bottom: 20px; opacity: 0.8;">
                                                <p style="margin: 0; font-weight: 800; color: #1e293b; font-size: 15px; text-transform: uppercase; letter-spacing: 1px;">Shri Vishwakarma Skill University</p>
                                                <p style="margin: 5px 0; color: #64748b; font-size: 13px;">(India's First Government Skill University)</p>
                                                
                                                <div style="margin: 25px 0; color: #475569; font-size: 13px; line-height: 1.8;">
                                                    <b>Campus:</b> Village Dudhola, Palwal, Haryana - 121102<br>
                                                    <b>Contact:</b> <a href="tel:01242746800" style="color: #c0392b; text-decoration: none; font-weight: 600;">0124-2746800</a> | <a href="tel:18001800147" style="color: #c0392b; text-decoration: none; font-weight: 600;">1800-1800-147</a><br>
                                                    <b>Email:</b> <a href="mailto:info@svsu.ac.in" style="color: #c0392b; text-decoration: none; font-weight: 600;">info@svsu.ac.in</a> | <a href="mailto:admissions@svsu.ac.in" style="color: #c0392b; text-decoration: none; font-weight: 600;">admissions@svsu.ac.in</a>
                                                </div>

                                                <div style="margin-top: 25px; padding-top: 20px; border-top: 1px dotted #e2e8f0;">
                                                    <a href="https://svsu.ac.in" style="color: #64748b; text-decoration: none; font-weight: 700; margin: 0 12px; font-size: 12px;">Official Website</a>
                                                    <a href="https://admission.svsu.ac.in" style="color: #64748b; text-decoration: none; font-weight: 700; margin: 0 12px; font-size: 12px;">Admission Portal</a>
                                                </div>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                        </table>
                        
                        <!-- Copyright & Legal -->
                        <table border="0" cellpadding="0" cellspacing="0" width="600">
                            <tr>
                                <td style="padding: 30px 0; text-align: center;">
                                    <p style="font-size: 12px; color: #94a3b8; margin: 0;">&copy; __CURRENT_YEAR__ Shri Vishwakarma Skill University. All rights reserved.</p>
                                    <p style="font-size: 11px; color: #cbd5e1; margin-top: 8px;">Powered by SVSU Intelligent Assistant</p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        # Re-formatting content_html to avoid double curly brace issues in f-strings
        full_html = full_html.replace("__CONTENT_HTML__", content_html).replace("__CURRENT_YEAR__", str(current_year))
        
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        msg = MIMEMultipart()
        msg['From'] = f"SVSU Intelligent <{sender_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(full_html, 'html'))

        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
    except Exception as e:
        print(f"Professional Email Error: {e}")

from agentic_system import master_process_query, evolution_process

@app.post("/api/chat")
async def chat(request: ChatRequest, background_tasks: BackgroundTasks, fastapi_request: Request):
    try:
        # Increment global chat counter for funnel
        increment_chats_count()

        # Resolve User ID (Request > IP Fallback)
        user_id = request.user_id or fastapi_request.client.host
        effective_question = request.question
        selected_program = ""
        if request.selected_program:
            selected_program = str(request.selected_program).strip()
            if selected_program and "program_selected:" not in effective_question.lower():
                effective_question = (
                    f"PROGRAM_SELECTED: {selected_program}\n"
                    f"{effective_question}"
                )

        # Deterministic admission-topic responder:
        # For fee/process/placement/scholarship/eligibility/career/faculty/intake/duration/NCrF
        # return verified structured answer first (or safe official fallback) instead of guessing.
        if request.mode == "admission":
            structured_admission_answer = get_structured_admission_answer(
                question=effective_question,
                selected_program=selected_program,
            )
            if structured_admission_answer:
                safe_answer = enforce_response_policy(structured_admission_answer)
                background_tasks.add_task(evolution_process, effective_question, safe_answer, user_id)
                return {"answer": safe_answer, "domain": "Admission"}
        
        # Admission mode: Pre-check for clearly off-topic questions
        if request.mode == "admission":
            admission_keywords = [
                "fee", "fees", "admission", "eligibility", "course", "program", "programme",
                "scholarship", "career", "placement", "intake", "seat", "duration", "apply",
                "mca", "bca", "mba", "bba", "btech", "b.tech", "mtech", "m.tech", "diploma",
                "b.voc", "bvoc", "phd", "pg", "ug", "postgraduate", "undergraduate",
                "process", "document", "merit", "counselling", "counseling", "portal",
                "ncrf", "syllabus", "industry", "partner",
            ]
            q_lower = effective_question.lower()
            is_admission_related = any(kw in q_lower for kw in admission_keywords)
            # Check if it's a clearly off-topic question (teachers, sports, canteen, etc.)
            off_topic_keywords = [
                "teacher", "professor", "faculty member", "sports", "game", "canteen",
                "hostel room", "bus route", "transport route", "library book", "club",
                "chancellor", "registrar", "principal", "vc", "vice chancellor",
                "warden", "mess", "food", "exam", "result", "admit card"
            ]
            is_off_topic = any(kw in q_lower for kw in off_topic_keywords) and not is_admission_related
            if is_off_topic:
                if should_use_hindi(effective_question):
                    answer = (
                        "I'm specialized for **Admission queries** only in this section. "
                        "Aap professionally aur politely **'Others Query'** section par switch kar lijiye, "
                        "vahan main aapke baaki sawalon ka jawab de paunga.\n\n"
                        "For admission help:\n"
                        f"- **Email:** {ADMISSION_CONTACT_EMAIL}\n"
                        f"- **Helpline:** {ADMISSION_CONTACT_HELPLINE}"
                    )
                else:
                    answer = (
                        "I'm specialized for **Admission queries** only in this section. "
                        "Please switch to the **'Others Query'** section from the menu, "
                        "where I can assist you with non-admission related questions.\n\n"
                        "For admission help:\n"
                        f"- **Email:** {ADMISSION_CONTACT_EMAIL}\n"
                        f"- **Helpline:** {ADMISSION_CONTACT_HELPLINE}"
                    )
                return {"answer": enforce_response_policy(answer), "domain": "Admission"}

        result = await master_process_query(effective_question, request.history, request.mode, user_id=user_id)

        # Admission safety guardrail:
        # If answer is uncertain OR fee query answer is off-target, return a professional support fallback.
        if isinstance(result, dict):
            answer_text = str(result.get("answer", "")).strip()
            if request.mode == "admission":
                if answer_looks_uncertain(answer_text):
                    result["answer"] = build_admission_support_fallback(
                        program_name=selected_program,
                        reason="your query",
                        question_context=effective_question
                    )
                    result["domain"] = "Admission"
                elif is_fee_or_financial_query(effective_question):
                    if (
                        not answer_has_fee_signal(answer_text)
                        or fee_answer_looks_generic(answer_text)
                        or (selected_program and not answer_mentions_program(answer_text, selected_program))
                    ):
                        result["answer"] = build_admission_support_fallback(
                            program_name=selected_program,
                            reason="fee details",
                            question_context=effective_question
                        )
                        result["domain"] = "Admission"
            result["answer"] = enforce_response_policy(result.get("answer", ""))
        else:
            result = {
                "answer": enforce_response_policy(str(result or "")),
                "domain": "General"
            }
        
        # Self-Evolving: Learn from this interaction in background (proper event loop wrapping for async)
        background_tasks.add_task(evolution_process, effective_question, result.get("answer", ""), user_id)
        
        return result
        
    except Exception as e:
        import traceback
        print(f"Chat Error (Agentic): {e}\n{traceback.format_exc()}")
        return {
            "answer": enforce_response_policy(build_admission_support_fallback(reason="your query")),
            "domain": "Admission"
        }

@app.get("/api/download-csv")
async def download_csv():
    if not os.path.exists(LEADS_FILE):
        raise HTTPException(status_code=404, detail="Lead data file not found")
    return FileResponse(LEADS_FILE, media_type="text/csv", filename="svsu_leads.csv")

@app.get("/api/applications")
async def get_applications():
    try:
        df = load_applications_df()
        if not df.empty:
            df['dt'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df = df.sort_values(by='dt', ascending=False, na_position='last').drop(columns=['dt'])
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"Error reading applications: {e}")
        return []

@app.get("/api/dashboard-stats")
async def get_dashboard_stats():
    from datetime import datetime, timedelta
    try:
        now = datetime.now()
        stats = {
            "total_leads": 0,
            "total_apps": 0,
            "total_traffic": 0,
            "engagement": {
                "today": 0,
                "yesterday": 0,
                "this_month": 0
            },
            "traffic": {
                "today": 0,
                "yesterday": 0,
                "this_month": 0
            },
            "bot_distribution": {
                "intelligent": 0,
                "general": 0,
                "admission": 0
            },
            "daily_trend": {
                "labels": [],
                "data": []
            },
            "top_courses": [],
            "top_cities": []
        }
        
        df_leads = load_leads_df()
        stats["total_leads"] = len(df_leads)

        df_engagement = load_engagements_df()
        if df_engagement.empty and not df_leads.empty:
            df_engagement = pd.DataFrame({
                "lead_id": df_leads["lead_id"],
                "email": df_leads["email"],
                "mobile": df_leads["mobile"],
                "bot_type": df_leads["bot_type"],
                "purpose": df_leads["purpose"],
                "timestamp": df_leads["created_at"].where(df_leads["created_at"] != "", df_leads["timestamp"])
            })

        if not df_engagement.empty:
            df_engagement["engagement_dt"] = pd.to_datetime(df_engagement["timestamp"], errors="coerce")
            df_engagement = df_engagement.dropna(subset=["engagement_dt"]).copy()
            if not df_engagement.empty:
                df_engagement["identity_key"] = df_engagement.apply(get_engagement_identity_key, axis=1)

                today_mask = df_engagement["engagement_dt"].dt.date == now.date()
                yesterday_mask = df_engagement["engagement_dt"].dt.date == (now - timedelta(days=1)).date()
                month_mask = df_engagement["engagement_dt"].dt.month == now.month

                stats["engagement"]["today"] = int(df_engagement.loc[today_mask, "identity_key"].nunique())
                stats["engagement"]["yesterday"] = int(df_engagement.loc[yesterday_mask, "identity_key"].nunique())
                stats["engagement"]["this_month"] = int(df_engagement.loc[month_mask, "identity_key"].nunique())

                labels = []
                counts = []
                for i in range(6, -1, -1):
                    day = (now - timedelta(days=i)).date()
                    labels.append((now - timedelta(days=i)).strftime("%a"))
                    counts.append(int(df_engagement.loc[df_engagement["engagement_dt"].dt.date == day, "identity_key"].nunique()))

                if sum(counts) == 0:
                    active_daily = (
                        df_engagement.assign(day=df_engagement["engagement_dt"].dt.date)
                        .groupby("day")["identity_key"]
                        .nunique()
                        .reset_index(name="count")
                        .sort_values("day")
                    )
                    if not active_daily.empty:
                        active_daily = active_daily.tail(7)
                        labels = [pd.to_datetime(day).strftime("%b %d") for day in active_daily["day"]]
                        counts = [int(v) for v in active_daily["count"]]

                stats["daily_trend"]["labels"] = labels
                stats["daily_trend"]["data"] = counts

        traffic_available = False
        if os.path.exists(TRAFFIC_FILE):
            try:
                df_t = deduplicate_traffic_df(load_traffic_df())
                if not df_t.empty:
                    traffic_available = True
                    df_t['dt'] = pd.to_datetime(df_t['timestamp'], errors='coerce')
                    df_t = df_t.dropna(subset=['dt']).copy()
                    stats["total_traffic"] = len(df_t)
                    stats["traffic"]["today"] = int(len(df_t[df_t['dt'].dt.date == now.date()]))
                    stats["traffic"]["yesterday"] = int(len(df_t[df_t['dt'].dt.date == (now - timedelta(days=1)).date()]))
                    stats["traffic"]["this_month"] = int(len(df_t[df_t['dt'].dt.month == now.month]))

                    if 'bot_type' in df_t.columns:
                        t_dist = df_t['bot_type'].astype(str).str.lower().value_counts().to_dict()
                        for k, v in t_dist.items():
                            if k in stats["bot_distribution"]:
                                stats["bot_distribution"][k] = int(v)
            except Exception as traffic_stats_err:
                print(f"Traffic Stats Parse Error: {traffic_stats_err}")

        if not traffic_available:
            stats["total_traffic"] = stats["total_leads"]
            if not df_leads.empty:
                if 'bot_type' in df_leads.columns:
                    dist = df_leads['bot_type'].astype(str).lower().value_counts().to_dict()
                    for k, v in dist.items():
                        if k in stats["bot_distribution"]:
                            stats["bot_distribution"][k] = int(v)
                else:
                    stats["bot_distribution"]["intelligent"] = len(df_leads)
            
    except Exception as e:
        import traceback
        print(f"Stats Processing Error: {e}\n{traceback.format_exc()}")
        if "total_traffic" not in stats: stats["total_traffic"] = stats.get("total_leads", 0)
            
    try:
        df_apps = load_applications_df()
        stats["total_apps"] = len(df_apps)
        if not df_apps.empty:
            if 'course' in df_apps.columns:
                course_counts = df_apps['course'].value_counts().head(5).to_dict()
                stats["top_courses"] = [{"course": k, "count": int(v)} for k, v in course_counts.items()]
            if 'city' in df_apps.columns:
                city_counts = df_apps['city'].value_counts().head(8).to_dict()
                stats["top_cities"] = [{"city": k, "count": int(v)} for k, v in city_counts.items()]
    except Exception as e:
        print(f"Stats Error Apps: {e}")
            
    return stats

@app.post("/api/voice")
async def voice_chat(audio_file: UploadFile = File(...), history: str = ""):
    import json
    conversation_history = json.loads(history) if history else []
    import edge_tts
    client = get_groq_client()
    if not client: raise HTTPException(status_code=503, detail="Groq API not configured")
    try:
        file_id = str(uuid.uuid4())
        input_path = f"temp_audio/{file_id}.webm"
        content = await audio_file.read()
        with open(input_path, "wb") as f: f.write(content)
        with open(input_path, "rb") as fileData:
            transcription = client.audio.transcriptions.create(
                file=(input_path, fileData.read()),
                model="whisper-large-v3-turbo", 
                response_format="json",
                temperature=0.0
            )
        user_text = transcription.text.strip()
        if not user_text or len(user_text) < 2:
            return {"transcription": "", "response": "Ji, main sun rahi hoon. Kripya punah prayaas karein.", "audio": ""}
        result = await generate_voice_response(user_text, conversation_history, file_id)
        if os.path.exists(input_path): os.remove(input_path)
        return result
    except Exception as e:
        print(f"Voice Chat Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/voice-text")
async def voice_text_chat(request: Request):
    """User writes text, Bot speaks answer."""
    import json
    data = await request.json()
    user_text = data.get("text", "")
    history = data.get("history", [])
    
    if not user_text:
        return {"response": "Kripya kuch likhein.", "audio": ""}
        
    try:
        file_id = str(uuid.uuid4())
        return await generate_voice_response(user_text, history, file_id)
    except Exception as e:
        print(f"Voice-Text Chat Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def generate_voice_response(user_text, history, file_id):
    """Common logic for generating specialized voice response + TTS."""
    import edge_tts
    import base64
    
    print(f"[VOICE/TEXT] Query: {user_text}")
    bot_response_full = await master_process_query(user_text, history=history, mode="voice")
    bot_response = bot_response_full["answer"] if isinstance(bot_response_full, dict) else str(bot_response_full)

    # Fast TTS Generation
    speech_text = bot_response.replace("*", "").replace("#", "").replace("_", "")
    output_path = f"temp_audio/{file_id}.mp3"
    
    # Using Swara for natural Indian tone
    communicate = edge_tts.Communicate(speech_text, "hi-IN-SwaraNeural", rate="+5%")
    await communicate.save(output_path)

    with open(output_path, "rb") as f:
        audio_base64 = base64.b64encode(f.read()).decode('utf-8')

    if os.path.exists(output_path): os.remove(output_path)

    return {
        "transcription": user_text,
        "response": bot_response,
        "audio": audio_base64
    }

# --- PREMIUM DASHBOARD FEATURES ---

@app.get("/api/knowledge")
async def get_knowledge():
    db_facts = get_custom_facts_text()
    if db_facts:
        return {"facts": db_facts}

    knowledge_paths = [
        os.path.join(ROOT_DIR, "data/custom_facts.txt"),
        os.path.join(BASE_DIR, "data/custom_facts.txt"),
    ]
    for k_file in knowledge_paths:
        if os.path.exists(k_file):
            with open(k_file, "r", encoding="utf-8") as f:
                return {"facts": f.read()}
    return {"facts": ""}

@app.post("/api/knowledge")
async def update_knowledge(data: KnowledgeData):
    upsert_custom_facts(data.facts)

    knowledge_paths = [
        os.path.join(ROOT_DIR, "data/custom_facts.txt"),
        os.path.join(BASE_DIR, "data/custom_facts.txt"),
    ]
    for k_file in knowledge_paths:
        os.makedirs(os.path.dirname(k_file), exist_ok=True)
        with open(k_file, "w", encoding="utf-8") as f:
            f.write(data.facts)
    try:
        refresh_knowledge_cache(force=True)
    except Exception as e:
        print(f"Knowledge cache refresh warning: {e}")
    return {"status": "success"}

@app.get("/api/knowledge-store/overview")
async def knowledge_store_overview():
    ensure_knowledge_store_ready()
    overview = get_knowledge_store_overview()
    overview["status"] = "success"
    return overview

@app.get("/api/knowledge-store/search")
async def knowledge_store_search(q: str = "", limit: int = 20):
    ensure_knowledge_store_ready()
    return {
        "status": "success",
        "query": q,
        "results": search_knowledge_store(q, limit=limit),
    }

@app.get("/api/knowledge-store/document/{source_key}")
async def knowledge_store_document(source_key: str):
    ensure_knowledge_store_ready()
    document = get_knowledge_document_details(source_key)
    if not document:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    return {"status": "success", "document": document}

@app.post("/api/knowledge-store/rebuild")
async def rebuild_knowledge_store_endpoint():
    rebuild_result = ensure_knowledge_store_ready(force=True)
    refresh_knowledge_cache(force=True)
    return {"status": "success", "result": rebuild_result}

@app.get("/knowledge-store", response_class=HTMLResponse)
async def knowledge_store_browser():
    ensure_knowledge_store_ready()
    overview = get_knowledge_store_overview()
    groups_html = "".join(
        f"<tr><td>{item['source_group']}</td><td>{item['document_count']}</td><td>{item['priority']}</td></tr>"
        for item in overview.get("groups", [])
    )
    docs_html = "".join(
        f"<tr><td>{item['source_group']}</td><td>{item['source_label']}</td><td>{item['raw_size_bytes']}</td><td>{item['origin_path']}</td></tr>"
        for item in overview.get("largest_documents", [])
    )
    db_path = get_knowledge_db_path()
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>SVSU Knowledge Store</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 32px; background: #f8fafc; color: #0f172a; }}
            .card {{ background: white; border-radius: 16px; padding: 24px; box-shadow: 0 10px 30px rgba(15,23,42,0.08); margin-bottom: 24px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
            th, td {{ text-align: left; border-bottom: 1px solid #e2e8f0; padding: 10px 8px; font-size: 14px; vertical-align: top; }}
            code {{ background: #eef2ff; padding: 2px 6px; border-radius: 6px; }}
            a {{ color: #2563eb; text-decoration: none; }}
            input {{ padding: 10px 12px; width: 340px; border-radius: 10px; border: 1px solid #cbd5e1; }}
            button {{ padding: 10px 14px; border: none; border-radius: 10px; background: #2563eb; color: white; cursor: pointer; }}
            pre {{ white-space: pre-wrap; background: #0f172a; color: #e2e8f0; padding: 16px; border-radius: 12px; overflow-x: auto; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>SVSU Unified Knowledge Store</h1>
            <p>Database path: <code>{db_path}</code></p>
            <p>Sources: <b>{overview.get('sources', 0)}</b> | Documents: <b>{overview.get('documents', 0)}</b> | Chunks: <b>{overview.get('chunks', 0)}</b></p>
            <p>Use these browser-friendly endpoints:</p>
            <p><a href="/api/knowledge-store/overview">/api/knowledge-store/overview</a></p>
            <p><a href="/api/knowledge-store/search?q=hostel">/api/knowledge-store/search?q=hostel</a></p>
        </div>
        <div class="card">
            <h2>Groups</h2>
            <table>
                <thead><tr><th>Group</th><th>Documents</th><th>Priority</th></tr></thead>
                <tbody>{groups_html}</tbody>
            </table>
        </div>
        <div class="card">
            <h2>Largest Documents</h2>
            <table>
                <thead><tr><th>Group</th><th>Label</th><th>Bytes</th><th>Origin Path</th></tr></thead>
                <tbody>{docs_html}</tbody>
            </table>
        </div>
        <div class="card">
            <h2>Quick Search</h2>
            <p>Open in browser: <code>/api/knowledge-store/search?q=library</code></p>
        </div>
    </body>
    </html>
    """

@app.get("/api/advanced-analytics")
async def get_advanced_analytics():
    # 1. Funnel Calculation
    total_chats = get_chats_count()
    total_leads = len(load_leads_df())
    total_apps = len(load_applications_df())
    
    # 2. Topic Clusters (Keyword analysis from leads)
    topics = []
    df = load_leads_df()
    if not df.empty and 'purpose' in df.columns:
        keywords = ["Admission", "Hostel", "Placement", "B.Tech", "Fees", "Course", "Eligibility", "MBA"]
        all_purposes = " ".join(df['purpose'].tolist()).lower()
        topic_counts = []
        for kw in keywords:
            count = all_purposes.count(kw.lower())
            if count > 0:
                topic_counts.append({"topic": kw, "count": count})
        topics = sorted(topic_counts, key=lambda x: x['count'], reverse=True)

    # 3. Counselor Routing (Grouping leads by counselor specialty)
    routing = []
    if not df.empty:
        routing = [
            {"specialty": "Admission Queries", "assigned": "Dr. Anuj (Head Counselor)", "status": "Active"},
            {"specialty": "Technical B.Tech", "assigned": "Prof. Sharma", "status": "Online"},
            {"specialty": "Placements", "assigned": "Training Cell", "status": "Busy"}
        ]

    return {
        "funnel": {
            "chats": total_chats,
            "leads": total_leads,
            "applications": total_apps
        },
        "topics": topics[:5],
        "counselors": routing
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
