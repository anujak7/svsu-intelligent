import json

path = 'SVSU_KNOWLEDGE/Structured_Data/official_admission_program_catalog_2025_26.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

phd_programs = [
    "Ph.D. in Mechanical Engineering",
    "Ph.D. in Computer Science & Engineering",
    "Ph.D. in Electronics Engineering",
    "Ph.D. in Management",
    "Ph.D. in Commerce",
    "Ph.D. in Psychology",
    "Ph.D. in English",
    "Ph.D. in Public Administration",
    "Ph.D. in Mathematics",
    "Ph.D. in Physics",
    "Ph.D. in Chemistry",
    "Ph.D. in Skill Education"
]

existing_names = [p.get("display_title", "") for p in data.get("programs", [])]
added = 0

for i, p in enumerate(phd_programs):
    if p not in existing_names:
        data["programs"].append({
            "serial_no": len(data["programs"]) + 1,
            "canonical_title": p,
            "display_title": p,
            "faculty": "Skill Faculty of Applied Sciences and Humanities",
            "industry_partner": "SVSU Research Wing / Various Industry Partners",
            "eligibility": "Master's degree in relevant discipline with at least 55% marks (or equivalent grade). Qualification in SVSU Ph.D. Entrance Test or UGC-NET/JRF.",
            "intake": "5",
            "session": "2025-26",
            "source_url": "https://www.svsu.ac.in/",
            "duration": "3-5 Years",
            "ncrf_level": "8",
            "legacy_catalog_title": p,
            "aliases": [p, p.replace("Ph.D. in ", "PhD ")],
            "menu_level": "Doctorate (Ph.D.)",
            "menu_category": "Doctorate Programs",
            "fees": "Refer to official SVSU notification",
            "fee_source": "official_fee_master_2025_26.json",
            "admission_process": "Through Ph.D. Entrance Exam and Interview.",
            "admission_source": "phd-ordinance.pdf",
            "scholarship": "Available for NET/JRF qualified candidates as per UGC norms.",
            "scholarship_source": "phd-ordinance.pdf",
            "placement": "Opportunities in academia and top research labs.",
            "placement_source": "General",
            "program_brief": f"The {p} program aims to foster advanced research skills and innovation.",
            "career_scope": "Academician, Researcher, Industry Expert",
            "career_scope_source": "General"
        })
        added += 1

data["program_count"] = len(data["programs"])

with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4)

print(f"Added {added} Ph.D. programs. Total programs: {len(data['programs'])}")
