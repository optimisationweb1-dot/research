#!/usr/bin/env python3
"""GEX key levels (Zero Gamma, Call Wall, Put Wall) for BTC/ETH from Deribit options.

Public Deribit API, no keys. Model, not fact: assumes dealers are long calls and
short puts (classic GEX convention). Read levels as zones.

Usage:
    python3 gex_levels.py BTC            # all expiries + 0DTE + 1DTE
    python3 gex_levels.py ETH --json
"""
import argparse
import json
import math
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

API = "https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency={c}&kind=option"
MONTHS = {m: i for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}


def parse_instrument(name):
    # BTC-28SEP26-88000-P ; Deribit options expire 08:00 UTC
    _, exp, strike, cp = name.split("-")
    day, mon, yr = int(exp[:-5]), MONTHS[exp[-5:-2]], 2000 + int(exp[-2:])
    expiry = datetime(yr, mon, day, 8, tzinfo=timezone.utc)
    return expiry, float(strike), cp


def bs_gamma(s, k, t, iv):
    if t <= 0 or iv <= 0:
        return 0.0
    d1 = (math.log(s / k) + 0.5 * iv * iv * t) / (iv * math.sqrt(t))
    return math.exp(-0.5 * d1 * d1) / math.sqrt(2 * math.pi) / (s * iv * math.sqrt(t))


def load(currency):
    with urllib.request.urlopen(API.format(c=currency), timeout=30) as r:
        rows = json.load(r)["result"]
    now = datetime.now(timezone.utc)
    opts = []
    for x in rows:
        if not x.get("open_interest") or not x.get("mark_iv"):
            continue
        expiry, k, cp = parse_instrument(x["instrument_name"])
        t = (expiry - now).total_seconds() / (365 * 86400)
        if t <= 0:
            continue
        opts.append({"expiry": expiry, "k": k, "cp": cp, "t": t,
                     "iv": x["mark_iv"] / 100, "oi": x["open_interest"]})
    spot = next(x["estimated_delivery_price"] for x in rows if x.get("estimated_delivery_price"))
    return spot, opts


def gex_by_strike(opts, s):
    """USD gamma exposure per 1% move, per strike. Calls +, puts -."""
    out = defaultdict(float)
    for o in opts:
        g = bs_gamma(s, o["k"], o["t"], o["iv"]) * o["oi"] * s * s * 0.01
        out[o["k"]] += g if o["cp"] == "C" else -g
    return out


def total_gex(opts, s):
    return sum(gex_by_strike(opts, s).values())


def zero_gamma(opts, spot, span=0.15, steps=300):
    grid = [spot * (1 - span + 2 * span * i / steps) for i in range(steps + 1)]
    vals = [total_gex(opts, s) for s in grid]
    flips = []
    for i in range(steps):
        if vals[i] == 0 or vals[i] * vals[i + 1] < 0:
            a, b, va, vb = grid[i], grid[i + 1], vals[i], vals[i + 1]
            flips.append(a - va * (b - a) / (vb - va) if vb != va else a)
    return min(flips, key=lambda f: abs(f - spot)) if flips else None


def levels(opts, spot):
    if not opts:
        return None
    by_k = gex_by_strike(opts, spot)
    above = {k: v for k, v in by_k.items() if k > spot}
    below = {k: v for k, v in by_k.items() if k < spot}
    call_wall = max(above, key=above.get) if above else None
    put_wall = min(below, key=below.get) if below else None
    zg = zero_gamma(opts, spot)
    net = sum(by_k.values())

    def dist(x):
        return None if x is None else {"level": round(x, 1), "pts": round(x - spot, 1),
                                       "pct": round(100 * (x - spot) / spot, 2)}
    return {"net_gex_usd_per_1pct": round(net), "regime": "positive" if net > 0 else "negative",
            "zero_gamma": dist(zg), "call_wall": dist(call_wall), "put_wall": dist(put_wall),
            "top_strikes": sorted(((k, round(v)) for k, v in by_k.items()),
                                  key=lambda kv: -abs(kv[1]))[:5]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("currency", nargs="?", default="BTC")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    spot, opts = load(a.currency.upper())
    expiries = sorted({o["expiry"] for o in opts})
    # 0DTE = nearest expiry if it settles within 24h; 1DTE = the next one
    near = [e for e in expiries if (e - datetime.now(timezone.utc)).total_seconds() < 86400]
    e0 = near[0] if near else None
    e1 = next((e for e in expiries if e != e0), None)
    res = {"currency": a.currency.upper(), "spot": spot,
           "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "all": levels(opts, spot),
           "0dte": levels([o for o in opts if o["expiry"] == e0], spot) if e0 else None,
           "0dte_expiry": e0.isoformat() if e0 else None,
           "1dte": levels([o for o in opts if o["expiry"] == e1], spot) if e1 else None,
           "1dte_expiry": e1.isoformat() if e1 else None}
    if a.json:
        print(json.dumps(res, indent=2, default=str))
        return
    print(f"{res['currency']} spot {spot:,.1f}  ({res['ts']})")
    for mode in ("all", "0dte", "1dte"):
        L = res[mode]
        if not L:
            print(f"\n[{mode}] no data")
            continue
        exp = res.get(f"{mode}_expiry") or "all expiries"
        print(f"\n[{mode}] {exp}  net GEX {L['net_gex_usd_per_1pct']/1e6:,.1f}M $/1%  regime={L['regime']}")
        for name in ("call_wall", "zero_gamma", "put_wall"):
            d = L[name]
            print(f"  {name:10s} " + ("—" if not d else f"{d['level']:>10,.0f}  {d['pts']:+9,.0f} pts  {d['pct']:+6.2f}%"))


if __name__ == "__main__":
    sys.exit(main())
