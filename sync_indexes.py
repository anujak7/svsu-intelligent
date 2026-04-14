import os
import sqlite3
import hashlib
import pickle
import sys
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

# Add paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "BOT_BACKEND")
sys.path.append(BACKEND_DIR)

from chatbot_engine import get_embeddings, KNOWLEDGE_DIR, FAISS_DIR, BM25_DOCS_PATH

DB_PATH = os.path.join(KNOWLEDGE_DIR, "Database", "svsu_knowledge.db")

def rebuild_vector_indexes():
    print(f"Reading chunks from {DB_PATH}...")
    if not os.path.exists(DB_PATH):
        print("Error: Database not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT content, source_label, source_group, priority FROM knowledge_chunks")
    rows = cursor.fetchall()
    conn.close()

    print(f"Found {len(rows)} chunks. Creating Documents...")
    documents = []
    for row in rows:
        metadata = {
            "source": row["source_label"],
            "group": row["source_group"],
            "priority": row["priority"]
        }
        documents.append(Document(page_content=row["content"], metadata=metadata))

    print("Building FAISS Vector Store (this may take a minute)...")
    embeddings = get_embeddings()
    vector_store = FAISS.from_documents(documents, embeddings)
    
    # Save FAISS
    os.makedirs(os.path.dirname(FAISS_DIR), exist_ok=True)
    vector_store.save_local(FAISS_DIR)
    print(f"FAISS index saved to {FAISS_DIR}")

    # Save BM25 Docs for EnsembleRetriever
    print(f"Saving BM25 documents to {BM25_DOCS_PATH}...")
    with open(BM25_DOCS_PATH, "wb") as f:
        pickle.dump(documents, f)
    
    print("All indexes (SQL, FAISS, BM25) are now synchronized and refined.")

if __name__ == "__main__":
    rebuild_vector_indexes()
