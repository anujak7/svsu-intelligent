import pdfplumber
import os

pdf_path = r"c:\Users\USER\Desktop\BOT-SVSU\SVSU_KNOWLEDGE\PDFs\SVSU BROCHURE2026.pdf"
output_path = r"c:\Users\USER\Desktop\BOT-SVSU\SVSU_KNOWLEDGE\Text_Knowledge\prospectus_pages_16_20.txt"

def extract_pages(start_page, end_page):
    if not os.path.exists(pdf_path):
        print(f"PDF not found: {pdf_path}")
        return
    
    text_content = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Pages 16 to 20 (1-based)
            for i in range(start_page - 1, end_page):
                if i < len(pdf.pages):
                    page = pdf.pages[i]
                    text = page.extract_text()
                    if text:
                        text_content.append(f"--- PAGE {i+1} ---\n{text}\n")
                else:
                    print(f"Page {i+1} out of range.")
        
        full_text = "\n".join(text_content)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        print(f"Extracted {len(text_content)} pages to {output_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    extract_pages(16, 20)
