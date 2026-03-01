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
    /* Full Page Background with Image (ORIGINAL COLORS) */
    .stApp {{
        background: linear-gradient(rgba(255, 255, 255, 0.1), rgba(0, 0, 0, 0.2)), 
                    url("data:image/png;base64,{img_base64}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Inter', sans-serif;
    }}

    /* Top Header Banner (Glass) */
    .header-banner {{
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(15px);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
    }}

    .header-banner img {{
        width: 220px;
        filter: drop-shadow(0 0 10px rgba(255,255,255,0.5));
    }}

    .header-title {{
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0.5rem 0;
        background: linear-gradient(to right, #ffffff, #df6d25);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}

    /* Chat Messages (Glassmorphism) */
    .stChatMessage {{
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(8px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 15px !important;
        color: white !important;
        padding: 1.2rem !important;
        margin-bottom: 1rem !important;
    }}

    [data-testid="chat-message-assistant"] {{
        border-right: 4px solid #df6d25 !important;
    }}

    [data-testid="chat-message-user"] {{
        border-left: 4px solid #1e4b8a !important;
    }}

    /* Make text white in chat for visibility */
    .stChatMessage p, .stChatMessage li, .stChatMessage span {{
        color: #f8fafc !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
    }}

    /* Sidebar Glass */
    [data-testid="stSidebar"] {{
        background: rgba(255, 255, 255, 0.1) !important ;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
    }}

    [data-testid="stSidebar"] * {{
        color: white !important;
    }}

    /* Chat Input Bar */
    .stChatInputContainer {{
        background: rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(15px) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 30px !important;
        padding: 0.5rem !important;
    }}

    .stChatInputContainer textarea {{
        color: white !important;
    }}

    /* --- LEAD FORM PREMIUM STYLING --- */
    .lead-container {
        background: rgba(255, 255, 255, 0.08); /* Dark Glass */
        backdrop-filter: blur(25px);
        padding: 3rem;
        border-radius: 24px;
        border: 1px solid rgba(255, 255, 255, 0.15);
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4);
        margin: 2rem auto;
        max-width: 900px;
        color: white;
        text-align: center;
        animation: fadeIn 0.8s ease-out;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .lead-logo {
        width: 320px !important; /* Larger Logo */
        margin-bottom: 30px;
        background: white;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }

    .lead-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #f8fafc;
        margin-bottom: 5px;
        letter-spacing: -0.5px;
    }

    .lead-subtitle {
        color: #94a3b8;
        font-size: 1.1rem;
        margin-bottom: 40px;
    }

    /* Input Field Styling */
    .stTextInput input, .stSelectbox select, .stTextArea textarea {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px !important;
        color: white !important;
        padding: 12px !important;
    }

    .stTextInput input:focus, .stSelectbox select:focus {
        border-color: #df6d25 !important;
        box-shadow: 0 0 0 2px rgba(223, 109, 37, 0.2) !important;
    }

    /* Horizontal Form Submit Button */
    .stButton button {
        width: 100%;
        background: linear-gradient(135deg, #df6d25, #f59e0b) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 18px !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.3s ease !important;
        box-shadow: 0 10px 20px rgba(223, 109, 37, 0.3) !important;
        margin-top: 15px;
    }

    .stButton button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 15px 30px rgba(223, 109, 37, 0.4) !important;
    }

    /* Hide defaults */
    #MainMenu, footer {visibility: hidden;}

</style>

""", unsafe_allow_html=True)


# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown('<div class="sidebar-brand"><img src="https://svsu.ac.in/img/SVSU-Logo.png" width="250"></div>', unsafe_allow_html=True)
    st.markdown("### About SVSU Intelligent")
    st.markdown("This is the official AI assistant for Shri Vishwakarma Skill University. Designed to help students, faculty, and visitors find information easily and rapidly.")


# ----------------- MAIN HEADER -----------------
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
    
    # Custom Container for Form to handle alignment
    form_placeholder = st.empty()
    with form_placeholder.container():
        with st.form("lead_form"):
            # Horizontal Group 1
            r1c1, r1c2 = st.columns(2)
            with r1c1:
                name = st.text_input("Full Name", placeholder="e.g. John Doe")
            with r1c2:
                mobile = st.text_input("Mobile Number", placeholder="e.g. 9876543210")
            
            # Horizontal Group 2
            r2c1, r2c2 = st.columns(2)
            with r2c1:
                email = st.text_input("Email Address", placeholder="e.g. john@svsu.ac.in")
            with r2c2:
                categories = ["Student", "Parent", "Faculty", "Staff", "Visitor", "Recruiter"]
                destination = st.selectbox("Designation/Category", categories, index=0)
            
            # Full Width Field
            purpose = st.text_area("Purpose of Chat (How can we help you today?)", placeholder="Admission, Exams, Placements, etc.")
            
            submit = st.form_submit_button("Start Intelligent Consulting")

            
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
