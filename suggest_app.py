"""Amharic next-word suggestions for Streamlit.

Locally:

    streamlit run suggest_app.py

On Streamlit Cloud, set the main file to suggest_app.py and keep
suggestion_model.json in this folder.
"""

import json
import re
from pathlib import Path

import streamlit as st

MODEL_PATH = Path(__file__).with_name("suggestion_model.json")

NORMALIZE = {
    "ሐ": "ሀ", "ሑ": "ሁ", "ሒ": "ሂ", "ሓ": "ሃ", "ሔ": "ሄ", "ሕ": "ህ", "ሖ": "ሆ",
    "ኀ": "ሀ", "ኁ": "ሁ", "ኂ": "ሂ", "ኃ": "ሃ", "ኄ": "ሄ", "ኅ": "ህ", "ኆ": "ሆ",
    "ሠ": "ሰ", "ሡ": "ሱ", "ሢ": "ሲ", "ሣ": "ሳ", "ሤ": "ሴ", "ሥ": "ስ", "ሦ": "ሶ",
    "ዐ": "አ", "ዑ": "ኡ", "ዒ": "ኢ", "ዓ": "ኣ", "ዔ": "ኤ", "ዕ": "እ", "ዖ": "ኦ",
    "ፀ": "ጸ", "ፁ": "ጹ", "ፂ": "ጺ", "ፃ": "ጻ", "ፄ": "ጼ", "ፅ": "ጽ", "ፆ": "ጾ",
}
TRANS = str.maketrans(NORMALIZE)
LETTERS = f"{chr(0x1200)}-{chr(0x135A)}"
DIGITS = f"{chr(0x1369)}-{chr(0x137C)}"
SPLIT_RE = re.compile(r"፡፡|[።፧?!？！]+")
HISTORY_CHOICES = {
    "Last three words": 4,
    "Last two words": 3,
    "Last word": 2,
}


def clean(sentence):
    text = sentence.translate(TRANS)
    text = re.sub(rf"\S*[0-9A-Za-z{DIGITS}]\S*", " ", text)
    text = re.sub(rf"[^{LETTERS}\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def words_of(text):
    words = []
    for part in SPLIT_RE.split(text):
        words.extend(clean(part).split())
    return words


def load_model(path=MODEL_PATH):
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def suggest_next(model, text, n=4, top=5):
    words = words_of(text)
    n = max(2, min(4, int(n)))
    orders = model.get("orders", {})
    sentence_start = len(words) == 0
    for order in range(n, 1, -1):
        need = order - 1
        if len(words) >= need:
            history = words[-need:]
        else:
            history = ["<s>"] * (need - len(words)) + words
        key = " ".join(history)
        found = orders.get(str(order), {}).get(key)
        if found and found.get("next"):
            given = found["total"] or 1
            rows = []
            for word, count in found["next"][:top]:
                rows.append({
                    "word": word,
                    "count": count,
                    "probability": count / given,
                })
            return {
                "words": words,
                "order": order,
                "history": key,
                "shorter": order != n,
                "sentence_start": sentence_start,
                "suggestions": rows,
            }
    given = model.get("unigram_total") or 1
    rows = []
    for word, count in model.get("unigram", [])[:top]:
        rows.append({
            "word": word,
            "count": count,
            "probability": count / given,
        })
    return {
        "words": words,
        "order": 1,
        "history": "",
        "shorter": True,
        "sentence_start": sentence_start,
        "suggestions": rows,
    }


def status_line(result):
    if result["sentence_start"]:
        return "Words that start a new sentence."
    if result["order"] == 1:
        return "Most frequent words. This history was not stored."
    used = "shorter history" if result["shorter"] else "exact history"
    return f"Used a {result['order']}-gram ({used}). History: {result['history']}"


@st.cache_resource
def get_model():
    return load_model()


def current_n():
    return HISTORY_CHOICES[st.session_state.get("history_label", "Last three words")]


def run_suggest():
    st.session_state["active"] = True
    st.session_state["result"] = suggest_next(
        get_model(),
        st.session_state.get("sentence", ""),
        n=current_n(),
    )


def stop_suggest():
    st.session_state["active"] = False
    st.session_state["result"] = None


def append_word(word):
    current = st.session_state.get("sentence", "").strip()
    st.session_state["sentence"] = (current + " " + word).strip()
    if st.session_state.get("active"):
        run_suggest()


st.set_page_config(page_title="Amharic next word", layout="centered")
st.markdown(
    """
    <style>
      .stApp { background: #f4f1ea; color: #1c1915; }
      h1, p, label, .stMarkdown, .stCaption { color: #1c1915 !important; }
      .stTextArea textarea, [data-baseweb="select"] * {
        color: #1c1915 !important;
        background: #ffffff !important;
        font-family: "Noto Sans Ethiopic", Nyala, sans-serif;
      }
      .stTextArea textarea { font-size: 1.25rem; }
      div[data-testid="stButton"] button {
        border-radius: 10px;
        min-height: 2.8rem;
        font-weight: 600;
        color: #1c1915 !important;
        background: #ffffff !important;
        border: 1px solid #c9bfb2 !important;
      }
      div[data-testid="stButton"] button[kind="primary"],
      div[data-testid="stButton"] button[data-testid="baseButton-primary"] {
        color: #ffffff !important;
        background: #8a3b12 !important;
        border-color: #8a3b12 !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Amharic next-word suggestions")
st.write(
    "Type the start of a sentence, then press **Suggest**. "
    "Click a word to add it. Press **Stop** when you want the list to go away."
)

model = get_model()
if model is None:
    st.error(
        "suggestion_model.json is not in this folder. "
        "Put the downloaded model next to suggest_app.py and reboot the app."
    )
    st.stop()

for key, value in (("sentence", ""), ("active", False), ("result", None)):
    if key not in st.session_state:
        st.session_state[key] = value

st.text_area("Sentence", key="sentence", height=120, placeholder="ኢትዮጵያ ውስጥ የቡና")
st.selectbox("History", list(HISTORY_CHOICES), index=0, key="history_label")

left, mid, right = st.columns(3)
with left:
    st.button("Suggest", type="primary", on_click=run_suggest, use_container_width=True)
with mid:
    st.button("Stop", on_click=stop_suggest, use_container_width=True)
with right:
    st.button("Clear", on_click=lambda: st.session_state.update(sentence="", result=None, active=False), use_container_width=True)

result = st.session_state.get("result") if st.session_state.get("active") else None
if result is None:
    st.caption("Press Suggest to see the next words. Press Stop to hide them.")
elif not result["suggestions"]:
    st.info("No suggestion for this history.")
else:
    st.caption(status_line(result))
    for item in result["suggestions"]:
        st.button(
            f"{item['word']}          {item['probability'] * 100:.2f}%",
            key=f"pick-{item['word']}-{item['count']}",
            on_click=append_word,
            args=(item["word"],),
            use_container_width=True,
        )

