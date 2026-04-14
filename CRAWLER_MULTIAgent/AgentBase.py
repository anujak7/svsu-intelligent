import os
import re
import logging
from bs4 import BeautifulSoup
from langchain_community.document_loaders import RecursiveUrlLoader

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')

class SVSUAgent:
    def __init__(self, name, start_url, max_depth=5):
        self.name = name
        self.start_url = start_url
        self.max_depth = max_depth
        self.logger = logging.getLogger(name)
        self.output_dir = "ALL_SVSU_DATA/crawled_text"
        self.pdf_links = set() # Track PDFs found by this agent
        os.makedirs(self.output_dir, exist_ok=True)

    def custom_extractor(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        
        # ── PDF DISCOVERY ──
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.endswith('.pdf'):
                # Normalize URL if needed
                if not href.startswith('http'):
                    href = os.path.join(self.start_url, href)
                self.pdf_links.add(href)

        # Remove Noise
        for s in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            s.decompose()
            
        # Extract meaningful text
        text = soup.get_text(separator='\n')
        # Clean extra whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()

    def crawl(self):
        self.logger.info(f"🚀 Starting crawl for section: {self.name} at {self.start_url}")
        loader = RecursiveUrlLoader(
            url=self.start_url,
            max_depth=self.max_depth,
            extractor=self.custom_extractor,
            prevent_outside=True
        )
        
        try:
            docs = loader.load()
            self.logger.info(f"✅ Found {len(docs)} pages in {self.name} section.")
            self.save_data(docs)
            return docs
        except Exception as e:
            self.logger.error(f"❌ Crawl failed for {self.name}: {e}")
            return []

    def save_data(self, docs):
        output_file = os.path.join(self.output_dir, f"{self.name.lower()}_data.txt")
        with open(output_file, "w", encoding="utf-8") as f:
            for doc in docs:
                source = doc.metadata.get("source", "Unknown")
                f.write(f"\n--- [AGENT: {self.name}] SOURCE: {source} ---\n")
                f.write(doc.page_content)
                f.write("\n\n")
        self.logger.info(f"💾 Data saved to {output_file}")

if __name__ == "__main__":
    # Quick Test
    import sys
    test_agent = SVSUAgent("AboutAgent", "https://svsu.ac.in/about/about-university", max_depth=1)
    test_agent.crawl()
