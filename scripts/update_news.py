"""Fetch APAC offshore-wind news from Google News RSS -> data/news.js (run daily by GitHub Actions)."""
import json, urllib.request, urllib.parse, datetime, re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

APAC = "(Taiwan OR Japan OR Korea OR Australia OR Philippines OR Vietnam OR APAC OR Asia)"
FEEDS = {
 "industry":    f'offshore wind {APAC} when:7d',
 "competitors": f'(DEME OR "Jan De Nul" OR "Van Oord" OR Boskalis OR "Fred. Olsen Windcarrier" OR Seajacks OR "Swire Blue Ocean" OR COSCO) offshore wind {APAC} when:14d',
 "cadeler":     '(Cadeler OR Nexra) (Taiwan OR Japan OR Korea OR Asia OR APAC) when:30d',
}
def fetch(q, limit=10):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q, "hl": "en", "gl": "US", "ceid": "US:en"})
    root = ET.fromstring(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())
    items, seen = [], set()
    for it in root.iter("item"):
        title = it.findtext("title", "")
        key = re.sub(r"\W+", "", title.lower())[:60]
        if key in seen: continue
        seen.add(key)
        items.append({"title": title, "url": it.findtext("link", ""), "source": it.findtext("source", ""),
                      "date": parsedate_to_datetime(it.findtext("pubDate")).strftime("%Y-%m-%d")})
    return sorted(items, key=lambda x: x["date"], reverse=True)[:limit]

out = {"updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
for k, q in FEEDS.items():
    try: out[k] = fetch(q)
    except Exception as e: print("failed", k, e); out[k] = []
open("data/news.js", "w", encoding="utf-8").write("window.NEWS=" + json.dumps(out, ensure_ascii=False, indent=1) + ";")
print("ok", {k: len(v) for k, v in out.items() if k != "updated"})
