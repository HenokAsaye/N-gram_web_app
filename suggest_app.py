"""Amharic next-word page.

Put suggestion_model.json in this folder, then run:

    python suggest_app.py

Open http://127.0.0.1:8765
"""

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8765
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


def suggest_next(model, text, n=3, top=5):
    words = words_of(text)
    n = 3 if int(n) >= 3 else 2
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


PAGE = """<!DOCTYPE html>
<html lang="am">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Amharic next word</title>
<style>
  body {
    margin: 0;
    font-family: "Noto Sans Ethiopic", "Nyala", sans-serif;
    background: #f4f1ea;
    color: #1c1915;
  }
  main {
    max-width: 720px;
    margin: 40px auto;
    padding: 28px;
    background: white;
    border-radius: 16px;
    box-shadow: 0 10px 30px rgba(40, 30, 10, 0.08);
  }
  h1 { font-size: 1.6rem; margin: 0 0 8px; }
  p { margin: 0 0 18px; line-height: 1.45; color: #4d463c; }
  label { display: block; font-size: 0.9rem; margin-bottom: 6px; }
  textarea {
    width: 100%;
    min-height: 90px;
    box-sizing: border-box;
    font: 1.25rem/1.5 "Noto Sans Ethiopic", "Nyala", sans-serif;
    padding: 12px;
    border: 1px solid #d9d0c3;
    border-radius: 10px;
  }
  .row { display: flex; gap: 10px; margin: 12px 0 18px; align-items: center; }
  select, button {
    font: 1rem "Noto Sans Ethiopic", sans-serif;
    border-radius: 10px;
    border: 1px solid #d9d0c3;
    background: white;
    padding: 10px 14px;
  }
  button.primary { background: #8a3b12; color: white; border-color: #8a3b12; cursor: pointer; }
  .meta { min-height: 1.4em; color: #6b6256; margin-bottom: 10px; }
  .suggestions { display: flex; flex-direction: column; gap: 8px; }
  .suggestion {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    text-align: left;
    cursor: pointer;
    padding: 12px 14px;
  }
  .suggestion strong { font-size: 1.15rem; }
  .suggestion span { color: #6b6256; }
  .missing { background: #fff4e8; border: 1px solid #efd3b4; padding: 12px; border-radius: 10px; }
</style>
</head>
<body>
<main>
  <h1>Amharic next-word suggestions</h1>
  <p>Type the start of a sentence. Choose a suggestion to add that word and continue. Typing only :: asks for words that start a new sentence.</p>
  <div id="missing" class="missing" hidden>
    Put suggestion_model.json in this folder, next to suggest_app.py, then restart the program.
  </div>
  <label for="text">Sentence</label>
  <textarea id="text" placeholder="ኢትዮጵያ ውስጥ የቡና"></textarea>
  <div class="row">
    <label for="n">History</label>
    <select id="n">
      <option value="3" selected>Last two words</option>
      <option value="2">Last word</option>
    </select>
    <button class="primary" id="go" type="button">Suggest</button>
  </div>
  <div class="meta" id="meta"></div>
  <div class="suggestions" id="list"></div>
</main>
<script>
const missing = document.getElementById("missing");
const text = document.getElementById("text");
const list = document.getElementById("list");
const meta = document.getElementById("meta");

async function suggest() {
  const response = await fetch("/suggest", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({text: text.value, n: Number(document.getElementById("n").value)})
  });
  const data = await response.json();
  if (data.missing) {
    missing.hidden = false;
    meta.textContent = "";
    list.replaceChildren();
    return;
  }
  missing.hidden = true;
  if (data.sentence_start) {
    meta.textContent = "Words that start a new sentence.";
  } else if (data.order === 1) {
    meta.textContent = "Most frequent words. This history was not stored.";
  } else {
    const used = data.shorter ? "shorter history" : "exact history";
    meta.textContent = "Used a " + data.order + "-gram (" + used + "). History: " + data.history;
  }
  list.replaceChildren();
  for (const item of data.suggestions) {
    const button = document.createElement("button");
    button.className = "suggestion";
    button.type = "button";
    const name = document.createElement("strong");
    name.textContent = item.word;
    const detail = document.createElement("span");
    detail.textContent = "P " + item.probability.toFixed(4);
    button.append(name, detail);
    button.addEventListener("click", () => {
      text.value = (text.value.trim() + " " + item.word).trim();
      suggest();
    });
    list.append(button);
  }
}

document.getElementById("go").addEventListener("click", suggest);
text.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    suggest();
  }
});
suggest();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    model = None

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    def _send(self, code, body, content_type):
        payload = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path.split("?", 1)[0] != "/":
            self._send(404, "Not found", "text/plain; charset=utf-8")
            return
        self._send(200, PAGE, "text/html; charset=utf-8")

    def do_POST(self):
        if self.path != "/suggest":
            self._send(404, "Not found", "text/plain; charset=utf-8")
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(min(length, 20_000))
        try:
            incoming = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            incoming = {}
        if self.model is None:
            result = {"missing": True, "suggestions": []}
        else:
            result = suggest_next(
                self.model,
                str(incoming.get("text", "")),
                incoming.get("n", 3),
            )
        self._send(200, json.dumps(result, ensure_ascii=False), "application/json; charset=utf-8")


def main():
    Handler.model = load_model()
    if Handler.model is None:
        print("suggestion_model.json was not found in this folder.")
        print("Put the downloaded file next to suggest_app.py and run this again.")
    else:
        orders = Handler.model.get("orders", {})
        print("Loaded histories:", {key: len(value) for key, value in orders.items()})
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Open http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
