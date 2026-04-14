import os
import logging
from AgentBase import SVSUAgent

# Setup Master Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [MASTER-DISPATCHER] - %(levelname)s - %(message)s')
logger = logging.getLogger("CrawlerDispatcher")

# Mapping of Sections to Root URLs (Optimized from browser mapping)
AGENTS_CONFIG = {
    "Home": "https://svsu.ac.in/home",
    "About": "https://svsu.ac.in/about/about-university",
    "Academics": "https://svsu.ac.in/academics/departments",
    "Administration": "https://svsu.ac.in/administration/governance",
    "Admissions": "https://svsu.ac.in/admissions/instructions-for-admission",
    "Research": "https://rnd.svsu.ac.in/",
    "Students": "https://svsu.ac.in/students/student-support",
    "Programs": "https://svsu.ac.in/curriculum/curriculum-development",
    "Examinations": "https://svsu.ac.in/examination/results",
    "Notice": "https://svsu.ac.in/notices/general",
    "Library": "https://www.svsulibrary.in/",
    "Contact": "https://svsu.ac.in/contact"
}

def run_all_agents():
    logger.info("🎬 STARTING MULTI-AGENT CRAWLING EXPEDITION...")
    logger.info(f"Targeting {len(AGENTS_CONFIG)} Navbar Sections + Centralized PDF Monitor.")
    
    all_pdf_links = set()
    
    for name, url in AGENTS_CONFIG.items():
        logger.info(f"📍 Dispatching Specialist Agent: {name}")
        # Standardize depth for thoroughness vs speed
        max_depth = 5 
        if name in ["Home", "Contact"]: max_depth = 2
        if name in ["Notice", "Academics", "About"]: max_depth = 8 # Deep sections
        
        agent = SVSUAgent(name, url, max_depth=max_depth)
        agent.crawl()
        
        # Collect discoverd PDF links for Agent 13
        all_pdf_links.update(agent.pdf_links)

    # Save all discovered PDF links for the NoticeMonitorAgent (Agent 13)
    master_dir = "ALL_SVSU_DATA/crawled_text"
    os.makedirs(master_dir, exist_ok=True)
    pdf_list_path = os.path.join(master_dir, "discovered_pdfs.txt")
    
    with open(pdf_list_path, "w", encoding="utf-8") as f:
        for link in sorted(list(all_pdf_links)):
            f.write(link + "\n")
            
    logger.info(f"📑 Discovery Complete: {len(all_pdf_links)} PDF links saved for Agent 13 processing.")
    logger.info("✅ MULTI-AGENT MISSION SUCCESSFUL.")

if __name__ == "__main__":
    run_all_agents()
