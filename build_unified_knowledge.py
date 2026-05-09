import os
import json
import sqlite3
import hashlib
import re
from datetime import datetime
import sys

# Add backend to path to import knowledge_store
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "BOT_BACKEND")
if BACKEND_DIR not in sys.path:
    sys.path.append(BACKEND_DIR)

try:
    from agentic_system import knowledge_store
except ImportError:
    # Fallback if pathing is different
    sys.path.append(os.path.join(BACKEND_DIR, "agentic_system"))
    import knowledge_store

KNOWLEDGE_BASE = os.path.join(BASE_DIR, "SVSU_KNOWLEDGE")
STRUCTURED_DATA_DIR = os.path.join(KNOWLEDGE_BASE, "Structured_Data")
TEXT_DATA_DIR = os.path.join(KNOWLEDGE_BASE, "Text_Knowledge")
OUTPUT_FILE = os.path.join(STRUCTURED_DATA_DIR, "master_fact_sheet.json")
PROGRAM_REPORT_FILE = os.path.join(STRUCTURED_DATA_DIR, "program_data_coverage_report.json")

def generate_master_fact_sheet():
    print("Generating EXTENSIVE Master Fact Sheet...")
    fact_sheet = {
        "university_identity": {
            "name": "Shri Vishwakarma Skill University (SVSU)",
            "motto": "Integrating Skill with Higher Education",
            "type": "India's First State Government Skill University",
            "founder": "Government of Haryana",
            "vision": "To be a leader in skill-based education and training.",
            "location": "Main Campus: Dudhola (Palwal); Transit Campus: Plot 147, Sector 44, Gurugram"
        },
        "leadership": [
            {"title": "Vice Chancellor", "name": "Professor (Dr.) Dinesh Kumar", "email": "vcoffice@svsu.ac.in"},
            {"title": "Registrar", "name": "Prof. (Dr.) Jyoti Rana", "email": "registrar@svsu.ac.in"},
            {"title": "Dean (Academic Affairs)", "name": "Prof. (Dr.) Vikram Singh", "email": "dean.academics@svsu.ac.in"},
            {"title": "Dean (Students Welfare)", "name": "Prof. (Dr.) Kulwant Singh", "email": "dean.dsw@svsu.ac.in"},
            {"title": "Dean SFMSR", "name": "Prof. (Dr.) Jyoti Rana"},
            {"title": "Dean SFET", "name": "Dr. Ashish Shrivastava"}
        ],
        "helplines": {
            "admission_toll_free": "1800-1800-147",
            "landline": "0124-2746800",
            "admission_email": "admissions@svsu.ac.in",
            "general_info": "info@svsu.ac.in",
            "exam_support": "coe@svsu.ac.in"
        },
        "faculties": [
            "Skill Faculty of Management Research and Studies (SFMSR)",
            "Skill Faculty of Engineering and Technology (SFET)",
            "Skill Faculty of Agriculture",
            "Skill Faculty of Applied Science and Humanities (SFASH)",
            "Skill Faculty of Hospitality and Tourism"
        ],
        "admission_portal": "https://www.svsu.ac.in",
        "creators_note": "Anuj Khan is the creator and owner of SVSU Intelligent AI.",
        "updated_at": datetime.now().isoformat()
    }

    # 1. Pull dynamic facts from core_facts.txt
    core_facts_path = os.path.join(TEXT_DATA_DIR, "core_facts.txt")
    if os.path.exists(core_facts_path):
        with open(core_facts_path, "r", encoding="utf-8") as f:
            lines = [l.strip("- ").strip() for l in f.readlines() if l.strip().startswith("-")]
            fact_sheet["key_highlights"] = lines[:30]

    # 2. Extract ALL Programs from Official Catalog
    catalog_path = os.path.join(STRUCTURED_DATA_DIR, "official_admission_program_catalog_2025_26.json")
    if os.path.exists(catalog_path):
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
            progs = catalog.get("programs", [])
            fact_sheet["total_programs"] = len(progs)
            fact_sheet["program_list_comprehensive"] = [
                {
                    "name": p["display_title"],
                    "eligibility": p["eligibility"],
                    "intake": p["intake"],
                    "level": p["menu_level"]
                } for p in progs
            ]

    # 2.5 Program data audit + PDF coverage
    if os.path.exists(PROGRAM_REPORT_FILE):
        with open(PROGRAM_REPORT_FILE, "r", encoding="utf-8") as f:
            report = json.load(f)
            fact_sheet["program_count_views"] = report.get("program_count_views", {})
            fact_sheet["program_data_quality"] = {
                "field_coverage_after": report.get("field_coverage_after", {}),
                "faculty_breakdown": report.get("faculty_breakdown", {}),
            }
            fact_sheet["pdf_ingestion_summary"] = report.get("pdf_inventory_summary", {})
            fact_sheet["pdf_source_inventory"] = [
                {
                    "file": row.get("file", ""),
                    "in_knowledge_db": row.get("in_knowledge_db", False),
                    "pages": row.get("pages", 0),
                }
                for row in report.get("pdf_inventory", [])
            ]

    # 3. Add Administrative Sections
    admin_path = os.path.join(TEXT_DATA_DIR, "administration_knowledge.txt")
    if os.path.exists(admin_path):
        with open(admin_path, "r", encoding="utf-8") as f:
            text = f.read()
            # Crude regex for emails and names
            emails = list(set(re.findall(r'[\w\.-]+@svsu\.ac\.in', text)))
            fact_sheet["university_emails"] = emails

    # 4. International Student Guidelines
    int_path = os.path.join(TEXT_DATA_DIR, "admission_knowledge.txt")
    if os.path.exists(int_path):
        fact_sheet["international_admissions"] = {
            "portal": "https://studyinindia.gov.in",
            "requirements": ["AIU Equivalence Certificate", "Student Visa", "Medical fitness", "10 photos"],
            "reservation": "5% Supernumerary seats",
            "equivalence_mandatory": True
        }

    # 5. Save Master Fact Sheet
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(fact_sheet, f, indent=2)
    print(f"EXTENSIVE Master Fact Sheet saved to {OUTPUT_FILE}")

def rebuild_all():
    print("Initializing Knowledge Store...")
    knowledge_store.init_knowledge_store()
    print("Rebuilding Knowledge Base...")
    knowledge_store.rebuild_knowledge_store(force=True)
    generate_master_fact_sheet()
    print("Success! SVSU Knowledge is now optimized with ALL data.")

if __name__ == "__main__":
    rebuild_all()
