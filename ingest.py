import os
import re
import pickle
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from langchain_community.document_loaders import PyMuPDFLoader, RecursiveUrlLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()
DATA_DIR = "./"
FAISS_DIR = "./faiss_db"
BM25_DOCS_PATH = "./bm25_docs.pkl"

def bs4_extractor(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # Only remove purely non-content tags. Footer/Header often have names/contacts.
    for s in soup(["script", "style", "nav"]):
        s.decompose()
    return re.sub(r"\n\n+", "\n\n", soup.get_text())

def ingest_data():
    documents = []
    
    # 1. Manual PDFs
    pdf_files = ["A3.pdf", "Document Prospectus-12.pdf"]
    for pdf_file in pdf_files:
        pdf_path = os.path.join(DATA_DIR, pdf_file)
        if os.path.exists(pdf_path):
            print(f"Loading Priority PDF: {pdf_file}...")
            loader = PyMuPDFLoader(pdf_path)
            documents.extend(loader.load())

    # 1.5 Load Core Facts
    core_facts_path = os.path.join(DATA_DIR, "core_facts.txt")
    if os.path.exists(core_facts_path):
        print("Loading Core Facts...")
        from langchain_community.document_loaders import TextLoader
        loader = TextLoader(core_facts_path, encoding="utf8")
        documents.extend(loader.load())

    # 2. MEGA HYBRID CRAWLING (Targeting 1000-15000 segments)
    sitemap_url = "https://svsu.ac.in/sitemap.xml"
    print(f"🚀 [Phase 1/2] SITEMAP CRAWL ({sitemap_url})...")
    
    from langchain_community.document_loaders.sitemap import SitemapLoader
    s_loader = SitemapLoader(
        web_path=sitemap_url,
        filter_urls=["https://svsu.ac.in/"],
        parsing_function=bs4_extractor,
        continue_on_failure=True
    )
    
    try:
        s_docs = s_loader.load()
        print(f"✅ Ingested {len(s_docs)} pages from Sitemap.")
        documents.extend(s_docs)
    except Exception as e:
        print(f"⚠️ Sitemap crawl partially failed: {e}")

    print(f"🚀 [Phase 2/2] DEEP EXPLOITATIVE CRAWL (Depth 8) for hidden data...")
    r_loader = RecursiveUrlLoader(
        url="https://svsu.ac.in/", 
        max_depth=8, 
        extractor=bs4_extractor,
        prevent_outside=True,
        use_async=True,
        timeout=30
    )
    try:
        r_docs = r_loader.load()
        print(f"✅ Deep-crawled {len(r_docs)} hidden/linked pages.")
        documents.extend(r_docs)
    except Exception as e:
        print(f"⚠️ Recursive crawl failed: {e}")

    # 3. Aggressive Clean and Deduplicate
    unique_docs = []
    seen_content = set()
    for doc in documents:
        content_id = doc.page_content[:1000].strip()
        if content_id and content_id not in seen_content:
            unique_docs.append(doc)
            seen_content.add(content_id)
    
    print(f"Total Unique High-Quality Pages: {len(unique_docs)}")

    # 4. Ultra-Granular Splitting (Targeting 10,000+ Chunks)
    # Reducing size a bit more to handle massive data with high precision
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    chunks = text_splitter.split_documents(unique_docs)
    
    for chunk in chunks:
        if "source" in chunk.metadata:
            s = chunk.metadata["source"]
            chunk.metadata["display_source"] = s if s.startswith("http") else os.path.basename(s)
                
    print(f"🔥 MEGA KNOWLEDGE BASE: {len(chunks)} chunks generated.")

    # 5. Save BM25 (Keyword Engine)
    print("Building Mega BM25 Index...")
    with open(BM25_DOCS_PATH, "wb") as f:
        pickle.dump(chunks, f)

    # 6. Build Mega FAISS (Semantic Engine)
    print("Building Mega FAISS Vector Database...")
    cache_folder = "./model_cache"
    os.environ["SENTENCE_TRANSFORMERS_HOME"] = cache_folder
    
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        cache_folder=cache_folder
    )
    
    db = FAISS.from_documents(chunks, embeddings)
    db.save_local(FAISS_DIR)
    print("✨ SUCCESS: Production Database Ready with 10k+ Chunks.")

if __name__ == "__main__":
    ingest_data()
