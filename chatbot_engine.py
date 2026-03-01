import os
# Prevent OpenMP deadlocks on Windows (common with FAISS + HuggingFace)
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

import re
import pickle
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from langchain_community.document_loaders import PyMuPDFLoader, RecursiveUrlLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# Robust EnsembleRetriever Import
try:
    from langchain.retrievers import EnsembleRetriever
except ImportError:
    try:
        from langchain_classic.retrievers.ensemble import EnsembleRetriever
    except ImportError:
        EnsembleRetriever = None

from langchain_community.retrievers import BM25Retriever

load_dotenv()
FAISS_DIR = "./faiss_db"
BM25_DOCS_PATH = "./bm25_docs.pkl"

# Global instances for speed
_embeddings = None
_bm25_retriever = None

def get_embeddings():
    global _embeddings
    if _embeddings is None:
        # HIGH-PERFORMANCE LOCAL EMBEDDINGS (ULTRA STABLE)
        # Ensure the model "all-MiniLM-L6-v2" is downloaded to HF_CACHE_DIR
        # You can pre-download it using:
        # from transformers import AutoTokenizer, AutoModel
        # AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2", cache_dir=HF_CACHE_DIR)
        # AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2", cache_dir=HF_CACHE_DIR)
        
        # Create cache directory if it doesn't exist
        cache_folder = "./model_cache"
        os.makedirs(cache_folder, exist_ok=True)

        _embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            cache_folder=cache_folder,
            model_kwargs={'local_files_only': True}
        )
    return _embeddings

def get_chatbot_chain():
    global _bm25_retriever
    embeddings = get_embeddings()
    
    if not os.path.exists(FAISS_DIR):
        return None

    db = FAISS.load_local(FAISS_DIR, embeddings, allow_dangerous_deserialization=True)
    # Reduced k to stay within Groq Free Tier limits (TPM: 6000), but k=3 is safe and provides better context.
    faiss_retriever = db.as_retriever(search_kwargs={"k": 3})

    # Instant BM25 loading from persistent storage
    if _bm25_retriever is None and EnsembleRetriever is not None:
        try:
            if os.path.exists(BM25_DOCS_PATH):
                with open(BM25_DOCS_PATH, "rb") as f:
                    docs = pickle.load(f)
                _bm25_retriever = BM25Retriever.from_documents(docs)
                _bm25_retriever.k = 3
        except Exception:
            pass

    if _bm25_retriever:
        # Balanced search for detailed fact-finding
        retriever = EnsembleRetriever(retrievers=[_bm25_retriever, faiss_retriever], weights=[0.4, 0.6])
    else:
        retriever = faiss_retriever

    # PRIMARY: Groq (Ultra Fast) | SECONDARY: Gemini
    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GOOGLE_API_KEY")

    if groq_key:
        llm = ChatGroq(model="llama-3.1-8b-instant", api_key=groq_key, temperature=0.1)
    elif gemini_key:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=gemini_key, temperature=0.1)
    else:
        return None
    
    # STATIC KNOWLEDGE LAYER (FAIL-PROOF)
    static_knowledge = ""
    core_facts_path = "./core_facts.txt"
    if os.path.exists(core_facts_path):
        try:
            with open(core_facts_path, "r", encoding="utf8") as f:
                static_knowledge = f.read()
        except: pass

    template = """You are SVSU Intelligent, the official high-performance AI guide for Shri Vishwakarma Skill University.
Your primary mission is to transform raw data into a BEAUTIFULLY ORGANIZED, HIGHLY READABLE, and PROFESSIONAL response.

ORGANIZATION RULES (STRICT):
1. **ZERO INTRODUCTIONS**: DO NOT start with "Based on the info," "As per the context," or "I can provide..." Simply give the answer immediately.
2. **VISUAL HIERARCHY**: Always use `###` Headers for distinct sections (e.g., ### University Leadership, ### Academic Programs).
3. **DATA ORGANIZATION**: 
   - **MANDATORY TABLES**: For any quantitative or list-style data (Courses, VC Details, Dates, Fees), you MUST use Markdown Tables.
   - **USE BULLETS**: For multi-point features or qualitative facts.
   - **NO LONG PARAGRAPHS**: Break every answer into small, digestible sections. Never write more than 3 sentences in a single block.
4. **RULE OF TRUTH**: Use the UNIVERSITY SNAPSHOT for core facts (VC/Leadership/Location).
5. **CLEANLINESS**: Never mention file names, internal technical terms, or source tags.
6. **STAY AUTHORITATIVE**: Answer like an official university brochure—clear, direct, and elite.

UNIVERSITY SNAPSHOT (CRITICAL FACTS):
{static_knowledge}

Context from University Database:
{context}

Question: {question}"""



    prompt = ChatPromptTemplate.from_template(template)

    def extract_sources(docs):
        # User requested to hide sources or make them less intrusive
        return "" # Hide for now as requested by user

    def format_docs(docs):
        if not docs: return "No additional records."
        return "\n\n---\n\n".join([d.page_content for d in docs])

    def final_response(input_data):
        query = input_data["question"].lower().strip()
        
        # 1. SMART GREETING DETECTOR
        greetings = ["hi", "hello", "hey", "hola", "namaste", "good morning", "good afternoon", "good evening"]
        is_greeting = any(query == g or query.startswith(g + " ") for g in greetings)
        
        if is_greeting and len(query.split()) < 4:
            return "Hello! I am SVSU Intelligent. How can I assist you with Shri Vishwakarma Skill University today?"


        # 2. RAG RETRIEVAL
        try:
            docs = retriever.invoke(input_data["question"])
        except Exception as e:
            raise e
            
        context_str = format_docs(docs)
        source_str = extract_sources(docs)
        
        full_prompt = prompt.format(
            static_knowledge=static_knowledge,
            context=context_str,
            question=input_data["question"]
        )
        
        try:
            response = llm.invoke(full_prompt)
        except Exception as e:
            raise e
            
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Clean response from any accidental source mentions
        content = re.sub(r"Source:.*?\n", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\[DOC.*?\]", "", content)
        
        return content.strip()

    return final_response

