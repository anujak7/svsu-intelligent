import os
import json
from typing import Dict, Any
from .evolution_agent import STYLE_EVOLUTION_PATH

def get_user_dossier(user_id: str) -> str:
    """
    Creates a summarized context string (Dossier) about the user
    based on their profile and style preferences.
    """
    if not os.path.exists(STYLE_EVOLUTION_PATH):
        return ""
    
    try:
        with open(STYLE_EVOLUTION_PATH, "r", encoding="utf-8") as f:
            all_prefs = json.load(f)
            user_data = all_prefs.get(user_id, {})
            
            if not user_data:
                return ""
            
            traits = ", ".join(user_data.get("traits", []))
            dossier = f"\n[USER MEMORY: {user_id}]\n"
            if traits:
                dossier += f"- Behavioral Traits: {traits}\n"
            
            return dossier
    except:
        return ""

def update_user_session_trait(user_id: str, trait: str):
    """Manually add a trait to a user during a session."""
    from .evolution_agent import update_style_preferences
    update_style_preferences(user_id, {"user_preference": trait})
