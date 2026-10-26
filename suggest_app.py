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


def append_word(word):
    current = st.session_state.get("sentence", "").strip()
    st.session_state["sentence"] = (current + " " + word).strip()


st.set_page_config(page_title="Amharic next word", layout="centered")
st.title("Amharic next-word suggestions")
st.write(
    "Type the start of a sentence. Choose a suggestion to add that word and continue. "
    "Typing only :: asks for words that start a new sentence."
)

model = get_model()
if model is None:
    st.error(
        "suggestion_model.json is not in this folder. "
        "Put the downloaded model next to suggest_app.py and reboot the app."
    )
    st.stop()

if "sentence" not in st.session_state:
    st.session_state["sentence"] = ""

st.text_area("Sentence", key="sentence", height=120, placeholder="ኢትዮጵያ ውስጥ የቡና")
history_label = st.selectbox("History", list(HISTORY_CHOICES), index=0)
n = HISTORY_CHOICES[history_label]

result = suggest_next(model, st.session_state["sentence"], n=n)
st.caption(status_line(result))

if not result["suggestions"]:
    st.info("No suggestion for this history.")
else:
    for item in result["suggestions"]:
        label = f"{item['word']}    P {item['probability']:.4f}"
        st.button(
            label,
            key=f"suggest-{item['word']}-{item['count']}",
            on_click=append_word,
            args=(item["word"],),
            use_container_width=True,
        )
