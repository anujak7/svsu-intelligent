import os
import re
import pickle
import logging
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from langchain_community.document_loaders import PyMuPDFLoader, RecursiveUrlLoader, SitemapLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# Configure Specialized Logging for Admission Crawler
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [ADMISSION-EXPERT] - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
# Data stored in the common ALL_SVSU_DATA folder
PDF_DIR = "ALL_SVSU_DATA"
FAISS_DIR = "faiss_db" 
BM25_DOCS_PATH = "bm25_docs.pkl"

def admission_extractor(html: str) -> str:
    """Specialized Extractor: Focuses on educational data like fees, seats, and tables."""
    soup = BeautifulSoup(html, "html.parser")
    # Remove UI noise
    for s in soup(["script", "style", "nav", "footer", "header", "aside"]):
        s.decompose()
    
    # Priority: Extract tables with structure
    for table in soup.find_all('table'):
        table.insert_before("\n [STRUCTURED DATA TABLE START] \n")
        table.insert_after("\n [STRUCTURED DATA TABLE END] \n")

    text = soup.get_text(separator=' | ')
    text = re.sub(r"\s+", " ", text) # Clean extra spaces
    return text.strip()

def ingest_admission_expert_data():
    logger.info("🎯 INITIALIZING SUPER-ADVANCED ADMISSION CRAWLER...")
    documents = []
    
    # 1. LOAD ALL PDFS FROM ALL_SVSU_DATA (This is where user uploads PDFs)
    if os.path.exists(PDF_DIR):
        for file in os.listdir(PDF_DIR):
            if file.endswith(".pdf"):
                logger.info(f"📂 Heavy Analysis of Prospectus: {file}")
                try:
                    loader = PyMuPDFLoader(os.path.join(PDF_DIR, file))
                    docs = loader.load()
                    for d in docs:
                        d.metadata["source"] = f"Official Prospectus 2025-26 - Page {d.metadata.get('page', '?')}"
                    documents.extend(docs)
                except Exception as e:
                    logger.error(f"Failed to read {file}: {e}")

    # 1.1 LOAD STRUCTURED TXT KNOWLEDGE (Precision Data)
    txt_files = ["svsu_program_catalog.txt", "prospectus_deep_knowledge.txt", "prospectus_general_deep.txt", "core_facts.txt"]
    for txt in txt_files:
        if os.path.exists(txt):
            logger.info(f"💎 Ingesting Precision Knowledge: {txt}")
            try:
                loader = TextLoader(txt, encoding='utf-8')
                docs = loader.load()
                for d in docs:
                    d.metadata["source"] = f"SVSU Knowledge Base - {txt}"
                documents.extend(docs)
            except Exception as e:
                logger.error(f"Failed to read {txt}: {e}")

    # 1.2 LOAD MULTI-AGENT CRAWLED DATA
    CRAWLED_DIR = "ALL_SVSU_DATA/crawled_text"
    if os.path.exists(CRAWLED_DIR):
        for file in os.listdir(CRAWLED_DIR):
            if file.endswith(".txt"):
                if "results_directory.txt" in file:
                    continue # Skip massive results file (handled via specialized lookup)
                logger.info(f"🤖 Ingesting Multi-Agent Knowledge: {file}")
                try:
                    loader = TextLoader(os.path.join(CRAWLED_DIR, file), encoding='utf-8')
                    docs = loader.load()
                    for d in docs:
                        d.metadata["source"] = f"SVSU Live Website - {file}"
                    documents.extend(docs)
                except Exception as e:
                    logger.error(f"Failed to read {file}: {e}")

    # 2. INTENTIONAL REDUNDANCY REMOVED: 
    # The new Multi-Agent Crawler system (Dispatcher) now handles deep crawling 
    # for all 12+1 sections. RecursiveUrlLoader here is no longer needed.
    # logger.info("🌐 Core website crawl handled by Multi-Agent System.")

    # 3. Intelligent Deduplication
    unique_docs = []
    seen = set()
    for doc in documents:
        content = doc.page_content.strip()
        if content and content[:500] not in seen:
            unique_docs.append(doc)
            seen.add(content[:500])

    # 4. Precision Splitting (Optimized for Admission Tables and Rules)
    # We use larger chunks for prospectus data to keep tables together
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1800, 
        chunk_overlap=400,
        add_start_index=True
    )
    chunks = text_splitter.split_documents(unique_docs)
    
    # Enrich chunks with source context directly in content for better retrieval
    for chunk in chunks:
        source_info = chunk.metadata.get("source", "SVSU Records")
        chunk.page_content = f"[SOURCE: {source_info}]\n{chunk.page_content}"
    
    logger.info(f"🔥 TOTAL KNOWLEDGE FRAGMENTS: {len(chunks)}")

    # 5. Build Knowledge Base
    logger.info("🏗️ Upgrading Vector Database with Admission Specialist Data...")
    
    # Save BM25 (Keyword backup)
    with open(BM25_DOCS_PATH, "wb") as f:
        pickle.dump(chunks, f)

    cache_folder = "./model_cache"
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        cache_folder=cache_folder
    )
    
    db = FAISS.from_documents(chunks, embeddings)
    db.save_local(FAISS_DIR)
    logger.info("✨ SUCCESS: Specialized Admission Knowledge Base is LIVE on VM.")

if __name__ == "__main__":
    ingest_admission_expert_data()
