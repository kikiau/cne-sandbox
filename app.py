import streamlit as st
import sqlite3
from datetime import datetime
from rag.retrieve import get_answer
from collections import Counter

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

def get_frequent_questions(limit=6):
    conn = sqlite3.connect("data/interactions.db")
    c = conn.cursor()
    c.execute("SELECT question FROM interactions")
    questions = [row[0].strip() for row in c.fetchall() if row[0] and row[0].strip()]
    conn.close()
    if not questions:
        return [
            "Guest reported a recording device that is not powered on",
            "What counts as a Reservation Issue?",
            "Host is refusing service because of guest's gender identity",
            "Neighbor reported a party and possible shots fired",
            "Review looks retaliatory — can it be removed?",
            "Multiple accounts connected to the same host"
        ]
    counter = Counter(questions)
    return [q for q, _ in counter.most_common(limit)]

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

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #FF5A5F 0%, #FF385C 100%);
        padding: 40px 20px 25px 20px;
        border-radius: 0 0 12px 12px;
        text-align: center;
        margin: -1rem -1rem 1.2rem -1rem;
    }
    .main-header h1 {
        color: white;
        font-size: 2.1rem;
        font-weight: 600;
        margin: 0;
    }
    .stTextArea textarea {
        min-height: 140px !important;
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

    frequent = get_frequent_questions()
    st.markdown("**Try a common question**")
    cols = st.columns(3)
    for i, q in enumerate(frequent):
        short = q[:55] + "..." if len(q) > 55 else q
        if cols[i % 3].button(short, key=f"sug_{i}", use_container_width=True):
            st.session_state.search_query = q
            st.session_state.run_search = True
            st.rerun()

    query = st.text_area(
        "Describe your issue",
        value=st.session_state.get("search_query", ""),
        placeholder="Describe the issue in detail (e.g. Guest reported an unplugged security camera in the living room...)",
        label_visibility="collapsed",
        height=140
    )

    if st.button("Get Self-Help", type="primary") or st.session_state.get("run_search"):
        if "run_search" in st.session_state:
            del st.session_state.run_search
        if query.strip():
            with st.spinner("Looking up relevant policies..."):
                answer, sources = get_answer(query)
            st.session_state.last_question = query
            st.session_state.last_answer = answer
            st.session_state.last_sources = sources
            st.session_state.search_query = query

if "last_answer" in st.session_state:
    st.divider()
    st.markdown("### Direction & Guidance")
    st.markdown(st.session_state.last_answer)

    if st.session_state.get("last_sources"):
        st.markdown("### Relevant Articles")
        for src in st.session_state.last_sources:
            st.markdown(f"- **{src}**")

    st.divider()
    st.markdown("**Did this resolve your issue?**")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Yes — resolved", use_container_width=True):
            log_interaction(st.session_state.last_question, st.session_state.last_sources, True)
            st.success("Logged as resolved. No ticket needed.")
            for key in ["last_answer", "last_question", "last_sources", "search_query"]:
                st.session_state.pop(key, None)
            st.rerun()
    with c2:
        if st.button("No — create ticket", type="primary", use_container_width=True):
            log_interaction(st.session_state.last_question, st.session_state.last_sources, False)
            st.info("Ticket would be created with this conversation pre-filled into the Brief Summary.")
            for key in ["last_answer", "last_question", "last_sources", "search_query"]:
                st.session_state.pop(key, None)
            st.rerun()


elif page == "Metrics":
    st.title("Metrics")
    total, resolved, rate = get_metrics()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Interactions", total)
    c2.metric("Resolved", resolved)
    c3.metric("Resolution Rate", f"{rate:.1f}%")

    st.subheader("Recent Interactions")
    conn = sqlite3.connect("data/interactions.db")
    try:
        import pandas as pd
        df = pd.read_sql_query(
            "SELECT timestamp, question, articles, resolved FROM interactions ORDER BY id DESC LIMIT 15",
            conn
        )
        if not df.empty:
            df["resolved"] = df["resolved"].map({1: "Yes", 0: "No"})
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No interactions yet.")
    except Exception:
        st.info("No interactions yet.")
    conn.close()

st.sidebar.markdown("---")
st.sidebar.caption("Sandbox demo for CNE interview • Uses Terms of Service + mock articles")

