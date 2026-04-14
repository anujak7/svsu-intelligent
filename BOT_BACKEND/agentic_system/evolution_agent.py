import os
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from .domain_agents import call_groq_with_retry

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
GLOBAL_KNOWLEDGE_PATH = os.path.join(DATA_DIR, "global_learned_knowledge.json")
STYLE_EVOLUTION_PATH = os.path.join(DATA_DIR, "style_preferences.json")

async def evolution_process(question: str, answer: str, user_id: str = "anonymous"):
    """
    Enhanced evolutionary process that learns facts (with confidence) 
    and interaction styles from user data.
    """
    try:
        # 1. Prompt for Deep Extraction
        prompt = f"""
        Analyze this interaction between a USER and SVSU AI. 
        Extract any NEW factual university info OR deep user profile traits.
        Pay extreme attention to:
        1. Language Preference (e.g., Hindi, Hinglish, English)
        2. Verbosity (e.g., short answers, detailed, bullet points)
        3. Tone (e.g., friendly, strictly professional)

        USER ({user_id}): {question}
        AI: {answer}

        OUTPUT EXACTLY THIS JSON FORMAT:
        {{
            "fact": "extracted university fact or null",
            "is_correction": true/false,
            "language": "Hindi/Hinglish/English or null",
            "format_preference": "e.g., short, bulleted, detailed or null",
            "user_interest": "e.g., B.Tech, Fees, Placement or null"
        }}
        """
        
        messages = [{"role": "system", "content": "You are a Knowledge Synthesis Engine. Output ONLY valid JSON."},
                    {"role": "user", "content": prompt}]
        
        raw_output = await call_groq_with_retry(messages, model="llama-3.1-8b-instant", max_tokens=300)
        
        # Clean JSON if LLM adds markdown
        if "```json" in raw_output:
            raw_output = raw_output.split("```json")[1].split("```")[0].strip()
        
        updates = json.loads(raw_output)
        
        # 2. Process Style & Preferences only.
        # Auto-learning university facts is intentionally disabled because
        # unverified model outputs can poison future answers.
        if updates.get("language") or updates.get("format_preference") or updates.get("user_interest"):
            update_style_preferences(user_id, updates)

    except Exception as e:
        print(f"[EVOLUTION AGENT ERROR] {e}")

def update_global_knowledge(fact: str, user_id: str):
    """Saves facts with mention counts to increase confidence."""
    os.makedirs(DATA_DIR, exist_ok=True)
    knowledge = []
    if os.path.exists(GLOBAL_KNOWLEDGE_PATH):
        try:
            with open(GLOBAL_KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
                knowledge = json.load(f)
        except: pass

    # Simple similarity check (approximate)
    found = False
    for item in knowledge:
        if fact.lower()[:30] in item["text"].lower():
            item["mention_count"] += 1
            if user_id not in item["sources"]:
                item["sources"].append(user_id)
            item["last_updated"] = datetime.now().isoformat()
            found = True
            break
    
    if not found:
        knowledge.append({
            "text": fact,
            "mention_count": 1,
            "sources": [user_id],
            "confidence": "low", # Can be upgraded to 'high' if mention_count > 3
            "created_at": datetime.now().isoformat()
        })
    
    with open(GLOBAL_KNOWLEDGE_PATH, "w", encoding="utf-8") as f:
        json.dump(knowledge, f, indent=2)

def update_style_preferences(user_id: str, updates: Dict):
    """Stores user-specific behavior preferences."""
    os.makedirs(DATA_DIR, exist_ok=True)
    prefs = {}
    if os.path.exists(STYLE_EVOLUTION_PATH):
        try:
            with open(STYLE_EVOLUTION_PATH, "r", encoding="utf-8") as f:
                prefs = json.load(f)
        except: pass
    
    user_pref = prefs.get(user_id, {"traits": [], "interests": [], "language": "English", "format": "standard"})
    
    if updates.get("language") and updates["language"] != "null":
        user_pref["language"] = updates["language"]
        
    if updates.get("format_preference") and updates["format_preference"] != "null":
        user_pref["format"] = updates["format_preference"]
        if updates["format_preference"] not in user_pref["traits"]:
            user_pref["traits"].append(updates["format_preference"])
            
    if updates.get("user_interest") and updates["user_interest"] != "null" and updates["user_interest"] not in user_pref["interests"]:
        user_pref["interests"].append(updates["user_interest"])
    
    user_pref["last_seen"] = datetime.now().isoformat()
    prefs[user_id] = user_pref
    
    with open(STYLE_EVOLUTION_PATH, "w", encoding="utf-8") as f:
        json.dump(prefs, f, indent=2)

def get_user_style_prompt(user_id: str) -> str:
    """Returns a customized system prompt instruction based on the user's learned style."""
    if not os.path.exists(STYLE_EVOLUTION_PATH):
        return ""
    try:
        with open(STYLE_EVOLUTION_PATH, "r", encoding="utf-8") as f:
            prefs = json.load(f)
            
        user_pref = prefs.get(user_id)
        if not user_pref:
            return ""
            
        instructions = []
        lang = user_pref.get("language", "").lower()
        if "hindi" in lang or "hinglish" in lang:
            instructions.append(f"CRITICAL: The user strongly prefers interacting in {lang.upper()}. You must answer in {lang.upper()} but use romanized script (Hinglish) if helpful.")
            
        fmt = user_pref.get("format", "").lower()
        if "short" in fmt or "brief" in fmt:
            instructions.append("CRITICAL: The user prefers very SHORT and CONCISE answers.")
        elif "bullet" in fmt:
            instructions.append("CRITICAL: The user prefers heavily BULLETED lists for easy reading.")
            
        if instructions:
            return "\n[USER-SPECIFIC ADAPTATION RULES]:\n" + "\n".join(instructions)
        return ""
    except Exception as e:
        print(f"Error reading style: {e}")
        return ""

def get_consolidated_knowledge() -> str:
    """Returns only manually verified facts for the AI prompt."""
    if not os.path.exists(GLOBAL_KNOWLEDGE_PATH):
        return ""
    try:
        with open(GLOBAL_KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
            knowledge = json.load(f)
            trusted = [
                item["text"]
                for item in knowledge
                if item.get("confidence") == "verified" and item.get("mention_count", 0) >= 2
            ]
            return "\n".join([f"- {t}" for t in trusted])
    except: return ""
