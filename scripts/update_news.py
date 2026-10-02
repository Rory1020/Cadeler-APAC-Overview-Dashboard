"""Fetch APAC offshore-wind news from Google News RSS -> data/news.js, removing near-duplicate stories."""
import json, urllib.request, urllib.parse, datetime, re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

APAC = "(Taiwan OR Japan OR Korea OR Australia OR Philippines OR Vietnam OR APAC OR Asia)"
FEEDS = {   # order = priority: a story shared by several sections stays in the first one
 "cadeler":     '(Cadeler OR Nexra) (Taiwan OR Japan OR Korea OR Asia OR APAC) when:30d',
 "competitors": f'(DEME OR "Jan De Nul" OR "Van Oord" OR Boskalis OR "Fred. Olsen Windcarrier" OR Seajacks OR "Swire Blue Ocean" OR COSCO) offshore wind {APAC} when:14d',
 "industry":    f'offshore wind {APAC} when:7d',
}
STOP = set("the a an of in on at to for and or with by from as is are its it new over after into says said will".split())
def words(t): return {w for w in re.findall(r"[a-z0-9]+", t.lower()) if w not in STOP and len(w) > 2}
def similar(a, b):
    wa, wb = words(a), words(b)
    return bool(wa and wb) and len(wa & wb) / min(len(wa), len(wb)) >= 0.6 and len(wa & wb) / len(wa | wb) >= 0.4

def fetch(q):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q, "hl": "en", "gl": "US", "ceid": "US:en"})
    root = ET.fromstring(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())
    out = []
    for it in root.iter("item"):
        src = it.findtext("source", "")
        title = re.sub(r"\s+-\s+[^-]+$", "", it.findtext("title", "")).strip()   # drop " - Publisher" suffix
        out.append({"title": title, "url": it.findtext("link", ""), "source": src,
                    "date": parsedate_to_datetime(it.findtext("pubDate")).strftime("%Y-%m-%d")})
    return sorted(out, key=lambda x: x["date"], reverse=True)

result = {k: [] for k in FEEDS}
kept = []   # (section, item)
for sec, q in FEEDS.items():
    try: items = fetch(q)
    except Exception as e: print("failed", sec, e); continue
    for it in items:
        dup = next((k for k in kept if similar(k[1]["title"], it["title"])), None)
        if dup:
            if len(it["title"]) > len(dup[1]["title"]): dup[1].update(it)   # keep the more complete headline
            continue
        kept.append((sec, it)); result[sec].append(it)
result = {k: v[:10] for k, v in result.items()}
result["updated"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
open("data/news.js", "w", encoding="utf-8").write("window.NEWS=" + json.dumps(result, ensure_ascii=False, indent=1) + ";")
print("ok", {k: len(v) for k, v in result.items() if k != "updated"})
