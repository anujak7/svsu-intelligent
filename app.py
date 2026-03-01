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
    /* Full Page Background with Image */
    .stApp {{
        background: linear-gradient(rgba(30, 75, 138, 0.7), rgba(0, 0, 0, 0.8)), 
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

    /* Hide defaults */
    #MainMenu, footer {{visibility: hidden;}}

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


# ----------------- CHAT UI -----------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Welcome! I am SVSU Intelligent. How can I assist you today?"}
    ]

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
