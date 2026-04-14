import os
import re
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')

AGENTS_CONFIG = {
    "Home": "https://svsu.ac.in/home",
    "About": "https://svsu.ac.in/about/about-university",
    "Administration": "https://svsu.ac.in/administration/governance/bog",
    "Academics": "https://svsu.ac.in/academics/academic-overview",
    "Admissions": "https://svsu.ac.in/admissions/admission-overview",
    "Students": "https://svsu.ac.in/students/student-activities",
    "Research": "https://rnd.svsu.ac.in/",
    "Programs": "https://svsu.ac.in/academic-programs",
    "Results": "https://svsu.ac.in/examination/results",
    "Notices": "https://svsu.ac.in/notices/all-notices"
}

class SVSUQuickAgent:
    def __init__(self, name, start_url, max_depth=2):
        self.name = name
        self.start_url = start_url
        self.max_depth = max_depth
        self.logger = logging.getLogger(name)
        self.output_dir = r"c:\Users\USER\Desktop\BOT-SVSU\ALL_SVSU_DATA\crawled_text"
        self.visited = set()
        self.pdf_links = set()
        os.makedirs(self.output_dir, exist_ok=True)

    def crawl(self):
        self.logger.info(f"🚀 Starting Quick Crawl: {self.name} at {self.start_url}")
        results = []
        self._recursive_crawl(self.start_url, 0, results)
        self.save_data(results)
        return results

    def _recursive_crawl(self, url, depth, results):
        if depth > self.max_depth or url in self.visited:
            return
        
        parsed_url = urlparse(url)
        if parsed_url.netloc != "svsu.ac.in" and parsed_url.netloc != "rnd.svsu.ac.in":
            return

        self.visited.add(url)
        
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                return
            
            content_type = resp.headers.get('Content-Type', '')
            if 'text/html' not in content_type:
                return

            soup = BeautifulSoup(resp.text, "html.parser")
            
            # PDF Discovery
            for a in soup.find_all('a', href=True):
                href = a['href']
                full_href = urljoin(url, href)
                if full_href.lower().endswith('.pdf'):
                    self.pdf_links.add(full_href)
                elif depth < self.max_depth and full_href.startswith("http") and ("svsu.ac.in" in full_href):
                    self._recursive_crawl(full_href, depth + 1, results)

            # Extract Text
            for s in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
                s.decompose()
            
            text = soup.get_text(separator='\n')
            text = re.sub(r'\n\s*\n', '\n\n', text).strip()
            
            if text:
                results.append({"source": url, "content": text})

        except Exception as e:
            self.logger.error(f"Error crawling {url}: {e}")

    def save_data(self, results):
        output_file = os.path.join(self.output_dir, f"{self.name.lower()}_data.txt")
        # Overwrite if exists to ensure fresh data
        with open(output_file, "w", encoding="utf-8") as f:
            for res in results:
                f.write(f"\n--- [AGENT: {self.name}] SOURCE: {res['source']} ---\n")
                f.write(res['content'])
                f.write("\n\n")
        self.logger.info(f"💾 Saved {len(results)} pages to {output_file}")

if __name__ == "__main__":
    import json
    all_pdf_links = set()
    for name, url in AGENTS_CONFIG.items():
        agent = SVSUQuickAgent(name, url, max_depth=1)
        agent.crawl()
        all_pdf_links.update(agent.pdf_links)
    
    # Save PDF links for later processing
    pdf_log = r"c:\Users\USER\Desktop\BOT-SVSU\ALL_SVSU_DATA\crawled_text\discovered_pdfs.txt"
    with open(pdf_log, "w", encoding="utf-8") as f:
        for link in sorted(list(all_pdf_links)):
            f.write(link + "\n")
    print(f"Total PDF links found: {len(all_pdf_links)}")
