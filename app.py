import os
import streamlit as st
import base64
from chatbot_engine import get_chatbot_chain
from dotenv import load_dotenv

# Load env variables
load_dotenv()

st.set_page_config(page_title="SVSU Intelligent", layout="wide")

# Helper to encode local image to base64
def get_base64_img(img_path):
    if os.path.exists(img_path):
        with open(img_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

img_base64 = get_base64_img("assets/campus.png")

# Modern, Premium Glassmorphism UI
st.markdown(f"""
<style>
    /* Full Page Background (Premium Light Theme) */
    .stApp {{
        background: linear-gradient(135deg, #f0f9ff 0%, #ffffff 100%);
        background-attachment: fixed;
        font-family: 'Inter', sans-serif;
    }}

    /* Top Header Banner (Glass) */
    .header-banner {{
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(10px);
        padding: 1.5rem;
        border-radius: 0 0 30px 30px;
        color: #1e293b;
        text-align: center;
        margin-bottom: 1rem;
        border-bottom: 2px solid #bae6fd;
        box-shadow: 0 4px 15px rgba(14, 165, 233, 0.1);
    }}

    .header-banner img {{
        width: 250px;
    }}

    .header-title {{
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0.2rem 0;
        background: linear-gradient(to right, #0369a1, #0ea5e9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}

    /* Chat Messages (Light Glass) */
    .stChatMessage {{
        background: rgba(255, 255, 255, 0.6) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 20px !important;
        color: #1e293b !important;
        padding: 1rem !important;
        margin-bottom: 1rem !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
    }}

    [data-testid="chat-message-assistant"] {{
        border-left: 5px solid #0ea5e9 !important;
    }}

    [data-testid="chat-message-user"] {{
        border-right: 5px solid #f59e0b !important;
    }}

    /* Make text white in chat for visibility */
    .stChatMessage p, .stChatMessage li, .stChatMessage span {{
        color: #334155 !important;
    }}

    /* Sidebar Light */
    [data-testid="stSidebar"] {{
        background: #ffffff !important ;
        border-right: 1px solid #e2e8f0 !important;
    }}

    [data-testid="stSidebar"] * {{
        color: #475569 !important;
    }}

    /* Chat Input Bar */
    .stChatInputContainer {{
        background: white !important;
        border: 2px solid #e0f2fe !important;
        border-radius: 30px !important;
        box-shadow: 0 10px 25px rgba(14, 165, 233, 0.15) !important;
    }}

    .stChatInputContainer textarea {{
        color: #1e293b !important;
    }}

    /* --- LEAD FORM PREMIUM LIGHT STYLING --- */
    .lead-container {{
        background: white;
        padding: 2.5rem;
        border-radius: 30px;
        border: 2px solid #e0f2fe;
        box-shadow: 0 25px 60px rgba(14, 165, 233, 0.15);
        margin: 0 auto;
        max-width: 1100px;
        text-align: center;
        animation: fadeIn 0.6s ease-out;
    }}

    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(20px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    .lead-logo {{
        width: 450px !important; /* MEGA LOGO */
        margin-bottom: 20px;
        transition: transform 0.3s ease;
    }}
    .lead-logo:hover {{ transform: scale(1.02); }}

    .lead-title {{
        font-size: 2.5rem;
        font-weight: 800;
        color: #0369a1;
        margin-bottom: 5px;
    }}

    .lead-subtitle {{
        color: #64748b;
        font-size: 1.1rem;
        margin-bottom: 30px;
    }}

    /* Input Field Styling */
    .stTextInput input, .stSelectbox select, .stTextArea textarea {{
        background: #f8fafc !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        color: #1e293b !important;
        padding: 12px !important;
    }}

    .stTextInput input:focus, .stSelectbox select:focus {{
        border-color: #0ea5e9 !important;
        box-shadow: 0 0 0 2px rgba(14, 165, 233, 0.2) !important;
    }}

    /* Horizontal Form Submit Button */
    .stButton button {{
        width: 100%;
        background: linear-gradient(135deg, #0ea5e9, #0284c7) !important;
        color: white !important;
        border: none !important;
        border-radius: 15px !important;
        padding: 15px !important;
        font-weight: 700 !important;
        font-size: 1.2rem !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.3s ease !important;
        box-shadow: 0 10px 20px rgba(14, 165, 233, 0.3) !important;
        margin-top: 15px;
    }}

    .stButton button:hover {{
        transform: translateY(-3px) !important;
        box-shadow: 0 15px 30px rgba(14, 165, 233, 0.4) !important;
    }}

    /* Hide defaults */
    #MainMenu, footer {{visibility: hidden;}}

</style>

""", unsafe_allow_html=True)


# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown('<div class="sidebar-brand"><img src="https://svsu.ac.in/img/SVSU-Logo.png" width="250"></div>', unsafe_allow_html=True)
    st.markdown("### About SVSU Intelligent")
    st.markdown("This is the official AI assistant for Shri Vishwakarma Skill University. Designed to help students, faculty, and visitors find information easily and rapidly.")


# ----------------- MAIN HEADER (Only after Lead Capture) -----------------
if st.session_state.lead_captured:
    st.markdown("""
    <div class="header-banner">
        <img src="https://svsu.ac.in/img/SVSU-Logo.png" alt="SVSU Logo">
        <h1 class="header-title">SVSU Intelligent</h1>
        <p class="header-subtitle">Your Official Assistant for Shri Vishwakarma Skill University</p>
    </div>
    """, unsafe_allow_html=True)



# ----------------- INITIALIZE ENGINE (LAZY) -----------------
@st.cache_resource(show_spinner=False)
def load_chain():
    return get_chatbot_chain()

# ----------------- LEAD GENERATION & DATA STORAGE -----------------
LEADS_FILE = "data/leads.csv"
if not os.path.exists("data"):
    os.makedirs("data")

def save_lead(data):
    import pandas as pd
    from datetime import datetime
    data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_exists = os.path.isfile(LEADS_FILE)
    df = pd.DataFrame([data])
    df.to_csv(LEADS_FILE, mode='a', index=False, header=not file_exists)

# Initialize Session States
if "lead_captured" not in st.session_state:
    st.session_state.lead_captured = False
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Welcome! I am SVSU Intelligent. Please introduce yourself to start our conversation."}
    ]

# ----------------- CHAT UI & LEAD FORM -----------------
# 1. Capture Leads First
if not st.session_state.lead_captured:
    st.markdown(f"""
    <div class="lead-container">
        <img src="https://svsu.ac.in/img/SVSU-Logo.png" class="lead-logo">
        <h1 class="lead-title">SVSU Intelligent Guide</h1>
        <p class="lead-subtitle">Initiate a dedicated consultation session by providing your details below.</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        with st.form("lead_form", border=False):
            # TRUE HORIZONTAL LAYOUT (3 columns for fields)
            c1, c2, c3 = st.columns(3)
            with c1:
                name = st.text_input("Full Name", placeholder="e.g. Rahul Sharma")
            with c2:
                mobile = st.text_input("Mobile Number", placeholder="e.g. 98123xxxxx")
            with c3:
                email = st.text_input("Email Address", placeholder="e.g. user@email.com")
            
            # Row 2
            c4, c5 = st.columns([1, 2])
            with c4:
                categories = ["Student", "Parent", "Faculty", "Staff", "Visitor", "Recruiter"]
                destination = st.selectbox("I am a...", categories, index=0)
            with c5:
                purpose = st.text_input("Purpose / Question", placeholder="Admission details, Exam dates, etc.")
            
            submit = st.form_submit_button("Start Consulting Now")


            
            if submit:
                if name and email and mobile:
                    lead_data = {
                        "name": name,
                        "email": email,
                        "mobile": mobile,
                        "designation": destination,
                        "purpose": purpose
                    }
                    save_lead(lead_data)
                    st.session_state.lead_captured = True
                    st.session_state.user_name = name
                    st.success(f"Welcome {name}! Let's find what you need.")
                    st.rerun()
                else:
                    st.error("Please fill in Name, Email and Mobile to continue.")
    st.stop() # Don't show the chat until lead is captured

# Display history
logo_base64 = f"data:image/png;base64,{get_base64_img('assets/logo-svsu.png')}"
for message in st.session_state.messages:
    avatar = logo_base64 if message["role"] == "assistant" else None
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# User Input
if prompt := st.chat_input("E.g., What are the admission procedures?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=logo_base64):
        with st.spinner("Thinking..."):



            try:
                # Lazy load the chain only when the user first interacts
                qa_chain = load_chain()
                
                # Engine returns a plain function - call it directly
                if callable(qa_chain) and not hasattr(qa_chain, 'stream'):
                    full_response = qa_chain({"question": prompt})
                else:
                    # Fallback: try invoke for LangChain chain objects
                    full_response = qa_chain.invoke(prompt)
                
                st.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error(f"Error: {e}")
