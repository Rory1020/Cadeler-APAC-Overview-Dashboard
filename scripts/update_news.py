"""APAC offshore-wind news -> data/news.js. Publisher RSS (with thumbnails) + Google News; near-duplicates removed."""
import json, re, datetime, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

UA = {"User-Agent": "Mozilla/5.0"}
DIRECT = {"https://www.offshorewind.biz/feed/": "offshoreWIND.biz", "https://www.renews.biz/feed/": "reNEWS",
          "https://www.windpowermonthly.com/rss/news": "Windpower Monthly"}   # any that fail are skipped
APAC = r"taiwan|japan|korea|australia|philippine|vietnam|apac|asia|singapore|india\b|china|chinese|victoria|gippsland"
CADELER = r"cadeler|nexra|wind (maker|zaratan|scylla|keeper|orca|osprey|peak|mover|pace|ally)"
COMP = r"\bdeme\b|jan de nul|van oord|boskalis|windcarrier|seajacks|swire blue|cosco|cdwe|sea challenger|green jade"
GOOGLE = {"cadeler": '(Cadeler OR Nexra) (Taiwan OR Japan OR Korea OR Asia OR APAC) when:30d',
          "competitors": '(DEME OR "Jan De Nul" OR "Van Oord" OR Boskalis OR "Fred. Olsen Windcarrier" OR Seajacks OR "Swire Blue Ocean" OR COSCO) offshore wind (Taiwan OR Japan OR Korea OR Australia OR Asia) when:14d',
          "industry": 'offshore wind (Taiwan OR Japan OR Korea OR Australia OR Philippines OR Vietnam OR APAC OR Asia) when:7d'}
STOP = set("the and for with from its new over after into says said will that this are was has have".split())
W = lambda t: {w for w in re.findall(r"[a-z0-9]+", t.lower()) if w not in STOP and len(w) > 2}
def similar(a, b):
    x, y = W(a), W(b); i = len(x & y)
    return bool(i) and i / min(len(x), len(y)) >= .6 and i / len(x | y) >= .4
def get(url): return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25).read()
def og_image(url):
    try:
        html = get(url)[:200000].decode("utf-8", "ignore")
        m = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', html) or re.search(r'content=["\']([^"\']+)["\'][^>]*property=["\']og:image', html)
        return m.group(1) if m else ""
    except Exception: return ""
def parse(xml, source=None):
    out = []
    for it in ET.fromstring(xml).iter("item"):
        img = ""
        for ch in it:
            tag = ch.tag.split("}")[-1]
            if tag in ("content", "thumbnail", "enclosure") and ch.get("url") and not img: img = ch.get("url")
        if not img:
            m = re.search(r'<img[^>]+src=["\']([^"\']+)', ET.tostring(it, encoding="unicode"))
            img = m.group(1).replace("&amp;", "&") if m else ""
        title = re.sub(r"\s+-\s+[^-]+$", "", it.findtext("title", "")).strip() if source is None else it.findtext("title", "").strip()
        try: date = parsedate_to_datetime(it.findtext("pubDate")).strftime("%Y-%m-%d")
        except Exception: continue
        out.append({"title": title, "url": it.findtext("link", ""), "source": source or it.findtext("source", ""), "date": date, "img": img})
    return out
def category(t):
    t = t.lower()
    return "cadeler" if re.search(CADELER, t) else "competitors" if re.search(COMP, t) and re.search(APAC, t) else "industry" if re.search(APAC, t) and "wind" in t else None

pool = []   # (category, item): direct feeds first (they carry images), then Google News
for url, name in DIRECT.items():
    try:
        for it in parse(get(url), name):
            c = category(it["title"])
            if c: pool.append((c, it))
    except Exception as e: print("skip", name, e)
for c, q in GOOGLE.items():
    try:
        for it in parse(get("https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q, "hl": "en", "gl": "US", "ceid": "US:en"}))):
            pool.append((c, it))
    except Exception as e: print("failed google", c, e)

cutoff = (datetime.date.today() - datetime.timedelta(days=45)).isoformat()
kept = []
for c, it in sorted(pool, key=lambda p: ("cadeler competitors industry".split().index(p[0]), p[1]["date"]), reverse=False):
    if it["date"] < cutoff: continue
    d = next((k for k in kept if k[1]["url"] == it["url"] or similar(k[1]["title"], it["title"])), None)
    if d:                                           # same story: keep the most complete headline, and a picture
        if len(it["title"]) > len(d[1]["title"]): d[1]["title"] = it["title"]
        if not d[1]["img"] and it["img"]: d[1]["img"] = it["img"]
        continue
    kept.append((c, dict(it)))
fetched = 0
for c, it in kept:                                  # fill missing thumbnails from the article page (publisher links only)
    if not it["img"] and "news.google.com" not in it["url"] and fetched < 15: it["img"] = og_image(it["url"]); fetched += 1
res = {c: sorted([i for k, i in kept if k == c], key=lambda x: x["date"], reverse=True)[:8] for c in ("industry", "competitors", "cadeler")}
res["updated"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
if sum(len(v) for k, v in res.items() if k != "updated") == 0: raise SystemExit("No news fetched - keeping previous data/news.js")
open("data/news.js", "w", encoding="utf-8").write("window.NEWS=" + json.dumps(res, ensure_ascii=False, indent=1) + ";")
print("ok", {k: len(v) for k, v in res.items() if k != "updated"})
