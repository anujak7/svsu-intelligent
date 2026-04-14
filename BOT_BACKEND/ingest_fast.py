import os
import re
import pickle
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()
DATA_DIR = "./"
FAISS_DIR = "./faiss_db"
BM25_DOCS_PATH = "./bm25_docs.pkl"

def ingest_fast():
    documents = []
    
    # 1. Manual PDFs
    pdf_files = ["A3.pdf", "Document Prospectus-12.pdf"]
    for pdf_file in pdf_files:
        pdf_path = os.path.join(DATA_DIR, pdf_file)
        if os.path.exists(pdf_path):
            print(f"Loading Priority PDF: {pdf_file}...")
            loader = PyMuPDFLoader(pdf_path)
            documents.extend(loader.load())

    # 2. Priority Text Files
    text_files = ["core_facts.txt", "svsu_program_catalog.txt"]
    for txt_file in text_files:
        txt_path = os.path.join(DATA_DIR, txt_file)
        if os.path.exists(txt_path):
            print(f"Loading Priority Text: {txt_file}...")
            loader = TextLoader(txt_path, encoding="utf8")
            documents.extend(loader.load())

    # 3. Splitting
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    chunks = text_splitter.split_documents(documents)
    
    for chunk in chunks:
        if "source" in chunk.metadata:
            s = chunk.metadata["source"]
            chunk.metadata["display_source"] = os.path.basename(s)
                
    print(f"Knowledge Base: {len(chunks)} chunks generated.")

    # 4. Save BM25
    print("Building BM25 Index...")
    with open(BM25_DOCS_PATH, "wb") as f:
        pickle.dump(chunks, f)

    # 5. Build FAISS
    print("Building FAISS Vector Database...")
    cache_folder = "./model_cache"
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        cache_folder=cache_folder
    )
    
    db = FAISS.from_documents(chunks, embeddings)
    db.save_local(FAISS_DIR)
    print("✨ SUCCESS: Fast Ingestion Complete.")

if __name__ == "__main__":
    ingest_fast()
