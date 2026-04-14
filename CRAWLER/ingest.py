import os
import re
import pickle
import logging
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from langchain_community.document_loaders import PyMuPDFLoader, RecursiveUrlLoader, SitemapLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
DATA_DIR = "."
FAISS_DIR = "faiss_db"
BM25_DOCS_PATH = "bm25_docs.pkl"

def bs4_extractor(html: str) -> str:
    """Advanced Extractor: Cleans noise while keeping structured content."""
    soup = BeautifulSoup(html, "html.parser")
    # Remove intrusive tags but keep tables and semantic headers
    for s in soup(["script", "style", "nav", "footer", "iframe"]):
        s.decompose()
    
    # Extract text with meaningful spacing
    text = soup.get_text(separator='\n')
    text = re.sub(r"\n\s*\n+", "\n\n", text) # Deduplicate newlines
    return text.strip()

def ingest_data():
    logger.info("🚀 Starting Advanced SVSU Crawl...")
    documents = []
    
    # 1. PRIORITY PDF DATA (Prospectus, Notices)
    pdf_files = ["A3.pdf", "Document Prospectus-12.pdf"]
    for pdf_file in pdf_files:
        pdf_path = os.path.join(DATA_DIR, pdf_file)
        if os.path.exists(pdf_path):
            logger.info(f"📄 Processing High-Value PDF: {pdf_file}")
            try:
                loader = PyMuPDFLoader(pdf_path)
                documents.extend(loader.load())
            except Exception as e:
                logger.error(f"Error loading PDF {pdf_file}: {e}")

    # 2. HYBRID CRAWLING (Sitemap + Deep Recursion)
    sitemap_url = "https://svsu.ac.in/sitemap.xml"
    logger.info(f"🔗 Phase 1: Sitemap Exploitation ({sitemap_url})")
    s_loader = SitemapLoader(
        web_path=sitemap_url,
        filter_urls=["https://svsu.ac.in/"],
        parsing_function=bs4_extractor,
        continue_on_failure=True
    )
    try:
        s_docs = s_loader.load()
        logger.info(f"✅ Ingested {len(s_docs)} pages from Sitemap.")
        documents.extend(s_docs)
    except Exception as e:
        logger.warning(f"Sitemap crawl issues: {e}")

    logger.info("🕸️ Phase 2: Deep Recursive Crawl (Depth 10) for granular data...")
    r_loader = RecursiveUrlLoader(
        url="https://svsu.ac.in/", 
        max_depth=10, 
        extractor=bs4_extractor,
        prevent_outside=True,
        use_async=True,
        timeout=60
    )
    try:
        r_docs = r_loader.load()
        logger.info(f"✅ Deep-crawled {len(r_docs)} hidden/linked pages.")
        documents.extend(r_docs)
    except Exception as e:
        logger.error(f"Recursive crawl failed: {e}")

    # 3. Intelligent Cleaning & Metadata Tagging
    unique_docs = []
    seen_content = set()
    for doc in documents:
        # Generate a content fingerprint to avoid duplicates
        fingerprint = doc.page_content[:1000].strip()
        if fingerprint and fingerprint not in seen_content:
            doc.metadata["last_crawled"] = datetime.now().isoformat()
            unique_docs.append(doc)
            seen_content.add(fingerprint)
    
    logger.info(f"✨ Total Unique Pages Identified: {len(unique_docs)}")

    # 4. Precision Splitting
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(unique_docs)
    
    for chunk in chunks:
        if "source" in chunk.metadata:
            s = chunk.metadata["source"]
            chunk.metadata["display_source"] = s if s.startswith("http") else os.path.basename(s)
                
    logger.info(f"🔥 KNOWLEDGE FRAGMENTS: {len(chunks)} chunks created.")

    # 5. Build Engines (BM25 + FAISS)
    logger.info("🏗️ Building Hybrid Retrieval Engines...")
    with open(BM25_DOCS_PATH, "wb") as f:
        pickle.dump(chunks, f)

    cache_folder = "./model_cache"
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        cache_folder=cache_folder,
        model_kwargs={'device': 'cpu'}
    )
    
    db = FAISS.from_documents(chunks, embeddings)
    db.save_local(FAISS_DIR)
    logger.info("✨ PRODUCTION DATABASE REBUILT SUCCESSFULLY.")

if __name__ == "__main__":
    ingest_data()
