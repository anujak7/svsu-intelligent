import streamlit as st
import pandas as pd
import os
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="SVSU Admin Dashboard", layout="wide", page_icon="🏛️")

# Custom CSS for Premium Dashboard
st.markdown("""
<style>
    .main {
        background: #f0f2f6;
    }
    .stMetric {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .stDataFrame {
        background: white;
        border-radius: 15px;
    }
    h1, h2, h3 {
        color: #1e4b8a;
    }
    .stButton>button {
        background: #df6d25;
        color: white;
        border-radius: 10px;
        border: none;
    }
</style>
""", unsafe_allow_html=True)

# Authentication logic
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    st.markdown("<h1 style='text-align: center;'>SVSU Admin Suite</h1>", unsafe_allow_html=True)
    with st.container():
        left, mid, right = st.columns([1,2,1])
        with mid:
            email = st.text_input("SVSU Official Email")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                if email.endswith("@svsu.ac.in") and password == "svsuindia47":
                    st.session_state.admin_logged_in = True
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please use @svsu.ac.in email.")
    st.stop()

# ----------------- DASHBOARD LOGIC -----------------
st.title("🏛️ SVSU Lead & Analytics Dashboard")

LEADS_FILE = "data/leads.csv"

if os.path.exists(LEADS_FILE):
    df = pd.read_csv(LEADS_FILE)
    
    # 1. TOP STATS
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Visitors/Leads", len(df))
    with col2:
        student_count = len(df[df['designation'] == 'Student'])
        st.metric("Inquisitive Students", student_count)
    with col3:
        unique_emails = df['email'].nunique()
        st.metric("Unique Leads", unique_emails)
    with col4:
        today = datetime.now().strftime("%Y-%m-%d")
        today_leads = len(df[df['timestamp'].str.contains(today, na=False)])
        st.metric("Leads Today", today_leads)

    st.markdown("---")

    # 2. CHARTS
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Visitor Distribution")
        fig1 = px.pie(df, names='designation', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig1, use_container_width=True)
    
    with c2:
        st.subheader("Lead Timeline")
        # Extract date from timestamp
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        timeline_df = df.groupby('date').size().reset_index(name='count')
        fig2 = px.line(timeline_df, x='date', y='count', markers=True, markers_size=10)
        fig2.update_traces(line_color='#df6d25')
        st.plotly_chart(fig2, use_container_width=True)

    # 3. LEAD TABLE
    st.subheader("📋 Detailed Lead Records")
    st.dataframe(df.sort_values(by='timestamp', ascending=False), use_container_width=True)

    # 4. DOWNLOAD DATA
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Lead Data (CSV)",
        data=csv,
        file_name='svsu_leads_export.csv',
        mime='text/csv',
    )

else:
    st.info("No leads captured yet. The dashboard will show data once the first visitor chats with the bot.")

# Logout
if st.sidebar.button("Logout"):
    st.session_state.admin_logged_in = False
    st.rerun()
