#!/usr/bin/env python3
"""Crowd-positioning 4h PAPER bot (strategy C_level 4h from strategies/funding_positioning.py::rcrowd).

Frozen rules (as backtested, src='level', pct=0.9):
    x_t  = ln(Binance global long/short ACCOUNT ratio) known at the 4h bar close
           (latest 5-minute snapshot stamped <= close - 6 min)
    p_t  = percentile of x_t among the previous 180 values (30 days of 4h bars)
    first bar with p >= 0.90 (crowd extremely long)  -> SHORT
    first bar with p <= 0.10 (crowd extremely short) -> LONG
    entry at the next 4h open (market), stop = close -/+ 2*ATR14(4h), target = 2R, max hold 18 bars (72h)
Paper only: fills are simulated on BingX 4h candles exactly like bt.engine (stop checked before target).

Run every 4 hours a few minutes after 00/04/08/12/16/20 UTC (cron in live/README.md).
Data: Binance public futures data API (not reachable from US clouds; works from EU servers),
BingX public candles via ccxt. No keys needed.
"""
import argparse
import json
import math
import os
import time
import urllib.request

import numpy as np

from live.tsmom_bot import STATE_DIR, load_env, log, make_exchange, record_trade, telegram

SYMBOLS = "BTC ETH SOL XRP DOGE BNB ADA AVAX LINK LTC".split()
PCT, LOOKBACK, STOP_ATR, RR, MAX_HOLD = 0.9, 180, 2.0, 2.0, 18
LAG_MS = 6 * 60 * 1000
BAR_MS = 4 * 3600 * 1000
TAKER, MAKER, SLIP = 0.0005, 0.0002, 0.0002
BINANCE = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"


# ------------------------------------------------------------------ data

def fetch_ratio(symbol, cache):
    """5m global L/S account ratio for the last ~30 days, cached incrementally {ts_ms: ratio}."""
    now = int(time.time() * 1000)
    start = max([int(k) for k in cache] + [now - 31 * 86400 * 1000]) + 1
    while start < now - 5 * 60 * 1000:
        url = f"{BINANCE}?symbol={symbol}USDT&period=5m&limit=500&startTime={start}"
        with urllib.request.urlopen(url, timeout=30) as r:
            rows = json.load(r)
        if not rows:
            break
        for x in rows:
            cache[str(int(x["timestamp"]))] = float(x["longShortRatio"])
        start = int(rows[-1]["timestamp"]) + 1
        if len(rows) < 500:
            break
    cutoff = now - 40 * 86400 * 1000
    return {k: v for k, v in cache.items() if int(k) >= cutoff}


def ratio_at(ts_sorted, vals, t_close):
    """Latest snapshot with ts + LAG <= t_close."""
    i = np.searchsorted(ts_sorted, t_close - LAG_MS, side="right") - 1
    return vals[i] if i >= 0 else np.nan


# ------------------------------------------------------------------ signal core (pure, testable)

def atr_ewm(h, l, c, n=14):
    pc = np.concatenate([[np.nan], c[:-1]])
    tr = np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    out = np.empty_like(tr)
    a = 1.0 / n
    out[0] = tr[0]
    for i in range(1, len(tr)):
        out[i] = out[i - 1] + a * (tr[i] - out[i - 1])
    return out


def roll_pct(x, n=LOOKBACK):
    out = np.full(len(x), np.nan)
    for t in range(n, len(x)):
        w = x[t - n:t]
        w = w[np.isfinite(w)]
        if len(w) >= n // 2 and np.isfinite(x[t]):
            out[t] = ((w < x[t]).sum() + 0.5 * (w == x[t]).sum()) / len(w)
    return out


def signals(o, h, l, c, x):
    """Arrays over closed 4h bars -> (signal, stop, target) decided at each bar close."""
    p = roll_pct(np.log(np.where(x > 0, x, np.nan)))
    hi, lo = p >= PCT, p <= 1 - PCT
    hi_prev = np.concatenate([[False], hi[:-1]])
    lo_prev = np.concatenate([[False], lo[:-1]])
    long_m = lo & ~lo_prev
    short_m = hi & ~hi_prev & ~long_m
    A = atr_ewm(h, l, c)
    sig = np.where(long_m, 1.0, np.where(short_m, -1.0, 0.0))
    stop = np.where(long_m, c - STOP_ATR * A, np.where(short_m, c + STOP_ATR * A, np.nan))
    tgt = np.where(long_m, c + RR * np.abs(c - stop), np.where(short_m, c - RR * np.abs(c - stop), np.nan))
    return sig, stop, tgt


# ------------------------------------------------------------------ paper book (mirrors bt.engine fills)

def step_position(pos, k, o, h, l, c, bars_open_next):
    """Manage an open market-entry position on closed bar k. Returns (exit_px, reason, fee) or None."""
    d, stop, tgt, k0 = pos["dir"], pos["stop"], pos["target"], pos["k0"]
    if (d > 0 and l[k] <= stop) or (d < 0 and h[k] >= stop):
        gap = k > k0 and ((d > 0 and o[k] < stop) or (d < 0 and o[k] > stop))
        return (o[k] if gap else stop) * (1 - d * SLIP), "stop", TAKER
    if (d > 0 and h[k] >= tgt) or (d < 0 and l[k] <= tgt):
        return tgt, "target", MAKER
    if k - k0 + 1 >= MAX_HOLD and bars_open_next is not None:
        return bars_open_next * (1 - d * SLIP), "time", TAKER
    return None


def _open(st, base, pe, t_fill, open_px, risk_pct, msgs):
    d = pe["dir"]
    entry = open_px * (1 + d * SLIP)
    if (d > 0 and entry > pe["stop"]) or (d < 0 and entry < pe["stop"]):
        qty = st["equity"] * risk_pct / 100 / abs(entry - pe["stop"])
        st["equity"] -= entry * qty * TAKER
        st["positions"][base] = {"dir": d, "entry": entry, "stop": pe["stop"], "target": pe["target"],
                                 "qty": qty, "t0": int(t_fill)}
        msgs.append(f"ENTRY {base} {'long' if d > 0 else 'short'} @ {entry:.6g} stop {pe['stop']:.6g} "
                    f"target {pe['target']:.6g}")


def process_symbol(st, base, t, o, h, l, c, sig, stop, tgt, last, forming_open, risk_pct, msgs, trades=None):
    """Advance the paper book over closed bars newer than `last` (mirrors bt.engine market-entry fills)."""
    for k in [k for k in range(len(t)) if t[k] > last]:
        next_open = o[k + 1] if k + 1 < len(t) else (forming_open[1] if forming_open else None)
        pe = st["pending"].get(base)
        if pe and pe["t_fill"] == int(t[k]):
            st["pending"].pop(base)
            _open(st, base, pe, t[k], o[k], risk_pct, msgs)
        pos = st["positions"].get(base)
        skip_signal = False
        if pos:
            pos["k0"] = int(np.searchsorted(t, pos["t0"]))
            res = step_position(pos, k, o, h, l, c, next_open)
            if res:
                px, reason, fee = res
                d = pos["dir"]
                pnl = d * (px - pos["entry"]) * pos["qty"] - px * pos["qty"] * fee
                st["equity"] += pnl
                risk_usd = abs(pos["entry"] - pos["stop"]) * pos["qty"]
                fee_in = pos["entry"] * pos["qty"] * TAKER
                R = (pnl - fee_in) / risk_usd
                row = {"symbol": base, "dir": d, "entry": pos["entry"], "exit": px, "reason": reason,
                       "R": round(R, 4), "pnl": round(pnl - fee_in, 4), "t_entry": pos["t0"], "t_exit_bar": int(t[k])}
                if trades is not None:
                    trades.append(row)
                else:
                    record_trade("crowd_paper", row)
                msgs.append(f"EXIT {base} {reason} @ {px:.6g} R={R:.2f}")
                del st["positions"][base]
                pos = None
                skip_signal = reason == "time"   # engine resumes at the exit bar k+1
        if not pos and not skip_signal and base not in st["pending"] and sig[k] != 0 and np.isfinite(stop[k]):
            pe = {"dir": int(sig[k]), "stop": float(stop[k]), "target": float(tgt[k]), "t_fill": int(t[k] + BAR_MS)}
            if forming_open and forming_open[0] == pe["t_fill"] and k == len(t) - 1:
                _open(st, base, pe, forming_open[0], forming_open[1], risk_pct, msgs)
            else:
                st["pending"][base] = pe
        st["last_bar"][base] = int(t[k])


def run(symbols):
    st_path = os.path.join(STATE_DIR, "state_crowd_paper.json")
    os.makedirs(STATE_DIR, exist_ok=True)
    st = json.load(open(st_path)) if os.path.exists(st_path) else {
        "equity": float(os.environ.get("PAPER_EQUITY", "1000")), "positions": {}, "pending": {}, "last_bar": {},
        "ratio_cache": {}}
    risk_pct = float(os.environ.get("CROWD_RISK_PCT", "0.25"))
    ex = make_exchange(keys=False)
    ex.load_markets()
    msgs = []
    for base in symbols:
        sym = f"{base}/USDT:USDT"
        try:
            st["ratio_cache"][base] = fetch_ratio(base, st["ratio_cache"].get(base, {}))
            rows = ex.fetch_ohlcv(sym, "4h", limit=400)
        except Exception as e:
            msgs.append(f"{base} data error: {e}")
            continue
        now_ms = int(time.time() * 1000)
        closed = [r for r in rows if r[0] + BAR_MS <= now_ms]
        forming = [r for r in rows if r[0] + BAR_MS > now_ms]
        t = np.array([r[0] for r in closed], dtype=np.int64)
        o, h, l, c = (np.array([r[i] for r in closed], float) for i in (1, 2, 3, 4))
        cache = st["ratio_cache"][base]
        ts_sorted = np.array(sorted(int(k) for k in cache), dtype=np.int64)
        vals = np.array([cache[str(k)] for k in ts_sorted], float)
        x = np.array([ratio_at(ts_sorted, vals, ti + BAR_MS) for ti in t])
        sig, stop, tgt = signals(o, h, l, c, x)
        last = st["last_bar"].get(base, int(t[-2]) if len(t) > 1 else 0)
        forming_open = (forming[0][0], forming[0][1]) if forming else None
        process_symbol(st, base, t, o, h, l, c, sig, stop, tgt, last, forming_open, risk_pct, msgs)
        pnow = roll_pct(np.log(np.where(x > 0, x, np.nan)))[-1] if len(x) else float("nan")
        msgs.append(f"{base}: crowd pct {pnow:.2f}" if np.isfinite(pnow) else f"{base}: crowd pct n/a")
    json.dump(st, open(st_path + ".tmp", "w"), default=float)
    os.replace(st_path + ".tmp", st_path)
    msgs.insert(0, f"[crowd paper] equity {st['equity']:.2f}, open {len(st['positions'])}")
    text = "\n".join(msgs)
    log(text)
    telegram("Crowd 4h bot\n" + text)


def main():
    load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="+", default=SYMBOLS)
    a = ap.parse_args()
    run(a.symbols)


if __name__ == "__main__":
    main()
