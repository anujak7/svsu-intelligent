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

    /* Hide defaults */
    #MainMenu, footer {{visibility: hidden;}}

</style>
""", unsafe_allow_html=True)


# ----------------- ADMIN COMPONENT -----------------
import pandas as pd
import plotly.express as px
from datetime import datetime

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown('<div class="sidebar-brand"><img src="https://svsu.ac.in/img/SVSU-Logo.png" width="250"></div>', unsafe_allow_html=True)
    st.markdown("### About SVSU Intelligent")
    st.markdown("This is the official AI assistant for Shri Vishwakarma Skill University. Designed to help students, faculty, and visitors find information easily and rapidly.")
    
    if st.session_state.admin_logged_in:
        st.markdown("---")
        st.success("👨‍💻 Admin Mode Active")
        if st.button("Logout Admin"):
            st.session_state.admin_logged_in = False
            st.rerun()

# ----------------- ADMIN VIEW -----------------
LEADS_FILE = "data/leads.csv"
if not os.path.exists("data"):
    os.makedirs("data")

if st.session_state.admin_logged_in:
    st.markdown("""
    <div class="header-banner">
        <h1 class="header-title">🏛️ SVSU Lead & Analytics Dashboard</h1>
    </div>
    """, unsafe_allow_html=True)
    
    if os.path.exists(LEADS_FILE):
        df = pd.read_csv(LEADS_FILE)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Visitors", len(df))
        with col2:
            st.metric("Inquisitive Students", len(df[df['designation'] == 'Student']))
        with col3:
            st.metric("Unique Leads", df['email'].nunique())
        with col4:
            today = datetime.now().strftime("%Y-%m-%d")
            st.metric("Leads Today", len(df[df['timestamp'].str.contains(today, na=False)]))
            
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Visitor Distribution")
            fig1 = px.pie(df, names='designation', hole=0.4)
            st.plotly_chart(fig1, use_container_width=True)
        with c2:
            st.markdown("### Lead Timeline")
            df['date'] = pd.to_datetime(df['timestamp']).dt.date
            timeline_df = df.groupby('date').size().reset_index(name='count')
            fig2 = px.line(timeline_df, x='date', y='count', markers=True)
            st.plotly_chart(fig2, use_container_width=True)
            
        st.markdown("### 📋 Detailed Records")
        st.dataframe(df.sort_values(by='timestamp', ascending=False), use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Lead Data (CSV)", csv, "svsu_leads.csv", "text/csv")
    else:
        st.info("No leads captured yet. Data will appear once the main chat is used.")
    st.stop() # Hide main chat for admins

# ----------------- MAIN HEADER (CHAT) -----------------
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
    with st.container():
        st.markdown("""
        <div style="background: rgba(255,255,255,0.1); backdrop-filter: blur(20px); padding: 2rem; border-radius: 20px; border: 1px solid rgba(255,255,255,0.1); margin: 2rem auto; max-width: 600px; color: white;">
            <h2 style="text-align: center; color: #df6d25;">Welcome to SVSU Intelligent</h2>
            <p style="text-align: center;">Choose your portal below.</p>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🎓 Student / Visitor Chat", "🛡️ Admin Access"])
        
        with tab1:
            with st.form("lead_form"):
                st.markdown("#### Enter your details to begin")
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Full Name")
                    email = st.text_input("Email Address")
                with col2:
                    mobile = st.text_input("Mobile Number")
                    destination = st.selectbox("Designation/Category", ["Student", "Parent", "Faculty", "Staff", "Visitor", "Recruiter"])
                
                purpose = st.text_area("Purpose of Chat (e.g., Admission, Exams, Hiring)")
                
                submit = st.form_submit_button("🚀 Start Chatting")
                
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
                        
        with tab2:
            st.markdown("#### Staff & Admin Portal")
            admin_email = st.text_input("Official Email (@svsu.ac.in)")
            admin_pass = st.text_input("Password", type="password")
            if st.button("Unlock Dashboard"):
                if admin_email.endswith("@svsu.ac.in") and admin_pass == "svsuindia47":
                    st.session_state.admin_logged_in = True
                    st.rerun()
                else:
                    st.error("Invalid SVSU Administrator credentials.")
    st.stop() # Don't show the chat until lead is captured/admin is active

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
