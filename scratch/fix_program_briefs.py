import json
import os

json_path = r"c:\Users\USER\Desktop\BOT-SVSU\SVSU_KNOWLEDGE\Structured_Data\official_admission_program_catalog_2025_26.json"

def clean_brief(program):
    full_title = program.get("display_title", program.get("canonical_title", "This program"))
    level = program.get("menu_level", "skill")
    faculty = program.get("faculty", "SVSU")
    brief = program.get("program_brief", "").strip()
    
    t_low = full_title.lower()
    b_low = brief.lower()
    
    # 1. Obvious garbage
    bad_markers = ["banchari", "brij culture", "radha-krishna", "guru-shishya", "divine love"]
    if any(m in b_low for m in bad_markers):
        if "music" not in t_low and "banchari" not in t_low:
            return f"{full_title} is a professional {level.lower()} programme offered by {faculty} at SVSU. This industry-aligned course focuses on developing practical expertise and hands-on skills through a robust dual-education model."

    # 2. Relevancy check: Brief should mention some part of the title
    title_tokens = [t.strip(",.()") for t in t_low.split() if len(t.strip(",.()")) > 3]
    # Filter out common words
    common = {"bachelor", "master", "diploma", "vocation", "science", "technology", "engineering"}
    distinct_tokens = [t for t in title_tokens if t not in common]
    
    if distinct_tokens:
        has_overlap = any(token in b_low for token in distinct_tokens)
        if not has_overlap:
             return f"{full_title} is a professional {level.lower()} programme offered by {faculty} at SVSU, designed to equip students with industry-relevant competencies and practical training."

    # 3. Swap checks
    if "bachelor" in t_low and "m voc" in b_low:
         return f"{full_title} is an undergraduate B.Voc programme at SVSU, integrating academic knowledge with practical industry exposure."
    if "master" in t_low and "b.voc" in b_low:
         return f"{full_title} is a postgraduate M.Voc programme at SVSU, providing advanced skill training in the relevant field."

    return brief

def main():
    if not os.path.exists(json_path): return
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    fixed_count = 0
    for p in data['programs']:
        old = p.get("program_brief", "")
        new = clean_brief(p)
        if old != new:
            p["program_brief"] = new
            fixed_count += 1

    print(f"Fixed {fixed_count} program briefs.")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    main()
