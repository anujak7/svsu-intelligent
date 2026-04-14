import os
import re
import sys
import pickle
import logging
import subprocess
import paramiko
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from langchain_community.document_loaders import TextLoader, PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SVSU-SYNC] - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Paths (Adjusted for actual project structure)
BASE_DIR = r"c:\Users\USER\Desktop\BOT-SVSU"
CRAWLER_DIR = os.path.join(BASE_DIR, "CRAWLER_MULTIAgent")
DATA_DIR = os.path.join(BASE_DIR, "ALL_SVSU_DATA")
CRAWLED_TEXT_DIR = os.path.join(DATA_DIR, "crawled_text")

# Backend target (Where the bot loads DB from)
BACKEND_DIR = os.path.join(BASE_DIR, "BOT_BACKEND")
FAISS_DIR = os.path.join(BACKEND_DIR, "faiss_db")
BM25_DOCS_PATH = os.path.join(BACKEND_DIR, "bm25_docs.pkl")

# VM Configuration
VM_IP = '98.70.37.219'
VM_USER = 'svsuuser'
VM_PASS = 'svsuindia@2026'
VM_BASE_PATH = '/home/svsuuser/svsu-intelligent'

def run_multi_agent_crawler():
    logger.info("🎬 Starting Multi-Agent Crawler...")
    try:
        # Run CrawlerDispatcher.py (Using sys.executable for consistency)
        dispatcher_path = os.path.join(CRAWLER_DIR, "CrawlerDispatcher.py")
        # We can also run our specialized ResultExtractor.py first to ensure results are fresh
        result_extractor = os.path.join(CRAWLER_DIR, "ResultExtractor.py")
        subprocess.run([sys.executable, result_extractor], check=True)
        
        # Now run the main dispatcher (if it doesn't hang)
        # For now, let's assume dispatcher hangs less when run correctly with sys.executable
        # subprocess.run([sys.executable, dispatcher_path], check=True, capture_output=True, text=True) 
        
        # Run QuickAgent.py instead if Dispatcher is problematic
        quick_agent = os.path.join(CRAWLER_DIR, "QuickAgent.py")
        subprocess.run([sys.executable, quick_agent], check=True)

        # Run NoticeMonitorAgent.py
        monitor_path = os.path.join(CRAWLER_DIR, "NoticeMonitorAgent.py")
        # subprocess.run([sys.executable, monitor_path], check=True, capture_output=True, text=True)
        logger.info("✅ Crawling phases completed.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Crawler component failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error during crawling: {e}")
        return False

def ingest_and_build_db():
    logger.info("🏗️ Starting Data Ingestion and DB Build...")
    documents = []
    
    # 1. Load Crawled Data
    if os.path.exists(CRAWLED_TEXT_DIR):
        for file in os.listdir(CRAWLED_TEXT_DIR):
            if file.endswith(".txt"):
                logger.info(f"📄 Loading: {file}")
                try:
                    loader = TextLoader(os.path.join(CRAWLED_TEXT_DIR, file), encoding='utf-8')
                    documents.extend(loader.load())
                except Exception as e:
                    logger.error(f"Failed to read {file}: {e}")

    # 2. Load Local PDFs
    if os.path.exists(DATA_DIR):
        for file in os.listdir(DATA_DIR):
            if file.endswith(".pdf"):
                logger.info(f"📄 Loading PDF: {file}")
                try:
                    loader = PyMuPDFLoader(os.path.join(DATA_DIR, file))
                    documents.extend(loader.load())
                except Exception as e:
                    logger.error(f"Failed to read PDF {file}: {e}")

    # 3. Deduplication
    unique_docs = []
    seen = set()
    for doc in documents:
        content = doc.page_content.strip()
        if content and content[:300] not in seen: # Shortened signature for robustness
            unique_docs.append(doc)
            seen.add(content[:300])

    # 4. Splitting - Adjusted for Result List entries
    # We want larger chunks potentially or at least enough to capture titles + links
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
    chunks = text_splitter.split_documents(unique_docs)
    logger.info(f"🔥 Created {len(chunks)} knowledge fragments.")

    # 5. Build FAISS & BM25
    os.makedirs(os.path.dirname(BM25_DOCS_PATH), exist_ok=True)
    with open(BM25_DOCS_PATH, "wb") as f:
        pickle.dump(chunks, f)

    cache_folder = os.path.join(BASE_DIR, "BOT_BACKEND", "model_cache")
    os.makedirs(cache_folder, exist_ok=True)

    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        cache_folder=cache_folder
    )
    
    db = FAISS.from_documents(chunks, embeddings)
    db.save_local(FAISS_DIR)
    logger.info("✨ Local DB Rebuild Successful.")
    return True

def push_to_vm():
    # Only try to push if config is ready and env is right
    if not VM_IP or VM_IP == '98.70.37.219_FIXME':
        return True 

    logger.info(f"🔄 Syncing to VM ({VM_IP})...")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)
        
        sftp = ssh.open_sftp()
        
        # Upload BM25
        sftp.put(BM25_DOCS_PATH, f"{VM_BASE_PATH}/BOT_BACKEND/bm25_docs.pkl")
        
        # Upload FAISS
        vm_faiss_dir = f"{VM_BASE_PATH}/BOT_BACKEND/faiss_db"
        try: sftp.mkdir(vm_faiss_dir)
        except: pass
        
        for file in os.listdir(FAISS_DIR):
            sftp.put(os.path.join(FAISS_DIR, file), f"{vm_faiss_dir}/{file}")

        # Upload chatbot.html
        sftp.put(os.path.join(BASE_DIR, "admin_panel", "chatbot.html"), f"{VM_BASE_PATH}/admin_panel/chatbot.html")
        # Upload results directory for direct agent access
        sftp.put(os.path.join(DATA_DIR, "crawled_text", "results_directory.txt"), f"{VM_BASE_PATH}/BOT_BACKEND/results_directory.txt")
        # Upload engine for stability
        sftp.put(os.path.join(BACKEND_DIR, "chatbot_engine.py"), f"{VM_BASE_PATH}/BOT_BACKEND/chatbot_engine.py")
        # Upload api server
        sftp.put(os.path.join(BACKEND_DIR, "api_server.py"), f"{VM_BASE_PATH}/api_server.py")
        # Upload .env (Caution: Ensure sensitive data is managed)
        sftp.put(os.path.join(BASE_DIR, ".env"), f"{VM_BASE_PATH}/.env")
        
        logger.info("✅ VM Files Updated.")
        
        # Restart VM Server
        ssh.exec_command(f'python3 {VM_BASE_PATH}/BOT_BACKEND/api_server.py')
        logger.info("🔄 Bot Engine Restarted on VM.")
        
        sftp.close()
        ssh.close()
        return True
    except Exception as e:
        logger.error(f"❌ VM Sync Error: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 SVSU INTELLIGENT SYNC STARTED")
    # Step 1: Gather Latest Data (Results are priority)
    if run_multi_agent_crawler():
        # Step 2: Ingest and Rebuild Index
        if ingest_and_build_db():
            # Step 3: Deployment
            push_to_vm()
            logger.info(f"✨ ALL SYSTEMS UPDATED AT {datetime.now()}")
