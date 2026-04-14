import streamlit as st
import pandas as pd
import os
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="SVSU Admin Portal", layout="wide", page_icon="🏛️")

# Custom CSS for Premium Dashboard
st.markdown("""
<style>
    /* Full Page Background with Image (ORIGINAL COLORS) */
    .stApp {
        background: linear-gradient(rgba(255, 255, 255, 0.9), rgba(240, 242, 246, 0.9));
        font-family: 'Inter', sans-serif;
    }
    
    .main {
        background: transparent;
    }
    .stMetric {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
    }
    .stDataFrame {
        background: white;
        border-radius: 15px;
        border: 1px solid #e2e8f0;
    }
    h1, h2, h3 {
        color: #1e4b8a;
        font-weight: 700;
    }
    .stButton>button {
        background: #df6d25;
        color: white;
        border-radius: 10px;
        border: none;
        font-weight: 600;
    }
    .stButton>button:hover {
        background: #c85a1a;
    }
</style>
""", unsafe_allow_html=True)

# Authentication logic
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    with st.container():
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div style="background: white; padding: 3rem; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); text-align: center;">
                <img src="https://svsu.ac.in/img/SVSU-Logo.png" width="200" style="margin-bottom: 20px;">
                <h2 style="color: #1e4b8a; margin-bottom: 10px;">Admin Portal Secured Login</h2>
                <p style="color: #64748b; margin-bottom: 30px;">Authorized University Personnel Only</p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("admin_login_form"):
                email = st.text_input("Official Email Address (@svsu.ac.in)")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Access Dashboard")
                
                if submitted:
                    if email.endswith("@svsu.ac.in") and password == "svsuindia47":
                        st.session_state.admin_logged_in = True
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Access Denied.")
    st.stop()

# ----------------- DASHBOARD LOGIC -----------------
# Header
colA, colB = st.columns([3, 1])
with colA:
    st.title("🏛️ Student & Visitor Data Analytics")
with colB:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Logout Securely", use_container_width=True):
        st.session_state.admin_logged_in = False
        st.rerun()

st.markdown("---")

# Data Loading
LEADS_FILE = "data/leads.csv"

if os.path.exists(LEADS_FILE):
    df = pd.read_csv(LEADS_FILE)
    
    # 1. TOP STATS
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Visitors / Leads", len(df))
    with col2:
        student_count = len(df[df['designation'].str.lower() == 'student'])
        st.metric("Inquisitive Students", student_count)
    with col3:
        unique_emails = df['email'].nunique()
        st.metric("Unique Individuals", unique_emails)
    with col4:
        today = datetime.now().strftime("%Y-%m-%d")
        today_leads = len(df[df['timestamp'].str.contains(today, na=False)])
        st.metric("New Leads Today", today_leads)

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. CHARTS
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 👥 Visitor Demographic")
        fig1 = px.pie(df, names='designation', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig1, use_container_width=True)
    
    with c2:
        st.markdown("### 📈 Lead Generation Timeline")
        # Extract date from timestamp
        try:
            df['date'] = pd.to_datetime(df['timestamp']).dt.date
            timeline_df = df.groupby('date').size().reset_index(name='count')
            fig2 = px.line(timeline_df, x='date', y='count', markers=True, markers_size=10)
            fig2.update_traces(line_color='#df6d25')
            st.plotly_chart(fig2, use_container_width=True)
        except Exception as e:
            st.warning("Not enough data dates for timeline yet.")

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. LEAD TABLE
    st.markdown("### 📋 Complete Lead Database")
    
    # Add filtering options
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        filter_desig = st.selectbox("Filter by Category", ["All"] + list(df['designation'].unique()))
    
    display_df = df.copy()
    if filter_desig != "All":
        display_df = display_df[display_df['designation'] == filter_desig]
        
    st.dataframe(
        display_df.sort_values(by='timestamp', ascending=False), 
        use_container_width=True,
        hide_index=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. EXPORT
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export Full Lead Database as CSV",
        data=csv,
        file_name=f'svsu_leads_export_{datetime.now().strftime("%Y%m%d")}.csv',
        mime='text/csv',
    )

else:
    # Empty State Dashboard
    st.info("No data captured yet. The dashboard will automatically populate when the first visitor uses the chatbot.")
    st.image("https://svsu.ac.in/img/SVSU-Logo.png", width=300)
    st.markdown("### Waiting for incoming traffic...")
