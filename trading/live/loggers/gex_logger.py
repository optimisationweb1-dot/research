#!/usr/bin/env python3
"""Snapshot GEX levels every run (cron every 15 min) to build a history that does not exist for free.

Sources:
  - Deribit BTC/ETH options (public API) via trading/gex_levels.py (all expiries, 0DTE, 1DTE)
  - IBIT options (BlackRock BTC ETF, ~half of BTC options OI by press reports) via CBOE delayed quotes JSON
    (15-min delayed, gamma supplied by CBOE; check CBOE terms of use before relying on it). IBIT strikes are
    converted to BTC-price equivalents with the ratio BTC spot / IBIT price.
Output: live/state/gex/YYYY-MM.jsonl, one JSON object per snapshot.
"""
import json
import os
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import gex_levels as G  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "gex")
CBOE = "https://cdn.cboe.com/api/global/delayed_quotes/options/IBIT.json"


def deribit_snapshot(cur):
    spot, opts = G.load(cur)
    exps = sorted({o["expiry"] for o in opts})
    now = datetime.now(timezone.utc)
    near = [e for e in exps if (e - now).total_seconds() < 86400]
    e0 = near[0] if near else None
    e1 = next((e for e in exps if e != e0), None)
    by_k = G.gex_by_strike(opts, spot)
    top = sorted(by_k.items(), key=lambda kv: -abs(kv[1]))[:40]
    return {"spot": spot, "all": G.levels(opts, spot),
            "0dte": G.levels([o for o in opts if o["expiry"] == e0], spot) if e0 else None,
            "1dte": G.levels([o for o in opts if o["expiry"] == e1], spot) if e1 else None,
            "expiry_0dte": e0, "expiry_1dte": e1,
            "strikes_top40": [[k, round(v)] for k, v in top]}


def parse_occ(sym):
    # IBIT260930C00030000 -> (date, 'C', 30.0)
    root = sym[:-15]
    d, cp, k = sym[len(root):len(root) + 6], sym[-9], int(sym[-8:]) / 1000
    return datetime.strptime(d, "%y%m%d").date(), cp, k


def ibit_snapshot(btc_spot):
    req = urllib.request.Request(CBOE, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    data = d["data"]
    s = float(data["current_price"])
    ratio = btc_spot / s
    today = datetime.now(timezone.utc).date()
    groups = {"all": defaultdict(float), "0dte": defaultdict(float), "1dte": defaultdict(float)}
    exps = sorted({parse_occ(o["option"])[0] for o in data["options"] if o.get("open_interest")})
    fut = [e for e in exps if e >= today]
    e0 = fut[0] if fut else None
    e1 = fut[1] if len(fut) > 1 else None
    for o in data["options"]:
        oi, g = float(o.get("open_interest") or 0), float(o.get("gamma") or 0)
        if not oi or not g:
            continue
        exp, cp, k = parse_occ(o["option"])
        if exp < today:
            continue
        gex = g * oi * 100 * s * s * 0.01 * (1 if cp == "C" else -1)
        kb = round(k * ratio, -2)
        groups["all"][kb] += gex
        if exp == e0:
            groups["0dte"][kb] += gex
        if exp == e1:
            groups["1dte"][kb] += gex
    out = {"cboe_timestamp": d.get("timestamp"), "ibit_price": s, "btc_per_ibit_ratio": ratio,
           "expiry_0dte": str(e0), "expiry_1dte": str(e1)}
    for name, gk in groups.items():
        above = {k: v for k, v in gk.items() if k > btc_spot}
        below = {k: v for k, v in gk.items() if k < btc_spot}
        out[name] = {"net_gex_usd_per_1pct": round(sum(gk.values())),
                     "call_wall_btc": max(above, key=above.get) if above else None,
                     "put_wall_btc": min(below, key=below.get) if below else None,
                     "strikes_top20": [[k, round(v)] for k, v in sorted(gk.items(), key=lambda kv: -abs(kv[1]))[:20]]}
    return out


def main():
    ts = datetime.now(timezone.utc)
    snap = {"ts": ts.isoformat(timespec="seconds")}
    for cur in ("BTC", "ETH"):
        try:
            snap[f"deribit_{cur}"] = deribit_snapshot(cur)
        except Exception as e:
            snap[f"deribit_{cur}"] = {"error": str(e)}
    try:
        snap["ibit"] = ibit_snapshot(snap["deribit_BTC"]["spot"])
    except Exception as e:
        snap["ibit"] = {"error": str(e)}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"{ts:%Y-%m}.jsonl"), "a") as f:
        f.write(json.dumps(snap, default=str) + "\n")
    b = snap.get("deribit_BTC", {})
    print(ts.isoformat(timespec="seconds"), "BTC", b.get("spot"), "0dte",
          (b.get("0dte") or {}).get("call_wall"), "| IBIT all call wall",
          (snap.get("ibit", {}).get("all") or {}).get("call_wall_btc"))


if __name__ == "__main__":
    main()
