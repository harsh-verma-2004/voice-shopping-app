from __future__ import annotations
import re
import json
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

from flask import Flask, request, jsonify, redirect, url_for
from flask import render_template_string
from flask_cors import CORS
from langdetect import detect as lang_detect
import json
app = Flask(__name__)
CORS(app)
DB_PATH = "shopping.db"

CATEGORIES = {
    "milk": "Dairy",
    "yogurt": "Dairy", 
    "cheese": "Dairy", 
    "bread": "Bakery", 
    "eggs": "Dairy", 
    "butter": "Dairy", 
    "almond milk": "Dairy", 
    "soy milk": "Dairy", 
    "oat milk": "Dairy", 
    "apple": "Produce", 
    "apples": "Produce", 
    "banana": "Produce", 
    "bananas": "Produce", 
    "mango": "Produce", 
    "mangoes": "Produce", 
    "orange": "Produce", 
    "oranges": "Produce", 
    "tomato": "Produce", 
    "tomatoes": "Produce", 
    "onion": "Produce", 
    "onions": "Produce", 
    "potato": "Produce", 
    "potatoes": "Produce", 
    "lettuce": "Produce", 
    "spinach": "Produce", 
    "chips": "Snacks", 
    "cookies": "Snacks", 
    "chocolate": "Snacks", 
    "rice": "Pantry", 
    "flour": "Pantry", 
    "sugar": "Pantry", 
    "salt": "Pantry", 
    "toothpaste": "Personal Care", 
    "soap": "Personal Care", 
    "shampoo": "Personal Care", 
    "toilet paper": "Household", 
    "detergent": "Household", }

SUBSTITUTES = { 
    "milk": ["almond milk", "soy milk", "oat milk"], 
    "butter": ["ghee", "olive oil"], 
    "sugar": ["jaggery", "brown sugar"], 
    "rice": ["quinoa", "millet"], 
    "bread": ["multigrain bread", 
    "gluten-free bread"], 
    "toothpaste": ["herbal toothpaste"], 
    }

SEASONAL_BY_MONTH = {
    1: ["oranges", "carrots", "spinach"],
    2: ["strawberries", "cabbage"],
    3: ["mangoes", "peas"],
    4: ["mangoes", "watermelon"],
    5: ["mangoes", "cucumbers"],
    6: ["lychees", "okra"],
    7: ["cherries", "corn"],
    8: ["peaches", "beans"],
    9: ["apples", "pumpkin"],
    10: ["apples", "cauliflower"],
    11: ["guava", "beets"],
    12: ["kiwi", "broccoli"],
}

NUMBER_WORDS_EN = {
    "zero":0, "one":1, "two":2, "three":3, "four":4, "five":5, "six":6, "seven":7, "eight":8, "nine":9, "ten":10,
}
NUMBER_WORDS_HI = {
    "ek":1, "do":2, "teen":3, "char":4, "paanch":5, "chhe":6, "saat":7, "aath":8, "nau":9, "das":10,
}

CATALOG = [
    ("milk", "Amul", "1L", 65, "Dairy", 1, 0),
    ("almond milk", "AlmondY", "1L", 220, "Dairy", 1, 1),
    ("soy milk", "SoyRich", "1L", 160, "Dairy", 1, 0),
    ("bread", "Britannia", "400g", 45, "Bakery", 1, 1),
    ("eggs", "Keggs", "12 pack", 90, "Dairy", 1, 0),
    ("apples", "Organic Farm", "1kg", 180, "Produce", 1, 0),
    ("bananas", "Local", "1dz", 60, "Produce", 1, 0),
    ("toothpaste", "Colgate", "100g", 55, "Personal Care", 1, 0),
    ("toothpaste", "Dabur Red", "100g", 50, "Personal Care", 1, 1),
    ("rice", "India Gate", "5kg", 520, "Pantry", 1, 0),
    ("sugar", "Madhur", "1kg", 50, "Pantry", 1, 0),
    ("detergent", "Surf Excel", "1kg", 190, "Household", 1, 0),
    ("toilet paper", "Softie", "4 rolls", 120, "Household", 1, 0),
]

def db():
    return sqlite3.connect(DB_PATH)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS shopping_list (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    category TEXT
);
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item TEXT NOT NULL,
    last_added TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    brand TEXT,
    size TEXT,
    price REAL,
    category TEXT,
    available INTEGER,
    promo INTEGER
);
"""

def init_db():
    con = db()
    cur = con.cursor()
    for stmt in SCHEMA_SQL.split(";"):
        s = stmt.strip()
        if s:
            cur.execute(s)
    # seed catalog if empty
    cur.execute("SELECT COUNT(*) FROM catalog")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO catalog(name,brand,size,price,category,available,promo) VALUES (?,?,?,?,?,?,?)",
            CATALOG,
        )
    con.commit()
    con.close()

init_db()

@dataclass
class ParsedCommand:
    intent: str  
    item: Optional[str] = None
    quantity: Optional[int] = None
    brand: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    raw: str = ""
    lang: str = "en"

TRANSLATIONS_HI_EN = {
    "seb": "apple",
    "kela": "banana",
    "aam": "mango",
    "santrā": "orange",
    "tamatar": "tomato",
    "pyaaz": "onion",
    "aaloo": "potato",
    "doodh": "milk",
    "badam doodh": "almond milk",
    "anda": "eggs",
    "chawal": "rice",
    "cheenee": "sugar",
    "namak": "salt",
}

ADD_KEYWORDS_EN = ["add", "buy", "need", "get", "include", "want"]
REMOVE_KEYWORDS_EN = ["remove", "delete", "drop", "clear"]
SEARCH_KEYWORDS_EN = ["find", "search", "look for", "show me"]
MODIFY_KEYWORDS_EN = ["change", "update", "set", "make"]

ADD_KEYWORDS_HI = ["jodo", "add karo", "khareedna", "chahiye", "lo"]
REMOVE_KEYWORDS_HI = ["hatao", "nikalo", "remove karo", "delete karo"]
SEARCH_KEYWORDS_HI = ["dhundo", "dhoondo", "talash", "find karo", "dekhna hai"]
MODIFY_KEYWORDS_HI = ["badlo", "update karo", "set karo"]

def build_filter_words(*lists):
    words = set()
    for lst in lists:
        for item in lst:
            words.update(item.split())
    return words

ALL_FILTER_KEYWORDS = build_filter_words(
    ADD_KEYWORDS_EN, REMOVE_KEYWORDS_EN, SEARCH_KEYWORDS_EN, MODIFY_KEYWORDS_EN,
    ADD_KEYWORDS_HI, REMOVE_KEYWORDS_HI, SEARCH_KEYWORDS_HI, MODIFY_KEYWORDS_HI,
    list(NUMBER_WORDS_EN.keys()), list(NUMBER_WORDS_HI.keys()),
    ["to", "my", "list", "please", "organic", "find", "under", "below", "over", "above", "brand", "by", "for", "a", "an"]
)

PRICE_UNDER_PAT = re.compile(r"(?:under|below|less than|<=?)\s*₹?\$?(\d+(?:\.\d+)?)", re.I)
PRICE_OVER_PAT = re.compile(r"(?:over|above|more than|>=?)\s*₹?\$?(\d+(?:\.\d+)?)", re.I)
PRICE_RANGE_PAT = re.compile(r"₹?\$?(\d+(?:\.\d+)?)\s*(?:to|-)\s*₹?\$?(\d+(?:\.\d+)?)", re.I)
QTY_PAT = re.compile(r"\b(\d+)\b")
BRAND_PAT = re.compile(r"\bby\s+([a-zA-Z][\w\s-]+)|brand\s+([\w\s-]+)", re.I)


def number_word_to_int(tok: str, lang: str) -> Optional[int]:
    tok_l = tok.lower()
    if lang.startswith("hi") and tok_l in NUMBER_WORDS_HI:
        return NUMBER_WORDS_HI[tok_l]
    if tok_l in NUMBER_WORDS_EN:
        return NUMBER_WORDS_EN[tok_l]
    return None

def detect_lang(text: str) -> str:
    try:
        return lang_detect(text)
    except Exception:
        return "en"

def normalize_item(raw_item: str) -> str:
    item = raw_item.strip().lower()
    if item in TRANSLATIONS_HI_EN:
        item = TRANSLATIONS_HI_EN[item]
    if item.endswith("es") and item[:-2] in CATEGORIES:
        return item[:-2]
    if item.endswith("s") and item[:-1] in CATEGORIES:
        return item[:-1]
    return item

def parse_command(text: str, lang_hint: Optional[str]=None) -> ParsedCommand:
    raw = text.strip()
    lang = lang_hint or detect_lang(raw)
    t = raw.lower()
    qty = None
    m = QTY_PAT.search(t)
    if m:
        qty = int(m.group(1))
    else:
        for tok in t.split():
            n = number_word_to_int(tok, lang)
            if n is not None:
                qty = n
                break
    min_price = None
    max_price = None
    r = PRICE_RANGE_PAT.search(t)
    if r:
        min_price, max_price = float(r.group(1)), float(r.group(2))
    o = PRICE_OVER_PAT.search(t)
    if o:
        min_price = float(o.group(1))
    u = PRICE_UNDER_PAT.search(t)
    if u:
        max_price = float(u.group(1))
    brand = None
    b = BRAND_PAT.search(t)
    if b:
        brand = (b.group(1) or b.group(2) or "").strip()
    def has_any(hay: str, keys: List[str]) -> bool:
        return any(f' {k} ' in f' {hay} ' for k in keys)
    if lang.startswith("hi"):
        add = has_any(t, ADD_KEYWORDS_HI) or has_any(t, ADD_KEYWORDS_EN)
        rem = has_any(t, REMOVE_KEYWORDS_HI) or has_any(t, REMOVE_KEYWORDS_EN)
        sea = has_any(t, SEARCH_KEYWORDS_HI) or has_any(t, SEARCH_KEYWORDS_EN)
        mod = has_any(t, MODIFY_KEYWORDS_HI) or has_any(t, MODIFY_KEYWORDS_EN)
    else:
        add = has_any(t, ADD_KEYWORDS_EN)
        rem = has_any(t, REMOVE_KEYWORDS_EN)
        sea = has_any(t, SEARCH_KEYWORDS_EN)
        mod = has_any(t, MODIFY_KEYWORDS_EN)
    tokens = [w for w in re.split(r"[^\w]+", t) if w]
    filtered_tokens = [w for w in tokens if w.lower() not in ALL_FILTER_KEYWORDS and not w.isdigit()]
    item = None
    if filtered_tokens:
        phrase = " ".join(filtered_tokens)
        if phrase in TRANSLATIONS_HI_EN:
            item = phrase 
        else:
            for n in range(min(3, len(filtered_tokens)), 0, -1):
                for i in range(len(filtered_tokens) - n + 1):
                    phrase = " ".join(filtered_tokens[i:i+n])
                    if phrase in CATEGORIES:
                        item = phrase
                        break
                if item:
                    break
    if not item and filtered_tokens:
        item = " ".join(filtered_tokens)    
    if item:
        item = normalize_item(item)
    intent = "unknown"
    if add and item:
        intent = "add"
    elif rem and item:
        intent = "remove"
    elif mod and item and qty is not None:
        intent = "modify"
    elif sea:
        intent = "search"
    return ParsedCommand(intent=intent, item=item, quantity=qty, brand=brand, min_price=min_price, max_price=max_price, raw=raw, lang=lang)

def add_to_list(item: str, qty: int = 1) -> Dict:
    item = normalize_item(item)
    cat = CATEGORIES.get(item, "Other")
    con = db(); cur = con.cursor()
    cur.execute("SELECT id, quantity FROM shopping_list WHERE item=?", (item,))
    row = cur.fetchone()
    if row:
        new_qty = row[1] + qty
        cur.execute("UPDATE shopping_list SET quantity=? WHERE id=?", (new_qty, row[0]))
    else:
        cur.execute("INSERT INTO shopping_list(item, quantity, category) VALUES (?,?,?)", (item, qty, cat))
    cur.execute("SELECT id, count FROM history WHERE item=?", (item,))
    h = cur.fetchone()
    if h:
        cur.execute("UPDATE history SET last_added=?, count=? WHERE id=?", (datetime.utcnow().isoformat(), h[1]+1, h[0]))
    else:
        cur.execute("INSERT INTO history(item, last_added, count) VALUES (?,?,?)", (item, datetime.utcnow().isoformat(), 1))
    con.commit(); con.close()
    return {"status": "ok", "message": f"Added {qty} {item}"}

def remove_from_list(item: str) -> Dict:
    item = normalize_item(item)
    con = db(); cur = con.cursor()
    cur.execute("DELETE FROM shopping_list WHERE item=?", (item,))
    con.commit(); con.close()
    return {"status": "ok", "message": f"Removed {item}"}

def modify_quantity(item: str, qty: int) -> Dict:
    item = normalize_item(item)
    con = db(); cur = con.cursor()
    cur.execute("SELECT id FROM shopping_list WHERE item=?", (item,))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE shopping_list SET quantity=? WHERE item=?", (qty, item))
        message = f"Updated {item} to {qty}"
    else:
        cat = CATEGORIES.get(item, "Other")
        cur.execute("INSERT INTO shopping_list(item, quantity, category) VALUES (?,?,?)", (item, qty, cat))
        message = f"Added {item} with quantity {qty}"
    con.commit(); con.close()
    return {"status": "ok", "message": message}

def get_list_grouped() -> Dict[str, List[Dict]]:
    con = db(); cur = con.cursor()
    cur.execute("SELECT item, quantity, category FROM shopping_list ORDER BY category, item")
    rows = cur.fetchall(); con.close()
    out: Dict[str, List[Dict]] = {}
    for item, qty, cat in rows:
        out.setdefault(cat or "Other", []).append({"item": item, "quantity": qty})
    return out

def history_recommendations() -> List[str]:
    con = db(); cur = con.cursor()
    cur.execute("SELECT item, last_added, count FROM history")
    rows = cur.fetchall(); con.close()
    recs = []
    cutoff = datetime.utcnow() - timedelta(days=14)
    for item, last_added, cnt in rows:
        try:
            when = datetime.fromisoformat(last_added)
        except Exception:
            when = datetime.utcnow()
        if when < cutoff:
            recs.append(item)
    return recs[:5]

def seasonal_recommendations() -> List[str]:
    month = datetime.now().month
    return SEASONAL_BY_MONTH.get(month, [])[:5]

def substitute_for(item: str) -> List[str]:
    item = normalize_item(item)
    return SUBSTITUTES.get(item, [])

def catalog_search(q: Optional[str], brand: Optional[str], min_price: Optional[float], max_price: Optional[float]) -> List[Dict]:
    con = db(); cur = con.cursor()
    base = "SELECT name, brand, size, price, category, available, promo FROM catalog WHERE 1=1"
    params: List = []
    if q:
        base += " AND lower(name) LIKE ?"
        params.append(f"%{q.lower()}%")
    if brand:
        base += " AND lower(brand) LIKE ?"
        params.append(f"%{brand.lower()}%")
    if min_price is not None:
        base += " AND price >= ?"; params.append(min_price)
    if max_price is not None:
        base += " AND price <= ?"; params.append(max_price)
    base += " ORDER BY promo DESC, price ASC"
    cur.execute(base, params)
    rows = cur.fetchall(); con.close()
    return [
        {"name": n, "brand": b, "size": s, "price": p, "category": c, "available": bool(a), "promo": bool(pr)}
        for (n,b,s,p,c,a,pr) in rows
    ]

@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.post("/api/command")
def api_command():
    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    lang = data.get("lang") or None
    if not text:
        return jsonify({"status":"error","message":"Empty command"}), 400
    parsed = parse_command(text, lang)
    result_msg = ""
    if parsed.intent == "add" and parsed.item:
        qty = parsed.quantity or 1
        res = add_to_list(parsed.item, qty)
        result_msg = res["message"]
    elif parsed.intent == "remove" and parsed.item:
        res = remove_from_list(parsed.item)
        result_msg = res["message"]
    elif parsed.intent == "modify" and parsed.item and parsed.quantity is not None:
        res = modify_quantity(parsed.item, parsed.quantity)
        result_msg = res["message"]
    elif parsed.intent == "search":
        found = catalog_search(parsed.item, parsed.brand, parsed.min_price, parsed.max_price)
        return jsonify({
            "status":"ok",
            "intent":"search",
            "query": {
                "item": parsed.item,
                "brand": parsed.brand,
                "min_price": parsed.min_price,
                "max_price": parsed.max_price
            },
            "results": found,
            "transcript": parsed.raw,
        })
    else:
        result_msg = "Sorry, I didn't understand that. Try: 'Add 2 apples' or 'Find toothpaste under 100'."

    grouped = get_list_grouped()
    suggest = suggestions_bundle()
    return jsonify({
        "status": "ok",
        "intent": parsed.intent,
        "message": result_msg,
        "list": grouped,
        "suggestions": suggest,
        "transcript": parsed.raw,
        "substitutes": substitute_for(parsed.item) if parsed.item else [],
    })

@app.get("/api/list")
def api_list():
    return jsonify({"list": get_list_grouped(), "suggestions": suggestions_bundle()})

@app.post("/api/list")
def api_list_post():
    data = request.get_json(force=True)
    action = data.get("action")
    item = normalize_item(data.get("item", ""))
    qty = int(data.get("quantity")) if data.get("quantity") else 1
    if action == "add":
        add_to_list(item, qty)
    elif action == "remove":
        remove_from_list(item)
    elif action == "modify":
        modify_quantity(item, qty)
    else:
        return jsonify({"status":"error","message":"Unknown action"}), 400
    return jsonify({"status":"ok","list": get_list_grouped(), "suggestions": suggestions_bundle()})

@app.get("/api/search")
def api_search():
    q = request.args.get("q")
    brand = request.args.get("brand")
    min_p = request.args.get("min_price", type=float)
    max_p = request.args.get("max_price", type=float)
    results = catalog_search(q, brand, min_p, max_p)
    return jsonify({"status":"ok","results": results})

@app.get("/api/suggestions")
def api_suggestions():
    return jsonify({"status":"ok","suggestions": suggestions_bundle()})


def suggestions_bundle():
    return {
        "history": history_recommendations(),
        "seasonal": seasonal_recommendations(),
    }

INDEX_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Voice Shopping Assistant</title>
  <style>
    :root {
      --bg: #0b0f14; --card: #121825; --muted: #93a1b1; --text: #ecf0f1; --accent:#7c5cff; --accent2:#20c997;
    }
    * { box-sizing: border-box; }
    body { margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; background: var(--bg); color: var(--text); }
    header { padding: 16px; display:flex; justify-content:space-between; align-items:center; background: linear-gradient(90deg, rgba(124,92,255,.2), rgba(32,201,151,.2)); border-bottom: 1px solid #1f2937; }
    h1 { margin:0; font-size: 20px; }
    main { padding: 16px; display:grid; grid-template-columns: 1fr; gap: 16px; max-width: 1100px; margin: 0 auto; }
    .card { background: var(--card); border: 1px solid #1f2937; border-radius: 16px; padding: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.25); }
    .row { display:flex; gap: 12px; flex-wrap: wrap; align-items: center; }
    button { background: var(--accent); color: white; border: none; border-radius: 999px; padding: 10px 16px; font-weight: 600; cursor: pointer; transition: background-color 0.2s; }
    button:hover { background: #6a4ee6; }
    button:disabled { background: #334155; cursor: not-allowed; }
    button.secondary { background: #334155; }
    button.ghost { background: transparent; border:1px solid #334155; }
    .pill { background: #1f2937; padding: 4px 10px; border-radius: 999px; font-size: 12px; color: var(--muted); }
    .grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(240px,1fr)); gap: 12px; }
    .category { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: .1em; margin-bottom: 6px; }
    .item { display:flex; justify-content: space-between; align-items: center; padding: 10px; background:#0e1420; border:1px solid #162033; border-radius: 12px; gap: 8px; }
    .qty { display:flex; gap: 8px; align-items: center; }
    input, select { background:#0e1420; color:var(--text); border:1px solid #162033; border-radius: 10px; padding: 10px; width: 100%; }
    .recognition { min-height: 44px; display:flex; align-items:center; gap:10px; color: var(--muted); }
    .spinner { width:18px; height:18px; border:3px solid #334155; border-top-color: var(--accent2); border-radius:50%; animation: spin 1s linear infinite; display:none; }
    .spinner.show { display:inline-block; }
    @keyframes spin { to { transform: rotate(360deg);} }
    .result-card { border-left: 3px solid var(--accent2); }
    .result { padding:10px; background:#0e1420; border:1px solid #162033; border-radius:12px; margin-top:8px; }
    .price { font-weight:700; }
    footer { text-align:center; color:#6b7280; padding: 20px; }
  </style>
</head>
<body>
  <header>
    <h1>🛒 Voice Shopping Assistant</h1>
    <div class="row">
      <select id="lang">
        <option value="en-US">English (US)</option>
        <option value="en-IN">English (India)</option>
        <option value="hi-IN">Hindi (India)</option>
      </select>
      <button id="startBtn">🎙️ Start</button>
      <button id="stopBtn" class="secondary" disabled>⏹ Stop</button>
    </div>
  </header>

  <main>
    <section class="card">
      <div class="row">
        <div class="pill">Try: "Add 2 almond milk", "Remove milk", "Find toothpaste under 100", "Set rice to 3"</div>
      </div>
      <div class="recognition" id="recog"><div class="spinner" id="spin"></div><span id="transcript">…</span></div>
      <div class="row">
        <input id="manual" placeholder="Or type a command and press Enter" />
      </div>
    </section>

    <section class="card">
      <h3>Shopping List</h3>
      <div id="list" class="grid"></div>
    </section>

    <section class="card result-card">
      <h3>Search / Action Results</h3>
      <div id="results"></div>
    </section>

    <section class="card">
      <h3>Suggestions</h3>
      <div class="grid">
        <div>
          <div class="category">Based on your history</div>
          <div id="hist" class="row"></div>
        </div>
        <div>
          <div class="category">Seasonal picks</div>
          <div id="season" class="row"></div>
        </div>
      </div>
    </section>
  </main>

  <footer>Built with Flask · Voice via Web Speech API · Multilingual (English/Hindi)</footer>

  <script>
    const transcriptEl = document.getElementById('transcript');
    const listEl = document.getElementById('list');
    const histEl = document.getElementById('hist');
    const seasonEl = document.getElementById('season');
    const resultsEl = document.getElementById('results');
    const manual = document.getElementById('manual');
    const spin = document.getElementById('spin');

    async function refreshList() {
      const res = await fetch('/api/list');
      const data = await res.json();
      renderList(data.list);
      renderSuggestions(data.suggestions);
    }

    function renderList(grouped){
      listEl.innerHTML = '';
      if(Object.keys(grouped).length === 0){
        listEl.textContent = 'Your shopping list is empty.';
        return;
      }
      Object.entries(grouped).forEach(([cat, items]) => {
        const wrap = document.createElement('div');
        const h = document.createElement('div'); h.className='category'; h.textContent = cat; wrap.appendChild(h);
        items.forEach(it => {
          const row = document.createElement('div'); row.className = 'item';
          const left = document.createElement('div'); left.textContent = `${it.item}`;
          const right = document.createElement('div'); right.className='qty';
          const minus = document.createElement('button'); minus.className='ghost'; minus.textContent='-'; minus.onclick=()=>updateQty(it.item, Math.max(1, (it.quantity-1)));
          const qty = document.createElement('span'); qty.textContent = it.quantity; qty.className='pill';
          const plus = document.createElement('button'); plus.className='ghost'; plus.textContent='+'; plus.onclick=()=>updateQty(it.item, it.quantity+1);
          const rem = document.createElement('button'); rem.className='secondary'; rem.textContent='✕'; rem.onclick=()=>removeItem(it.item);
          right.append(minus, qty, plus, rem);
          row.append(left, right);
          wrap.appendChild(row);
        });
        listEl.appendChild(wrap);
      });
    }

    function renderSuggestions(sug){
      histEl.innerHTML = '';
      seasonEl.innerHTML = '';
      (sug.history||[]).forEach(x=> {
        const b = document.createElement('button'); b.className='ghost'; b.textContent = `+ ${x}`; b.onclick=()=>quickAdd(x);
        histEl.appendChild(b);
      });
      (sug.seasonal||[]).forEach(x=> {
        const b = document.createElement('button'); b.className='ghost'; b.textContent = `+ ${x}`; b.onclick=()=>quickAdd(x);
        seasonEl.appendChild(b);
      });
    }

    async function quickAdd(item){
      await fetch('/api/list', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({action:'add', item, quantity:1})});
      refreshList();
    }
    async function removeItem(item){
      await fetch('/api/list', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({action:'remove', item})});
      refreshList();
    }
    async function updateQty(item, quantity){
      await fetch('/api/list', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({action:'modify', item, quantity})});
      refreshList();
    }

    async function sendCommand(text, lang){
      spin.classList.add('show');
      resultsEl.innerHTML = ''; // Clear previous results
      const res = await fetch('/api/command', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({text, lang})});
      const data = await res.json();
      spin.classList.remove('show');
      transcriptEl.textContent = `"${data.transcript || text}"`;
      
      if(data.intent === 'search'){
        renderResults(data.results, data.query);
      } else {
        renderList(data.list);
        renderSuggestions(data.suggestions);
        if(data.message){
             const info = document.createElement('div'); info.className='result'; info.textContent = data.message;
             resultsEl.prepend(info);
        }
      }
      if(data.substitutes && data.substitutes.length){
        const info = document.createElement('div'); info.className='result'; info.textContent = 'Substitutes available: ' + data.substitutes.join(', ');
        resultsEl.prepend(info);
      }
    }

    function renderResults(items, query){
      resultsEl.innerHTML = '';
      const info = document.createElement('div'); info.className='pill';
      const qparts = [];
      if(query.item) qparts.push(query.item);
      if(query.brand) qparts.push('brand '+query.brand);
      if(query.min_price!=null) qparts.push('≥ ₹'+query.min_price);
      if(query.max_price!=null) qparts.push('≤ ₹'+query.max_price);
      info.textContent = `Found ${items.length} result(s) for: ` + (qparts.join(', ') || 'all');
      resultsEl.appendChild(info);

      if(items.length === 0){
        const d = document.createElement('div'); d.className='result';
        d.textContent = 'No products found matching your criteria.';
        resultsEl.appendChild(d);
        return;
      }

      items.forEach(x=>{
        const d = document.createElement('div'); d.className='result';
        d.innerHTML = `<div><b>${x.name}</b> · ${x.brand} · ${x.size}</div><div class="price">₹ ${x.price}</div><div><span class="pill">${x.category}</span> ${x.promo?'<span class="pill" style="background:var(--accent2); color:white;">On Sale!</span>':''}</div>`;
        const btn = document.createElement('button'); btn.textContent='Add to List'; btn.onclick=()=>quickAdd(x.name);
        d.appendChild(btn);
        resultsEl.appendChild(d);
      });
    }

    // Voice recognition via Web Speech API
    let recog; const startBtn = document.getElementById('startBtn'); const stopBtn = document.getElementById('stopBtn'); const langSel = document.getElementById('lang');
    function initRecog(){
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if(!SR){ transcriptEl.textContent = 'SpeechRecognition not supported in this browser.'; startBtn.disabled = true; return; }
      recog = new SR();
      recog.lang = langSel.value;
      recog.interimResults = false; recog.continuous = true;
      recog.onresult = (e)=>{
        const last = e.results[e.results.length-1];
        const text = last[0].transcript.trim();
        transcriptEl.textContent = text;
        sendCommand(text, langSel.value);
      };
      recog.onstart = ()=>{ startBtn.disabled = true; stopBtn.disabled = false; };
      recog.onend = ()=>{ startBtn.disabled = false; stopBtn.disabled = true; };
      recog.onerror = (e)=>{ transcriptEl.textContent = 'Voice error: '+ (e.error||'unknown'); };
    }
    startBtn.onclick = ()=>{ if(!recog) initRecog(); if(recog){ recog.lang = langSel.value; recog.start(); }};
    stopBtn.onclick = ()=>{ if(recog) recog.stop(); };

    manual.addEventListener('keydown', (e)=>{
      if(e.key==='Enter'){
        const text = manual.value.trim(); if(!text) return; manual.value='';
        transcriptEl.textContent = text; sendCommand(text, langSel.value);
      }
    });

    refreshList();
    initRecog();
  </script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)