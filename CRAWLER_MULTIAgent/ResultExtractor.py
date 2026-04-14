import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def extract_results():
    url = "https://svsu.ac.in/examination/results"
    print(f"Fetching results from {url}...")
    try:
        resp = requests.get(url, timeout=20)
        if resp.status_code != 200:
            print(f"Failed to fetch results page: {resp.status_code}")
            return
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        links = soup.find_all('a', href=True)
        
        results = []
        for link in links:
            href = link['href']
            text = link.get_text(separator=' ', strip=True)
            
            # Filter for PDF links that look like results
            if '.pdf' in href.lower() and ('result' in text.lower() or 'b.tech' in text.lower() or 'b.voc' in text.lower()):
                full_url = urljoin(url, href)
                results.append(f"RESULT_TITLE: {text} | PDF_LINK: {full_url}")
        
        # Also check for other result pages if any (pagination or specific semester pages)
        # For now, let's stick to the main one and maybe 'resultsjune2025' which I saw earlier
        
        # Check for resultsjune2025
        june_url = "https://svsu.ac.in/examination/resultsjune2025"
        resp_june = requests.get(june_url, timeout=20)
        if resp_june.status_code == 200:
            soup_june = BeautifulSoup(resp_june.text, 'html.parser')
            for link in soup_june.find_all('a', href=True):
                href = link['href']
                text = link.get_text(separator=' ', strip=True)
                if '.pdf' in href.lower() and ('result' in text.lower() or 'b.tech' in text.lower() or 'b.voc' in text.lower()):
                    full_url = urljoin(june_url, href)
                    results.append(f"RESULT_TITLE: {text} | PDF_LINK: {full_url}")

        output_path = r"c:\Users\USER\Desktop\BOT-SVSU\ALL_SVSU_DATA\crawled_text\results_directory.txt"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("SVSU OFFICIAL EXAMINATION RESULTS DIRECTORY\n")
            f.write("==========================================\n\n")
            for res in sorted(list(set(results))): # Deduplicate
                f.write(res + "\n\n")
        
        print(f"Successfully saved {len(set(results))} result links to {output_path}")

    except Exception as e:
        print(f"Error extracting results: {e}")

if __name__ == "__main__":
    extract_results()
