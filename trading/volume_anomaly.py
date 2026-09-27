#!/usr/bin/env python3
"""Volume anomalies on 5m/15m candles: who pushed volume in, and did price move?

Per candle: volume, taker buy/sell volume, delta = buy - sell, RVOL (volume vs
rolling median), range vs rolling median range.

Events:
  ABSORB_BULL   high RVOL, sellers aggressive (delta < 0), price did not fall
                -> passive buyers absorbed the selling
  ABSORB_BEAR   high RVOL, buyers aggressive (delta > 0), price did not rise
  CLIMAX_UP/DN  high RVOL and wide range in the delta direction (exhaustion or breakout)
  DIVERGENCE    candle closes one way, delta points the other way

Data: Binance USD-M futures klines (they carry taker buy volume).
  --source vision   monthly archives from data.binance.vision (history, works everywhere)
  --source live     fapi.binance.com (may be geo-blocked in some regions)

Usage:
    python3 volume_anomaly.py BTCUSDT --tf 5m --months 2026-07 2026-08
    python3 volume_anomaly.py ETHUSDT --tf 15m --source live --limit 500
"""
import argparse
import csv
import io
import json
import statistics
import urllib.request
import zipfile
from datetime import datetime, timezone

VISION = "https://data.binance.vision/data/futures/um/monthly/klines/{s}/{tf}/{s}-{tf}-{m}.zip"
LIVE = "https://fapi.binance.com/fapi/v1/klines?symbol={s}&interval={tf}&limit={n}"


def fetch_vision(symbol, tf, months):
    rows = []
    for m in months:
        with urllib.request.urlopen(VISION.format(s=symbol, tf=tf, m=m), timeout=60) as r:
            z = zipfile.ZipFile(io.BytesIO(r.read()))
        for line in csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))):
            if line[0].isdigit():
                rows.append(line)
    return rows


def fetch_live(symbol, tf, n):
    with urllib.request.urlopen(LIVE.format(s=symbol, tf=tf, n=n), timeout=30) as r:
        return json.load(r)


def to_bars(rows):
    bars = []
    for x in rows:
        o, h, l, c, v, tb = map(float, (x[1], x[2], x[3], x[4], x[5], x[9]))
        bars.append({"t": int(x[0]), "o": o, "h": h, "l": l, "c": c, "v": v,
                     "buy": tb, "sell": v - tb, "delta": 2 * tb - v})
    return bars


def enrich(bars, win=96):
    for i, b in enumerate(bars):
        past = bars[max(0, i - win):i]
        if len(past) < win // 2:
            b["rvol"] = b["rrange"] = None
            continue
        med_v = statistics.median(p["v"] for p in past) or 1e-9
        med_r = statistics.median(p["h"] - p["l"] for p in past) or 1e-9
        b["rvol"] = b["v"] / med_v
        b["rrange"] = (b["h"] - b["l"]) / med_r
        b["dshare"] = b["delta"] / b["v"] if b["v"] else 0  # -1..+1, share of aggressive side
    return bars


def mark_sweeps(bars, n=48):
    """Liquidity sweep: candle pierces the prior n-bar low/high and closes back inside."""
    for i, b in enumerate(bars):
        past = bars[max(0, i - n):i]
        b["sweep"] = 0
        if len(past) < n:
            continue
        lo, hi = min(p["l"] for p in past), max(p["h"] for p in past)
        if b["l"] < lo and b["c"] > lo:
            b["sweep"] = +1
        elif b["h"] > hi and b["c"] < hi:
            b["sweep"] = -1
    return bars


def classify(b, rvol_min=2.5, narrow=1.2, wide=2.0, dmin=0.15):
    """Return (event, direction) where direction +1 = bullish, -1 = bearish."""
    if b.get("rvol") is None or b["rvol"] < rvol_min:
        return None, 0
    ds, move = b["dshare"], b["c"] - b["o"]
    rng = b["h"] - b["l"] or 1e-9
    close_pos = (b["c"] - b["l"]) / rng  # 0 = closed at low, 1 = at high
    if b["rrange"] <= narrow:
        if ds <= -dmin and close_pos >= 0.5:
            return "ABSORB_BULL", +1
        if ds >= dmin and close_pos <= 0.5:
            return "ABSORB_BEAR", -1
    if b["rrange"] >= wide:
        if ds >= dmin and move > 0:
            return "CLIMAX_UP", +1
        if ds <= -dmin and move < 0:
            return "CLIMAX_DN", -1
    if ds >= dmin and move < 0:
        return "DIVERGENCE", -1
    if ds <= -dmin and move > 0:
        return "DIVERGENCE", +1
    return "HIGH_VOL", 0


def event_study(bars, horizons=(3, 6, 12), sweep_rvol=2.0):
    """Forward return in direction of the signal, % of price, gross of fees."""
    stats = {}

    def add(key, i, d):
        s = stats.setdefault(key, {h: [] for h in horizons})
        for h in horizons:
            if i + h < len(bars):
                s[h].append(d * 100 * (bars[i + h]["c"] - bars[i]["c"]) / bars[i]["c"])

    for i, b in enumerate(bars):
        ev, d = classify(b)
        b["event"], b["dir"] = ev, d
        if ev and d:
            add(ev, i, d)
        sw = b.get("sweep", 0)
        if sw:
            add("SWEEP_any", i, sw)
            if b.get("rvol") and b["rvol"] >= sweep_rvol:
                add("SWEEP+RVOL", i, sw)
                if b["dshare"] * sw < 0:  # aggressive flow into the sweep, price reclaimed = absorption
                    add("SWEEP+ABSORB", i, sw)
    base = {h: [abs(100 * (bars[i + h]["c"] - bars[i]["c"]) / bars[i]["c"])
                for i in range(len(bars) - h)] for h in horizons}
    return stats, base


def fmt_t(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol", nargs="?", default="BTCUSDT")
    ap.add_argument("--tf", default="5m", choices=["1m", "5m", "15m", "1h"])
    ap.add_argument("--source", default="vision", choices=["vision", "live"])
    ap.add_argument("--months", nargs="*", default=["2026-08"])
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--sweep", type=int, default=48, help="lookback bars for liquidity sweep")
    ap.add_argument("--last", type=int, default=15, help="print N latest events")
    a = ap.parse_args()

    rows = fetch_vision(a.symbol, a.tf, a.months) if a.source == "vision" else fetch_live(a.symbol, a.tf, a.limit)
    bars = mark_sweeps(enrich(to_bars(rows)), a.sweep)
    stats, base = event_study(bars)

    print(f"{a.symbol} {a.tf}  bars={len(bars)}  {fmt_t(bars[0]['t'])} .. {fmt_t(bars[-1]['t'])} UTC")
    print("\nEvent study: mean forward move in signal direction, % (gross, before ~0.1% round-trip fees)")
    hz = sorted(base)
    print(f"{'event':12s} {'n':>5s} " + " ".join(f"{'+'+str(h)+'b mean':>11s} {'hit%':>5s}" for h in hz))
    for ev, s in sorted(stats.items()):
        n = len(s[hz[0]])
        cells = []
        for h in hz:
            xs = s[h]
            cells.append(f"{statistics.mean(xs):+11.3f} {100*sum(x > 0 for x in xs)/len(xs):5.0f}" if xs else f"{'—':>11s} {'—':>5s}")
        print(f"{ev:12s} {n:5d} " + " ".join(cells))
    print("baseline     avg |move|: " + "  ".join(f"+{h}b {statistics.mean(base[h]):.3f}%" for h in hz))

    evs = [b for b in bars if b.get("event")][-a.last:]
    print(f"\nLatest {len(evs)} high-volume candles:")
    print(f"{'time UTC':16s} {'event':12s} {'close':>10s} {'RVOL':>5s} {'range×':>6s} {'delta%':>7s}")
    for b in evs:
        print(f"{fmt_t(b['t']):16s} {b['event']:12s} {b['c']:10.1f} {b['rvol']:5.1f} {b['rrange']:6.1f} {100*b['dshare']:+7.0f}")


if __name__ == "__main__":
    main()
