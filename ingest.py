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
    
    # 1. Manual PDFs (Start with high-priority files)
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

    # 2. Exhaustive Sitemap Crawling (GUARANTEED 500+ Pages)
    sitemap_url = "https://svsu.ac.in/sitemap.xml"
    print(f"🚀 Starting MASSIVE SITEMAP CRAWL for 500+ pages ({sitemap_url})...")
    
    from langchain_community.document_loaders.sitemap import SitemapLoader
    loader = SitemapLoader(
        web_path=sitemap_url,
        filter_urls=["https://svsu.ac.in/"],
        parsing_function=bs4_extractor,
        continue_on_failure=True
    )
    
    try:
        sitemap_docs = loader.load()
        print(f"✅ Successfully ingested {len(sitemap_docs)} pages from Sitemap.")
        documents.extend(sitemap_docs)
    except Exception as e:
        print(f"❌ Sitemap ingest failed: {e}. Falling back to Recursive Loader.")
        # Fallback to recursive if sitemap fails
        loader = RecursiveUrlLoader(url="https://svsu.ac.in/", max_depth=5, extractor=bs4_extractor)
        documents.extend(loader.load())

    # 3. Clean and Deduplicate
    unique_docs = []
    seen_content = set()
    for doc in documents:
        # Use a more robust check: first 500 chars
        content_prefix = doc.page_content[:500].strip()
        if content_prefix and content_prefix not in seen_content:
            unique_docs.append(doc)
            seen_content.add(content_prefix)
    
    print(f"Total Unique Pages/Docs after Deduplication: {len(unique_docs)}")

    # 4. Split Text (High Precision for Production)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(unique_docs)
    
    for chunk in chunks:
        if "source" in chunk.metadata:
            s = chunk.metadata["source"]
            chunk.metadata["display_source"] = s if s.startswith("http") else os.path.basename(s)
                
    print(f"Total Chunks Generated: {len(chunks)}")

    # 5. Save BM25 Knowledge Base (Keyword Search)
    print("Building BM25 Index...")
    with open(BM25_DOCS_PATH, "wb") as f:
        pickle.dump(chunks, f)

    # 6. Build FAISS Vector DB (Semantic Search)
    print("Building FAISS Vector Database...")
    cache_folder = "./model_cache"
    os.environ["SENTENCE_TRANSFORMERS_HOME"] = cache_folder
    
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        cache_folder=cache_folder
    )
    
    db = FAISS.from_documents(chunks, embeddings)
    db.save_local(FAISS_DIR)
    print("✨ SUCCESS: Production Database Ready with Exhaustive Data.")

if __name__ == "__main__":
    ingest_data()
