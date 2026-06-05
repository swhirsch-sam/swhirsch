import os
import re
from datetime import datetime

import anthropic
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-6"
SEARCH_TOOL = [{"type": "web_search_20250305", "name": "web_search"}]


@st.cache_resource
def get_client() -> anthropic.Anthropic:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        st.error("ANTHROPIC_API_KEY environment variable is not set.")
        st.stop()
    return anthropic.Anthropic(api_key=key)


def run_research(topic: str) -> str:
    client = get_client()

    prompt = f"""You are a trend intelligence analyst. Search the web for the latest developments in: **{topic}**

Write a structured trend brief using these exact section headers:

**TOP STORY**

2–3 sentences on the single most significant development right now. Cite the source as a markdown hyperlink [Publication Name](https://url.com). Bold 2–3 key terms with **term** formatting.

**NARRATIVE THREADS**

• **Thread 1 name**: 1–2 sentences. Bold key terms.

• **Thread 2 name**: 1–2 sentences. Bold key terms.

• **Thread 3 name**: 1–2 sentences. Bold key terms.

**SENTIMENT SNAPSHOT**

2–3 sentences on the overall mood—optimistic, cautious, uncertain—and what is driving it. Bold 1–2 key terms. Cite any source as a markdown hyperlink [Source](https://url.com).

**EMERGING SIGNAL**

2–3 sentences on one early or weak signal not yet mainstream but worth watching. Bold the signal name and key terms. Cite source as [Source Name](https://url.com) if available.

**SO WHAT**

2–3 sentences on the key takeaway for a practitioner in this space. Bold the most critical action or insight.

**LEARN MORE**

2–3 recommended resources—online courses, key articles, or authoritative guides—for going deeper on this topic. Format each as:
• [Resource Title](https://actual-url.com) — one sentence on what it covers and why it's worth reading.

**TREND SIGNALS**

4–6 short trend labels (2–5 words each), comma-separated.

Example: AI-Generated Ads, Influencer Regulation, Shoppable Video

**RELATED TOPICS**

4–5 related topics (2–5 words each) a reader might want to explore next, comma-separated.

Example: Voice Search Optimization, AR Commerce, Creator Economy

Formatting rules:
- Always use real, clickable URLs: [Publication Name](https://actual-url.com)
- Bold key terms with **double asterisks** (2–4 word phrases, not full sentences)"""

    messages = [{"role": "user", "content": prompt}]

    text = ""
    for _ in range(5):  # max continuations for pause_turn
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


def md_to_html(text: str) -> str:
    # [text](url) → clickable anchor
    text = re.sub(
        r'\[([^\]]+)\]\((https?://[^\)]+)\)',
        r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>',
        text,
    )
    # **term** → highlighted mark
    text = re.sub(r'\*\*([^*\n]+)\*\*', r'<mark>\1</mark>', text)
    # newlines → <br>
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
mark {
    background: #FEF08A;
    color: #713F12;
    border-radius: 3px;
    padding: 0 2px;
    font-weight: 600;
}
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
.stMarkdown strong {
    background: #FEF08A;
    color: #713F12;
    border-radius: 3px;
    padding: 0 2px;
    font-weight: 600;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Header ─────────────────────────────────────────────────────────────────────────────────
st.title("📡 Trend Intelligence Dashboard")
st.caption("Real-time research synthesized by Claude · Powered by web search")

# ── Input row ─────────────────────────────────────────────────────────────────────────────
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
    go = st.button("▶  Run Brief", type="primary", use_container_width=True)

st.write("")

# ── Fetch ─────────────────────────────────────────────────────────────────────────────────
if go and topic.strip():
    with st.spinner(f'Researching "{topic.strip()}"…'):
        raw = run_research(topic.strip())

    st.session_state.update(
        raw=raw,
        topic=topic.strip(),
        fetched_at=datetime.now().strftime("%d %b %Y, %H:%M"),
    )

# ── Display ─────────────────────────────────────────────────────────────────────────────────
if "raw" not in st.session_state:
    st.info("Enter a topic above and click **▶ Run Brief** to generate a trend report.")
    st.stop()

raw = st.session_state["raw"]

h1, h2 = st.columns([4, 1])
with h1:
    st.subheader(st.session_state["topic"].title())
with h2:
    st.caption(f"🕐 {st.session_state['fetched_at']}")

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
        st.markdown(
            f'<div class="card-slate">{md_to_html(sections["SENTIMENT SNAPSHOT"])}</div>',
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
    st.markdown('<p class="meta-label">🔀 Explore Related Topics</p>', unsafe_allow_html=True)
    cols = st.columns(len(related_topics))
    for col, rt in zip(cols, related_topics):
        with col:
            if st.button(rt, key=f"rt_{rt}", use_container_width=True):
                st.session_state["topic_input"] = rt
                st.rerun()

with st.expander("📄 Raw output"):
    st.markdown(raw)
