# ── Streamlit Cloud compatibility shims — DO NOT REMOVE ───────────────────────
# 1) ChromaDB needs sqlite3 >= 3.35.0; Streamlit Cloud's system sqlite3 is older.
# Swapping in pysqlite3-binary before any other import fixes this.
# __import__('pysqlite3')
# import sys
# sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass  # not installed (e.g. local Windows dev) — fine, system sqlite3 is used instead

# 2) Streamlit Cloud doesn't read .env files — secrets are set in the dashboard
#    (Settings → Secrets) and exposed via st.secrets. This bridges them into
#    os.environ so os.getenv("MISTRAL_API_KEY") in your core/ modules still works.
import streamlit as st
import os
for _k, _v in st.secrets.items():
    os.environ[_k] = str(_v)


import time
from dotenv import load_dotenv
from utils.audio_processor import process_input
from core.transcriber import transcribe_all
from core.summarizer import summarize, generate_title
from core.extractor import extract_action_items, extract_key_decisions, extract_questions
from core.rag_engine import build_rag_chain, ask_question

load_dotenv()

# ─── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Video Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Sora:wght@600;700;800&family=JetBrains+Mono:wght@300;400;500;600&display=swap');

/* ── Root Variables ── */
:root {
    --bg: #08090d;
    --bg-radial-1: rgba(99, 102, 241, 0.12);
    --bg-radial-2: rgba(45, 212, 191, 0.08);
    --surface: #12131a;
    --surface-2: #191b24;
    --surface-3: #20222e;
    --border: #262836;
    --border-soft: rgba(255,255,255,0.06);
    --accent: #6366f1;
    --accent-glow: #a5b4fc;
    --accent-2: #2dd4bf;
    --accent-3: #f472b6;
    --text: #eef0f7;
    --text-muted: #8b8da3;
    --text-faint: #565870;
    --success: #34d399;
    --warning: #fbbf24;
    --danger: #f87171;
    --radius: 16px;
    --radius-sm: 10px;
}

/* ── Global Reset ── */
html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}

.stApp {
    background:
        radial-gradient(circle at 12% 8%, var(--bg-radial-1) 0%, transparent 42%),
        radial-gradient(circle at 88% 92%, var(--bg-radial-2) 0%, transparent 45%),
        var(--bg) !important;
}

.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background-image:
        linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px);
    background-size: 44px 44px;
    pointer-events: none;
    z-index: 0;
}

.block-container {
    padding-top: 2.2rem !important;
    max-width: 1180px;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--surface) 0%, #0d0e14 100%) !important;
    border-right: 1px solid var(--border-soft) !important;
}

[data-testid="stSidebar"] * {
    color: var(--text) !important;
}

[data-testid="stSidebar"] .block-container {
    padding-top: 1.6rem !important;
}

/* ── Headings ── */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Sora', sans-serif !important;
    color: var(--text) !important;
}

/* ── Hero Title ── */
.hero-title {
    font-family: 'Sora', sans-serif;
    font-size: clamp(2.1rem, 4.6vw, 3.2rem);
    font-weight: 800;
    line-height: 1.08;
    margin: 0;
    letter-spacing: -0.02em;
    background: linear-gradient(120deg, #ffffff 0%, var(--accent-glow) 45%, var(--accent-2) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.hero-sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: var(--text-muted);
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-top: 0.55rem;
}

.sidebar-brand {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 0.2rem;
}

.sidebar-brand-icon {
    font-size: 1.7rem;
    filter: drop-shadow(0 0 10px rgba(99,102,241,0.5));
}

.sidebar-brand-text {
    font-family: 'Sora', sans-serif;
    font-weight: 800;
    font-size: 1.25rem;
    line-height: 1.15;
    background: linear-gradient(120deg, #ffffff 0%, var(--accent-glow) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

/* ── Section Label ── */
.section-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--text-faint);
    margin: 0.2rem 0 0.6rem 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.section-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, var(--border), transparent);
}

/* ── Cards ── */
.card {
    background: linear-gradient(155deg, var(--surface) 0%, var(--surface-2) 100%);
    border: 1px solid var(--border-soft);
    border-radius: var(--radius);
    padding: 1.4rem 1.5rem;
    margin-bottom: 1rem;
    position: relative;
    overflow: hidden;
    transition: border-color 0.25s ease, transform 0.25s ease, box-shadow 0.25s ease;
    box-shadow: 0 4px 24px rgba(0,0,0,0.25);
}

.card:hover {
    border-color: rgba(99,102,241,0.35);
    transform: translateY(-2px);
    box-shadow: 0 12px 32px rgba(99,102,241,0.12);
}

.card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: linear-gradient(180deg, var(--accent), var(--accent-2));
    opacity: 0.85;
}

.card-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 0.85rem;
    display: flex;
    align-items: center;
    gap: 0.55rem;
}

.card-content {
    font-size: 0.9rem;
    line-height: 1.75;
    color: var(--text);
}

/* ── Accent Badge ── */
.badge {
    display: inline-block;
    padding: 0.28rem 0.7rem;
    border-radius: 999px;
    font-size: 0.62rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-family: 'JetBrains Mono', monospace;
}

.badge-purple { background: rgba(99,102,241,0.15); color: var(--accent-glow); border: 1px solid rgba(99,102,241,0.3); }
.badge-cyan   { background: rgba(45,212,191,0.12); color: var(--accent-2);    border: 1px solid rgba(45,212,191,0.3); }
.badge-green  { background: rgba(52,211,153,0.12); color: var(--success);    border: 1px solid rgba(52,211,153,0.3); }
.badge-pink   { background: rgba(244,114,182,0.12); color: var(--accent-3);   border: 1px solid rgba(244,114,182,0.3); }

/* ── Input & Buttons ── */
.stTextInput > div > div > input,
.stSelectbox > div > div {
    background: var(--surface-3) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text) !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

.stTextInput > div > div > input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.18) !important;
}

.stButton > button {
    background: linear-gradient(135deg, var(--accent) 0%, #4338ca 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    font-family: 'Sora', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.04em !important;
    padding: 0.65rem 1.5rem !important;
    transition: all 0.2s ease !important;
    text-transform: uppercase !important;
    box-shadow: 0 4px 14px rgba(99,102,241,0.25) !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 28px rgba(99,102,241,0.4) !important;
}

.stButton > button:active {
    transform: translateY(0) !important;
}

/* Secondary button */
.stButton > button[kind="secondary"] {
    background: var(--surface-3) !important;
    border: 1px solid var(--border) !important;
    box-shadow: none !important;
}

.stButton > button[kind="secondary"]:hover {
    border-color: var(--danger) !important;
    box-shadow: 0 6px 18px rgba(248,113,113,0.18) !important;
}

/* ── Progress / Status ── */
.status-bar {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 0.65rem 0.9rem;
    background: var(--surface-3);
    border-radius: var(--radius-sm);
    margin: 0.35rem 0;
    border: 1px solid var(--border-soft);
    font-size: 0.78rem;
    transition: border-color 0.3s ease, background 0.3s ease;
}

.status-bar.is-done {
    border-color: rgba(52,211,153,0.25);
}

.status-bar.is-active {
    border-color: rgba(99,102,241,0.35);
    background: rgba(99,102,241,0.06);
}

.status-dot {
    width: 9px; height: 9px;
    border-radius: 50%;
    flex-shrink: 0;
}

.dot-active   { background: var(--accent-glow); box-shadow: 0 0 10px var(--accent-glow); animation: pulse 1.4s ease-in-out infinite; }
.dot-done     { background: var(--success); box-shadow: 0 0 6px rgba(52,211,153,0.5); }
.dot-pending  { background: var(--border); }

@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.45; transform: scale(0.85); }
}

/* ── Chat ── */
.chat-container {
    background: linear-gradient(155deg, var(--surface) 0%, var(--surface-2) 100%);
    border: 1px solid var(--border-soft);
    border-radius: var(--radius);
    padding: 1.4rem;
    max-height: 430px;
    overflow-y: auto;
    margin-bottom: 1rem;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
}

.chat-msg {
    margin-bottom: 1.1rem;
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
}

.chat-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}

.chat-bubble {
    display: inline-block;
    padding: 0.7rem 1.05rem;
    border-radius: 14px;
    font-size: 0.87rem;
    line-height: 1.6;
    max-width: 88%;
}

.user-label  { color: var(--accent-glow); }
.bot-label   { color: var(--accent-2); }

.user-bubble { background: rgba(99,102,241,0.14); border: 1px solid rgba(99,102,241,0.22); align-self: flex-end; border-bottom-right-radius: 4px; }
.bot-bubble  { background: rgba(45,212,191,0.08);  border: 1px solid rgba(45,212,191,0.18);  align-self: flex-start; border-bottom-left-radius: 4px; }

/* ── Divider ── */
hr {
    border: none !important;
    border-top: 1px solid var(--border-soft) !important;
    margin: 1.6rem 0 !important;
}

/* ── Transcript box ── */
.transcript-box {
    background: var(--surface-3);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 1.25rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    line-height: 1.85;
    max-height: 300px;
    overflow-y: auto;
    color: var(--text-muted);
    white-space: pre-wrap;
    word-break: break-word;
}

/* ── Title banner ── */
.title-banner {
    background: linear-gradient(155deg, var(--surface) 0%, var(--surface-2) 100%);
    border: 1px solid var(--border-soft);
    border-radius: var(--radius);
    padding: 1.4rem 1.6rem;
    margin-bottom: 1.1rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 4px 24px rgba(0,0,0,0.25);
}

.title-banner::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: linear-gradient(180deg, var(--accent-3), var(--accent));
}

.title-banner-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--text-faint);
    margin-bottom: 0.5rem;
}

.title-banner-text {
    font-family: 'Sora', sans-serif;
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.01em;
}

/* ── Empty state ── */
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 4.5rem 2rem;
    text-align: center;
}

.empty-state-icon {
    font-size: 3.6rem;
    margin-bottom: 1.2rem;
    filter: drop-shadow(0 0 24px rgba(99,102,241,0.35));
}

.empty-state-title {
    font-family: 'Sora', sans-serif;
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 0.6rem;
    letter-spacing: -0.01em;
}

.empty-state-desc {
    color: var(--text-muted);
    font-size: 0.87rem;
    max-width: 400px;
    line-height: 1.8;
}

.empty-state-badges {
    margin-top: 1.8rem;
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
    justify-content: center;
}

.chat-empty {
    text-align: center;
    padding: 2.4rem 1.5rem !important;
}

.chat-empty-icon { font-size: 2.2rem; margin-bottom: 0.6rem; opacity: 0.9; }

/* ── Stale Streamlit elements ── */
.stProgress > div > div > div { background: linear-gradient(90deg, var(--accent), var(--accent-2)) !important; }
.stSpinner > div { border-top-color: var(--accent) !important; }
[data-testid="stMarkdownContainer"] p { color: var(--text) !important; }
label { color: var(--text-muted) !important; font-size: 0.8rem !important; font-family: 'JetBrains Mono', monospace !important; }

/* expander */
[data-testid="stExpander"] {
    background: var(--surface) !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: var(--radius-sm) !important;
}

/* alerts */
.stAlert {
    border-radius: var(--radius-sm) !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

/* scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }
</style>
""", unsafe_allow_html=True)

# ─── Session State Init ──────────────────────────────────────────────────────────
for key, default in {
    "result": None,
    "chat_history": [],
    "processing": False,
    "pipeline_done": False,
    "pipeline_steps": {},
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ─── Helpers ────────────────────────────────────────────────────────────────────
def step_status(steps: dict, key: str) -> str:
    s = steps.get(key, "pending")
    if s == "active":  return "dot-active"
    if s == "done":    return "dot-done"
    return "dot-pending"

def render_step_bar(label: str, key: str, icon: str):
    state = st.session_state.pipeline_steps.get(key, "pending")
    dot_css = step_status(st.session_state.pipeline_steps, key)
    bar_css = "is-active" if state == "active" else ("is-done" if state == "done" else "")
    trailing = "✓" if state == "done" else ("···" if state == "active" else "")
    st.markdown(f"""
    <div class="status-bar {bar_css}">
        <div class="status-dot {dot_css}"></div>
        <span style="flex:1">{icon} {label}</span>
        <span style="color:var(--text-faint);font-size:0.7rem">{trailing}</span>
    </div>""", unsafe_allow_html=True)

# ─── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <span class="sidebar-brand-icon">🎬</span>
        <span class="sidebar-brand-text">AI Video<br>Assistant</span>
    </div>
    <div class="hero-sub" style="margin-top:0.3rem">Meeting Intelligence</div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    st.markdown('<div class="section-label">Input Source</div>', unsafe_allow_html=True)
    source = st.text_input("YouTube URL or File Path", placeholder="https://youtube.com/watch?v=... or /path/to/file.mp4", label_visibility="collapsed")

    st.markdown('<div class="section-label" style="margin-top:1rem">Language</div>', unsafe_allow_html=True)
    language = st.selectbox("Language", ["english", "hinglish"], index=0, label_visibility="collapsed")

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
    run_btn = st.button("⚡  Analyse", use_container_width=True)

    if st.session_state.pipeline_done:
        st.markdown("---")
        st.markdown('<div class="section-label">Pipeline Status</div>', unsafe_allow_html=True)
        for step, icon, label in [
            ("audio",      "🔊", "Audio Processing"),
            ("transcript", "📝", "Transcription"),
            ("title",      "🏷️", "Title Generation"),
            ("summary",    "📋", "Summarisation"),
            ("extract",    "🔍", "Extraction"),
            ("rag",        "🧠", "RAG Engine"),
        ]:
            render_step_bar(label, step, icon)

# ─── Main Area ──────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">AI Video Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Transcribe · Summarise · Chat with your meetings</div>', unsafe_allow_html=True)
st.markdown("---")

# ── Run Pipeline ────────────────────────────────────────────────────────────────
if run_btn:
    if not source.strip():
        st.error("Please enter a YouTube URL or file path.")
    else:
        st.session_state.pipeline_done = False
        st.session_state.result = None
        st.session_state.chat_history = []
        st.session_state.pipeline_steps = {}

        progress_placeholder = st.empty()

        def update_step(key, state):
            st.session_state.pipeline_steps[key] = state

        try:
            with progress_placeholder.container():
                st.info("⚙️ Pipeline running — see sidebar for live status…")

            update_step("audio", "active")
            chunks = process_input(source)
            update_step("audio", "done")

            update_step("transcript", "active")
            transcript = transcribe_all(chunks, language)
            update_step("transcript", "done")

            update_step("title", "active")
            title = generate_title(transcript)
            update_step("title", "done")

            update_step("summary", "active")
            summary = summarize(transcript)
            update_step("summary", "done")

            update_step("extract", "active")
            action_items  = extract_action_items(transcript)
            decisions     = extract_key_decisions(transcript)
            questions     = extract_questions(transcript)
            update_step("extract", "done")

            update_step("rag", "active")
            rag_chain = build_rag_chain(transcript)
            update_step("rag", "done")

            st.session_state.result = {
                "title": title,
                "transcript": transcript,
                "summary": summary,
                "action_items": action_items,
                "key_decisions": decisions,
                "open_questions": questions,
                "rag_chain": rag_chain,
            }
            st.session_state.pipeline_done = True
            progress_placeholder.success("✅ Analysis complete!")
            time.sleep(0.5)
            progress_placeholder.empty()
            st.rerun()

        except Exception as e:
            for k in ["audio","transcript","title","summary","extract","rag"]:
                if st.session_state.pipeline_steps.get(k) == "active":
                    st.session_state.pipeline_steps[k] = "pending"
            progress_placeholder.error(f"❌ Error: {e}")

# ── Results ──────────────────────────────────────────────────────────────────────
if st.session_state.result:
    r = st.session_state.result

    # Title banner
    st.markdown(f"""
    <div class="title-banner">
        <div class="title-banner-label">📌 Session Title</div>
        <div class="title-banner-text">{r['title']}</div>
    </div>""", unsafe_allow_html=True)

    # Top row: summary + transcript
    col1, col2 = st.columns([3, 2], gap="medium")

    with col1:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">📋 Summary</div>
            <div class="card-content">{r['summary']}</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        with st.expander("📝 Full Transcript", expanded=False):
            st.markdown(f'<div class="transcript-box">{r["transcript"]}</div>', unsafe_allow_html=True)

    # Second row: action items | decisions | questions
    c1, c2, c3 = st.columns(3, gap="medium")

    with c1:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">✅ Action Items</div>
            <div class="card-content">{r['action_items']}</div>
        </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">🔑 Key Decisions</div>
            <div class="card-content">{r['key_decisions']}</div>
        </div>""", unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">❓ Open Questions</div>
            <div class="card-content">{r['open_questions']}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── RAG Chat ──────────────────────────────────────────────────────────────
    st.markdown('<div class="section-label" style="font-size:0.9rem;color:var(--text);text-transform:none;letter-spacing:0;font-family:\'Sora\',sans-serif;font-weight:700">💬 Chat with your Meeting</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

    # Chat history display
    if st.session_state.chat_history:
        chat_html = '<div class="chat-container">'
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                chat_html += f"""
                <div class="chat-msg" style="align-items:flex-end">
                    <span class="chat-label user-label">You</span>
                    <div class="chat-bubble user-bubble">{msg['content']}</div>
                </div>"""
            else:
                chat_html += f"""
                <div class="chat-msg" style="align-items:flex-start">
                    <span class="chat-label bot-label">🤖 Assistant</span>
                    <div class="chat-bubble bot-bubble">{msg['content']}</div>
                </div>"""
        chat_html += '</div>'
        st.markdown(chat_html, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="card chat-empty">
            <div class="chat-empty-icon">💬</div>
            <div style="color:var(--text-muted);font-size:0.85rem">Ask anything about your meeting transcript</div>
        </div>""", unsafe_allow_html=True)

    # Chat input
    chat_col1, chat_col2 = st.columns([5, 1], gap="small")
    with chat_col1:
        user_input = st.text_input("Your question", placeholder="What were the main decisions made?", label_visibility="collapsed")
    with chat_col2:
        send_btn = st.button("Send →", use_container_width=True)

    if send_btn and user_input.strip():
        with st.spinner("Thinking…"):
            answer = ask_question(r["rag_chain"], user_input.strip())
        st.session_state.chat_history.append({"role": "user",      "content": user_input.strip()})
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        st.rerun()

    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat", type="secondary"):
            st.session_state.chat_history = []
            st.rerun()

else:
    # Empty state
    st.markdown("""
    <div class="empty-state">
        <div class="empty-state-icon">🎬</div>
        <div class="empty-state-title">Ready to Analyse</div>
        <div class="empty-state-desc">
            Paste a YouTube URL or local file path in the sidebar, choose your language, and hit <strong>Analyse</strong> to get started.
        </div>
        <div class="empty-state-badges">
            <span class="badge badge-purple">Transcription</span>
            <span class="badge badge-cyan">Summarisation</span>
            <span class="badge badge-green">RAG Chat</span>
            <span class="badge badge-pink">Action Items</span>
        </div>
    </div>""", unsafe_allow_html=True)


# import streamlit as st
# import time
# from dotenv import load_dotenv
# from utils.audio_processor import process_input
# from core.transcriber import transcribe_all
# from core.summarizer import summarize, generate_title
# from core.extractor import extract_action_items, extract_key_decisions, extract_questions
# from core.rag_engine import build_rag_chain, ask_question

# load_dotenv()

# # ─── Page Config ────────────────────────────────────────────────────────────────
# st.set_page_config(
#     page_title="AI Video Assistant",
#     page_icon="🎬",
#     layout="wide",
#     initial_sidebar_state="expanded",
# )

# # ─── Custom CSS ─────────────────────────────────────────────────────────────────
# st.markdown("""
# <style>
# @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Sora:wght@600;700;800&family=JetBrains+Mono:wght@300;400;500;600&display=swap');

# /* ── Root Variables ── */
# :root {
#     --bg: #08090d;
#     --bg-radial-1: rgba(99, 102, 241, 0.12);
#     --bg-radial-2: rgba(45, 212, 191, 0.08);
#     --surface: #12131a;
#     --surface-2: #191b24;
#     --surface-3: #20222e;
#     --border: #262836;
#     --border-soft: rgba(255,255,255,0.06);
#     --accent: #6366f1;
#     --accent-glow: #a5b4fc;
#     --accent-2: #2dd4bf;
#     --accent-3: #f472b6;
#     --text: #eef0f7;
#     --text-muted: #8b8da3;
#     --text-faint: #565870;
#     --success: #34d399;
#     --warning: #fbbf24;
#     --danger: #f87171;
#     --radius: 16px;
#     --radius-sm: 10px;
# }

# /* ── Global Reset ── */
# html, body, [class*="css"] {
#     font-family: 'Space Grotesk', sans-serif;
#     background-color: var(--bg) !important;
#     color: var(--text) !important;
# }

# .stApp {
#     background:
#         radial-gradient(circle at 12% 8%, var(--bg-radial-1) 0%, transparent 42%),
#         radial-gradient(circle at 88% 92%, var(--bg-radial-2) 0%, transparent 45%),
#         var(--bg) !important;
# }

# .stApp::before {
#     content: '';
#     position: fixed;
#     top: 0; left: 0;
#     width: 100%; height: 100%;
#     background-image:
#         linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px),
#         linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px);
#     background-size: 44px 44px;
#     pointer-events: none;
#     z-index: 0;
# }

# .block-container {
#     padding-top: 2.2rem !important;
#     max-width: 1180px;
# }

# /* ── Sidebar ── */
# [data-testid="stSidebar"] {
#     background: linear-gradient(180deg, var(--surface) 0%, #0d0e14 100%) !important;
#     border-right: 1px solid var(--border-soft) !important;
# }

# [data-testid="stSidebar"] * {
#     color: var(--text) !important;
# }

# [data-testid="stSidebar"] .block-container {
#     padding-top: 1.6rem !important;
# }

# /* ── Headings ── */
# h1, h2, h3, h4, h5, h6 {
#     font-family: 'Sora', sans-serif !important;
#     color: var(--text) !important;
# }

# /* ── Hero Title ── */
# .hero-title {
#     font-family: 'Sora', sans-serif;
#     font-size: clamp(2.1rem, 4.6vw, 3.2rem);
#     font-weight: 800;
#     line-height: 1.08;
#     margin: 0;
#     letter-spacing: -0.02em;
#     background: linear-gradient(120deg, #ffffff 0%, var(--accent-glow) 45%, var(--accent-2) 100%);
#     -webkit-background-clip: text;
#     -webkit-text-fill-color: transparent;
#     background-clip: text;
# }

# .hero-sub {
#     font-family: 'JetBrains Mono', monospace;
#     font-size: 0.78rem;
#     color: var(--text-muted);
#     letter-spacing: 0.18em;
#     text-transform: uppercase;
#     margin-top: 0.55rem;
# }

# .sidebar-brand {
#     display: flex;
#     align-items: center;
#     gap: 0.6rem;
#     margin-bottom: 0.2rem;
# }

# .sidebar-brand-icon {
#     font-size: 1.7rem;
#     filter: drop-shadow(0 0 10px rgba(99,102,241,0.5));
# }

# .sidebar-brand-text {
#     font-family: 'Sora', sans-serif;
#     font-weight: 800;
#     font-size: 1.25rem;
#     line-height: 1.15;
#     background: linear-gradient(120deg, #ffffff 0%, var(--accent-glow) 100%);
#     -webkit-background-clip: text;
#     -webkit-text-fill-color: transparent;
#     background-clip: text;
# }

# /* ── Section Label ── */
# .section-label {
#     font-family: 'JetBrains Mono', monospace;
#     font-size: 0.68rem;
#     font-weight: 600;
#     letter-spacing: 0.16em;
#     text-transform: uppercase;
#     color: var(--text-faint);
#     margin: 0.2rem 0 0.6rem 0;
#     display: flex;
#     align-items: center;
#     gap: 0.5rem;
# }

# .section-label::after {
#     content: '';
#     flex: 1;
#     height: 1px;
#     background: linear-gradient(90deg, var(--border), transparent);
# }

# /* ── Cards ── */
# .card {
#     background: linear-gradient(155deg, var(--surface) 0%, var(--surface-2) 100%);
#     border: 1px solid var(--border-soft);
#     border-radius: var(--radius);
#     padding: 1.4rem 1.5rem;
#     margin-bottom: 1rem;
#     position: relative;
#     overflow: hidden;
#     transition: border-color 0.25s ease, transform 0.25s ease, box-shadow 0.25s ease;
#     box-shadow: 0 4px 24px rgba(0,0,0,0.25);
# }

# .card:hover {
#     border-color: rgba(99,102,241,0.35);
#     transform: translateY(-2px);
#     box-shadow: 0 12px 32px rgba(99,102,241,0.12);
# }

# .card::before {
#     content: '';
#     position: absolute;
#     top: 0; left: 0;
#     width: 3px; height: 100%;
#     background: linear-gradient(180deg, var(--accent), var(--accent-2));
#     opacity: 0.85;
# }

# .card-title {
#     font-family: 'JetBrains Mono', monospace;
#     font-size: 0.68rem;
#     font-weight: 600;
#     letter-spacing: 0.14em;
#     text-transform: uppercase;
#     color: var(--text-muted);
#     margin-bottom: 0.85rem;
#     display: flex;
#     align-items: center;
#     gap: 0.55rem;
# }

# .card-content {
#     font-size: 0.9rem;
#     line-height: 1.75;
#     color: var(--text);
# }

# /* ── Accent Badge ── */
# .badge {
#     display: inline-block;
#     padding: 0.28rem 0.7rem;
#     border-radius: 999px;
#     font-size: 0.62rem;
#     font-weight: 600;
#     letter-spacing: 0.1em;
#     text-transform: uppercase;
#     font-family: 'JetBrains Mono', monospace;
# }

# .badge-purple { background: rgba(99,102,241,0.15); color: var(--accent-glow); border: 1px solid rgba(99,102,241,0.3); }
# .badge-cyan   { background: rgba(45,212,191,0.12); color: var(--accent-2);    border: 1px solid rgba(45,212,191,0.3); }
# .badge-green  { background: rgba(52,211,153,0.12); color: var(--success);    border: 1px solid rgba(52,211,153,0.3); }
# .badge-pink   { background: rgba(244,114,182,0.12); color: var(--accent-3);   border: 1px solid rgba(244,114,182,0.3); }

# /* ── Input & Buttons ── */
# .stTextInput > div > div > input,
# .stSelectbox > div > div {
#     background: var(--surface-3) !important;
#     border: 1px solid var(--border) !important;
#     border-radius: var(--radius-sm) !important;
#     color: var(--text) !important;
#     font-family: 'Space Grotesk', sans-serif !important;
# }

# .stTextInput > div > div > input:focus {
#     border-color: var(--accent) !important;
#     box-shadow: 0 0 0 3px rgba(99,102,241,0.18) !important;
# }

# .stButton > button {
#     background: linear-gradient(135deg, var(--accent) 0%, #4338ca 100%) !important;
#     color: white !important;
#     border: none !important;
#     border-radius: var(--radius-sm) !important;
#     font-family: 'Sora', sans-serif !important;
#     font-weight: 700 !important;
#     font-size: 0.85rem !important;
#     letter-spacing: 0.04em !important;
#     padding: 0.65rem 1.5rem !important;
#     transition: all 0.2s ease !important;
#     text-transform: uppercase !important;
#     box-shadow: 0 4px 14px rgba(99,102,241,0.25) !important;
# }

# .stButton > button:hover {
#     transform: translateY(-2px) !important;
#     box-shadow: 0 10px 28px rgba(99,102,241,0.4) !important;
# }

# .stButton > button:active {
#     transform: translateY(0) !important;
# }

# /* Secondary button */
# .stButton > button[kind="secondary"] {
#     background: var(--surface-3) !important;
#     border: 1px solid var(--border) !important;
#     box-shadow: none !important;
# }

# .stButton > button[kind="secondary"]:hover {
#     border-color: var(--danger) !important;
#     box-shadow: 0 6px 18px rgba(248,113,113,0.18) !important;
# }

# /* ── Progress / Status ── */
# .status-bar {
#     display: flex;
#     align-items: center;
#     gap: 0.7rem;
#     padding: 0.65rem 0.9rem;
#     background: var(--surface-3);
#     border-radius: var(--radius-sm);
#     margin: 0.35rem 0;
#     border: 1px solid var(--border-soft);
#     font-size: 0.78rem;
#     transition: border-color 0.3s ease, background 0.3s ease;
# }

# .status-bar.is-done {
#     border-color: rgba(52,211,153,0.25);
# }

# .status-bar.is-active {
#     border-color: rgba(99,102,241,0.35);
#     background: rgba(99,102,241,0.06);
# }

# .status-dot {
#     width: 9px; height: 9px;
#     border-radius: 50%;
#     flex-shrink: 0;
# }

# .dot-active   { background: var(--accent-glow); box-shadow: 0 0 10px var(--accent-glow); animation: pulse 1.4s ease-in-out infinite; }
# .dot-done     { background: var(--success); box-shadow: 0 0 6px rgba(52,211,153,0.5); }
# .dot-pending  { background: var(--border); }

# @keyframes pulse {
#     0%, 100% { opacity: 1; transform: scale(1); }
#     50%       { opacity: 0.45; transform: scale(0.85); }
# }

# /* ── Chat ── */
# .chat-container {
#     background: linear-gradient(155deg, var(--surface) 0%, var(--surface-2) 100%);
#     border: 1px solid var(--border-soft);
#     border-radius: var(--radius);
#     padding: 1.4rem;
#     max-height: 430px;
#     overflow-y: auto;
#     margin-bottom: 1rem;
#     box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
# }

# .chat-msg {
#     margin-bottom: 1.1rem;
#     display: flex;
#     flex-direction: column;
#     gap: 0.3rem;
# }

# .chat-label {
#     font-family: 'JetBrains Mono', monospace;
#     font-size: 0.62rem;
#     font-weight: 600;
#     letter-spacing: 0.14em;
#     text-transform: uppercase;
# }

# .chat-bubble {
#     display: inline-block;
#     padding: 0.7rem 1.05rem;
#     border-radius: 14px;
#     font-size: 0.87rem;
#     line-height: 1.6;
#     max-width: 88%;
# }

# .user-label  { color: var(--accent-glow); }
# .bot-label   { color: var(--accent-2); }

# .user-bubble { background: rgba(99,102,241,0.14); border: 1px solid rgba(99,102,241,0.22); align-self: flex-end; border-bottom-right-radius: 4px; }
# .bot-bubble  { background: rgba(45,212,191,0.08);  border: 1px solid rgba(45,212,191,0.18);  align-self: flex-start; border-bottom-left-radius: 4px; }

# /* ── Divider ── */
# hr {
#     border: none !important;
#     border-top: 1px solid var(--border-soft) !important;
#     margin: 1.6rem 0 !important;
# }

# /* ── Transcript box ── */
# .transcript-box {
#     background: var(--surface-3);
#     border: 1px solid var(--border);
#     border-radius: var(--radius-sm);
#     padding: 1.25rem;
#     font-family: 'JetBrains Mono', monospace;
#     font-size: 0.8rem;
#     line-height: 1.85;
#     max-height: 300px;
#     overflow-y: auto;
#     color: var(--text-muted);
#     white-space: pre-wrap;
#     word-break: break-word;
# }

# /* ── Title banner ── */
# .title-banner {
#     background: linear-gradient(155deg, var(--surface) 0%, var(--surface-2) 100%);
#     border: 1px solid var(--border-soft);
#     border-radius: var(--radius);
#     padding: 1.4rem 1.6rem;
#     margin-bottom: 1.1rem;
#     position: relative;
#     overflow: hidden;
#     box-shadow: 0 4px 24px rgba(0,0,0,0.25);
# }

# .title-banner::before {
#     content: '';
#     position: absolute;
#     top: 0; left: 0;
#     width: 3px; height: 100%;
#     background: linear-gradient(180deg, var(--accent-3), var(--accent));
# }

# .title-banner-label {
#     font-family: 'JetBrains Mono', monospace;
#     font-size: 0.65rem;
#     font-weight: 600;
#     letter-spacing: 0.16em;
#     text-transform: uppercase;
#     color: var(--text-faint);
#     margin-bottom: 0.5rem;
# }

# .title-banner-text {
#     font-family: 'Sora', sans-serif;
#     font-size: 1.5rem;
#     font-weight: 700;
#     color: var(--text);
#     letter-spacing: -0.01em;
# }

# /* ── Empty state ── */
# .empty-state {
#     display: flex;
#     flex-direction: column;
#     align-items: center;
#     justify-content: center;
#     padding: 4.5rem 2rem;
#     text-align: center;
# }

# .empty-state-icon {
#     font-size: 3.6rem;
#     margin-bottom: 1.2rem;
#     filter: drop-shadow(0 0 24px rgba(99,102,241,0.35));
# }

# .empty-state-title {
#     font-family: 'Sora', sans-serif;
#     font-size: 1.5rem;
#     font-weight: 700;
#     color: var(--text);
#     margin-bottom: 0.6rem;
#     letter-spacing: -0.01em;
# }

# .empty-state-desc {
#     color: var(--text-muted);
#     font-size: 0.87rem;
#     max-width: 400px;
#     line-height: 1.8;
# }

# .empty-state-badges {
#     margin-top: 1.8rem;
#     display: flex;
#     gap: 0.6rem;
#     flex-wrap: wrap;
#     justify-content: center;
# }

# .chat-empty {
#     text-align: center;
#     padding: 2.4rem 1.5rem !important;
# }

# .chat-empty-icon { font-size: 2.2rem; margin-bottom: 0.6rem; opacity: 0.9; }

# /* ── Stale Streamlit elements ── */
# .stProgress > div > div > div { background: linear-gradient(90deg, var(--accent), var(--accent-2)) !important; }
# .stSpinner > div { border-top-color: var(--accent) !important; }
# [data-testid="stMarkdownContainer"] p { color: var(--text) !important; }
# label { color: var(--text-muted) !important; font-size: 0.8rem !important; font-family: 'JetBrains Mono', monospace !important; }

# /* expander */
# [data-testid="stExpander"] {
#     background: var(--surface) !important;
#     border: 1px solid var(--border-soft) !important;
#     border-radius: var(--radius-sm) !important;
# }

# /* alerts */
# .stAlert {
#     border-radius: var(--radius-sm) !important;
#     font-family: 'Space Grotesk', sans-serif !important;
# }

# /* scrollbar */
# ::-webkit-scrollbar { width: 6px; height: 6px; }
# ::-webkit-scrollbar-track { background: transparent; }
# ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
# ::-webkit-scrollbar-thumb:hover { background: var(--accent); }
# </style>
# """, unsafe_allow_html=True)

# # ─── Session State Init ──────────────────────────────────────────────────────────
# for key, default in {
#     "result": None,
#     "chat_history": [],
#     "processing": False,
#     "pipeline_done": False,
#     "pipeline_steps": {},
# }.items():
#     if key not in st.session_state:
#         st.session_state[key] = default

# # ─── Helpers ────────────────────────────────────────────────────────────────────
# def step_status(steps: dict, key: str) -> str:
#     s = steps.get(key, "pending")
#     if s == "active":  return "dot-active"
#     if s == "done":    return "dot-done"
#     return "dot-pending"

# def render_step_bar(label: str, key: str, icon: str):
#     state = st.session_state.pipeline_steps.get(key, "pending")
#     dot_css = step_status(st.session_state.pipeline_steps, key)
#     bar_css = "is-active" if state == "active" else ("is-done" if state == "done" else "")
#     trailing = "✓" if state == "done" else ("···" if state == "active" else "")
#     st.markdown(f"""
#     <div class="status-bar {bar_css}">
#         <div class="status-dot {dot_css}"></div>
#         <span style="flex:1">{icon} {label}</span>
#         <span style="color:var(--text-faint);font-size:0.7rem">{trailing}</span>
#     </div>""", unsafe_allow_html=True)

# # ─── Sidebar ────────────────────────────────────────────────────────────────────
# with st.sidebar:
#     st.markdown("""
#     <div class="sidebar-brand">
#         <span class="sidebar-brand-icon">🎬</span>
#         <span class="sidebar-brand-text">AI Video<br>Assistant</span>
#     </div>
#     <div class="hero-sub" style="margin-top:0.3rem">Meeting Intelligence</div>
#     """, unsafe_allow_html=True)
#     st.markdown("---")

#     st.markdown('<div class="section-label">Input Source</div>', unsafe_allow_html=True)
#     source = st.text_input("YouTube URL or File Path", placeholder="https://youtube.com/watch?v=... or /path/to/file.mp4", label_visibility="collapsed")

#     st.markdown('<div class="section-label" style="margin-top:1rem">Language</div>', unsafe_allow_html=True)
#     language = st.selectbox("Language", ["english", "hinglish"], index=0, label_visibility="collapsed")

#     st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
#     run_btn = st.button("⚡  Analyse", use_container_width=True)

#     if st.session_state.pipeline_done:
#         st.markdown("---")
#         st.markdown('<div class="section-label">Pipeline Status</div>', unsafe_allow_html=True)
#         for step, icon, label in [
#             ("audio",      "🔊", "Audio Processing"),
#             ("transcript", "📝", "Transcription"),
#             ("title",      "🏷️", "Title Generation"),
#             ("summary",    "📋", "Summarisation"),
#             ("extract",    "🔍", "Extraction"),
#             ("rag",        "🧠", "RAG Engine"),
#         ]:
#             render_step_bar(label, step, icon)

# # ─── Main Area ──────────────────────────────────────────────────────────────────
# st.markdown('<div class="hero-title">AI Video Assistant</div>', unsafe_allow_html=True)
# st.markdown('<div class="hero-sub">Transcribe · Summarise · Chat with your meetings</div>', unsafe_allow_html=True)
# st.markdown("---")

# # ── Run Pipeline ────────────────────────────────────────────────────────────────
# if run_btn:
#     if not source.strip():
#         st.error("Please enter a YouTube URL or file path.")
#     else:
#         st.session_state.pipeline_done = False
#         st.session_state.result = None
#         st.session_state.chat_history = []
#         st.session_state.pipeline_steps = {}

#         progress_placeholder = st.empty()

#         def update_step(key, state):
#             st.session_state.pipeline_steps[key] = state

#         try:
#             with progress_placeholder.container():
#                 st.info("⚙️ Pipeline running — see sidebar for live status…")

#             update_step("audio", "active")
#             chunks = process_input(source)
#             update_step("audio", "done")

#             update_step("transcript", "active")
#             transcript = transcribe_all(chunks, language)
#             update_step("transcript", "done")

#             update_step("title", "active")
#             title = generate_title(transcript)
#             update_step("title", "done")

#             update_step("summary", "active")
#             summary = summarize(transcript)
#             update_step("summary", "done")

#             update_step("extract", "active")
#             action_items  = extract_action_items(transcript)
#             decisions     = extract_key_decisions(transcript)
#             questions     = extract_questions(transcript)
#             update_step("extract", "done")

#             update_step("rag", "active")
#             rag_chain = build_rag_chain(transcript)
#             update_step("rag", "done")

#             st.session_state.result = {
#                 "title": title,
#                 "transcript": transcript,
#                 "summary": summary,
#                 "action_items": action_items,
#                 "key_decisions": decisions,
#                 "open_questions": questions,
#                 "rag_chain": rag_chain,
#             }
#             st.session_state.pipeline_done = True
#             progress_placeholder.success("✅ Analysis complete!")
#             time.sleep(0.5)
#             progress_placeholder.empty()
#             st.rerun()

#         except Exception as e:
#             for k in ["audio","transcript","title","summary","extract","rag"]:
#                 if st.session_state.pipeline_steps.get(k) == "active":
#                     st.session_state.pipeline_steps[k] = "pending"
#             progress_placeholder.error(f"❌ Error: {e}")

# # ── Results ──────────────────────────────────────────────────────────────────────
# if st.session_state.result:
#     r = st.session_state.result

#     # Title banner
#     st.markdown(f"""
#     <div class="title-banner">
#         <div class="title-banner-label">📌 Session Title</div>
#         <div class="title-banner-text">{r['title']}</div>
#     </div>""", unsafe_allow_html=True)

#     # Top row: summary + transcript
#     col1, col2 = st.columns([3, 2], gap="medium")

#     with col1:
#         st.markdown(f"""
#         <div class="card">
#             <div class="card-title">📋 Summary</div>
#             <div class="card-content">{r['summary']}</div>
#         </div>""", unsafe_allow_html=True)

#     with col2:
#         with st.expander("📝 Full Transcript", expanded=False):
#             st.markdown(f'<div class="transcript-box">{r["transcript"]}</div>', unsafe_allow_html=True)

#     # Second row: action items | decisions | questions
#     c1, c2, c3 = st.columns(3, gap="medium")

#     with c1:
#         st.markdown(f"""
#         <div class="card">
#             <div class="card-title">✅ Action Items</div>
#             <div class="card-content">{r['action_items']}</div>
#         </div>""", unsafe_allow_html=True)

#     with c2:
#         st.markdown(f"""
#         <div class="card">
#             <div class="card-title">🔑 Key Decisions</div>
#             <div class="card-content">{r['key_decisions']}</div>
#         </div>""", unsafe_allow_html=True)

#     with c3:
#         st.markdown(f"""
#         <div class="card">
#             <div class="card-title">❓ Open Questions</div>
#             <div class="card-content">{r['open_questions']}</div>
#         </div>""", unsafe_allow_html=True)

#     st.markdown("---")

#     # ── RAG Chat ──────────────────────────────────────────────────────────────
#     st.markdown('<div class="section-label" style="font-size:0.9rem;color:var(--text);text-transform:none;letter-spacing:0;font-family:\'Sora\',sans-serif;font-weight:700">💬 Chat with your Meeting</div>', unsafe_allow_html=True)
#     st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

#     # Chat history display
#     if st.session_state.chat_history:
#         chat_html = '<div class="chat-container">'
#         for msg in st.session_state.chat_history:
#             if msg["role"] == "user":
#                 chat_html += f"""
#                 <div class="chat-msg" style="align-items:flex-end">
#                     <span class="chat-label user-label">You</span>
#                     <div class="chat-bubble user-bubble">{msg['content']}</div>
#                 </div>"""
#             else:
#                 chat_html += f"""
#                 <div class="chat-msg" style="align-items:flex-start">
#                     <span class="chat-label bot-label">🤖 Assistant</span>
#                     <div class="chat-bubble bot-bubble">{msg['content']}</div>
#                 </div>"""
#         chat_html += '</div>'
#         st.markdown(chat_html, unsafe_allow_html=True)
#     else:
#         st.markdown("""
#         <div class="card chat-empty">
#             <div class="chat-empty-icon">💬</div>
#             <div style="color:var(--text-muted);font-size:0.85rem">Ask anything about your meeting transcript</div>
#         </div>""", unsafe_allow_html=True)

#     # Chat input
#     chat_col1, chat_col2 = st.columns([5, 1], gap="small")
#     with chat_col1:
#         user_input = st.text_input("Your question", placeholder="What were the main decisions made?", label_visibility="collapsed")
#     with chat_col2:
#         send_btn = st.button("Send →", use_container_width=True)

#     if send_btn and user_input.strip():
#         with st.spinner("Thinking…"):
#             answer = ask_question(r["rag_chain"], user_input.strip())
#         st.session_state.chat_history.append({"role": "user",      "content": user_input.strip()})
#         st.session_state.chat_history.append({"role": "assistant", "content": answer})
#         st.rerun()

#     if st.session_state.chat_history:
#         if st.button("🗑️ Clear Chat", type="secondary"):
#             st.session_state.chat_history = []
#             st.rerun()

# else:
#     # Empty state
#     st.markdown("""
#     <div class="empty-state">
#         <div class="empty-state-icon">🎬</div>
#         <div class="empty-state-title">Ready to Analyse</div>
#         <div class="empty-state-desc">
#             Paste a YouTube URL or local file path in the sidebar, choose your language, and hit <strong>Analyse</strong> to get started.
#         </div>
#         <div class="empty-state-badges">
#             <span class="badge badge-purple">Transcription</span>
#             <span class="badge badge-cyan">Summarisation</span>
#             <span class="badge badge-green">RAG Chat</span>
#             <span class="badge badge-pink">Action Items</span>
#         </div>
#     </div>""", unsafe_allow_html=True)
