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

    prompt = (
        f"You are a trend intelligence analyst. Search the web for the latest developments in: **{topic}**\n\n"
        "Write a structured trend brief using these exact section headers. "
        "Keep every section tight: short bullet points only, no paragraphs.\n\n"
        "**TOP STORY**\n"
        "- [Source name]: one-sentence summary of the biggest development\n"
        "- 1-2 more bullet points of essential context\n\n"
        "**NARRATIVE THREADS**\n"
        "- Thread name: one sentence\n"
        "- Thread name: one sentence\n"
        "- Thread name: one sentence\n\n"
        "**SENTIMENT SNAPSHOT**\n"
        "- Overall mood (optimistic/cautious/uncertain): one sentence why\n"
        "- 1-2 bullet points on key drivers\n\n"
        "**EMERGING SIGNAL**\n"
        "- Signal: one sentence describing it\n"
        "- Why it matters: one sentence\n\n"
        "**SO WHAT**\n"
        "- 2-3 bullet points: actionable takeaways for a practitioner\n\n"
        "**TREND SIGNALS**\n"
        "4-6 short trend labels (2-5 words each), comma-separated.\n"
        "Example: AI-Generated Ads, Influencer Regulation, Shoppable Video"
    )

    messages = [{"role": "user", "content": prompt}]
    text = ""

    for _ in range(5):
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
    parts = re.split(r"[,\n;*\-]", raw)
    cleaned = [p.strip().strip("\"'*-") for p in parts]
    return [c for c in cleaned if 2 < len(c) <= 50][:6]


st.set_page_config(
    page_title="Trend Intelligence",
    page_icon="radar",
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
.card-green  { background:#F0FDF4; border-left:4px solid #16A34A; padding:14px 18px;
               border-radius:0 6px 6px 0; line-height:1.65; margin:6px 0 14px; }
.card-amber  { background:#FFFBEB; border-left:4px solid #D97706; padding:14px 18px;
               border-radius:0 6px 6px 0; line-height:1.65; margin:6px 0; }
.card-purple { background:#FDF4FF; border-left:4px solid #9333EA; padding:14px 18px;
               border-radius:0 6px 6px 0; line-height:1.65; margin:6px 0; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("Trend Intelligence Dashboard")
st.caption("Real-time research synthesized by Claude - Web search - Data reflects recent days")

col_input, col_btn = st.columns([5, 1])
with col_input:
    topic = st.text_input(
        "Topic",
        value="digital marketing and social media",
        placeholder="e.g. generative AI, climate tech, fintech",
        label_visibility="collapsed",
    )
with col_btn:
    go = st.button("Run Brief", type="primary", use_container_width=True)

st.write("")

if go and topic.strip():
    with st.spinner('Researching "' + topic.strip() + '"...'):
        raw = run_research(topic.strip())
    st.session_state.update(
        raw=raw,
        topic=topic.strip(),
        fetched_at=datetime.now().strftime("%d %b %Y, %H:%M"),
    )

if "raw" not in st.session_state:
    st.info("Enter a topic above and click **Run Brief** to generate a trend report.")
    st.stop()

raw = st.session_state["raw"]

h1, h2 = st.columns([4, 1])
with h1:
    st.subheader(st.session_state["topic"].title())
with h2:
    st.caption(st.session_state["fetched_at"])

sections = {
    k: parse_section(raw, k)
    for k in ("TOP STORY", "NARRATIVE THREADS", "SENTIMENT SNAPSHOT", "EMERGING SIGNAL", "SO WHAT")
}
signals = parse_signals(raw)

left, right = st.columns([2, 3], gap="large")

with left:
    st.markdown('<p class="meta-label">Trending Topics</p>', unsafe_allow_html=True)
    if signals:
        st.markdown(
            "".join(f'<span class="chip">{s}</span>' for s in signals),
            unsafe_allow_html=True,
        )
    else:
        st.caption("No signals extracted.")

    st.write("")

    if sections["SENTIMENT SNAPSHOT"]:
        st.markdown('<p class="meta-label">Sentiment Snapshot</p>', unsafe_allow_html=True)
        st.markdown(sections["SENTIMENT SNAPSHOT"])

    st.write("")

    if sections["EMERGING SIGNAL"]:
        st.markdown('<p class="meta-label">Emerging Signal</p>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="card-purple">{sections["EMERGING SIGNAL"]}</div>',
            unsafe_allow_html=True,
        )

with right:
    if sections["TOP STORY"]:
        st.markdown('<p class="meta-label">Top Story</p>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="card-green">{sections["TOP STORY"]}</div>',
            unsafe_allow_html=True,
        )

    if sections["NARRATIVE THREADS"]:
        st.markdown('<p class="meta-label">Narrative Threads</p>', unsafe_allow_html=True)
        st.markdown(sections["NARRATIVE THREADS"])

    if sections["SO WHAT"]:
        st.markdown('<p class="meta-label">So What</p>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="card-amber">{sections["SO WHAT"]}</div>',
            unsafe_allow_html=True,
        )

with st.expander("Raw output"):
    st.markdown(raw)