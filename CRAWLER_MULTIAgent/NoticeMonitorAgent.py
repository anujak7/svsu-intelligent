import os
import requests
import logging
import fitz # PyMuPDF
from urllib.parse import urlparse

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [NOTICE-MONITOR-13] - %(levelname)s - %(message)s')
logger = logging.getLogger("NoticeMonitor")

class NoticeMonitorAgent:
    def __init__(self):
        self.pdf_list_path = "ALL_SVSU_DATA/crawled_text/discovered_pdfs.txt"
        self.download_dir = "ALL_SVSU_DATA/pdfs"
        self.output_file = "ALL_SVSU_DATA/crawled_text/agent13_pdf_data.txt"
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs("ALL_SVSU_DATA/crawled_text", exist_ok=True)

    def process_all_pdfs(self):
        if not os.path.exists(self.pdf_list_path):
            logger.error(f"❌ PDF list not found at {self.pdf_list_path}. Run Dispatcher first.")
            return

        with open(self.pdf_list_path, "r", encoding="utf-8") as f:
            links = [line.strip() for line in f if line.strip()]

        logger.info(f"🔎 Found {len(links)} PDF links to process.")
        
        extracted_content = []
        
        for i, link in enumerate(links):
            # Limit to first 20 for testing / safety if list is huge
            # if i > 20: break 
            
            try:
                filename = os.path.basename(urlparse(link).path)
                if not filename.endswith(".pdf"):
                    filename += ".pdf"
                
                local_path = os.path.join(self.download_dir, filename)
                
                # 1. Download
                if not os.path.exists(local_path):
                    logger.info(f"📥 Downloading: {filename}")
                    resp = requests.get(link, timeout=10)
                    with open(local_path, "wb") as pf:
                        pf.write(resp.content)
                
                # 2. Extract Text
                logger.info(f"📄 Extracting: {filename}")
                doc_text = self.extract_text_from_pdf(local_path)
                
                if doc_text.strip():
                    extracted_content.append(f"\n--- [AGENT 13: PDF MONITOR] SOURCE: {link} ---\n{doc_text}\n")
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to process {link}: {e}")

        # 3. Save Master PDF Data
        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write("# SVSU PDF UPDATES & NOTICES DATA (AGENT 13)\n")
            f.writelines(extracted_content)
        
        logger.info(f"✅ Successfully processed PDFs and saved to {self.output_file}")

    def extract_text_from_pdf(self, path):
        try:
            doc = fitz.open(path)
            text = ""
            for page in doc:
                text += page.get_text()
            return text
        except Exception as e:
            return f"[ERROR EXTRACTING TEXT: {e}]"

if __name__ == "__main__":
    monitor = NoticeMonitorAgent()
    monitor.process_all_pdfs()
