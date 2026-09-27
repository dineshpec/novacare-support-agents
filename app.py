import asyncio

import streamlit as st

from support_bot.agents import SPECIALISTS, TRIAGE
from support_bot.config import load_settings
from support_bot.service import SupportService

# gpt-4o-mini and text-embedding-3-small list prices, USD per 1M tokens.
PRICE_IN, PRICE_OUT, PRICE_EMBED = 0.15, 0.60, 0.02

AGENT_STYLE = {name: (spec["icon"], spec["label"]) for name, spec in SPECIALISTS.items()}
AGENT_STYLE[TRIAGE] = ("🧭", "Support Desk")
SOURCE_TAG = {
    "web": ("🌐 Live web search", "tag-web"),
    "memory": ("🧠 From memory", "tag-memory"),
    "clarify": ("💬 Clarification", "tag-clarify"),
    "escalated": ("🙋 Escalated to human", "tag-escalated"),
    "error": ("⚠️ Error", "tag-error"),
    "human": ("🙋 Human handoff", "tag-escalated"),
}
SUGGESTIONS = [
    "What are the latest AI model releases this month?",
    "Which movies are releasing in theatres this week?",
    "What was the result of the latest India cricket match?",
    "What are the in-demand skills for data science jobs right now?",
]

st.set_page_config(page_title="NovaCare Support", page_icon="🛎️", layout="wide")

st.markdown(
    """
<style>
.stApp { background: linear-gradient(160deg, #0f172a 0%, #1e1b4b 55%, #312e81 100%); }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.6rem; max-width: 1000px; }
h1, h2, h3, p, li, label, .stMarkdown { color: #e2e8f0; }
.hero { background: linear-gradient(90deg, #6366f1, #a855f7 50%, #ec4899); border-radius: 20px;
        padding: 22px 28px; margin-bottom: 18px; box-shadow: 0 10px 30px rgba(99,102,241,.35); }
.hero h1 { color: #fff; margin: 0; font-size: 2rem; }
.hero p { color: #f5f3ff; margin: 4px 0 0 0; }
[data-testid="stSidebar"] { background: rgba(15,23,42,.92); border-right: 1px solid #334155; }
[data-testid="stChatMessage"] { background: rgba(30,41,59,.72); border: 1px solid #334155;
        border-radius: 16px; padding: 12px 16px; backdrop-filter: blur(6px); }
.badge { display:inline-block; padding:2px 10px; border-radius:999px; font-size:.75rem; font-weight:600;
         margin-right:6px; background:#312e81; color:#c7d2fe; border:1px solid #4f46e5; }
.tag-web { background:#064e3b; color:#6ee7b7; border-color:#10b981; }
.tag-memory { background:#4a044e; color:#f0abfc; border-color:#d946ef; }
.tag-clarify { background:#1e3a8a; color:#bfdbfe; border-color:#3b82f6; }
.tag-escalated { background:#7c2d12; color:#fed7aa; border-color:#f97316; }
.tag-error { background:#7f1d1d; color:#fecaca; border-color:#ef4444; }
.topic { background: rgba(99,102,241,.15); border:1px solid #4f46e5; border-radius:12px;
         padding:8px 12px; margin-bottom:8px; color:#e0e7ff; font-size:.9rem; }
.stButton>button { border-radius: 999px; border: 1px solid #6366f1; background: rgba(99,102,241,.15);
         color: #e0e7ff; }
.stButton>button:hover { background: #6366f1; color: #fff; border-color: #a5b4fc; }
[data-testid="stMetricValue"] { color: #a5b4fc; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def get_service() -> SupportService:
    return SupportService(load_settings())


settings = load_settings()
missing = settings.missing_keys()

state = st.session_state
state.setdefault("chats", {})
state.setdefault("usage", {"prompt": 0, "completion": 0, "embedding": 0, "last": 0})
state.setdefault("pending", None)

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## 🛎️ NovaCare")
    customer_id = st.text_input("Your name or customer ID", value=state.get("customer_id", ""), placeholder="e.g. alice01")
    state.customer_id = customer_id.strip()

    st.markdown("### Our specialists")
    for spec in SPECIALISTS.values():
        st.markdown(f"<div class='topic'>{spec['icon']} <b>{spec['label']}</b><br><small>{spec['focus']}</small></div>",
                    unsafe_allow_html=True)

    st.markdown("### ⚡ Token usage")
    u = state.usage
    cost = (u["prompt"] * PRICE_IN + u["completion"] * PRICE_OUT + u["embedding"] * PRICE_EMBED) / 1_000_000
    c1, c2 = st.columns(2)
    c1.metric("Last turn", f"{u['last']:,}")
    c2.metric("Session", f"{u['prompt'] + u['completion'] + u['embedding']:,}")
    st.caption(f"Prompt {u['prompt']:,} · Completion {u['completion']:,} · Embedding {u['embedding']:,} · ≈ ${cost:.4f}")

    if state.customer_id and not missing:
        saved = get_service().memory(state.customer_id).count()
        st.caption(f"🧠 {saved} answer(s) remembered for this customer")

    st.divider()
    talk_to_human = st.button("🙋 Talk to a human", use_container_width=True, disabled=not state.customer_id or bool(missing))
    if st.button("🧹 Clear chat", use_container_width=True):
        state.chats[state.customer_id] = []
        st.rerun()

# ---------- Header ----------
st.markdown(
    "<div class='hero'><h1>🛎️ NovaCare Customer Support</h1>"
    "<p>Live answers on AI, movies, sports and jobs, powered by AutoGen agents and real-time web search.</p></div>",
    unsafe_allow_html=True,
)

if missing:
    st.error(f"Missing {', '.join(missing)}. Copy `.env.example` to `.env`, add your keys and restart the app.")
    st.stop()
if not state.customer_id:
    st.info("👈 Enter your name or customer ID in the sidebar to start chatting. Your conversations are remembered per ID.")
    st.stop()

messages = state.chats.setdefault(state.customer_id, [])
service = get_service()


def render(msg: dict, index: int) -> None:
    if msg["role"] == "user":
        with st.chat_message("user", avatar="🧑"):
            st.markdown(msg["text"])
        return
    icon, label = AGENT_STYLE.get(msg["agent"], ("🛎️", "Support"))
    tag_text, tag_class = SOURCE_TAG.get(msg["source"], ("", ""))
    with st.chat_message("assistant", avatar=icon):
        extra = ""
        if msg["source"] == "memory" and msg.get("remembered_at"):
            extra = f"<span class='badge'>saved {msg['remembered_at'][:16].replace('T', ' ')}</span>"
        tokens = f"<span class='badge'>{msg['tokens']:,} tokens</span>" if msg.get("tokens") else ""
        st.markdown(f"<span class='badge'>{icon} {label}</span><span class='badge {tag_class}'>{tag_text}</span>"
                    f"{extra}{tokens}", unsafe_allow_html=True)
        st.markdown(msg["text"])
        if msg["source"] == "memory" and st.button("🔄 Refresh with web search", key=f"refresh-{index}"):
            state.pending = {"question": msg["question"], "force_web": True}
            st.rerun()


def ask(question: str, force_web: bool = False) -> None:
    history = [(m["role"], m["text"]) for m in messages if m["source"] not in ("error",)]
    messages.append({"role": "user", "text": question, "source": "user"})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(question)
    with st.chat_message("assistant", avatar="🧭"):
        with st.spinner("Checking memory and consulting our specialists…"):
            reply = asyncio.run(service.answer(state.customer_id, question, history=history, force_web=force_web))
    turn_tokens = reply.prompt_tokens + reply.completion_tokens + reply.embedding_tokens
    state.usage["prompt"] += reply.prompt_tokens
    state.usage["completion"] += reply.completion_tokens
    state.usage["embedding"] += reply.embedding_tokens
    state.usage["last"] = turn_tokens
    messages.append({
        "role": "assistant", "text": reply.text, "agent": reply.agent, "source": reply.source,
        "question": question, "tokens": turn_tokens, "remembered_at": reply.remembered_at,
    })
    st.rerun()


for i, msg in enumerate(messages):
    render(msg, i)

if talk_to_human:
    ticket = service.create_ticket(state.customer_id, "Customer requested a human via the Talk to a human button")
    messages.append({
        "role": "assistant", "agent": TRIAGE, "source": "human",
        "text": f"✅ I've created ticket **{ticket}**. A human support colleague will reach out to you shortly.",
    })
    st.rerun()

if not messages:
    st.markdown("#### ✨ Try asking")
    cols = st.columns(2)
    for i, suggestion in enumerate(SUGGESTIONS):
        if cols[i % 2].button(suggestion, key=f"suggest-{i}", use_container_width=True):
            state.pending = {"question": suggestion, "force_web": False}
            st.rerun()

if state.pending:
    pending, state.pending = state.pending, None
    ask(pending["question"], pending["force_web"])

if prompt := st.chat_input("Ask about AI, movies, sports or jobs…"):
    ask(prompt.strip())
