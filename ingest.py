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
    # 1. Load PDFs
    pdf_files = ["A3.pdf", "Document Prospectus-12.pdf"]
    for pdf_file in pdf_files:
        pdf_path = os.path.join(DATA_DIR, pdf_file)
        if os.path.exists(pdf_path):
            print(f"Loading PDF: {pdf_file}...")
            loader = PyMuPDFLoader(pdf_path)
            documents.extend(loader.load())

    # 1.5 Load Core Facts
    core_facts_path = os.path.join(DATA_DIR, "core_facts.txt")
    if os.path.exists(core_facts_path):
        print("Loading Core Facts...")
        from langchain_community.document_loaders import TextLoader
        loader = TextLoader(core_facts_path, encoding="utf8")
        documents.extend(loader.load())

    # 2. Website Crawling (Exhaustive Entrance Points)
    start_urls = [
        "https://svsu.ac.in/",
        "https://svsu.ac.in/admissions/",
        "https://svsu.ac.in/courses/",
        "https://svsu.ac.in/examinations/",
        "https://svsu.ac.in/contact-us/"
    ]
    
    print(f"Crawling SVSU website from {len(start_urls)} entry points (Depth 4)...")
    for url in start_urls:
        print(f"Crawling: {url}...")
        loader = RecursiveUrlLoader(
            url=url, 
            max_depth=4, 
            extractor=bs4_extractor, 
            prevent_outside=True,
            use_async=True
        )
        try:
            web_docs = loader.load()
            print(f"Crawled {len(web_docs)} pages from {url}.")
            documents.extend(web_docs)
        except Exception as e:
            print(f"Web crawl failed for {url}: {e}")

    # 3. Split Text (Optimized for Accuracy & Granularity)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = text_splitter.split_documents(documents)
    
    # Clean up source names in metadata for cleaner display
    for chunk in chunks:
        if "source" in chunk.metadata:
            # Map long paths to cleaner names
            s = chunk.metadata["source"]
            if "Document Prospectus-12.pdf" in s:
                chunk.metadata["display_source"] = "University Prospectus"
            elif "A3.pdf" in s:
                chunk.metadata["display_source"] = "University Brochure"
            elif s.startswith("http"):
                chunk.metadata["display_source"] = s
            else:
                chunk.metadata["display_source"] = os.path.basename(s)
                
    print(f"Total chunks: {len(chunks)}")

    # 4. Save BM25 Docs for Instant Loading
    print("Saving BM25 documents...")
    with open(BM25_DOCS_PATH, "wb") as f:
        pickle.dump(chunks, f)

    # 5. Local Embeddings & FAISS (Optimized for speed)
    print("Initializing local embeddings...")
    cache_folder = "./model_cache"
    if not os.path.exists(cache_folder):
        os.makedirs(cache_folder)
    os.environ["SENTENCE_TRANSFORMERS_HOME"] = cache_folder
    
    from langchain_huggingface import HuggingFaceEmbeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        cache_folder=cache_folder
    )
    
    print("Building FAISS Database...")
    db = FAISS.from_documents(chunks, embeddings)
    db.save_local(FAISS_DIR)
    print("Success: Knowledge base updated.")

if __name__ == "__main__":
    ingest_data()
