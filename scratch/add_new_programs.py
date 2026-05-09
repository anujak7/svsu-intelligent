import json
import os
import re

CATALOG_PATH = r"C:\Users\USER\Desktop\BOT-SVSU\SVSU_KNOWLEDGE\Structured_Data\official_admission_program_catalog_2025_26.json"
NEW_PROGRAMS_PATH = r"C:\Users\USER\Desktop\BOT-SVSU\scratch\new_programs_raw.json"

def normalize_title(t):
    t = t.lower()
    t = re.sub(r'[^a-z0-9]', '', t)
    return t

def main():
    with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
        catalog = json.load(f)

    with open(NEW_PROGRAMS_PATH, 'r', encoding='utf-8') as f:
        new_programs = json.load(f)

    existing_titles = set()
    for p in catalog.get('programs', []):
        existing_titles.add(normalize_title(p.get('canonical_title', '')))
        existing_titles.add(normalize_title(p.get('display_title', '')))
        for alias in p.get('aliases', []):
            existing_titles.add(normalize_title(alias))

    max_serial = max([p.get('serial_no', 0) for p in catalog.get('programs', [])])

    added_count = 0
    for np in new_programs:
        np_norm = normalize_title(np['canonical_title'])
        # Also strip trailing stars/hashes for comparison
        clean_title = np['canonical_title'].replace('*', '').replace('#', '').strip()
        clean_norm = normalize_title(clean_title)

        if np_norm not in existing_titles and clean_norm not in existing_titles:
            max_serial += 1
            
            # Format the new program to match the schema
            new_entry = {
                "serial_no": max_serial,
                "canonical_title": clean_title,
                "display_title": clean_title,
                "faculty": np['faculty'],
                "industry_partner": np['industry_partner'],
                "eligibility": np['eligibility'],
                "intake": np['intake'],
                "session": "2026-27",
                "source_url": "SVSU BROCHURE2026.pdf",
                "duration": np['duration'],
                "ncrf_level": np['ncrf_level'],
                "legacy_catalog_title": "",
                "aliases": [clean_title],
                "menu_level": np['menu_level'],
                "menu_category": np['menu_category'],
                "fees": np['fees'],
                "fee_source": "SVSU BROCHURE2026.pdf",
                "admission_process": "Admissions will be as per the official SVSU 2026 brochure guidelines.",
                "admission_source": "SVSU BROCHURE2026.pdf",
                "scholarship": "As per SVSU prospectus scholarship section.",
                "scholarship_source": "SVSU BROCHURE2026.pdf",
                "placement": f"Industry Partners: {np['industry_partner']}",
                "placement_source": "SVSU BROCHURE2026.pdf",
                "program_brief": f"A comprehensive program in {clean_title} offered by {np['faculty']} with industry partner(s) {np['industry_partner']}.",
                "career_scope": f"Graduates can explore opportunities with our industry partners: {np['industry_partner']}.",
                "career_scope_source": "SVSU BROCHURE2026.pdf"
            }
            catalog['programs'].append(new_entry)
            added_count += 1
            print(f"Added new program: {clean_title}")

    catalog['program_count'] = len(catalog['programs'])

    with open(CATALOG_PATH, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=4, ensure_ascii=False)

    print(f"\nTotal new programs added: {added_count}")
    print(f"Total programs now in catalog: {catalog['program_count']}")

if __name__ == "__main__":
    main()
