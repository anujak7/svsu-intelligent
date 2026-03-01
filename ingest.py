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

    # 2. Exhaustive Website Crawling (Mega Depth for 600+ pages)
    start_urls = [
        "https://svsu.ac.in/",
        "https://svsu.ac.in/admissions/",
        "https://svsu.ac.in/courses/",
        "https://svsu.ac.in/examinations/",
        "https://svsu.ac.in/contact-us/",
        "https://svsu.ac.in/notices/",
        "https://svsu.ac.in/tenders/",
        "https://svsu.ac.in/faculty-staff/"
    ]
    
    print(f"🚀 Starting MASSIVE CRAWL (Depth 7) for 600+ pages...")
    for url in start_urls:
        print(f"Deep Crawling: {url}...")
        loader = RecursiveUrlLoader(
            url=url, 
            max_depth=7,  # Increased depth for exhaustive search
            extractor=bs4_extractor, 
            prevent_outside=True,
            use_async=True,
            timeout=20, # Higher timeout for heavy pages
            check_response_status=True
        )
        try:
            web_docs = loader.load()
            print(f"✅ Crawled {len(web_docs)} pages from {url}.")
            documents.extend(web_docs)
        except Exception as e:
            print(f"❌ Web crawl failed for {url}: {e}")

    # 3. Clean and Deduplicate
    unique_docs = []
    seen_content = set()
    for doc in documents:
        content_hash = hash(doc.page_content)
        if content_hash not in seen_content:
            unique_docs.append(doc)
            seen_content.add(content_hash)
    
    print(f"Total Unique Pages/Docs: {len(unique_docs)}")

    # 4. Split Text (High Precision for Production)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(unique_docs)
    
    for chunk in chunks:
        if "source" in chunk.metadata:
            s = chunk.metadata["source"]
            chunk.metadata["display_source"] = s if s.startswith("http") else os.path.basename(s)
                
    print(f"Total Chunks Generated: {len(chunks)}")

    # 5. Save BM25 Docs (For Keyword Accuracy)
    print("Saving BM25 Knowledge Base...")
    with open(BM25_DOCS_PATH, "wb") as f:
        pickle.dump(chunks, f)

    # 6. Build FAISS (Semantic Accuracy)
    print("Initializing FAISS Vector DB...")
    cache_folder = "./model_cache"
    os.environ["SENTENCE_TRANSFORMERS_HOME"] = cache_folder
    
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        cache_folder=cache_folder
    )
    
    db = FAISS.from_documents(chunks, embeddings)
    db.save_local(FAISS_DIR)
    print("✨ SUCCESS: Production Database Ready with Massive Data.")

if __name__ == "__main__":
    ingest_data()
