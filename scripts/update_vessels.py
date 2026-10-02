"""Collect last AIS positions of fleet MMSIs from the free aisstream.io feed -> data/vessels_live.js. Needs env AISSTREAM_API_KEY."""
import os, re, json, asyncio, datetime
import websockets

KEY = os.environ.get("AISSTREAM_API_KEY")
if not KEY: raise SystemExit("AISSTREAM_API_KEY not set - skipping")
fleet = json.loads(re.sub(r"(\{|,)\s*([a-zA-Z_]+):", r'\1"\2":', re.search(r"=(\[.*\]);", open("data/fleet.js", encoding="utf-8").read(), re.S).group(1)))
mmsis = {v["mmsi"]: v["name"] for v in fleet if v.get("mmsi")}
if not mmsis: raise SystemExit("No MMSI configured in data/fleet.js")
NAV = {0: "Under way (engine)", 1: "At anchor", 2: "Not under command", 3: "Restricted manoeuvrability", 5: "Moored", 7: "Fishing", 8: "Under way (sailing)", 15: "Not defined"}

async def run():
    got = {}
    async with websockets.connect("wss://stream.aisstream.io/v0/stream") as ws:
        await ws.send(json.dumps({"APIKey": KEY, "BoundingBoxes": [[[-90, -180], [90, 180]]],
                                  "FiltersShipMMSI": list(mmsis), "FilterMessageTypes": ["PositionReport"]}))
        try:
            async with asyncio.timeout(240):
                async for raw in ws:
                    m = json.loads(raw); p = m["Message"]["PositionReport"]; k = str(m["MetaData"]["MMSI"])
                    got[mmsis[k]] = {"mmsi": k, "lat": p["Latitude"], "lon": p["Longitude"], "sog": p["Sog"],
                                     "status": NAV.get(p["NavigationalStatus"], "—"), "time": m["MetaData"]["time_utc"][:16] + " UTC"}
                    if len(got) == len(mmsis): break
        except TimeoutError: pass
    return got

new = asyncio.run(run())
try: old = json.loads(re.search(r"positions:(\{.*\})\}", open("data/vessels_live.js").read(), re.S).group(1))
except Exception: old = {}
old.update(new)   # keep last known position for vessels not heard this run
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
open("data/vessels_live.js", "w").write('window.VESSELS_LIVE={updated:"%s",positions:%s};' % (now, json.dumps(old)))
print("positions:", list(new))
