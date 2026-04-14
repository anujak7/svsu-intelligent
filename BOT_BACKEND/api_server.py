import os
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
    return RedirectResponse(url="/admin_panel/chatbot.html")

NO_CACHE_PATHS = {
    "/admin",
    "/talk",
    "/admin_panel/chatbot.html",
    "/admin_panel/admin.html",
    "/admin_panel/admin_dashboard.html",
    "/admin_panel/talk.html",
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

print(f"DEBUG: ADMIN_DIR={ADMIN_DIR}")
print(f"DEBUG: ASSETS_DIR={ASSETS_DIR}")

# Robust fallback for mounted directories
if not os.path.exists(ADMIN_DIR):
    ADMIN_DIR = os.path.join(BASE_DIR, "admin_panel")

print(f"STITCH LOG: ROOT_DIR is {ROOT_DIR}")
print(f"STITCH LOG: ADMIN_DIR is {ADMIN_DIR}")

if not os.path.exists(ADMIN_DIR):
    os.makedirs(ADMIN_DIR, exist_ok=True)
if not os.path.exists(ASSETS_DIR):
    os.makedirs(ASSETS_DIR, exist_ok=True)

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
    "app_id", "lead_id", "name", "email", "mobile", "course", "qualification",
    "passing_year", "city", "timestamp", "source_bot", "purpose"
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
    course: str
    qualification: str
    passing_year: str
    city: str
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


class CustomEmailRequest(BaseModel):
    to_email: str
    subject: str
    body: str
class KnowledgeData(BaseModel):
    facts: str

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}$")

CHATS_COUNT_FILE = os.path.join(OPERATIONAL_DIR, "chats_count.txt")
TRAFFIC_FILE = os.path.join(OPERATIONAL_DIR, "traffic.csv")

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
    if not lead_id:
        return
    df = load_engagements_df()
    if not df.empty and (df["lead_id"] == lead_id).any():
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
async def log_traffic(data: TrafficLog):
    try:
        import pandas as pd
        if not os.path.exists("data"): os.makedirs("data")
        t_dict = {
            "bot_type": data.bot_type,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        file_exists = os.path.isfile(TRAFFIC_FILE)
        df = pd.DataFrame([t_dict])
        df.to_csv(TRAFFIC_FILE, mode='a', index=False, header=not file_exists)
        return {"status": "success"}
    except Exception as e:
        print(f"Traffic Log Error: {e}")
        return {"status": "error"}

@app.get("/api/traffic-analytics")
async def get_traffic_analytics(range_type: str = "7days", start_date: str = None, end_date: str = None):
    try:
        from datetime import timedelta, datetime
        all_dfs = []
        # Load Leads as base
        if os.path.exists(LEADS_FILE):
            try:
                df_l = pd.read_csv(LEADS_FILE, usecols=['timestamp'], on_bad_lines='skip')
                df_l['dt'] = pd.to_datetime(df_l['timestamp'], errors='coerce')
                all_dfs.append(df_l[['dt']])
            except: pass
            
        # Load Traffic logs
        if os.path.exists(TRAFFIC_FILE):
            try:
                df_t = pd.read_csv(TRAFFIC_FILE, usecols=['timestamp'], on_bad_lines='skip')
                df_t['dt'] = pd.to_datetime(df_t['timestamp'], errors='coerce')
                all_dfs.append(df_t[['dt']])
            except: pass
            
        if not all_dfs:
            return {"labels": [], "data": [], "summary": {"today": 0, "total": 0}}
            
        df = pd.concat(all_dfs).dropna(subset=['dt'])
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

def send_welcome_email(to_email, name, purpose):
    try:
        sender_email = os.getenv("SMTP_USER", "svsuintelligent@svsu.ac.in")
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 465))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")

        if not smtp_user or not smtp_password:
            print("Email skipped: SMTP credentials not set in .env")
            return

        subject = f"Welcome to SVSU - Inquiry Regarding {purpose.capitalize()}"
        purpose_text = "Admissions, Courses & Fees" if purpose == "admission" else "General University Information"
        
        html = f"""
        <html>
        <head>
            <style>
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    margin: 10px 8px;
                    background-color: #c0392b;
                    color: #ffffff !important;
                    text-decoration: none;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 15px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
                .button:hover {{ background-color: #a93226; }}
            </style>
        </head>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #1e293b; max-width: 600px; margin: 0 auto; background-color: #f8fafc; padding: 20px;">
            <div style="background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;">
                
                <!-- Logo Header -->
                <div style="padding: 30px 20px; text-align: center; border-bottom: 1px solid #f1f5f9;">
                    <img src="https://svsu.ac.in/img/SVSU-Logo.png" alt="SVSU Official Logo" style="height: 70px; margin-bottom: 15px;">
                    <h2 style="margin: 0; color: #0f172a; font-size: 20px; font-weight: 800; letter-spacing: -0.5px;">SVSU Intelligent Assistant</h2>
                </div>
                
                <!-- Content -->
                <div style="padding: 40px;">
                    <h2 style="color: #0f172a; margin-top: 0; font-size: 22px;">Dear {name},</h2>
                    <p style="font-size: 16px; color: #475569;">Thank you for interacting with <b>SVSU Intelligent</b>. We are pleased to confirm that we have received your inquiry regarding <b>{purpose_text}</b>.</p>
                    
                    <div style="background: #f8fafc; padding: 24px; border-radius: 12px; margin: 30px 0; border: 1px solid #edf2f7; border-left: 6px solid #c0392b;">
                        <p style="margin: 0; font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 1px;"><b>Nature of Inquiry</b></p>
                        <p style="margin: 4px 0 0; font-size: 16px; color: #0f172a; font-weight: 700;">{purpose.upper()} SPECIALIST</p>
                        <p style="margin: 15px 0 0; font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 1px;"><b>Ref ID</b></p>
                        <p style="margin: 4px 0 0; font-size: 16px; color: #0f172a; font-weight: 500;">#SVSU-{uuid.uuid4().hex[:6].upper()}</p>
                    </div>

                    <p style="font-size: 15px; color: #475569;">SVSU is dedicated to bridging the skill gap through industry-integrated programs. Based on your interest, we recommend exploring the following official resources:</p>
                    
                    <div style="text-align: center; margin: 35px 0;">
                        <a href="https://svsu.ac.in/programs" class="button">Academic Programs</a>
                        <a href="https://svsu.ac.in/admission" class="button">Admission Portal</a>
                        <a href="https://svsu.ac.in/fee-structure" class="button">Fee Structure</a>
                    </div>

                    <p style="font-size: 14px; color: #64748b; font-style: italic;">Our specialized counseling team has been alerted to your request. You will receive a follow-up shortly.</p>
                    
                    <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 40px 0;">
                    
                    <!-- Footer Info -->
                    <div style="font-size: 13px; color: #94a3b8; text-align: center;">
                        <p style="margin: 0; font-weight: bold; color: #64748b;">Shri Vishwakarma Skill University</p>
                        <p style="margin: 5px 0;">Village Dudhola, Palwal, Haryana - 121102</p>
                        <p style="margin: 10px 0 0;"><b>Helpdesk:</b> admissions@svsu.ac.in | <b>Web:</b> <a href="https://svsu.ac.in" style="color: #c0392b; text-decoration: none;">www.svsu.ac.in</a></p>
                    </div>
                </div>
                
                <div style="background: #f8fafc; padding: 20px; text-align: center; font-size: 11px; color: #cbd5e1; border-top: 1px solid #f1f5f9;">
                    &copy; {datetime.now().year} SVSU Intelligent Assistant. Confidential & Official.
                </div>
            </div>
        </body>
        </html>
        """

        msg = MIMEMultipart()
        msg['From'] = f"SVSU Intelligent <{sender_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html, 'html'))

        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        print(f"Professional welcome email sent to {to_email}")
    except Exception as e:
        print(f"Email Error: {e}")

@app.post("/api/lead")
async def save_lead(data: LeadData, background_tasks: BackgroundTasks):
    try:
        lead_dict = data.dict()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        is_pending_purpose = (not data.purpose) or data.purpose.lower().startswith("pending")
        send_welcome = False

        lead_dict["name"] = normalize_person_name(lead_dict.get("name", ""))
        lead_dict["email"] = normalize_email_address(lead_dict.get("email", ""))
        lead_dict["mobile"] = clean_mobile_number(lead_dict.get("mobile", ""))

        if len(lead_dict["name"]) < 2:
            raise HTTPException(status_code=400, detail="Please enter a valid name.")
        if not is_valid_mobile_number(lead_dict["mobile"]):
            raise HTTPException(status_code=400, detail="Mobile number must be a valid 10-digit Indian number.")
        if not is_valid_email_address(lead_dict["email"]):
            raise HTTPException(status_code=400, detail="Please enter a valid email address.")

        df_existing = load_leads_df()
        lead_dict["bot_type"] = str(lead_dict.get("bot_type", "intelligent")).strip().lower() or "intelligent"
        lead_dict["updated_at"] = now_str
        lead_dict["stage"] = "lead_captured" if is_pending_purpose else "purpose_selected"

        row_index = None
        if data.lead_id and not df_existing.empty and (df_existing['lead_id'] == data.lead_id).any():
            row_index = df_existing.index[df_existing['lead_id'] == data.lead_id][0]
        elif not df_existing.empty:
            email = lead_dict.get("email", "")
            mobile = lead_dict.get("mobile", "")
            match_mask = pd.Series([False] * len(df_existing), index=df_existing.index)
            if mobile and email:
                match_mask = (df_existing["mobile"] == mobile) & (df_existing["email"] == email)
            elif mobile:
                match_mask = df_existing["mobile"] == mobile
            elif email:
                match_mask = df_existing["email"] == email
            if match_mask.any():
                row_index = df_existing.index[match_mask][0]

        if row_index is not None:
            previous_purpose = str(df_existing.at[row_index, 'purpose']) if 'purpose' in df_existing.columns else ""
            original_created_at = str(df_existing.at[row_index, 'created_at']) if 'created_at' in df_existing.columns else ""
            original_timestamp = str(df_existing.at[row_index, 'timestamp']) if 'timestamp' in df_existing.columns else ""
            existing_app_count = int(df_existing.at[row_index, 'application_count']) if 'application_count' in df_existing.columns and str(df_existing.at[row_index, 'application_count']).strip() else 0
            existing_stage = str(df_existing.at[row_index, 'stage']) if 'stage' in df_existing.columns else ""
            existing_course = str(df_existing.at[row_index, 'latest_course']) if 'latest_course' in df_existing.columns else ""
            existing_last_app = str(df_existing.at[row_index, 'last_application_at']) if 'last_application_at' in df_existing.columns else ""

            for key, value in lead_dict.items():
                df_existing.at[row_index, key] = value

            df_existing.at[row_index, 'created_at'] = original_created_at or original_timestamp or now_str
            df_existing.at[row_index, 'timestamp'] = original_timestamp or original_created_at or now_str
            df_existing.at[row_index, 'application_count'] = existing_app_count
            df_existing.at[row_index, 'latest_course'] = existing_course
            df_existing.at[row_index, 'last_application_at'] = existing_last_app
            if existing_stage == "application_submitted":
                df_existing.at[row_index, 'stage'] = "application_submitted"

            if previous_purpose.lower().startswith("pending") and not is_pending_purpose:
                send_welcome = True

            save_leads_df(df_existing)
        else:
            lead_dict["timestamp"] = now_str
            lead_dict["created_at"] = now_str
            lead_dict["application_count"] = 0
            lead_dict["latest_course"] = ""
            lead_dict["last_application_at"] = ""
            df_new = pd.DataFrame([lead_dict])
            df_final = pd.concat([df_existing, df_new], ignore_index=True) if not df_existing.empty else df_new
            save_leads_df(df_final)
            if not is_pending_purpose:
                send_welcome = True

        if is_pending_purpose and data.lead_id:
            append_engagement_event(
                lead_id=data.lead_id,
                email=lead_dict.get("email", ""),
                mobile=lead_dict.get("mobile", ""),
                bot_type=lead_dict.get("bot_type", "intelligent"),
                purpose=lead_dict.get("purpose", ""),
                timestamp=now_str
            )

        if send_welcome:
            background_tasks.add_task(send_welcome_email, data.email, data.name, data.purpose)
        
        return {"status": "success", "message": "Lead saved", "bot_type": data.bot_type, "lead_id": data.lead_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/application")
async def save_application(data: ApplicationData, background_tasks: BackgroundTasks):
    try:
        app_dict = data.dict()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        app_dict["timestamp"] = app_dict.get("timestamp") or now_str
        app_dict["name"] = normalize_person_name(app_dict.get("name", ""))
        app_dict["email"] = normalize_email_address(app_dict.get("email", ""))
        app_dict["mobile"] = clean_mobile_number(app_dict.get("mobile", ""))
        app_dict["app_id"] = f"APP-{uuid.uuid4().hex[:8].upper()}"
        app_dict["source_bot"] = str(app_dict.get("source_bot", "")).strip().lower()
        app_dict["purpose"] = str(app_dict.get("purpose", "admission")).strip().lower() or "admission"

        if len(app_dict["name"]) < 2:
            raise HTTPException(status_code=400, detail="Please enter a valid name.")
        if not is_valid_mobile_number(app_dict["mobile"]):
            raise HTTPException(status_code=400, detail="Mobile number must be a valid 10-digit Indian number.")
        if not is_valid_email_address(app_dict["email"]):
            raise HTTPException(status_code=400, detail="Please enter a valid email address.")

        df_apps = load_applications_df()
        df_apps = pd.concat([df_apps, pd.DataFrame([app_dict])], ignore_index=True) if not df_apps.empty else pd.DataFrame([app_dict])
        save_applications_df(df_apps)

        df_leads = load_leads_df()
        matched_index = None
        if app_dict.get("lead_id") and not df_leads.empty and (df_leads["lead_id"] == app_dict["lead_id"]).any():
            matched_index = df_leads.index[df_leads["lead_id"] == app_dict["lead_id"]][0]
        elif not df_leads.empty:
            email = app_dict.get("email", "")
            mobile = app_dict.get("mobile", "")
            combined_mask = pd.Series([False] * len(df_leads), index=df_leads.index)
            if mobile and email:
                combined_mask = (df_leads["mobile"] == mobile) & (df_leads["email"] == email)
            elif mobile:
                combined_mask = df_leads["mobile"] == mobile
            elif email:
                combined_mask = df_leads["email"] == email
            if combined_mask.any():
                matched_index = df_leads.index[combined_mask][0]

        if matched_index is not None:
            existing_count = int(df_leads.at[matched_index, "application_count"]) if str(df_leads.at[matched_index, "application_count"]).strip() else 0
            if app_dict.get("lead_id"):
                df_leads.at[matched_index, "lead_id"] = app_dict["lead_id"]
            df_leads.at[matched_index, "name"] = app_dict["name"]
            df_leads.at[matched_index, "email"] = app_dict["email"]
            df_leads.at[matched_index, "mobile"] = app_dict["mobile"]
            df_leads.at[matched_index, "purpose"] = "admission"
            df_leads.at[matched_index, "stage"] = "application_submitted"
            if app_dict.get("source_bot"):
                df_leads.at[matched_index, "bot_type"] = app_dict["source_bot"]
            df_leads.at[matched_index, "latest_course"] = app_dict["course"]
            df_leads.at[matched_index, "application_count"] = existing_count + 1
            df_leads.at[matched_index, "last_application_at"] = app_dict["timestamp"]
            df_leads.at[matched_index, "updated_at"] = now_str
        else:
            fallback_lead = {
                "lead_id": app_dict.get("lead_id", ""),
                "name": app_dict["name"],
                "email": app_dict["email"],
                "mobile": app_dict["mobile"],
                "designation": "Student/Inquirer",
                "purpose": "admission",
                "bot_type": app_dict.get("source_bot", "admission") or "admission",
                "timestamp": app_dict["timestamp"],
                "created_at": app_dict["timestamp"],
                "updated_at": now_str,
                "stage": "application_submitted",
                "latest_course": app_dict["course"],
                "application_count": 1,
                "last_application_at": app_dict["timestamp"]
            }
            df_leads = pd.concat([df_leads, pd.DataFrame([fallback_lead])], ignore_index=True) if not df_leads.empty else pd.DataFrame([fallback_lead])

        save_leads_df(df_leads)
        
        # Enhanced Professional Email Content
        subject = f"Registration Successful: Interest in {data.course} at SVSU"
        
        html_content = f"""
        <div style="color: #1e293b;">
            <p style="font-size: 18px; font-weight: bold; color: #0f172a;">Dear {data.name},</p>
            <p>Greetings from <b>Shri Vishwakarma Skill University (SVSU)</b>, Haryana.</p>
            
            <p>We are pleased to inform you that your expression of interest for the <b>{data.course}</b> program has been successfully registered in our academic database.</p>
            
            <div style="background-color: #f8fafc; padding: 25px; border-radius: 12px; margin: 25px 0; border: 1px solid #e2e8f0; border-left: 6px solid #c0392b;">
                <h3 style="margin-top:0; color: #c0392b; font-size: 16px; text-transform: uppercase; letter-spacing: 1px;">Registration Summary</h3>
                <table style="width:100%; font-size: 14px; color: #334155;">
                    <tr><td style="padding: 5px 0; width: 40%;"><b>Applied Program:</b></td><td><b>{data.course}</b></td></tr>
                    <tr><td style="padding: 5px 0;"><b>City:</b></td><td>{data.city}</td></tr>
                    <tr><td style="padding: 5px 0;"><b>Reference ID:</b></td><td>#REG-{uuid.uuid4().hex[:8].upper()}</td></tr>
                </table>
            </div>

            <p><b>Next Steps:</b></p>
            <p>Our Admission Counseling Team will reach out to you within <b>24-48 hours</b> to discuss:</p>
            <ul style="padding-left: 20px; font-size: 14px; color: #475569;">
                <li>Course curriculum and industry tie-ups.</li>
                <li>Detailed fee structure and scholarships.</li>
                <li>Official admission process and documentation.</li>
            </ul>

            <div style="text-align: center; margin: 35px 0;">
                <a href="https://svsu.ac.in/programs" style="background-color: #c0392b; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block; box-shadow: 0 4px 6px rgba(192,57,43,0.2);">Explore SVSU Campus</a>
            </div>

            <p style="font-size: 14px; color: #64748b;">If you have any urgent queries, please reach out at <b>admissions@svsu.ac.in</b>.</p>
            
            <p style="margin-bottom: 0;">Yours Sincerely,</p>
            <p style="margin-top: 5px; font-weight: bold; color: #0f172a;">Admission Desk<br>Shri Vishwakarma Skill University</p>
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
        # Use existing professional template style
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

        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; margin: 0; padding: 0; background-color: #f1f5f9; -webkit-font-smoothing: antialiased;">
            <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f1f5f9; padding: 40px 10px;">
                <tr>
                    <td align="center">
                        <table border="0" cellpadding="0" cellspacing="0" width="600" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 15px 25px rgba(0,0,0,0.05);">
                            <!-- Header -->
                            <tr>
                                <td style="padding: 40px 30px; text-align: center; border-bottom: 3px solid #f1f5f9;">
                                    <img src="https://svsu.ac.in/img/SVSU-Logo.png" alt="SVSU Official Logo" style="height: 80px; margin-bottom: 20px;">
                                    <h1 style="color: #0f172a; margin: 0; font-size: 26px; letter-spacing: -0.5px; font-weight: 800;">SHRI VISHWAKARMA</h1>
                                    <h2 style="color: #c0392b; margin: 2px 0 0; font-size: 18px; font-weight: bold; letter-spacing: 2px;">SKILL UNIVERSITY</h2>
                                    <p style="color: #94a3b8; margin: 10px 0 0; font-size: 11px; text-transform: uppercase; font-weight: bold; letter-spacing: 1px;">India's First Government Skill University</p>
                                </td>
                            </tr>
                            
                            <!-- Body -->
                            <tr>
                                <td style="padding: 40px 40px 30px;">
                                    {content_html}
                                </td>
                            </tr>
                            
                            <!-- Notice Footer -->
                            <tr>
                                <td style="padding: 0 40px 40px;">
                                    <div style="border-top: 1px solid #e2e8f0; padding-top: 30px; font-size: 12px; color: #94a3b8; line-height: 1.5; text-align: center;">
                                        <p style="margin: 0; font-weight: bold; color: #64748b;">Shri Vishwakarma Skill University</p>
                                        <p style="margin: 5px 0 0;">Village Dudhola, Palwal, Haryana - 1211102. India</p>
                                        <p style="margin: 15px 0 0;">This email was sent by SVSU Intelligent. For official queries, contact admissions@svsu.ac.in.</p>
                                    </div>
                                </td>
                            </tr>
                        </table>
                        <p style="font-size: 10px; color: #94a3b8; margin-top: 20px;">&copy; {datetime.now().year} Shri Vishwakarma Skill University. All rights reserved.</p>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
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
        if request.selected_program:
            selected_program = str(request.selected_program).strip()
            if selected_program and "program_selected:" not in effective_question.lower():
                effective_question = (
                    f"PROGRAM_SELECTED: {selected_program}\n"
                    f"{effective_question}"
                )
        
        # Delegate query to Master Agent with explicit mode awareness
        result = await master_process_query(effective_question, request.history, request.mode, user_id=user_id)
        
        # Self-Evolving: Learn from this interaction in background (proper event loop wrapping for async)
        background_tasks.add_task(evolution_process, effective_question, result.get("answer", ""), user_id)
        
        return result


        
    except Exception as e:
        import traceback
        print(f"Chat Error (Agentic): {e}\n{traceback.format_exc()}")
        return {"answer": "I apologize, but I am currently facing a connectivity issue while retrieving official records. Please wait a moment and try asking again.", "domain": "error"}





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
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    yesterday_str = (now - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    
    stats = {
        "total_leads": 0,
        "total_apps": 0,
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
    
    # Process Leads
    try:
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

        if not df_leads.empty:
            # Bot Distribution from master leads
            if 'bot_type' in df_leads.columns:
                dist = df_leads['bot_type'].value_counts().to_dict()
                for k, v in dist.items():
                    if k in stats["bot_distribution"]:
                        stats["bot_distribution"][k] = int(v)
            else:
                stats["bot_distribution"]["intelligent"] = len(df_leads)
                    
        # Total Traffic = All Hits (traffic.csv) + All Leads (leads.csv)
        stats["total_traffic"] = stats["total_leads"]
        if os.path.exists(TRAFFIC_FILE):
            try:
                df_t = pd.read_csv(TRAFFIC_FILE, on_bad_lines='skip')
                if not df_t.empty:
                    df_t['dt'] = pd.to_datetime(df_t['timestamp'], errors='coerce')
                    df_t = df_t.dropna(subset=['dt'])
                    stats["total_traffic"] += len(df_t)
                    stats["traffic"]["today"] += int(len(df_t[df_t['dt'].dt.date == now.date()]))
                    stats["traffic"]["yesterday"] += int(len(df_t[df_t['dt'].dt.date == (now - timedelta(days=1)).date()]))
                    stats["traffic"]["this_month"] += int(len(df_t[df_t['dt'].dt.month == now.month]))
                    
                    # Add hit counts to bot distribution
                    if 'bot_type' in df_t.columns:
                        t_dist = df_t['bot_type'].value_counts().to_dict()
                        for k, v in t_dist.items():
                            if k.lower() in stats["bot_distribution"]:
                                stats["bot_distribution"][k.lower()] += int(v)

            except: pass
        else:
            stats["total_traffic"] = stats["total_leads"] # Base line 1:1 if no logs
            
    except Exception as e:
        print(f"Stats Processing Error: {e}")
        # Ensure total_traffic exists to prevent frontend undefined
        if "total_traffic" not in stats: stats["total_traffic"] = stats["total_leads"]
            
    # Process Applications
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

        # 1. Transcribe STT
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

        # 2. Get AI Response and Generate Audio
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
