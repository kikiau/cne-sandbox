import streamlit as st
import sqlite3
from datetime import datetime
from rag.retrieve import get_answer

# ---------- Database ----------
def init_db():
    conn = sqlite3.connect("data/interactions.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            question TEXT,
            articles TEXT,
            resolved INTEGER
        )
    """)
    conn.commit()
    conn.close()

def log_interaction(question, articles, resolved):
    conn = sqlite3.connect("data/interactions.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO interactions (timestamp, question, articles, resolved) VALUES (?, ?, ?, ?)",
        (datetime.now().isoformat(), question, ", ".join(articles), 1 if resolved else 0)
    )
    conn.commit()
    conn.close()

def get_metrics():
    conn = sqlite3.connect("data/interactions.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM interactions")
    total = c.fetchone()[0]
    c.execute("SELECT SUM(resolved) FROM interactions")
    resolved = c.fetchone()[0] or 0
    conn.close()
    rate = (resolved / total * 100) if total > 0 else 0
    return total, resolved, rate

init_db()

# ---------- UI ----------
st.set_page_config(page_title="Community Policy Request Center", layout="wide")

# Custom CSS to better match the real interface
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #FF5A5F 0%, #FF385C 100%);
        padding: 60px 20px 40px 20px;
        border-radius: 0 0 12px 12px;
        text-align: center;
        margin: -1rem -1rem 2rem -1rem;
    }
    .main-header h1 {
        color: white;
        font-size: 2.4rem;
        font-weight: 600;
        margin: 0;
    }
    .search-container {
        max-width: 700px;
        margin: 30px auto 0 auto;
    }
    .stTextInput > div > div > input {
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

page = st.sidebar.radio("Navigation", ["Request Center", "Metrics"])

if page == "Request Center":
    st.markdown("""
        <div class="main-header">
            <h1>Community & Product Policy Team Request Center</h1>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="search-container">', unsafe_allow_html=True)
    user_issue = st.text_input(
        "Search",
        placeholder="Search for self-help or create a ticket in one search box...",
        label_visibility="collapsed"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Get Self-Help", type="primary", use_container_width=True):
            if not user_issue.strip():
                st.warning("Please describe your issue.")
            else:
                with st.spinner("Looking up relevant policy articles..."):
                    answer, sources = get_answer(user_issue)

                st.session_state.last_question = user_issue
                st.session_state.last_answer = answer
                st.session_state.last_sources = sources

    if "last_answer" in st.session_state:
        st.divider()
        st.subheader("Suggested Guidance")
        st.write(st.session_state.last_answer)

        st.subheader("Relevant Articles")
        for src in st.session_state.last_sources:
            st.markdown(f"- **{src}**")

        st.divider()
        st.write("**Did this solve your issue?**")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Yes, this solved it", use_container_width=True):
                log_interaction(st.session_state.last_question, st.session_state.last_sources, True)
                st.success("Great! No ticket needed. Interaction logged.")
        with c2:
            if st.button("No, I still need help → Create ticket", use_container_width=True, type="primary"):
                log_interaction(st.session_state.last_question, st.session_state.last_sources, False)
                st.info("Ticket would be created here with the conversation history pre-filled into the Brief Summary.")

elif page == "Metrics":
    st.title("Metrics")
    total, resolved, rate = get_metrics()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Interactions", total)
    col2.metric("Resolved", resolved)
    col3.metric("Resolution Rate", f"{rate:.1f}%")

    st.subheader("Recent Interactions")
    conn = sqlite3.connect("data/interactions.db")
    try:
        import pandas as pd
        df = pd.read_sql_query(
            "SELECT timestamp, question, articles, resolved FROM interactions ORDER BY id DESC LIMIT 20",
            conn
        )
        if not df.empty:
            df["resolved"] = df["resolved"].map({1: "Yes", 0: "No"})
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No interactions yet.")
    except Exception:
        st.info("No interactions yet.")
    conn.close()

st.sidebar.markdown("---")
st.sidebar.caption("Sandbox demo • Uses Terms of Service + mock articles")


