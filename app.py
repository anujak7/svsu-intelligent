import os
import streamlit as st
from chatbot_engine import get_chatbot_chain
from dotenv import load_dotenv

# Load env variables (including the provided API key)
load_dotenv()

st.set_page_config(page_title="SVSU Intelligent", layout="wide")

# Modern, Govt-official premium UI via CSS injection
st.markdown("""
<style>
    /* Global Background */
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgb(239, 246, 255) 0%, rgb(255, 255, 255) 90%);
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }

    /* Top Header Banner */
    .header-banner {
        background: white;
        padding: 2.5rem 1rem;
        border-radius: 12px;
        color: #1e4b8a; /* SVSU Dark Blue */
        text-align: center;
        box-shadow: 0 4px 25px rgba(0,0,0,0.06);
        margin-bottom: 2rem;
        border-top: 5px solid #df6d25; /* SVSU Orange */
    }

    .header-banner img {
        width: 250px;
        margin-bottom: 1.5rem;
    }

    .header-title {
        font-size: 2.8rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: 1px;
    }

    .header-subtitle {
        font-size: 1.2rem;
        font-weight: 400;
        opacity: 0.9;
        margin-top: 0.5rem;
    }

    /* Chat window area */
    .stChatMessage {
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(0,0,0,0.05);
        box-shadow: 0 2px 10px rgba(0,0,0,0.02);
    }

    /* Assistant Message styling */
    [data-testid="chat-message-assistant"] {
        background-color: white !important;
        border-right: 5px solid #df6d25 !important;
    }

    /* User Message styling */
    [data-testid="chat-message-user"] {
        background-color: #f1f5f9 !important;
        border-left: 5px solid #1e4b8a !important; 
    }

    /* Input area styling */
    .stChatInputContainer {
        border-radius: 30px !important;
        border: 2px solid #e2e8f0 !important;
        background-color: white !important;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05) !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    .stChatInputContainer:focus-within {
        border-color: #1e4b8a !important;
    }

    /* Hide default Streamlit marks */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    
    .sidebar-brand {
        text-align: center;
        padding: 1rem 0;
        border-bottom: 2px solid #f1f5f9;
        margin-bottom: 1.5rem;
    }
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
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input
if prompt := st.chat_input("E.g., What are the admission procedures?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
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
