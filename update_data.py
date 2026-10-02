"""Daily: ask Claude (with web search) to refresh APAC tenders & projects. Needs env ANTHROPIC_API_KEY."""
import os, re, json, datetime, urllib.request

KEY = os.environ.get("ANTHROPIC_API_KEY")
if not KEY: raise SystemExit("ANTHROPIC_API_KEY not set - skipping")
MODEL = "claude-sonnet-5-5"
today = datetime.date.today().isoformat()

def load(path, var):
    s = open(path, encoding="utf-8").read()
    m = re.search(r"window\.%s=(\[.*?\n\]);" % var, s, re.S)
    return json.loads(re.sub(r"(\{|,)\s*([a-zA-Z_]+):", r'\1"\2":', m.group(1)))   # JS object literal -> JSON

def ask(prompt):
    msgs = [{"role": "user", "content": prompt}]
    for _ in range(6):
        body = json.dumps({"model": MODEL, "max_tokens": 8000, "messages": msgs,
            "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 10}]}).encode()
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", body,
            {"x-api-key": KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        r = json.load(urllib.request.urlopen(req, timeout=300))
        if r["stop_reason"] != "pause_turn":
            return "".join(b.get("text", "") for b in r["content"] if b["type"] == "text")
        msgs += [{"role": "assistant", "content": r["content"]}]
    raise RuntimeError("too many pauses")

def refresh(path, var, kind, schema, hint):
    cur = load(path, var)
    prompt = f"""Today is {today}. You maintain a dashboard for Cadeler (offshore wind installation vessels) covering APAC.
Current {kind} list (JSON):
{json.dumps(cur, ensure_ascii=False)}

Use web search to update it: {hint}
Rules: keep every existing id (update fields if facts changed, never delete - mark finished items instead); add genuinely new APAC items with a new kebab-case id; only use facts found in sources; give a real source url for each item; cc = lowercase ISO country code (tw, jp, kr, au, ph, vn, cn, in, sg...).
Schema per item: {schema}
Return ONLY the full updated JSON array, no prose, no markdown fences."""
    out = ask(prompt)
    new = json.loads(re.search(r"\[.*\]", out, re.S).group(0))
    old_ids = {x["id"] for x in cur}
    assert isinstance(new, list) and len(new) >= len(cur) - 0 and all("id" in x for x in new)
    for x in new:
        if x["id"] not in old_ids: x["added"] = today
        elif "added" not in x: x["added"] = next(o.get("added", today) for o in cur if o["id"] == x["id"])
    head = open(path, encoding="utf-8").read().split("window.")[0]
    tail = open(path, encoding="utf-8").read().split(";\nwindow.AUCTIONS", 1)
    body = f"window.{var}=" + json.dumps(new, ensure_ascii=False, indent=1) + ";"
    extra = ("\nwindow.AUCTIONS" + tail[1]) if len(tail) > 1 else ""
    open(path, "w", encoding="utf-8").write(head + body + extra)
    print(var, "updated:", len(cur), "->", len(new))

for fn in (lambda: refresh("data/tenders.js", "TENDERS", "tender",
        '{id,name,cc,status:"open|closing|planned|awarded",detail,deadline:"YYYY-MM-DD or null",why:"why it matters to Cadeler",actions:[{t,due:"YYYY-MM-DD"}] (2-3 concrete next steps),url}',
        "ongoing, upcoming and recently awarded offshore wind tenders/auctions in Taiwan, Japan, South Korea, Australia, Philippines, Vietnam, India, China."),
    lambda: refresh("data/projects.js", "PROJECTS", "project",
        '{id,name,cc,stage:"planned|active|complete|risk",window:"timing",note:"1 line status",url}',
        "offshore wind projects in APAC that are in construction/installation or scheduled to start within the next 12 months.")):
    try: fn()
    except Exception as e: print("FAILED (kept old data):", e)
