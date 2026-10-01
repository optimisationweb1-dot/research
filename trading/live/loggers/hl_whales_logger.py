#!/usr/bin/env python3
"""Hyperliquid whale positions logger (cron every 15 min).

Hyperliquid is an on-chain perp exchange: every account's open positions are public. We take the top-N
accounts of the public leaderboard by account value (refreshed daily) and snapshot their positions via
the public info API (clearinghouseState). Output per run:
  live/state/hl/positions_YYYY-MM.jsonl  - raw positions of each tracked wallet
  live/state/hl/agg_YYYY-MM.csv          - per coin: whale net notional (long - short), #long, #short
No keys, read-only. Note: top accounts include vaults/market makers (e.g. HLP); their flow is not
'directional whale' flow - keep the address column to filter later.
"""
import csv
import json
import os
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "hl")
LEADERBOARD = "https://stats-data.hyperliquid.xyz/Mainnet/leaderboard"
INFO = "https://api.hyperliquid.xyz/info"
TOP_N = int(os.environ.get("HL_TOP_N", "100"))


def post(payload):
    req = urllib.request.Request(INFO, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def top_wallets():
    path = os.path.join(OUT, "leaderboard_top.json")
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < 86400:
        return json.load(open(path))
    with urllib.request.urlopen(LEADERBOARD, timeout=60) as r:
        rows = json.load(r)["leaderboardRows"]
    rows.sort(key=lambda x: -float(x.get("accountValue") or 0))
    top = [{"address": x["ethAddress"], "account_value": float(x["accountValue"]), "name": x.get("displayName")}
           for x in rows[:TOP_N]]
    os.makedirs(OUT, exist_ok=True)
    json.dump(top, open(path, "w"))
    return top


def main():
    ts = datetime.now(timezone.utc)
    wallets = top_wallets()
    agg = defaultdict(lambda: {"net_usd": 0.0, "long_usd": 0.0, "short_usd": 0.0, "n_long": 0, "n_short": 0})
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"positions_{ts:%Y-%m}.jsonl"), "a") as f:
        for w in wallets:
            try:
                st = post({"type": "clearinghouseState", "user": w["address"]})
            except Exception as e:
                continue
            pos = []
            for ap in st.get("assetPositions", []):
                p = ap["position"]
                szi = float(p["szi"])
                val = float(p["positionValue"])
                pos.append({"coin": p["coin"], "szi": szi, "value_usd": val, "entry": p.get("entryPx"),
                            "upnl": p.get("unrealizedPnl"), "lev": (p.get("leverage") or {}).get("value"),
                            "liq_px": p.get("liquidationPx")})
                a = agg[p["coin"]]
                if szi > 0:
                    a["long_usd"] += val; a["n_long"] += 1; a["net_usd"] += val
                elif szi < 0:
                    a["short_usd"] += val; a["n_short"] += 1; a["net_usd"] -= val
            f.write(json.dumps({"ts": ts.isoformat(timespec="seconds"), "address": w["address"],
                                "account_value": st.get("marginSummary", {}).get("accountValue"),
                                "positions": pos}) + "\n")
            time.sleep(0.05)
    path = os.path.join(OUT, f"agg_{ts:%Y-%m}.csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        wr = csv.writer(f)
        if new:
            wr.writerow(["ts", "coin", "net_usd", "long_usd", "short_usd", "n_long", "n_short"])
        for coin, a in sorted(agg.items(), key=lambda kv: -abs(kv[1]["net_usd"])):
            wr.writerow([ts.isoformat(timespec="seconds"), coin, round(a["net_usd"]), round(a["long_usd"]),
                         round(a["short_usd"]), a["n_long"], a["n_short"]])
    top5 = sorted(agg.items(), key=lambda kv: -abs(kv[1]["net_usd"]))[:5]
    print(ts.isoformat(timespec="seconds"), f"wallets={len(wallets)}",
          "; ".join(f"{c} net {a['net_usd']/1e6:+.1f}M ({a['n_long']}L/{a['n_short']}S)" for c, a in top5))


if __name__ == "__main__":
    main()
