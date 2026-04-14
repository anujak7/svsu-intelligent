import os
from datetime import datetime
# Prevent OpenMP deadlocks on Windows (common with FAISS + HuggingFace)
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

import re
import pickle
from dotenv import load_dotenv
import re
import pickle
from dotenv import load_dotenv
# Heavy imports moved inside functions for instant startup

# Robust EnsembleRetriever Import
# EnsembleRetriever moved to local import
EnsembleRetriever = "PENDING" 

# Identification of standard project structure logic
CURRENT_FILE_PATH = os.path.abspath(__file__)
BASE_DIR = os.path.dirname(CURRENT_FILE_PATH)
if "BOT_BACKEND" in BASE_DIR:
    ROOT_DIR = os.path.dirname(BASE_DIR)
else:
    ROOT_DIR = BASE_DIR

KNOWLEDGE_DIR = os.path.join(ROOT_DIR, "SVSU_KNOWLEDGE")

# Robust .env loading (VM compatibility)
env_path = os.path.join(ROOT_DIR, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

FAISS_DIR = os.path.join(KNOWLEDGE_DIR, "Indexes", "faiss_db")
BM25_DOCS_PATH = os.path.join(KNOWLEDGE_DIR, "Indexes", "bm25_docs.pkl")
MASTER_FACT_SHEET_PATH = os.path.join(KNOWLEDGE_DIR, "Structured_Data", "master_fact_sheet.json")
core_facts_path = os.path.join(KNOWLEDGE_DIR, "Text_Knowledge", "core_facts.txt")

# Set offline flags
if "TRANSFORMERS_OFFLINE" in os.environ:
    del os.environ["TRANSFORMERS_OFFLINE"]
if "HF_HUB_OFFLINE" in os.environ:
    del os.environ["HF_HUB_OFFLINE"]

# Global instances
_embeddings = None
_bm25_retriever = None

def get_embeddings():
    from langchain_huggingface import HuggingFaceEmbeddings
    global _embeddings
    if _embeddings is None:
        model_name = "all-MiniLM-L6-v2"
        # Search for snapshots (VM structure)
        m_cache = os.path.join(ROOT_DIR, "model_cache")
        # Standard VM path: /home/svsuuser/svsu-intelligent/model_cache/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/c9745ed1...
        found_path = None
        if os.path.exists(m_cache):
            for r, d, f in os.walk(m_cache):
                if "config.json" in f:
                    found_path = r
                    break
        
        if found_path:
            print(f"DEBUG: Found local model snapshot at {found_path}")
            model_name = found_path # Point directly to snapshot folder
        else:
             print("WARNING: Local model snapshot not found via scan.")

        _embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={'local_files_only': True}
        )
    return _embeddings

def get_chatbot_chain():
    from langchain_community.vectorstores import FAISS
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_groq import ChatGroq
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    # Robust EnsembleRetriever Import (LOCAL)
    global EnsembleRetriever
    if EnsembleRetriever == "PENDING":
        try:
            from langchain.retrievers import EnsembleRetriever as ER
            EnsembleRetriever = ER
        except ImportError:
            try:
                from langchain_classic.retrievers.ensemble import EnsembleRetriever as ER
                EnsembleRetriever = ER
            except ImportError:
                EnsembleRetriever = None

    global _bm25_retriever
    embeddings = get_embeddings()
    
    if not os.path.exists(FAISS_DIR):
        print(f"CRITICAL ERROR: FAISS_DIR not found at {FAISS_DIR}")
        return None

    db = FAISS.load_local(FAISS_DIR, embeddings, allow_dangerous_deserialization=True)
    faiss_retriever = db.as_retriever(search_kwargs={"k": 15})

    if _bm25_retriever is None and EnsembleRetriever is not None:
        try:
            if os.path.exists(BM25_DOCS_PATH):
                from langchain_community.retrievers import BM25Retriever
                with open(BM25_DOCS_PATH, "rb") as f:
                    docs = pickle.load(f)
                _bm25_retriever = BM25Retriever.from_documents(docs)
                _bm25_retriever.k = 15
        except Exception as e:
            print(f"BM25 Loading Failed: {e}")

    if _bm25_retriever:
        retriever = EnsembleRetriever(retrievers=[_bm25_retriever, faiss_retriever], weights=[0.4, 0.6])
    else:
        retriever = faiss_retriever

    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GOOGLE_API_KEY")

    if groq_key:
        print(f"ENGINE INIT: Groq Key Detected ({groq_key[:6]}...{groq_key[-4:]})")
    if gemini_key:
        print(f"ENGINE INIT: Gemini Key Detected ({gemini_key[:6]}...{gemini_key[-4:]})")

    groq_llm = None
    if groq_key:
        try:
            groq_llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=groq_key, temperature=0.0)
            print("ENGINE: Groq (Llama 3.3) ready.")
        except Exception as e:
            print(f"Groq setup failed: {e}")
    
    gemini_llm = None
    if gemini_key:
        try:
            # Using gemini-1.5-flash as it's the most common stable model
            gemini_llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=gemini_key, temperature=0.1)
            print("ENGINE: Gemini ready.")
        except Exception as e:
            print(f"Gemini setup failed: {e}")

    if not groq_llm and not gemini_llm:
        return None
    
    # SYSTEM PROMPTS (FAIL-PROOF)
    static_knowledge = ""
    if os.path.exists(core_facts_path):
        try:
            with open(core_facts_path, "r", encoding="utf8") as f:
                static_knowledge = f.read()
        except: pass
        
    # INJECT MASTER FACT SHEET (FOR 100% ACCURACY)
    master_facts = ""
    if os.path.exists(MASTER_FACT_SHEET_PATH):
        try:
            with open(MASTER_FACT_SHEET_PATH, "r", encoding="utf-8") as f:
                m_data = json.load(f)
                master_facts = f"CORE UNIVERSITY MASTER FACTS (STRICT FIDELITY):\n{json.dumps(m_data, indent=2)}\n"
        except: pass

    # INJECT PROGRAM CATALOG FOR 100% ACCURACY
    catalog_path = os.path.join(KNOWLEDGE_DIR, "Structured_Data", "svsu_program_catalog.txt")
    if os.path.exists(catalog_path):
        try:
            with open(catalog_path, "r", encoding="utf8") as f:
                static_knowledge += "\n\nOFFICIAL PROGRAM CATALOG:\n" + f.read()
        except: pass

    def get_custom_facts():
        path = os.path.join(KNOWLEDGE_DIR, "Text_Knowledge", "custom_facts.txt")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            except:
                return ""
        return ""

    template = """You are the Senior Counselor at Shri Vishwakarma Skill University.
Your objective: Provide highly professional, accurate, and minimalist guidance.

MINIMALIST PROFESSIONALISM PROTOCOLS:
1. DATA ACCURACY: Use 'MASTER FACTS' and 'CATALOG' for 100% precision.
2. CLEAN FORMATTING:
   - Use Markdown Tables for clarity, but keep them COMPACT and CLEAN.
   - Use bold ONLY for key terms (e.g., **MBA**, **Eligibility**).
   - Use sufficient white space (new lines) between sections to avoid a cluttered look.
   - Never use more than 2-3 emojis per response; keep it sober and academic.
3. CONCISE RESPONSES: Don't write long paragraphs. Use clear, short bullet points.
4. SCOPE: Stick strictly to SVSU academic and admission queries.
5. LEAD NUDGE: At the end of helpful info, add a single, clean line: "Would you like to proceed with your application for this program? I can guide you through the next steps."

{master_facts}

OFFICIAL UNIVERSITY DATA (CATALOG & CORE FACTS):
{static_knowledge}

RETRIEVED PROSPECTUS CONTEXT:
{context}

CONVERSATION HISTORY:
{chat_history}

USER QUESTION: {question}

SVSU PROFESSIONAL RESPONSE (Clean, Minimalist, Accurate):"""

    prompt = ChatPromptTemplate.from_template(template)

    def extract_sources(docs):
        # User requested to hide sources or make them less intrusive
        return "" # Hide for now as requested by user

    def format_docs(docs):
        if not docs: return "No additional records."
        return "\n\n---\n\n".join([d.page_content for d in docs])

    def final_response(input_data):
        query = input_data["question"].lower().strip()
        mode = input_data.get("mode", "intelligent").lower()
        
        # SMART GREETING DETECTOR
        greetings = ["hi", "hello", "hey", "hola", "namaste", "good morning", "good afternoon", "good evening"]
        is_greeting = any(query == g or query.startswith(g + " ") for g in greetings)
        
        if is_greeting and len(query.split()) < 3:
            return "Namaste! How can I assist you with SVSU admissions or university information today?"

        # 2. 12 MASTER AGENTS - DOMAIN ROUTING
        # Instead of just 3 modes, we use 12 Specialized Personas to handle queries with high precision.
        domain_prompts = {
            "ADMISSION": "Persona: SVSU Admission Analyst. Experts in Eligibility, Application Process, and Admission dates. Use Program Catalog for absolute facts.",
            "EXAM": "Persona: SVSU Examination Registrar. Expert in Results, Marks, Degree Verification, and Result PDFs. Prioritize URL links.",
            "FEE": "Persona: SVSU Financial Officer. Expert in Semester fees, Scholarships, and Payment portals. Be precise with currency figures.",
            "BVOC": "Persona: B.Voc Strategy Expert. Explain the Dual Model (Industry + Academic). Use B.Voc documents for Earn-while-you-learn details.",
            "ENGINEERING": "Persona: B.Tech Engineering Dean. Deep knowledge of CSE, Robotics, Mechanical, and Engineering infrastructure.",
            "MASTERS": "Persona: M.Voc/PG Coordinator. Focused on Post-graduate programs, research, and advanced skills.",
            "PLACEMENTS": "Persona: Career & Placement Coach. Details on Industry Partners, Internship stipends, and past placement records.",
            "INFRASTRUCTURE": "Persona: Campus Facilities Manager. Details on Hostels, Transportation, Labs, and Library resources.",
            "ADMIN": "Persona: University Secretariat. Authentic info on VC, Registrar, History, and Organizational hierarchy.",
            "HELPLINE": "Persona: Student Support Specialist. Accurate contact numbers, emails, and address for helpdesk assistance.",
            "SKILL_COURSES": "Persona: Short-term Skills Instructor. Information on 3-6 month certification and diploma courses.",
            "CAMPUS_LIFE": "Persona: Student Affairs Lead. Info on Clubs, Events, Extracurriculars, and Life at SVSU.",
            "PROSPECTUS": "Persona: SVSU Prospectus Auditor. Expert in general rules, university history, vision, and infrastructure from the 174-page official document."
        }

        # Dynamic Domain Detection (Professional Router)
        detected_domain = "general"
        if any(kw in query for kw in ["m.voc", "mvoc", "master", "postgrad", "pg"]):
            detected_domain = "postgraduate"
        elif any(kw in query for kw in ["undergraduate", "ug", "b.voc", "btech", "b.tech", "bachelor"]):
            detected_domain = "undergraduate"
        elif any(kw in query for kw in ["result", "mark", "rank", "verify", "scorecard"]):
            detected_domain = "exam"
        elif any(kw in query for kw in ["fee", "money", "cost", "scholarship", "payment"]):
            detected_domain = "fee"
        elif any(kw in query for kw in ["admission", "apply", "form", "eligibility", "date", "seat", "intake"]):
            detected_domain = "admission"
        elif any(kw in query for kw in ["placement", "job", "salary", "package", "company"]):
            detected_domain = "placements"
        
        # Mapping for display badge titles
        display_map = {
            "admission": "Admission Expert",
            "exam": "Result Specialist",
            "fee": "Finance Agent",
            "undergraduate": "UG Admission Counselor",
            "postgraduate": "PG Admission Counselor",
            "placements": "Career Officer",
            "general": "SVSU Counselor"
        }
        
        mode_instruction = f"""
        (Instructional Context: You are currently acting as a {display_map.get(detected_domain, "SVSU Counselor")}. 
        Focus on program details if {detected_domain} is related to academics. 
        ENSURE ABSOLUTE FACTUAL ACCURACY FROM THE PROSPECTUS AND CATALOG.)
        """

        # 3. SPECIALIZED RESULT LOOKUP (ONLY for Result queries)
        result_context = ""
        is_result_query = any(kw in query for kw in ["result", "marks", "cutoff", "scorecard", "merit list"])
        if is_result_query:
            results_file = os.path.join(KNOWLEDGE_DIR, "Text_Knowledge", "results_directory.txt")
            
            if os.path.exists(results_file):
                matches = []
                # Advanced keyword matching
                clean_query = query.lower().replace(".", " ").replace("-", " ")
                query_words = set(re.findall(r'\w+', clean_query))
                
                # Filter out common stop words
                stop_words = {"the", "of", "and", "in", "to", "for", "with", "result", "results", "marks", "what", "is", "my"}
                keywords = [w for w in query_words if w not in stop_words and len(w) > 2]
                
                try:
                    with open(results_file, "r", encoding="utf8") as f:
                        content = f.read().split("\n\n")
                        for block in content:
                            block_low = block.lower().replace(".", " ").replace("-", " ")
                            # Match if any significant keyword is in the block
                            match_count = sum(1 for kw in keywords if kw in block_low)
                            
                            if match_count > 0:
                                # Prioritize sem/year matches
                                score = match_count
                                for sem in ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth"]:
                                    if sem in clean_query and sem in block_low:
                                        score += 10 # Strong boost for semester match
                                
                                # Boost match for specific program acronyms
                                for prog in ["mlt", "cse", "bhm", "mech", "robotics"]:
                                    if prog in clean_query and prog in block_low:
                                        score += 5
                                        
                                matches.append((score, block))
                    
                    if matches:
                        # Sort by match quality
                        matches.sort(key=lambda x: x[0], reverse=True)
                        result_context = "\n\nLATEST MATCHING RESULTS FOUND:\n" + "\n\n".join([m[1] for m in matches[:5]])
                except Exception as e:
                    print(f"Result Search Error: {e}")
        # 4. RAG RETRIEVAL (Optimized for Accuracy)
        try:
            full_docs = retriever.invoke(input_data["question"])
            # Take top 12 for maximum precision from the 174-page prospectus
            docs = full_docs[:12]
        except Exception as e:
            raise e
            
        context_str = format_docs(docs) + "\n" + result_context
        
        # 5. EXECUTION WITH MEMORY
        chat_history = input_data.get("chat_history", [])
        history_str = ""
        if chat_history:
            # Format last 5 turns for context
            history_str = "\n".join([f"User: {m['user']}\nAI: {m['bot']}" for m in chat_history[-5:]])
        else:
            history_str = "No prior conversation context."

        full_prompt = prompt.format(
            static_knowledge=f"CURRENT DATE: {datetime.now().strftime('%B %d, %Y')}\n" + static_knowledge + "\n\nLATEST UNI UPDATES (PRIORITY):\n" + get_custom_facts() + mode_instruction,
            context=context_str,
            chat_history=history_str,
            question=input_data["question"]
        )
        
        try:
            # TRY GROQ FIRST (SPEED)
            if groq_llm:
                try:
                    response = groq_llm.invoke(full_prompt)
                except Exception as e:
                    print(f"--- Groq Failed --- Error: {e}")
                    # FALLBACK TO GEMINI IF GROQ EXPIRED OR DOWN
                    if gemini_llm:
                        print(f"Falling back to Gemini...")
                        try:
                            response = gemini_llm.invoke(full_prompt)
                        except Exception as ge:
                            print(f"--- Gemini Also Failed --- Error: {ge}")
                            raise ge
                    else: 
                        raise e
            elif gemini_llm:
                response = gemini_llm.invoke(full_prompt)
            else:
                return "The service is temporarily unavailable. Please check the API configurations."
        except Exception as e:
            import traceback
            # print(f"LLM Final Error Traceback: {traceback.format_exc()}")
            return "I apologize, but I am currently facing a connectivity issue. Please try again or visit svsu.ac.in for details."
            
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Clean response from any accidental source mentions or artifacts
        content = re.sub(r"Source:.*?\n", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\[DOC.*?\]", "", content)
        
        # COMPLETE ASTERISK / STAR REMOVAL FOR FULL PROFESSIONAL FORMAT
        content = content.replace("*", "")
        
        # FORCE NEWLINES ON CLUMPED BULLETS (Fixing formatting)
        content = re.sub(r'(?i)\s+-\s*(Duration:|Fee:|Eligibility:|Industry Partners:|Intake:|Admission:|Placement:)', r'\n- \1', content)
        content = re.sub(r'(?i)\s+([0-9]+\.)\s', r'\n\1 ', content)

        # Remove double newlines if any
        content = re.sub(r'\n+', '\n', content)

        return {
            "answer": content.strip(),
            "domain": detected_domain
        }

    return final_response

