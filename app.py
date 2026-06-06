import os
import re
from datetime import datetime

import anthropic
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-6"
SEARCH_TOOL = [{"type": "web_search_20250305", "name": "web_search"}]

SENTIMENT_COLORS = {
    "Optimistic": ("#DCFCE7", "#16A34A", "#14532D"),
    "Mixed":      ("#FEF9C3", "#CA8A04", "#713F12"),
    "Cautious":   ("#FFEDD5", "#EA580C", "#7C2D12"),
    "Uncertain":  ("#FEE2E2", "#DC2626", "#7F1D1D"),
}


@st.cache_resource
def get_client() -> anthropic.Anthropic:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        st.error("ANTHROPIC_API_KEY environment variable is not set.")
        st.stop()
    return anthropic.Anthropic(api_key=key)


def run_research(topic: str, on_step=None) -> str:
    client = get_client()

    if on_step:
        on_step("🔍 Searching the web for recent developments…")

    prompt = f"""You are a trend intelligence analyst. Search the web for the latest developments in: **{topic}**

Write a structured trend brief using these exact section headers:

**TOP STORY**

1–2 sentences on the single most significant development. Cite as [Publication](url). Bold 2–3 key terms.

**NARRATIVE THREADS**

• **Thread 1 name**: 1 sentence. Cite as [Source](url). Bold key terms.

• **Thread 2 name**: 1 sentence. Cite as [Source](url). Bold key terms.

• **Thread 3 name**: 1 sentence. Cite as [Source](url). Bold key terms.

**SENTIMENT SNAPSHOT**

1–2 sentences on the overall mood. Bold 1 key term. Cite as [Source](url).
Score: [Optimistic | Mixed | Cautious | Uncertain]

**EMERGING SIGNAL**

1–2 sentences on one early signal worth watching. Bold the signal name. Cite as [Source](url) if available.

**SO WHAT**

1–2 sentences on the key takeaway for a practitioner. Bold the critical action. Link a relevant resource as [Resource](url) if available.

**LEARN MORE**

2–3 resources for going deeper. Format each as:
• [Title](https://actual-url.com) — 5–7 words on what it covers.

**TREND SIGNALS**

4–6 short trend labels (2–5 words each), comma-separated.

**RELATED TOPICS**

4–5 related topics (2–5 words each) to explore next, comma-separated.

Formatting rules:
- Use real, clickable URLs in every section: [Name](https://actual-url.com)
- Bold key terms with **double asterisks** (2–4 word phrases only)
- Keep every section tight — no filler sentences
- Never use # or ## markdown headings — use only the **SECTION NAME** format above"""

    messages = [{"role": "user", "content": prompt}]

    text = ""
    for i in range(5):
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            tools=SEARCH_TOOL,
            messages=messages,
        )

        text = "".join(b.text for b in response.content if b.type == "text")

        if response.stop_reason == "end_turn":
            return text

        if response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            if on_step:
                if i == 0:
                    on_step("📊 Analyzing sources…")
                elif i == 1:
                    on_step("✍️ Synthesizing trend brief…")
        else:
            return text

    return text


def parse_section(text: str, header: str) -> str:
    pattern = rf"\*\*{re.escape(header)}\*\*\s*(.*?)(?=\*\*[A-Z\s]{{2,}}\*\*|\Z)"
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1).strip() if m else ""


def parse_signals(text: str) -> list[str]:
    raw = parse_section(text, "TREND SIGNALS")
    if not raw:
        return []
    parts = re.split(r"[,\n;•\-–]", raw)
    cleaned = [p.strip().strip("\"'*•–") for p in parts]
    return [c for c in cleaned if 2 < len(c) <= 50][:6]


def parse_related_topics(text: str) -> list[str]:
    raw = parse_section(text, "RELATED TOPICS")
    if not raw:
        return []
    parts = re.split(r"[,\n;•\-–]", raw)
    cleaned = [p.strip().strip("\"'*•–") for p in parts]
    return [c for c in cleaned if 2 < len(c) <= 60][:5]


def parse_sentiment_score(snapshot_text: str) -> str:
    m = re.search(r'\bScore:\s*(Optimistic|Mixed|Cautious|Uncertain)\b', snapshot_text, re.IGNORECASE)
    return m.group(1).capitalize() if m else ""


def strip_sentiment_score(snapshot_text: str) -> str:
    return re.sub(r'\n?Score:\s*(Optimistic|Mixed|Cautious|Uncertain)[^\n]*', '', snapshot_text, flags=re.IGNORECASE).strip()


def md_to_html(text: str) -> str:
    text = re.sub(
        r'\[([^\]]+)\]\((https?://[^\)]+)\)',
        r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>',
        text,
    )
    text = re.sub(r'\*\*([^*\n]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\n+', '<br>', text)
    return text


# ── Page setup ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Trend Intelligence",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
.chip {
    display: inline-block;
    padding: 4px 13px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 500;
    margin: 3px 2px;
    background: #EEF2FF;
    color: #4338CA;
    border: 1px solid #C7D2FE;
}
.meta-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: #6B7280;
    margin: 0 0 6px;
}
.card-green   { background:#F0FDF4; border-left:4px solid #16A34A; padding:14px 18px;
                border-radius:0 6px 6px 0; line-height:1.65; margin:6px 0 14px; }
.card-amber   { background:#FFFBEB; border-left:4px solid #D97706; padding:14px 18px;
                border-radius:0 6px 6px 0; line-height:1.65; margin:6px 0; }
.card-purple  { background:#FDF4FF; border-left:4px solid #9333EA; padding:14px 18px;
                border-radius:0 6px 6px 0; line-height:1.65; margin:6px 0; }
.card-slate   { background:#F8FAFC; border-left:4px solid #64748B; padding:14px 18px;
                border-radius:0 6px 6px 0; line-height:1.65; margin:6px 0 14px; }
.card-threads { background:#FAFAFA; border-left:4px solid #D1D5DB; padding:14px 18px;
                border-radius:0 6px 6px 0; line-height:1.75; margin:6px 0 14px; }
.card-blue    { background:#EFF6FF; border-left:4px solid #2563EB; padding:14px 18px;
                border-radius:0 6px 6px 0; line-height:1.65; margin:6px 0; }
.card-green a, .card-amber a, .card-purple a,
.card-slate a, .card-threads a, .card-blue a {
    color: #1D4ED8;
    font-weight: 500;
    text-decoration: underline;
    text-decoration-color: #BFDBFE;
    text-underline-offset: 2px;
}
.card-green a:hover, .card-amber a:hover, .card-purple a:hover,
.card-slate a:hover, .card-threads a:hover, .card-blue a:hover {
    text-decoration-color: #1D4ED8;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Header ─────────────────────────────────────────────────────────────────────────────────
st.title("📡 Trend Intelligence Dashboard")
st.caption("Real-time research synthesized by Claude · Powered by web search")

# ── Input row ─────────────────────────────────────────────────────────────────────────────
with st.form("search_form"):
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        topic = st.text_input(
            "Topic",
            value="digital marketing and social media",
            placeholder="e.g. generative AI, climate tech, fintech…",
            label_visibility="collapsed",
            key="topic_input",
        )
    with col_btn:
        go = st.form_submit_button("▶  Run Brief", type="primary", use_container_width=True)

# ── Topic history ─────────────────────────────────────────────────────────────────────────
auto_run = st.session_state.pop("_auto_run", False)

history = st.session_state.get("topic_history", [])
if history:
    st.markdown('<p class="meta-label" style="margin:6px 0 4px">Recent</p>', unsafe_allow_html=True)
    hist_cols = st.columns(min(len(history), 5))
    for col, ht in zip(hist_cols, history):
        with col:
            if st.button(ht, key=f"hist_{ht}", use_container_width=True):
                st.session_state["topic_input"] = ht
                st.session_state["_auto_run"] = True
                st.rerun()

st.write("")

# ── Fetch ─────────────────────────────────────────────────────────────────────────────────
if (go or auto_run) and topic.strip():
    with st.status(f'Researching "{topic.strip()}"…', expanded=True) as status:
        raw = run_research(topic.strip(), on_step=st.write)
        status.update(
            label=f'Brief ready · {topic.strip().title()}',
            state="complete",
            expanded=False,
        )

    history = st.session_state.get("topic_history", [])
    if topic.strip() not in history:
        history = [topic.strip()] + history[:4]

    st.session_state.update(
        raw=raw,
        topic=topic.strip(),
        fetched_at=datetime.now().strftime("%d %b %Y, %H:%M"),
        topic_history=history,
    )

# ── Display ─────────────────────────────────────────────────────────────────────────────────
if "raw" not in st.session_state:
    st.stop()

raw = st.session_state["raw"]

h1, h2, h3 = st.columns([4, 1, 1])
with h1:
    st.subheader(st.session_state["topic"].title())
with h2:
    st.caption(f"🕐 {st.session_state['fetched_at']}")
with h3:
    topic_slug = re.sub(r'[^a-z0-9]+', '-', st.session_state["topic"].lower()).strip('-')
    st.download_button(
        "⬇ Export",
        data=raw,
        file_name=f"{topic_slug}.md",
        mime="text/markdown",
        use_container_width=True,
    )

sections = {
    k: parse_section(raw, k)
    for k in (
        "TOP STORY",
        "NARRATIVE THREADS",
        "SENTIMENT SNAPSHOT",
        "EMERGING SIGNAL",
        "SO WHAT",
        "LEARN MORE",
    )
}

signals = parse_signals(raw)
related_topics = parse_related_topics(raw)

left, right = st.columns([2, 3], gap="large")

# ── Left column ─────────────────────────────────────────────────────────────────────────────
with left:
    st.markdown('<p class="meta-label">🔖 Trending Topics</p>', unsafe_allow_html=True)
    if signals:
        st.markdown(
            "".join(f'<span class="chip">{s}</span>' for s in signals),
            unsafe_allow_html=True,
        )
    else:
        st.caption("No signals extracted.")

    st.write("")

    if sections["SENTIMENT SNAPSHOT"]:
        st.markdown('<p class="meta-label">🧭 Sentiment Snapshot</p>', unsafe_allow_html=True)
        score = parse_sentiment_score(sections["SENTIMENT SNAPSHOT"])
        if score:
            bg, border, fg = SENTIMENT_COLORS.get(score, ("#F1F5F9", "#64748B", "#1E293B"))
            st.markdown(
                f'<span style="background:{bg};color:{fg};border:1px solid {border};'
                f'padding:2px 10px;border-radius:999px;font-size:12px;font-weight:700;'
                f'display:inline-block;margin-bottom:6px">{score}</span>',
                unsafe_allow_html=True,
            )
        clean_snapshot = strip_sentiment_score(sections["SENTIMENT SNAPSHOT"])
        st.markdown(
            f'<div class="card-slate">{md_to_html(clean_snapshot)}</div>',
            unsafe_allow_html=True,
        )

    st.write("")

    if sections["EMERGING SIGNAL"]:
        st.markdown('<p class="meta-label">🔬 Emerging Signal</p>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="card-purple">{md_to_html(sections["EMERGING SIGNAL"])}</div>',
            unsafe_allow_html=True,
        )

    st.write("")

    if sections["LEARN MORE"]:
        st.markdown('<p class="meta-label">📚 Learn More</p>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="card-blue">{md_to_html(sections["LEARN MORE"])}</div>',
            unsafe_allow_html=True,
        )

# ── Right column ──────────────────────────────────────────────────────────────────────────────
with right:
    if sections["TOP STORY"]:
        st.markdown('<p class="meta-label">🔥 Top Story</p>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="card-green">{md_to_html(sections["TOP STORY"])}</div>',
            unsafe_allow_html=True,
        )

    if sections["NARRATIVE THREADS"]:
        st.markdown('<p class="meta-label">🧵 Narrative Threads</p>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="card-threads">{md_to_html(sections["NARRATIVE THREADS"])}</div>',
            unsafe_allow_html=True,
        )

    if sections["SO WHAT"]:
        st.markdown('<p class="meta-label">💡 So What</p>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="card-amber">{md_to_html(sections["SO WHAT"])}</div>',
            unsafe_allow_html=True,
        )

# ── Related Topics ──────────────────────────────────────────────────────────────────────────
if related_topics:
    st.write("")
    st.divider()
    st.markdown('<p class="meta-label">🔀 Related Topics</p>', unsafe_allow_html=True)
    st.markdown(
        "".join(f'<span class="chip">{rt}</span>' for rt in related_topics),
        unsafe_allow_html=True,
    )

with st.expander("📄 Raw output"):
    st.markdown(raw)
