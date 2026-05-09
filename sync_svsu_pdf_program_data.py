import json
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = ROOT_DIR / "SVSU_KNOWLEDGE"
STRUCTURED_DIR = KNOWLEDGE_DIR / "Structured_Data"
TEXT_DIR = KNOWLEDGE_DIR / "Text_Knowledge"
PDF_DIR = KNOWLEDGE_DIR / "PDFs"
DATABASE_PATH = KNOWLEDGE_DIR / "Database" / "svsu_knowledge.db"

CATALOG_PATH = STRUCTURED_DIR / "official_admission_program_catalog_2025_26.json"
PDF_TEXT_PATH = TEXT_DIR / "pdf_knowledge.txt"
PROGRAM_LIST_PATH = STRUCTURED_DIR / "svsu_all_programs_list.txt"
OCR_REPORT_PATH = STRUCTURED_DIR / "pdf_ocr_refresh_report.json"
REPORT_PATH = STRUCTURED_DIR / "program_data_coverage_report.json"


MANUAL_ALIAS_MAP = {
    "B.Voc Public Services": [
        "B.Voc. (Public Services)",
        "B.Voc (Public Services)",
        "Bachelor in Vocation (Public Services)",
    ],
    "M.Voc Management-HRM": [
        "M.Voc. Management (HRM)",
    ],
    "BCA / BCA (Honours / Honours with Research)": [
        "Bachelor in Computer Applications BCA/ BCA (Honours) Specialization in AI&ML/Data Science/ BCA (Honours with Research)",
        "Bachelor in Computer Applications (BCA)",
    ],
    "Bachelor of Hotel Management": [
        "B. Hotel Management",
        "Bachelor of Hotel Management",
    ],
    "Diploma in Computer Science & Engineering": [
        "Diploma Computer Science and Engineering (AICTE Approved)",
        "Diploma in Computer Engineering",
    ],
    "Diploma Computer Generative AI / Cyber Security": [
        "Diploma (Computer) Generative AI/ Cyber Security",
    ],
    "M.Sc. Geo-informatics": [
        "M.Sc. (Geo-Informatics)",
        "M.Sc. (Geo- Informatics)",
    ],
    "B.Tech Computer Science & Engineering (AI/ML)": [
        "B. Tech. Computer Science and Engineering (Artificial Intelligence and Machine Learning)",
        "Bachelor of Technology (B.Tech.) Computer Science & Engineering (AI & ML)",
    ],
    "B.Tech Electrical Engineering": [
        "B.Tech. (Electrical Engineering) with Minor/Hons. in Electric Vehicles/ Cyber Security/ Robotics",
        "Bachelor of Technology (B.Tech.) Electrical Engineering",
    ],
    "B.Voc (Medical Laboratory Technology) Honours with Research": [
        "B.Voc. (Medical Laboratory Technology) Honours with Research",
        "B.Voc. (MLT) Honours with Research",
        "B.Voc. (Medical Laboratory Technology)",
    ],
    "Undergraduate Certificate in Animation, Multimedia and Graphics": [
        "Undergraduate Certificate in Graphics and communication Design",
        "Undergraduate Certificate in Animation, Multimedia and Graphics",
    ],
    "Undergraduate Certificate in Music (Folk Art - Banchari / Instrumental / Vocal)": [
        "Undergraduate Certificate in Music (Folk Art -Banchari/ Vocal/ Instrumental)",
        "Undergraduate Certificate in Music (Folk Art - Banchari/Instrumental/Vocal)",
        "UG Certificate in Music (Folk Art-Banchari)",
    ],
    "Undergraduate Diploma in German Language": [
        "Undergraduate Diploma in German Language",
        "Undergraduate Certificate German Language",
    ],
    "Undergraduate Diploma in Japanese Language": [
        "Undergraduate Diploma in Japanese Language",
        "Undergraduate Certificate in Japanese Language",
    ],
    "MBA": [
        "MBA (General)",
        "MBA",
    ],
}


FIELD_NAMES = [
    "industry_partner",
    "duration",
    "ncrf_level",
    "program_brief",
]


MANUAL_PDF_BACKED_OVERRIDES = {
    "B.Com (Hons. / Hons. with Research)": {
        "ncrf_level": {
            "value": "5.5/6",
            "source": "Document Prospectus-12.pdf p.46",
        },
        "industry_partner": {
            "value": "All India Chartered Accountants Society, Ease My Process (Gujrani & Assoc), SOTC, The Jammu & Kashmir Bank",
            "source": "Document Prospectus-12.pdf p.46",
        },
        "program_brief": {
            "value": (
                "The B.Com. (Hons./Hons. with Research) is a professional 3/4 year program aligned to NEP with "
                "multiple entry and exit at each year. The program is divided into 6/8 semesters. Students after "
                "1st year will be eligible to get a UG Certificate, after 2nd year will be eligible to get UG "
                "Diploma and after completion of 3rd year will get B.Com degree and after 4th year will get "
                "B.Com (Hons.) / Hons. with Research. The program enables and empowers students to acquire the "
                "necessary knowledge, skills and abilities to analyze and synthesize the contemporary realities "
                "of business and commerce including accounting, finance and management. The program prepares "
                "students for job roles such as business development, accountancy, e-commerce, analyst, taxation, "
                "financial planning, marketing and business management in public and private sectors."
            ),
            "source": "Document Prospectus-12.pdf p.51",
            "source_mode": "direct_pdf_text",
        },
    },
    "B.Voc Management-Financial Services": {
        "ncrf_level": {
            "value": "5.5/6",
            "source": "Document Prospectus-12.pdf p.51",
        },
        "industry_partner": {
            "value": "Ease My Process (Gujrani & Assoc), SOTC, The Jammu & Kashmir Bank",
            "source": "Document Prospectus-12.pdf p.51",
        },
        "program_brief": {
            "value": (
                "The financial services including retail and corporate banking, investment management, investment "
                "consulting, investment banking, mortgages, and life insurance and micro financing offers huge "
                "opportunities to individuals with required skills. The 3/4-year B.Voc. (Management in Financial "
                "Services) offers a wide range of courses to enable individuals to become highly competent "
                "professionals for the industry particularly in microfinance, insurance and mutual fund advisory, "
                "investment banking and financial consulting."
            ),
            "source": "Document Prospectus-12.pdf p.51",
            "source_mode": "direct_pdf_text",
        },
    },
    "D.Voc Office Management": {
        "ncrf_level": {
            "value": "4",
            "source": "Document Prospectus-12.pdf p.48",
        },
        "industry_partner": {
            "value": "SOTC, Techview Research & Processing Pvt Ltd",
            "source": "Document Prospectus-12.pdf p.48",
        },
        "program_brief": {
            "value": (
                "The Diploma of Vocation in Office Management includes the management of all office work which "
                "includes planning, organising, leading and controlling. It enables students to be professionally "
                "trained in different aspects of day-to-day office management. Graduates are prepared for positions "
                "such as Typist/Stenographer, Computer Operator, Office Coordinator and Office Secretary."
            ),
            "source": "Document Prospectus-12.pdf p.48",
            "source_mode": "direct_pdf_text",
        },
    },
    "Undergraduate Certificate in Food Production & Traditional Sweets": {
        "ncrf_level": {
            "value": "4.5",
            "source": "Document Prospectus-12.pdf p.53",
        },
        "program_brief": {
            "value": (
                "The industry driven by taste buds is recently undergoing a revolution. Indian ethnic foods are "
                "filling the market space yielded by fast and continental foods. The consumer is gravitating "
                "towards Indian food for its simplicity and use of healthy ingredients. To cater to this "
                "ever-growing segment, SVSU has designed this program under the dual vocational education model. "
                "Processing of food involves the use of raw ingredients to produce marketable food products that "
                "can be easily prepared and served to the consumer. Typical activities include mincing, "
                "emulsification, cooking, pasteurization, preservation, canning, dicing, slicing, freezing and drying."
            ),
            "source": "Document Prospectus-12.pdf p.53",
            "source_mode": "direct_pdf_text",
        },
    },
    "M.Voc Management-HRM": {
        "ncrf_level": {
            "value": "6.5",
            "source": "brochure_2024.pdf p.7",
        },
        "program_brief": {
            "value": (
                "Official PDF programme rows describe M.Voc. Management-HRM as a 2-year, NCrF 6.5 SVSU "
                "postgraduate programme under SFMSR with industry linkage through Mount Talent and Dzire Group "
                "for advanced management and human-resource focused learning."
            ),
            "source": "brochure_2024.pdf p.7",
            "source_mode": "derived_from_official_pdf_row",
        },
    },
    "B.Tech Computer Engineering": {
        "ncrf_level": {
            "value": "6",
            "source": "Document Prospectus-12.pdf p.35",
        },
        "industry_partner": {
            "value": "DarkBlue DevOps, Vastav Intellect, Globus Eight, and YBI Foundation",
            "source": "Document Prospectus-12.pdf p.35",
        },
        "program_brief": {
            "value": (
                "The Bachelor of Technology (B.Tech.) in Computer Engineering is a comprehensive four-year "
                "undergraduate program structured to provide students with a robust academic and technical "
                "foundation in computer science and engineering. The curriculum integrates mathematical theories "
                "and computational principles to solve complex real-world engineering problems, with in-depth "
                "exposure to system architecture, software development methodologies and secure computing practices. "
                "Through theoretical and hands-on training, students build skills in programming, algorithmic "
                "thinking, software engineering and cybersecurity, and may also pursue minor specializations such "
                "as Data Science, Cyber Security and Blockchain."
            ),
            "source": "Document Prospectus-12.pdf p.35",
            "source_mode": "direct_pdf_text",
        },
    },
    "B.Tech Computer Science & Engineering (AI/ML)": {
        "ncrf_level": {
            "value": "6",
            "source": "Document Prospectus-12.pdf p.36",
        },
        "program_brief": {
            "value": (
                "The B.Tech. Computer Science & Engineering (AI & ML) is a 4-year undergraduate program "
                "comprising 8 semesters. It is designed to develop advanced machine learning systems by deploying "
                "artificial intelligence algorithms and to build efficient applications or solutions integrated "
                "with analytical information. The program imparts comprehensive knowledge of programming languages "
                "for AI and ML applications and may offer electives in Blockchain, Internet of Things (IoT) and "
                "cloud. Project-based learning, choice-based credits and industry-backed internship/OJT prepare "
                "learners for the professional environment."
            ),
            "source": "Document Prospectus-12.pdf p.36",
            "source_mode": "direct_pdf_text",
        },
    },
    "D.Voc Mechanical Manufacturing": {
        "ncrf_level": {
            "value": "4",
            "source": "Document Prospectus-12.pdf p.23",
        },
        "program_brief": {
            "value": (
                "D.Voc. (Mechanical-Manufacturing) is aligned to NEP 2020 and NCrF Level 4.0 on the dual "
                "education model. It offers multiple entry and exit options, allowing students to obtain a "
                "Certificate of Vocation or Diploma of Vocation in Mechanical Manufacturing based on the level "
                "completed. Students spend the first year in the classroom and the second year in industry for OJT. "
                "The program focuses on shop-floor familiarity, tools and equipment, quality manufacturing "
                "processes, CNC and CMM exposure, metrology, quality inspection/control and automotive component "
                "manufacturing."
            ),
            "source": "Document Prospectus-12.pdf p.23",
            "source_mode": "direct_pdf_text",
        },
    },
    "Undergraduate Certificate in Music (Folk Art - Banchari / Instrumental / Vocal)": {
        "ncrf_level": {
            "value": "4.5",
            "source": "Document Prospectus-12.pdf p.58, p.62",
        },
        "industry_partner": {
            "value": "SVSU",
            "source": "Document Prospectus-12.pdf p.58, p.62",
        },
        "program_brief": {
            "value": (
                "Banchari/Instrumental/Vocal belongs to old Brij culture. This rich art form is today confined "
                "to a few villages in Faridabad and Palwal districts and is being kept alive through the "
                "guru-shishya parampara. The art form is dedicated to the worship of Radha-Krishna and divine "
                "love, and includes singing, dancing, and playing instruments such as harmonium, dholak, manjeera, "
                "bansuri, jhanj and nagada. Banchari artists also stage Ram Leela and other plays."
            ),
            "source": "Document Prospectus-12.pdf p.62",
            "source_mode": "direct_pdf_text",
        },
    },
    "Undergraduate Certificate in Animation, Multimedia and Graphics": {
        "ncrf_level": {
            "value": "4.5",
            "source": "Document Prospectus-12.pdf p.58, p.62",
        },
        "industry_partner": {
            "value": "SVSU",
            "source": "Document Prospectus-12.pdf p.58, p.62",
        },
        "program_brief": {
            "value": (
                "Undergraduate Certificate in Animation, Multimedia and Graphics is a 1 year (2 semesters) "
                "program at NCrF Level 4.5. The program offers overall training from traditional print to online "
                "and interactive design and multimedia training. Core courses such as page layout, typography, "
                "sketching and photography are taught with a focus on fundamental skills, practice, and leading "
                "graphic-design software. The program also helps students manage projects and interact with clients "
                "professionally."
            ),
            "source": "Document Prospectus-12.pdf p.62",
            "source_mode": "direct_pdf_text",
        },
    },
}


def compact_text(value: str) -> str:
    return " ".join(str(value or "").replace("\u00a0", " ").split()).strip()


def normalize_lookup_text(value: str) -> str:
    text = compact_text(value).lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, payload) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_text_sources() -> dict:
    sources = {}
    for path in [PDF_TEXT_PATH, PROGRAM_LIST_PATH]:
        if path.exists():
            sources[path.name] = path.read_text(encoding="utf-8", errors="ignore")
    return sources


def compute_field_coverage(programs: list) -> dict:
    coverage = {}
    total = len(programs)
    for field in FIELD_NAMES:
        present = sum(1 for row in programs if compact_text(row.get(field)))
        coverage[field] = {
            "present": present,
            "missing": max(total - present, 0),
        }
    return coverage


def make_search_terms(program: dict) -> list:
    raw_terms = []
    for key in ("display_title", "canonical_title", "legacy_catalog_title"):
        cleaned = compact_text(program.get(key))
        if cleaned:
            raw_terms.append(cleaned)
    for alias in program.get("aliases", []) if isinstance(program.get("aliases"), list) else []:
        cleaned = compact_text(alias)
        if cleaned:
            raw_terms.append(cleaned)
    raw_terms.extend(MANUAL_ALIAS_MAP.get(compact_text(program.get("display_title")), []))

    expanded = set()
    for term in raw_terms:
        if not term:
            continue
        expanded.add(term)
        expanded.add(term.replace(" / ", "/"))
        expanded.add(term.replace(" / ", " "))
        expanded.add(term.replace("(AI/ML)", "(AI & ML)"))
        expanded.add(term.replace("Geo-informatics", "Geo Informatics"))
        expanded.add(term.replace("Honours / Honours with Research", "Honours) Specialization in AI&ML/Data Science/ BCA (Honours with Research)"))

    ordered = sorted(
        {compact_text(term) for term in expanded if compact_text(term)},
        key=lambda value: (-len(value), value.lower()),
    )
    return ordered


def score_window(window: str) -> int:
    lower = window.lower()
    score = 0
    for marker in [
        "eligibility",
        "ncrf level",
        "industry partner",
        "industry partners",
        "duration",
        "seats",
        "about the program",
        "about the programme",
    ]:
        if marker in lower:
            score += 1
    return score


def find_best_windows(program: dict, source_texts: dict) -> list:
    terms = make_search_terms(program)
    windows = []
    for source_name, source_text in source_texts.items():
        best_window = ""
        best_score = -1
        best_term = ""
        for term in terms:
            for match in re.finditer(re.escape(term), source_text, flags=re.IGNORECASE):
                start = max(0, match.start() - 250)
                end = min(len(source_text), match.end() + 4500)
                window = source_text[start:end]
                current_score = score_window(window) * 100 + len(term)
                if current_score > best_score:
                    best_score = current_score
                    best_window = window
                    best_term = term
                if best_score >= 700:
                    break
            if best_score >= 700:
                break
        if best_window:
            windows.append({
                "source": source_name,
                "term": best_term,
                "score": best_score,
                "window": best_window,
            })
    windows.sort(key=lambda item: item["score"], reverse=True)
    return windows


def pick_best_value(values: list, minimum_length: int = 1) -> str:
    cleaned = [compact_text(value) for value in values if compact_text(value)]
    cleaned = [value for value in cleaned if len(value) >= minimum_length]
    if not cleaned:
        return ""
    return max(cleaned, key=lambda value: (len(value), value))


def extract_regex_values(patterns: list, text: str) -> list:
    values = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE | re.DOTALL):
            captured = compact_text(match.group(1))
            if captured:
                values.append(captured)
    return values


def normalize_duration(value: str) -> str:
    cleaned = compact_text(value)
    if not cleaned:
        return ""
    if "year" in cleaned.lower():
        return cleaned

    match = re.fullmatch(r"(\d+)(?:/(\d+))?\s*semesters?", cleaned, flags=re.IGNORECASE)
    if not match:
        return cleaned

    first = int(match.group(1))
    second = int(match.group(2)) if match.group(2) else None
    if second:
        return f"{first // 2}/{second // 2} Years ({first}/{second} Semesters)"
    return f"{first // 2} Years ({first} Semesters)"


def duration_from_fees(fees_text: str) -> str:
    match = re.search(r"Course duration reference:\s*([^.]*)\.", fees_text or "", flags=re.IGNORECASE)
    if not match:
        return ""
    return normalize_duration(match.group(1))


def extract_fields_from_windows(windows: list, current_program: dict) -> dict:
    field_candidates = {
        "industry_partner": [],
        "duration": [],
        "ncrf_level": [],
        "program_brief": [],
    }

    for item in windows:
        window = item["window"]

        field_candidates["industry_partner"].extend(
            extract_regex_values(
                [
                    r"Industry Partners?\s*:\s*(.*?)\s*(?:Duration|Seats?|About the Program|About the Programme|Job Roles|How to Apply|$)",
                ],
                window,
            )
        )
        field_candidates["duration"].extend(
            extract_regex_values(
                [
                    r"Duration\s*:\s*(.*?)\s*(?:Seats?|About the Program|About the Programme|Job Roles|How to Apply|$)",
                ],
                window,
            )
        )
        field_candidates["ncrf_level"].extend(
            extract_regex_values(
                [
                    r"NCrF Level\s*:\s*(.*?)\s*(?:Industry Partner|Industry Partners|Duration|Seats?|About the Program|About the Programme|$)",
                ],
                window,
            )
        )
        field_candidates["program_brief"].extend(
            extract_regex_values(
                [
                    r"About the Program(?:me)?(?:s)?\s*[-:]\s*(.*?)\s*(?:Programme Outcomes|Program Outcomes|How to Apply|Job Roles aligned|Job Role|Job Opportunity|$)",
                ],
                window,
            )
        )

        if "DETAIL DATA:" in window and "Eligibility:" in window:
            detail_match = re.search(
                r"DETAIL DATA:\s*(.*?)\s*Eligibility:",
                window,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if detail_match:
                field_candidates["program_brief"].append(detail_match.group(1))

    extracted = {
        "industry_partner": pick_best_value(field_candidates["industry_partner"]),
        "duration": normalize_duration(
            pick_best_value(field_candidates["duration"]) or duration_from_fees(current_program.get("fees", ""))
        ),
        "ncrf_level": pick_best_value(field_candidates["ncrf_level"]),
        "program_brief": pick_best_value(field_candidates["program_brief"], minimum_length=40),
    }

    if extracted["program_brief"]:
        extracted["program_brief"] = compact_text(extracted["program_brief"])[:1400]

    return extracted


def apply_manual_pdf_overrides(program: dict) -> list:
    overrides = MANUAL_PDF_BACKED_OVERRIDES.get(compact_text(program.get("display_title")))
    if not overrides:
        return []

    updated_fields = []
    verified_sources = list(program.get("verified_sources", [])) if isinstance(program.get("verified_sources"), list) else []

    for field_name, meta in overrides.items():
        value = compact_text(meta.get("value"))
        if not value:
            continue

        current_value = compact_text(program.get(field_name))
        should_apply = not current_value or field_name == "program_brief"
        if should_apply and current_value != value:
            program[field_name] = value
            updated_fields.append(field_name)

        source_value = compact_text(meta.get("source"))
        if source_value:
            program[f"{field_name}_source"] = source_value
            verified_sources.append(source_value)

        source_mode = compact_text(meta.get("source_mode"))
        if source_mode:
            program[f"{field_name}_source_mode"] = source_mode

    if verified_sources:
        deduped = []
        seen = set()
        for source in verified_sources:
            key = source.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(source)
        program["verified_sources"] = deduped

    return updated_fields


def enrich_catalog(payload: dict, source_texts: dict) -> dict:
    programs = payload.get("programs", [])
    before = compute_field_coverage(programs)

    enrichment_log = []
    for program in programs:
        windows = find_best_windows(program, source_texts)
        extracted = extract_fields_from_windows(windows, program)

        updated_fields = []
        for field_name, value in extracted.items():
            current_value = compact_text(program.get(field_name))
            if not current_value and value:
                program[field_name] = value
                updated_fields.append(field_name)
            elif field_name == "program_brief" and value and len(value) > len(current_value):
                program[field_name] = value
                updated_fields.append(field_name)

        updated_fields.extend(apply_manual_pdf_overrides(program))
        updated_fields = sorted(set(updated_fields))

        enrichment_log.append({
            "program": compact_text(program.get("display_title")),
            "updated_fields": updated_fields,
            "matched_sources": [item["source"] for item in windows[:2]],
            "matched_terms": [item["term"] for item in windows[:2]],
        })

    payload["program_count"] = len(programs)
    payload["enriched_from"] = sorted(
        set(
            list(payload.get("enriched_from", []))
            + [name for name in source_texts.keys()]
        )
    )
    enriched_fields = set(payload.get("enriched_fields", []))
    enriched_fields.update(FIELD_NAMES)
    payload["enriched_fields"] = sorted(enriched_fields)

    after = compute_field_coverage(programs)
    return {
        "payload": payload,
        "before": before,
        "after": after,
        "enrichment_log": enrichment_log,
    }


def load_db_pdf_labels() -> set:
    if not DATABASE_PATH.exists():
        return set()
    try:
        import sqlite3

        conn = sqlite3.connect(DATABASE_PATH)
        rows = conn.execute(
            "SELECT source_label FROM knowledge_documents WHERE source_type = 'pdf'"
        ).fetchall()
        conn.close()
        return {row[0] for row in rows}
    except Exception:
        return set()


def build_pdf_inventory() -> list:
    ocr_lookup = {}
    if OCR_REPORT_PATH.exists():
        report = load_json(OCR_REPORT_PATH)
        for row in report.get("pdfs", []):
            ocr_lookup[row.get("file")] = row

    db_labels = load_db_pdf_labels()
    inventory = []
    for pdf_path in sorted(PDF_DIR.glob("*.pdf")):
        ocr_row = ocr_lookup.get(pdf_path.name, {})
        inventory.append({
            "file": pdf_path.name,
            "bytes": pdf_path.stat().st_size,
            "in_knowledge_db": pdf_path.name in db_labels,
            "pages": ocr_row.get("pages"),
            "native_text_pages": ocr_row.get("native_text_pages"),
            "ocr_pages": ocr_row.get("ocr_pages"),
            "empty_pages": ocr_row.get("empty_pages"),
        })
    return inventory


def build_program_count_views(payload: dict) -> dict:
    return {
        "official_catalog_loaded_for_bot": len(payload.get("programs", [])),
        "official_admission_bulletin_2025_26_programs": len(payload.get("programs", [])),
        "updated_bulletin_2025_26_programs": len(payload.get("programs", [])),
        "document_prospectus_12_detailed_program_profiles": len(payload.get("programs", [])),
        "short_term_program_calendar_entries": 20,
        "count_note": (
            "Current SVSU PDFs mix long-term admission programmes, short-term programmes, and research/regulation "
            "documents. The bot should answer with the source/session label instead of forcing one universal total."
        ),
    }


def build_faculty_breakdown(programs: list) -> dict:
    breakdown = Counter()
    for row in programs:
        faculty = compact_text(row.get("faculty")) or "Unknown"
        breakdown[faculty] += 1
    return dict(sorted(breakdown.items(), key=lambda item: item[0]))


def build_missing_field_report(programs: list) -> list:
    rows = []
    for row in programs:
        missing = [field for field in FIELD_NAMES if not compact_text(row.get(field))]
        if missing:
            rows.append({
                "program": compact_text(row.get("display_title")),
                "missing_fields": missing,
            })
    return rows


def main() -> None:
    if not CATALOG_PATH.exists():
        raise FileNotFoundError(f"Catalog not found: {CATALOG_PATH}")

    payload = load_json(CATALOG_PATH)
    source_texts = load_text_sources()
    enriched = enrich_catalog(payload, source_texts)
    save_json(CATALOG_PATH, enriched["payload"])

    inventory = build_pdf_inventory()
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "catalog_path": str(CATALOG_PATH),
        "official_catalog_session": payload.get("session", ""),
        "field_coverage_before": enriched["before"],
        "field_coverage_after": enriched["after"],
        "updated_programs": [
            row for row in enriched["enrichment_log"] if row["updated_fields"]
        ],
        "programs_still_missing_fields": build_missing_field_report(enriched["payload"].get("programs", [])),
        "program_count_views": build_program_count_views(enriched["payload"]),
        "faculty_breakdown": build_faculty_breakdown(enriched["payload"].get("programs", [])),
        "pdf_inventory": inventory,
        "pdf_inventory_summary": {
            "pdfs_in_folder": len(inventory),
            "pdfs_already_in_knowledge_db": sum(1 for row in inventory if row["in_knowledge_db"]),
            "pdfs_missing_from_knowledge_db": [
                row["file"] for row in inventory if not row["in_knowledge_db"]
            ],
        },
    }
    save_json(REPORT_PATH, report)

    print("Updated catalog:", CATALOG_PATH)
    print("Coverage report:", REPORT_PATH)
    print("Program brief coverage:", enriched["before"]["program_brief"], "->", enriched["after"]["program_brief"])
    print("Duration coverage:", enriched["before"]["duration"], "->", enriched["after"]["duration"])
    print("NCrF coverage:", enriched["before"]["ncrf_level"], "->", enriched["after"]["ncrf_level"])
    print("Industry partner coverage:", enriched["before"]["industry_partner"], "->", enriched["after"]["industry_partner"])


if __name__ == "__main__":
    main()
