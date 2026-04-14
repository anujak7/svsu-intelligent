import os
import re
import pickle
import time
from dotenv import load_dotenv
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

# Universal Paths (Relative to BOT_BACKEND)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "CRAWLER_MULTIAgent", "ALL_SVSU_DATA")
TXT_DIR = os.path.join(DATA_DIR, "crawled_text")
BACKEND_DATA = os.path.join(BASE_DIR, "data")
FAISS_DIR = os.path.join(BASE_DIR, "faiss_db")
BM25_DOCS_PATH = os.path.join(BASE_DIR, "bm25_docs.pkl")

def ingest_all_svsu_knowledge():
    print("🚀 STARTING DEEP INGESTION (SVSU INTEL v4.0)")
    documents = []

    # 1. SCAN PDFS IN CRAWLER_MULTIAgent/ALL_SVSU_DATA
    if os.path.exists(DATA_DIR):
        print(f"Scanning Deep PDFs in: {DATA_DIR}")
        for file in os.listdir(DATA_DIR):
            if file.lower().endswith(".pdf"):
                pdf_path = os.path.join(DATA_DIR, file)
                print(f"  [PDF] Loading {file}...")
                try:
                    loader = PyMuPDFLoader(pdf_path)
                    documents.extend(loader.load())
                except Exception as e:
                    print(f"  [ERROR] Could not load {file}: {e}")

    # 2. SCAN TEXT FILES IN crawled_text
    if os.path.exists(TXT_DIR):
        print(f"Scanning Crawled Text in: {TXT_DIR}")
        for file in os.listdir(TXT_DIR):
            f_path = os.path.join(TXT_DIR, file)
            if file.lower().endswith(".txt") and os.path.getsize(f_path) > 10:
                print(f"  [TXT] Loading {file}...")
                try:
                    loader = TextLoader(f_path, encoding="utf-8")
                    documents.extend(loader.load())
                except Exception as e:
                    print(f"  [ERROR] Could not load {file}: {e}")

    # 3. SCAN LOCAL data FOLDER (Programs list, leads, etc.)
    if os.path.exists(BACKEND_DATA):
        print(f"Scanning Backend Data: {BACKEND_DATA}")
        for file in os.listdir(BACKEND_DATA):
            if file.lower().endswith(".txt"):
                txt_path = os.path.join(BACKEND_DATA, file)
                print(f"  [DATA] Loading {file}...")
                try:
                    loader = TextLoader(txt_path, encoding="utf-8")
                    documents.extend(loader.load())
                except: pass

    # 4. CORE FACTS (Root)
    core_facts_root = os.path.join(ROOT_DIR, "core_facts.txt")
    if os.path.exists(core_facts_root):
        print(f"  [CORE] Loading core_facts.txt...")
        loader = TextLoader(core_facts_root, encoding="utf-8")
        documents.extend(loader.load())

    print(f"\n--- Total Raw Documents Loaded: {len(documents)}")

    if len(documents) == 0:
        print("❌ CRITICAL: No documents found to ingest!")
        return

    # 5. DEEP CHUNKING (Optimized for Context Retrieval)
    # Larger chunks (1000) for better deep reasoning context
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=300)
    chunks = text_splitter.split_documents(documents)
    
    for chunk in chunks:
        if "source" in chunk.metadata:
            chunk.metadata["display_source"] = os.path.basename(chunk.metadata["source"])
            
    print(f"Generated {len(chunks)} high-precision chunks.")

    # 6. EXPORT BM25 (FAST PATH)
    print("Building BM25 Index...")
    with open(BM25_DOCS_PATH, "wb") as f:
        pickle.dump(chunks, f)

    # 7. BUILD FAISS VECTOR DB
    print("Building FAISS Database (This may take a minute)...")
    cache_folder = os.path.join(ROOT_DIR, "model_cache")
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        cache_folder=cache_folder
    )
    
    start_time = time.time()
    db = FAISS.from_documents(chunks, embeddings)
    db.save_local(FAISS_DIR)
    
    end_time = time.time()
    print(f"✨ SUCCESS: Deep Ingestion Complete in {int(end_time - start_time)}s.")
    print(f"FAISS saved to: {FAISS_DIR}")
    print(f"BM25 saved to: {BM25_DOCS_PATH}")

if __name__ == "__main__":
    ingest_all_svsu_knowledge()
