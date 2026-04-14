import fitz  # PyMuPDF
import os
import glob

def extract_pdf_text(pdf_path):
    print(f"Extracting: {pdf_path}")
    if not os.path.exists(pdf_path):
        return f"File not found: {pdf_path}"
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
        return text
    except Exception as e:
        return f"Error reading {pdf_path}: {e}"

knowledge_data = ""

# Search for all PDFs in the data directory
pdf_dir = r"CRAWLER_MULTIAgent\ALL_SVSU_DATA"
pdf_files = glob.glob(os.path.join(pdf_dir, "*.pdf"))

print(f"Found {len(pdf_files)} PDF files to process.")

for f in pdf_files:
    extracted = extract_pdf_text(f)
    knowledge_data += f"\n\n--- DOCUMENT: {os.path.basename(f)} ---\n{extracted}"

# Write to custom_facts.txt (Clear and Rewrite to avoid huge duplicates, or append carefully)
# The user wants "full crawl", so I will rewrite to ensure clean state with latest versions.
output_path = r"BOT_BACKEND\data\custom_facts.txt"

with open(output_path, "w", encoding="utf-8") as out:
    out.write("=== SVSU COMPREHENSIVE KNOWLEDGE BASE (Updated March 2026) ===\n")
    out.write(knowledge_data)

print(f"Knowledge base updated at {output_path} with all PDF data.")
