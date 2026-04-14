import os
import re

def clean_text(text):
    return text.strip().replace("\n", " ")

def extract_catalog():
    kb_path = "prospectus_deep_knowledge.txt"
    catalog_path = "svsu_program_catalog.txt"
    
    if not os.path.exists(kb_path):
        print(f"Error: {kb_path} not found.")
        return

    with open(kb_path, "r", encoding="utf8") as f:
        lines = f.readlines()

    catalog = []
    current_faculty = "General"
    
    for i, line in enumerate(lines):
        if "Skill Faculty of" in line:
            current_faculty = line.strip()
            continue

        if "Eligibility:" in line:
            # Look back for program name (usually 1-3 lines back)
            program_name = "Unknown Program"
            for j in range(1, 4):
                if i - j >= 0:
                    prev_line = lines[i-j].strip()
                    if prev_line and not prev_line.isdigit() and len(prev_line) > 3 and "---" not in prev_line and "About" not in prev_line:
                        program_name = prev_line
                        break
            
            # Look forward for details
            seats = "As per norms"
            duration = "N/A"
            eligibility = line.replace("Eligibility:", "").strip()
            partner = "TBA"
            
            for k in range(1, 15):
                if i + k < len(lines):
                    next_line = lines[i+k]
                    if "Seat" in next_line:
                        match = re.search(r"Seat[s]?:\s*(.*)", next_line, re.I)
                        if match: seats = match.group(1).strip()
                    elif "Duration" in next_line:
                        match = re.search(r"Duration:\s*(.*)", next_line, re.I)
                        if match: duration = match.group(1).strip()
                    elif "Industry Partner" in next_line:
                        match = re.search(r"Industry Partner:\s*(.*)", next_line, re.I)
                        if match: partner = match.group(1).strip()
                    elif "About the Program" in next_line:
                        break
            
            entry = f"[PROGRAM CATALOG]\n"
            entry += f"Faculty: {current_faculty}\n"
            entry += f"Program: {program_name}\n"
            entry += f"Seats: {seats}\n"
            entry += f"Duration: {duration}\n"
            entry += f"Eligibility: {eligibility}\n"
            entry += f"Industry Partner: {partner}\n"
            catalog.append(entry)

    # De-duplicate
    unique_catalog = []
    seen = set()
    for item in catalog:
        if item not in seen:
            unique_catalog.append(item)
            seen.add(item)

    with open(catalog_path, "w", encoding="utf8") as f:
        f.write("# SVSU OFFICIAL PROGRAM CATALOG (2025-26)\n\n")
        f.write("\n\n".join(unique_catalog))
    
    print(f"Catalog created with {len(unique_catalog)} entries.")

if __name__ == "__main__":
    extract_catalog()
