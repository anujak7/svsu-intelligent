import pickle
import re

print("Starting deep extraction of all SVSU programs using multi-pattern regex...")

with open('BOT_BACKEND/data/admission_bm25_db.pkl', 'rb') as f:
    db = pickle.load(f)

program_entries = []
seen_programs = set()

# Regex for Table Rows: [ID] [NAME] [NCrF] [DURATION] [SEATS]
table_regex = re.compile(r'(\d{1,2})\s+([A-Z][^0-9\n]{5,100}?)\s+([4567](?:\.[05])?)\s+(\d+)\s+(\d+)')

for chunk in db['chunks']:
    text = chunk['text']
    
    # 1. Extract from Tables
    matches = table_regex.findall(text)
    for m in matches:
        prog_id, prog_name, ncrf, duration, seats = m
        prog_name = prog_name.strip()
        if prog_name.lower() not in seen_programs:
            entry = f"PROGRAM: {prog_name}\nID: {prog_id}\nNCrF Level: {ncrf}\nDuration: {duration} Years\nSeats: {seats}"
            program_entries.append(entry)
            seen_programs.add(prog_name.lower())

    # 2. Extract Detailed Blocks
    # We look for blocks containing "Eligibility:" and "About the Program"
    blocks = re.split(r'About the Program[s]?:', text)
    for block in blocks:
        if "Eligibility:" in block and "Duration:" in block:
            # Check if this program name is already in our list or if we can extract it
            # The name is often at the very end of the previous chunk or end of this block
            # For catalog purpose, we'll just store the raw detail block as a rich context
            detail = " ".join(block.split())
            if len(detail) > 100:
                program_entries.append(f"DETAIL DATA:\n{detail}")

print(f"Extraction finished. Total unique program entries/blocks: {len(program_entries)}")

output_file = 'BOT_BACKEND/data/svsu_all_programs_list.txt'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("# SVSU OFFICIAL PROGRAM DATABASE\n\n")
    f.write("\n\n---\n\n".join(program_entries))

print(f"Database saved to {output_file}")
