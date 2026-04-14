from .domain_agents import execute_domain_agent, get_llm_client, call_groq_with_retry
from .evolution_agent import get_consolidated_knowledge, get_user_style_prompt
from .memory_manager import get_user_dossier



DOMAIN_LIST = [
    "Home", "About", "Academics", "Administration", "Admission", 
    "Research", "Student Programs", "Examination", "Notices", 
    "Library", "Contact", "Updates"
]

async def master_process_query(question: str, history: list = None, mode: str = "intelligent", user_id: str = "anonymous") -> dict:
    """Master Agent classifies intent and delegates to specialized agents.
    Strictly enforces admission-only queries if mode is 'admission'.
    """
    # 0. FAST PATH: Greetings or empty queries to save performance
    greetings = ["hi", "hello", "hey", "hola", "namaste", "good morning", "good afternoon", "good evening"]
    q_clean = question.lower().strip().replace("?", "").replace("!", "")
    if q_clean in greetings or len(q_clean) < 2:
        return {
            "answer": "Hello! Welcome to **Shri Vishwakarma Skill University (SVSU)**. I am your specialized AI counselor. How can I assist you with your academic journey today?",
            "domain": "Home"
        }

    if "program_selected:" in question.lower():
        detected_domain = "Admission"
    else:
        classification_prompt = f"""You are the Master Intent Classifier for Shri Vishwakarma Skill University (SVSU).
Your goal is to classify the user's question into exactly ONE of the following precise domains.

DOMAINS: {', '.join(DOMAIN_LIST)}

CLASSIFICATION RULES:
- Admission: Fees, apply process, eligibility, course intake, seats, registration, prospectus.
- Academics: Departments, faculties, professors (Deans/Chairpersons), curricula, schools, degree types.
- Administration: VC, Registrar, Executive Council, Finance Committee, Establishment, VC/Registrar office contact.
- Library: Books, e-resources, library timings, digital library, Shodhganga.
- Examination: Controller of Examination (COE), results, DMCs, exam schedule, supplementary exams.
- Research: PhD admissions, research projects, IIC, patents, innovation.
- Student Programs: Hostel (accommodation/fees), Health Centre (doctors/nursing), NSS, DSW, transport, canteen, culturals.
- Notices/Updates: Recent circulars, office orders, latest news, tender notices.
- Contact: University address, general phone numbers, location, map.
- Home: ANY OTHER SVSU QUERY. Campus life, rules, clubs, VC info, history, facilities, student welfare, or anything not fitting above. Treat this as the "Universal SVSU Expert" domain.

STRICT INSTRUCTION: Output ONLY the single domain name from the list. No commentary. No periods.
"""

        try:
            messages = [
                {"role": "system", "content": classification_prompt},
                {"role": "user", "content": f"USER QUERY: {question}"}
            ]
            
            detected_domain = await call_groq_with_retry(
                messages, 
                model="llama-3.1-8b-instant", # Classification is fast
                max_tokens=10, 
                temperature=0.0
            )
            
            # Validations
            valid_domains = [d.lower() for d in DOMAIN_LIST]
            if detected_domain.lower() not in valid_domains:
                # Fallback parsing
                detected_domain = "Home"
                for d in DOMAIN_LIST:
                    if d.lower() in detected_domain.lower():
                        detected_domain = d
                        break
            else:
                # Proper Case matching
                detected_domain = next(d for d in DOMAIN_LIST if d.lower() == detected_domain.lower())
        except Exception as e:
            print(f"[MASTER AGENT] Error classifying intent: {e}")
            detected_domain = "Home"  # Default fallback
            
    print(f"\n==============================================")
    print(f"[MASTER AGENT ROUTER] Mode: {mode} | Detected: {detected_domain}")
    print(f"==============================================\n")
    
    # Mode Logic: Map 'voice' to 'intelligent' but keep the flag for downstream brevity
    is_voice = (mode == "voice")
    
    # RESTORED: Mode Redirection for 'Admission' section to maintain domain focus
    if mode == "admission":
        # Check if query is related to core Admission concerns (Courses, Fees, Placements, Exams)
        admission_keywords = ["admission", "apply", "fee", "course", "program", "eligibility", "criteria", "intake", "seat", "registration", "form", "cutoff", "entrance", "placement", "exam", "result", "job", "career"]
        is_admission_related = (detected_domain in ["Admission", "Academics", "Examination"]) or any(kw in question.lower() for kw in admission_keywords)
        
        if not is_admission_related:
            return {
                "answer": "Greetings! I am currently in the **SVSU Admission AI Portal**. I am specifically tuned to answer questions regarding admissions, placements, programs, and examinations.\n\nFor general campus queries, VC info, or miscellaneous university history, please switch to the **Other Queries** mode from the menu above to get full details!",
                "domain": "Admission"
            }
    
    # Inject Learned facts and User Dossier before delegation
    learned_facts = get_consolidated_knowledge()
    user_dossier = get_user_dossier(user_id)
    learned_user_style = get_user_style_prompt(user_id)
    
    enhanced_context = ""
    if learned_user_style:
        enhanced_context += f"{learned_user_style}\n"
    if learned_facts:
        enhanced_context += f"\n[GLOBAL UNIVERSITY UPDATES]:\n{learned_facts}\n"
    if user_dossier:
        enhanced_context += f"\n[PERSONAL USER CONTEXT]:\n{user_dossier}\n"

    if enhanced_context:
        question = f"{enhanced_context}\n\nUSER REQUEST: {question}"


    # Delegate to Specific Domain Agent (Live Web Scraper + LLM Summarizer)
    final_answer = await execute_domain_agent(detected_domain, question, history, mode=mode)

    
    # Allow Markdown for professional formatting (Bold, Titles, etc.)
    # final_answer = final_answer.replace("*", "") 
    
    
    # Voice Mode optimization: Ensure brevity for faster TTS but keep depth
    if mode == "voice" and len(final_answer) > 1200:
        shorten_prompt = f"Summarize the following university answer into a natural, conversational voice response (max 5 sentences). Keep key facts like dates, fees, and contact info intact. Answer exactly in the same language (English/Hindi/Hinglish) as the original.\n\nORIGINAL: {final_answer}"
        try:
            final_answer = await call_groq_with_retry([{"role": "user", "content": shorten_prompt}], model="llama-3.1-8b-instant", max_tokens=250)
        except: pass
    
    return {
        "answer": final_answer.strip(),
        "domain": detected_domain
    }
