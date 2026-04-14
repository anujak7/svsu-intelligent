import fitz  # PyMuPDF
import pickle
import os
import re
from rank_bm25 import BM25Okapi

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "CRAWLER_MULTIAgent", "ALL_SVSU_DATA")
OUT_DIR = os.path.join(BASE_DIR, "BOT_BACKEND", "data")
if not os.path.exists(OUT_DIR):
    os.makedirs(OUT_DIR)

PROSPECTUS_PATH = os.path.join(DATA_DIR, "Document Prospectus-12.pdf")
A3_PATH = os.path.join(DATA_DIR, "A3.pdf")

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def build_db():
    chunks = []
    
    # Process Prospectus
    print("Extracting Document Prospectus-12.pdf ...")
    if os.path.exists(PROSPECTUS_PATH):
        try:
            doc = fitz.open(PROSPECTUS_PATH)
            # Pages 17 to 174 (0-indexed means 16 to 173)
            for page_num in range(16, 174):
                if page_num < len(doc):
                    page = doc[page_num]
                    text = page.get_text()
                    if text.strip():
                        chunks.append({
                            "source": f"Prospectus Page {page_num + 1}",
                            "text": clean_text(text)
                        })
            doc.close()
            print(f"Extracted {len(chunks)} chunks from Prospectus.")
        except Exception as e:
            print(f"Error reading Prospectus: {e}")
    else:
        print(f"Missing Prospectus at {PROSPECTUS_PATH}")

    # Process A3.pdf
    print("Extracting A3.pdf ...")
    initial_len = len(chunks)
    if os.path.exists(A3_PATH):
        try:
            doc = fitz.open(A3_PATH)
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                # Fallback to OCR if it's a scanned PDF
                if not text.strip():
                    import pytesseract
                    from PIL import Image
                    pix = page.get_pixmap(dpi=300)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    text = pytesseract.image_to_string(img)
                    
                if text.strip():
                    chunks.append({
                        "source": f"A3 Page {page_num + 1}",
                        "text": clean_text(text)
                    })
            doc.close()
            print(f"Extracted {len(chunks) - initial_len} chunks from A3.")
        except Exception as e:
            print(f"Error reading A3: {e}")
    else:
        print(f"Missing A3 at {A3_PATH}")

    # Build BM25 Index
    print("Building BM25 Fast Index for Admission Agent...")
    tokenized_corpus = [chunk["text"].lower().split() for chunk in chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    
    # Save the DB
    out_file = os.path.join(OUT_DIR, "admission_bm25_db.pkl")
    with open(out_file, "wb") as f:
        pickle.dump({"bm25": bm25, "chunks": chunks}, f)
        
    print(f"SUCCESS! Admission Database created at {out_file} with {len(chunks)} entries.")

if __name__ == "__main__":
    build_db()
