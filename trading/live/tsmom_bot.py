#!/usr/bin/env python3
"""TSMOM 1d forward-test bot for BingX USDT-M perpetuals.

Strategy (frozen, as backtested in strategies/trend_momentum.py::tsmom, K=72, z0=0.5):
    sigma = std of daily log returns over the last 30 closed days
    z     = ln(C_t / C_{t-72}) / (sigma * sqrt(72))
    flat and z > +0.5 -> long;  flat and z < -0.5 -> short   (entry right after the daily close)
    stop  = C_t * (1 -/+ sigma * sqrt(7))        fixed, placed on the exchange as STOP_MARKET reduce-only
    exit  = long when z < 0, short when z > 0, or after 60 days (market, reduce-only)
Size: risk_pct of equity per trade = qty * |entry - stop|.

Modes:
    --mode paper   (default) no keys needed; simulated fills at the last price, stops checked on daily high/low
    --mode live    real orders; needs BINGX_API_KEY / BINGX_SECRET in trading/live/.env
    --check        read-only connectivity check (markets, candles, balance, positions if keys given)

Run once a day after 00:00 UTC (cron example in live/README.md). Safe to re-run: entries/exits
happen once per closed daily candle; reconciliation with the exchange runs every time.
Kill switch: create file trading/live/state/STOP  -> no new entries (exits and stops still managed).
"""
import argparse
import csv
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import ccxt

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.path.join(HERE, "state")
DEFAULT_SYMBOLS = ("BTC ETH SOL XRP DOGE BNB ADA AVAX LINK LTC "
                   "APT ARB ATOM BCH DOT ETC FIL NEAR OP UNI").split()

K, Z0, VOL_DAYS, STOP_DAYS, MAX_DAYS = 72, 0.5, 30, 7, 60
PAPER_FEE, PAPER_SLIP = 0.0005, 0.0002


# ------------------------------------------------------------------ utils

def load_env(path=os.path.join(HERE, ".env")):
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def now_utc():
    return datetime.now(timezone.utc)


def log(msg):
    line = f"{now_utc():%Y-%m-%d %H:%M:%S}Z {msg}"
    print(line, flush=True)
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, "bot.log"), "a") as f:
        f.write(line + "\n")


def telegram(msg):
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        return
    data = urllib.parse.urlencode({"chat_id": chat, "text": msg[:4000]}).encode()
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data=data, timeout=20)
    except Exception as e:  # never let notifications break trading
        log(f"telegram error: {e}")


def load_state(mode):
    path = os.path.join(STATE_DIR, f"state_{mode}.json")
    if os.path.exists(path):
        return json.load(open(path))
    return {"positions": {}, "last_bar": {}, "equity": None, "peak": None, "paper_cash": None}


def save_state(mode, st):
    os.makedirs(STATE_DIR, exist_ok=True)
    path = os.path.join(STATE_DIR, f"state_{mode}.json")
    tmp = path + ".tmp"
    json.dump(st, open(tmp, "w"), indent=1, default=str)
    os.replace(tmp, path)


def record_trade(mode, row):
    path = os.path.join(STATE_DIR, f"trades_{mode}.csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)


# ------------------------------------------------------------------ signal

def signal_from_candles(ohlcv):
    """ohlcv: CLOSED daily candles, oldest first. Returns dict with z, sigma, close, bar time."""
    closes = [c[4] for c in ohlcv]
    if len(closes) < K + VOL_DAYS + 1:
        return None
    lr = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    w = lr[-VOL_DAYS:]
    m = sum(w) / len(w)
    sigma = math.sqrt(sum((x - m) ** 2 for x in w) / (len(w) - 1))
    z = math.log(closes[-1] / closes[-1 - K]) / (sigma * math.sqrt(K))
    return {"z": z, "sigma": sigma, "close": closes[-1], "bar": ohlcv[-1][0],
            "high": ohlcv[-1][2], "low": ohlcv[-1][3], "stop_dist": sigma * math.sqrt(STOP_DAYS)}


def closed_daily(ex, symbol, limit=150):
    rows = ex.fetch_ohlcv(symbol, "1d", limit=limit)
    today = int(now_utc().replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    return [r for r in rows if r[0] < today]


# ------------------------------------------------------------------ brokers

class PaperBroker:
    def __init__(self, ex, st):
        self.ex, self.st = ex, st
        if st.get("paper_cash") is None:
            st["paper_cash"] = float(os.environ.get("PAPER_EQUITY", "1000"))

    def equity(self):
        return self.st["paper_cash"]

    def exchange_positions(self):
        return None  # paper: state is the source of truth

    def open(self, symbol, side, qty, price, stop):
        fill = price * (1 + (PAPER_SLIP if side == "long" else -PAPER_SLIP))
        self.st["paper_cash"] -= fill * qty * PAPER_FEE
        return {"entry": fill, "stop_order": None}

    def close(self, pos, price):
        d = 1 if pos["side"] == "long" else -1
        fill = price * (1 - d * PAPER_SLIP)
        pnl = d * (fill - pos["entry"]) * pos["qty"] - fill * pos["qty"] * PAPER_FEE
        self.st["paper_cash"] += pnl
        return fill, pnl

    def stopped(self, pos, sig):
        """Paper stop check on the closed candle's high/low since entry."""
        if pos["side"] == "long" and sig["low"] <= pos["stop"]:
            return True
        if pos["side"] == "short" and sig["high"] >= pos["stop"]:
            return True
        return False


class BingXBroker:
    def __init__(self, ex, st, hedged=False, leverage=3):
        self.ex, self.st, self.hedged, self.leverage = ex, st, hedged, leverage

    def equity(self):
        bal = self.ex.fetch_balance({"type": "swap"})
        return float(bal["total"].get("USDT") or 0)

    def exchange_positions(self):
        out = {}
        for p in self.ex.fetch_positions():
            amt = float(p.get("contracts") or 0)
            if amt:
                out[p["symbol"]] = {"side": p["side"], "qty": amt, "entry": float(p.get("entryPrice") or 0)}
        return out

    def _params(self, extra=None):
        p = {"hedged": True} if self.hedged else {}
        p.update(extra or {})
        return p

    def open(self, symbol, side, qty, price, stop):
        try:
            self.ex.set_leverage(self.leverage, symbol, {"side": "LONG" if side == "long" else "SHORT"}
                                 if self.hedged else {"side": "BOTH"})
        except Exception as e:
            log(f"{symbol} set_leverage warning: {e}")
        o = self.ex.create_order(symbol, "market", "buy" if side == "long" else "sell", qty, None, self._params())
        entry = float(o.get("average") or 0)
        if not entry:
            time.sleep(1)
            o = self.ex.fetch_order(o["id"], symbol)
            entry = float(o.get("average") or price)
        so = self.ex.create_order(symbol, "market", "sell" if side == "long" else "buy", qty, None,
                                  self._params({"stopLossPrice": stop, "reduceOnly": True}))
        return {"entry": entry, "stop_order": so["id"]}

    def close(self, pos, price):
        sym = pos["symbol"]
        if pos.get("stop_order"):
            try:
                self.ex.cancel_order(pos["stop_order"], sym)
            except Exception as e:
                log(f"{sym} cancel stop warning: {e}")
        o = self.ex.create_order(sym, "market", "sell" if pos["side"] == "long" else "buy", pos["qty"], None,
                                 self._params({"reduceOnly": True}))
        fill = float(o.get("average") or 0) or price
        d = 1 if pos["side"] == "long" else -1
        return fill, d * (fill - pos["entry"]) * pos["qty"]

    def stopped(self, pos, sig):
        return False  # live: the exchange stop decides; detected via reconciliation


# ------------------------------------------------------------------ main loop

def make_exchange(keys=True):
    cfg = {"options": {"defaultType": "swap"}, "enableRateLimit": True}
    if keys and os.environ.get("BINGX_API_KEY"):
        cfg.update(apiKey=os.environ["BINGX_API_KEY"], secret=os.environ["BINGX_SECRET"])
    ex = ccxt.bingx(cfg)
    if os.environ.get("CA_BUNDLE"):  # only for proxied sandboxes; still verifies TLS
        ex.validateServerSsl = os.environ["CA_BUNDLE"]
    return ex


def run(mode, symbols, risk_pct, max_open_risk_pct, dd_halt_pct, leverage, hedged):
    st = load_state(mode)
    ex = make_exchange(keys=(mode == "live"))
    ex.load_markets()
    broker = BingXBroker(ex, st, hedged, leverage) if mode == "live" else PaperBroker(ex, st)
    equity = broker.equity()
    st["equity"] = equity
    st["peak"] = max(st.get("peak") or equity, equity)
    halted = os.path.exists(os.path.join(STATE_DIR, "STOP")) or equity < st["peak"] * (1 - dd_halt_pct / 100)
    msgs = [f"[{mode}] equity {equity:.2f} USDT, peak {st['peak']:.2f}" + (" | NEW ENTRIES HALTED" if halted else "")]

    # 1) reconcile with exchange (live): positions closed by the exchange stop
    live_pos = broker.exchange_positions()
    if live_pos is not None:
        for sym, pos in list(st["positions"].items()):
            if sym not in live_pos:
                last = float(ex.fetch_ticker(sym)["last"])
                d = 1 if pos["side"] == "long" else -1
                pnl = d * (pos["stop"] - pos["entry"]) * pos["qty"]
                R = d * (pos["stop"] - pos["entry"]) / abs(pos["entry"] - pos["stop"])
                record_trade(mode, {**pos, "exit_time": now_utc().isoformat(), "exit": pos["stop"],
                                    "reason": "stop(exchange)", "pnl_est": round(pnl, 4), "R_est": round(R, 3),
                                    "last_price_seen": last})
                msgs.append(f"{sym} closed by exchange stop ~{pos['stop']} (R~{R:.2f})")
                del st["positions"][sym]
        for sym in live_pos:
            if sym not in st["positions"]:
                msgs.append(f"WARNING {sym}: position on exchange not managed by the bot - left untouched")

    open_risk = sum(abs(p["entry"] - p["stop"]) * p["qty"] for p in st["positions"].values())

    for base in symbols:
        sym = f"{base}/USDT:USDT"
        if sym not in ex.markets:
            msgs.append(f"{sym} not listed - skipped")
            continue
        try:
            sig = signal_from_candles(closed_daily(ex, sym))
        except Exception as e:
            msgs.append(f"{sym} data error: {e}")
            continue
        if not sig:
            continue
        if st["last_bar"].get(sym) == sig["bar"]:
            continue  # this closed candle was already processed
        pos = st["positions"].get(sym)
        price = float(ex.fetch_ticker(sym)["last"])

        # 2) exits: paper stop on the closed candle, then signal exit / time exit
        if pos:
            reason = None
            if broker.stopped(pos, sig):
                reason, exit_ref = "stop", pos["stop"]
            elif (pos["side"] == "long" and sig["z"] < 0) or (pos["side"] == "short" and sig["z"] > 0):
                reason, exit_ref = "z_flip", price
            elif (sig["bar"] - pos["entry_bar"]) / 86400000 >= MAX_DAYS:
                reason, exit_ref = "max_days", price
            if reason:
                fill, pnl = broker.close(pos, exit_ref)
                d = 1 if pos["side"] == "long" else -1
                R = d * (fill - pos["entry"]) / abs(pos["entry"] - pos["stop"])
                record_trade(mode, {**pos, "exit_time": now_utc().isoformat(), "exit": fill, "reason": reason,
                                    "pnl_est": round(pnl, 4), "R_est": round(R, 3), "last_price_seen": price})
                msgs.append(f"EXIT {sym} {pos['side']} @ {fill:.6g} ({reason}) R={R:.2f} pnl={pnl:.2f}")
                open_risk -= abs(pos["entry"] - pos["stop"]) * pos["qty"]
                del st["positions"][sym]
                pos = None

        # 3) entries
        if not pos and not halted:
            side = "long" if sig["z"] > Z0 else "short" if sig["z"] < -Z0 else None
            if side:
                d = 1 if side == "long" else -1
                stop = sig["close"] * (1 - d * sig["stop_dist"])
                if (side == "long" and price <= stop) or (side == "short" and price >= stop):
                    msgs.append(f"{sym} {side}: price already beyond stop - skipped")
                else:
                    risk_usd = equity * risk_pct / 100
                    qty = float(ex.amount_to_precision(sym, risk_usd / abs(price - stop)))
                    mk = ex.markets[sym]
                    min_qty = mk["limits"]["amount"]["min"] or 0
                    min_cost = mk["limits"]["cost"]["min"] or 0
                    if qty < min_qty or qty * price < min_cost:
                        msgs.append(f"{sym} {side}: size {qty} below exchange minimum ({min_qty}) - skipped")
                    elif open_risk + risk_usd > equity * max_open_risk_pct / 100:
                        msgs.append(f"{sym} {side}: portfolio risk cap {max_open_risk_pct}% reached - skipped")
                    else:
                        stop = float(ex.price_to_precision(sym, stop))
                        res = broker.open(sym, side, qty, price, stop)
                        st["positions"][sym] = {"symbol": sym, "side": side, "qty": qty, "entry": res["entry"],
                                                "stop": stop, "stop_order": res["stop_order"],
                                                "entry_time": now_utc().isoformat(), "entry_bar": sig["bar"],
                                                "z_entry": round(sig["z"], 3), "risk_usd": round(risk_usd, 4)}
                        open_risk += abs(res["entry"] - stop) * qty
                        msgs.append(f"ENTRY {sym} {side} qty={qty} @ {res['entry']:.6g} stop={stop} "
                                    f"({100 * sig['stop_dist']:.1f}%) z={sig['z']:.2f} risk=${risk_usd:.2f}")
        st["last_bar"][sym] = sig["bar"]
        save_state(mode, st)

    msgs.append(f"open positions: {len(st['positions'])}, open risk ${open_risk:.2f} "
                f"({100 * open_risk / equity:.2f}% of equity)" if equity else "")
    save_state(mode, st)
    text = "\n".join(m for m in msgs if m)
    log(text)
    telegram("TSMOM bot\n" + text)


def check():
    ex = make_exchange()
    ex.load_markets()
    print("markets:", len(ex.markets))
    for base in ("BTC", "ETH"):
        sym = f"{base}/USDT:USDT"
        s = signal_from_candles(closed_daily(ex, sym))
        print(sym, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in s.items()})
    if os.environ.get("BINGX_API_KEY"):
        bal = ex.fetch_balance({"type": "swap"})
        print("USDT total:", bal["total"].get("USDT"))
        print("positions:", [(p["symbol"], p["side"], p["contracts"]) for p in ex.fetch_positions() if p.get("contracts")])
        try:
            print("position mode:", ex.fetch_position_mode())
        except Exception as e:
            print("position mode: unknown", e)
    else:
        print("no API keys - public checks only")


def main():
    load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["paper", "live"], default="paper")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--symbols", nargs="+", default=os.environ.get("SYMBOLS", " ".join(DEFAULT_SYMBOLS)).split())
    ap.add_argument("--risk", type=float, default=float(os.environ.get("RISK_PCT", "0.25")))
    ap.add_argument("--max-open-risk", type=float, default=float(os.environ.get("MAX_OPEN_RISK_PCT", "3")))
    ap.add_argument("--dd-halt", type=float, default=float(os.environ.get("DD_HALT_PCT", "15")))
    ap.add_argument("--leverage", type=int, default=int(os.environ.get("LEVERAGE", "3")))
    ap.add_argument("--hedged", action="store_true", default=os.environ.get("HEDGE_MODE", "0") == "1")
    a = ap.parse_args()
    if a.check:
        return check()
    if a.mode == "live" and os.environ.get("LIVE_CONFIRM") != "YES":
        sys.exit("live mode requires LIVE_CONFIRM=YES in live/.env")
    run(a.mode, a.symbols, a.risk, a.max_open_risk, a.dd_halt, a.leverage, a.hedged)


if __name__ == "__main__":
    main()
