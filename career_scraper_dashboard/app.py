import streamlit as st
import pandas as pd
import sys
import os
import time

# Ensure we can import sibling modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import storage

st.set_page_config(page_title="H1B Career Cloud", layout="wide", page_icon="☁️")

# Styling
st.markdown("""
    <style>
    .main {
        background-color: #f0f2f6;
    }
    .stDataFrame {
        background-color: white;
        border-radius: 10px;
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("☁️ H1B Career Portal")
st.caption("AI-Powered Job Discovery System")

# Sidebar Stats
stats = storage.get_stats()
st.sidebar.header("System Status")
st.sidebar.metric("Total Jobs Found", stats["total"])
st.sidebar.metric("New Today", stats["new_today"])
st.sidebar.text(f"Last Updated: {time.strftime('%H:%M:%S')}")

if st.sidebar.button("Refresh Data"):
    st.rerun()

# --- NEW: Top H1B Sponsors Section ---
import json
try:
    with open(os.path.join(os.path.dirname(__file__), "uscis_h1b_top_list.json"), "r") as f:
        h1b_data = json.load(f)
    
    st.subheader("🏆 Top H1B Sponsors (2024)")
    with st.expander("View Top 100 H1B Filers", expanded=False):
        df_h1b = pd.DataFrame(h1b_data)
        
        # Ensure URL column exists (handle older JSON without it)
        if "url" not in df_h1b.columns:
            df_h1b["url"] = None

        if not df_h1b.empty:
            st.dataframe(
                df_h1b[["rank", "name", "industry", "h1b_2024", "url"]], # Simplified view
                use_container_width=True,
                column_config={
                    "rank": st.column_config.NumberColumn("Rank"),
                    "name": "Company",
                    "industry": "Industry",
                    "h1b_2024": st.column_config.NumberColumn("2024 Filings"),
                    "url": st.column_config.LinkColumn("Career Page", display_text="🔗 Visit Site"),
                },
                hide_index=True
            )
except Exception as e:
    st.warning(f"Could not load H1B data: {e}")
# -------------------------------------

# Data Loading
rows = storage.get_all_jobs()
if not rows:
    st.info("No jobs found yet. Start the Monitor (monitor.py) to begin scraping.")
else:
    # Convert to DataFrame
    df = pd.DataFrame([dict(row) for row in rows])
    
    # Defensive: Ensure columns exist (in case of legacy DB rows)
    expected_cols = ["category", "funding_info", "posted_date"]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = "Unknown"
            
    # Fill N/As
    df.fillna("Unknown", inplace=True)
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        search_term = st.text_input("🔍 Search Title or Company")
    with col2:
        category_filter = st.multiselect("Filter by Category", options=df["category"].unique())
    with col3:
        company_filter = st.multiselect("Filter by Company", options=df["company"].unique())

    # Apply Filters
    if search_term:
        df = df[df["title"].str.contains(search_term, case=False, na=False) | 
                df["company"].str.contains(search_term, case=False, na=False)]
    
    if category_filter:
        df = df[df["category"].isin(category_filter)]

    if company_filter:
        df = df[df["company"].isin(company_filter)]

    # Display
    st.dataframe(
        df[["company", "title", "location", "category", "funding_info", "first_seen", "url"]],
        use_container_width=True,
        column_config={
            "url": st.column_config.LinkColumn("Apply Link"),
            "first_seen": st.column_config.DatetimeColumn("Discovered", format="D MMM, HH:mm"),
            "category": st.column_config.TextColumn("Category"),
            "funding_info": st.column_config.TextColumn("Funding Status")
        }
    )

    st.markdown("---")
    st.markdown(f"**Showing {len(df)} jobs**")
