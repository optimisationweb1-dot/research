#!/usr/bin/env python3
"""Hourly GEX snapshot logger (BTC, ETH) built on trading/gex_levels.py (not modified).

Every run appends one row per (currency, mode) to
    trading/data/ext/options_expiry/gex_log.parquet
with mode in {all, 0dte, 1dte}: spot, net GEX, regime, zero gamma, call wall, put wall, top strikes.
It also stores the raw per-instrument open interest / mark IV it used
    trading/data/ext/options_expiry/oi_snapshots/<CUR>/<YYYY-MM-DD>.parquet
so that pinning / GEX-level tests can later be run on TRUE OI-by-strike history (not free elsewhere).

    python3 strategies/options_expiry_gex_logger.py            # one snapshot (cron: hourly)
    python3 strategies/options_expiry_gex_logger.py --show 10  # print the last rows of the log

Public Deribit API, no keys. Uses a lock file so overlapping cron runs do not corrupt the parquet.
"""
import argparse
import fcntl
import json
import os
import sys
import time
from datetime import datetime, timezone

import pandas as pd

TRADING = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TRADING)
import gex_levels as G  # noqa: E402

EXT = os.path.join(TRADING, "data", "ext", "options_expiry")
LOG = os.path.join(EXT, "gex_log.parquet")
LOCK = os.path.join(EXT, ".gex_logger.lock")


def _lvl(d, name):
    x = (d or {}).get(name)
    return None if not x else x["level"]


def snapshot(cur, now):
    for k in range(3):
        try:
            spot, opts = G.load(cur)
            break
        except Exception as e:  # network hiccup: retry
            if k == 2:
                raise
            time.sleep(5 * (k + 1))
    expiries = sorted({o["expiry"] for o in opts})
    near = [e for e in expiries if (e - now).total_seconds() < 86400]
    e0 = near[0] if near else None
    e1 = next((e for e in expiries if e != e0), None)
    rows = []
    for mode, sel, exp in (("all", opts, None),
                           ("0dte", [o for o in opts if o["expiry"] == e0], e0),
                           ("1dte", [o for o in opts if o["expiry"] == e1], e1)):
        L = G.levels(sel, spot) if sel else None
        rows.append({
            "ts": pd.Timestamp(now), "currency": cur, "mode": mode, "spot": spot,
            "expiry": pd.Timestamp(exp) if exp else pd.NaT,
            "n_options": len(sel), "oi_total": float(sum(o["oi"] for o in sel)),
            "net_gex_usd_per_1pct": None if not L else float(L["net_gex_usd_per_1pct"]),
            "regime": None if not L else L["regime"],
            "zero_gamma": _lvl(L, "zero_gamma"), "call_wall": _lvl(L, "call_wall"), "put_wall": _lvl(L, "put_wall"),
            "top_strikes": None if not L else json.dumps(L["top_strikes"]),
        })
    raw = pd.DataFrame([{"ts": pd.Timestamp(now), "expiry": pd.Timestamp(o["expiry"]), "strike": o["k"],
                         "cp": o["cp"], "oi": o["oi"], "mark_iv": o["iv"], "spot": spot} for o in opts])
    return rows, raw


def _append(path, df):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        df = pd.concat([pd.read_parquet(path), df], ignore_index=True)
    tmp = path + ".tmp"
    df.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--currencies", nargs="+", default=["BTC", "ETH"])
    ap.add_argument("--show", type=int, default=0)
    ap.add_argument("--no-raw", action="store_true", help="skip per-instrument OI snapshot")
    a = ap.parse_args()
    if a.show:
        with pd.option_context("display.width", 200, "display.max_columns", 20):
            print(pd.read_parquet(LOG).tail(a.show).drop(columns=["top_strikes"]))
        return 0
    os.makedirs(EXT, exist_ok=True)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    with open(LOCK, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        rows, errs = [], []
        for cur in a.currencies:
            try:
                r, raw = snapshot(cur, now)
                rows += r
                if not a.no_raw:
                    _append(os.path.join(EXT, "oi_snapshots", cur, f"{now:%Y-%m-%d}.parquet"), raw)
            except Exception as e:
                errs.append(f"{cur}: {e!r}")
        if rows:
            _append(LOG, pd.DataFrame(rows))
    for r in rows:
        print(f"{r['ts']:%Y-%m-%d %H:%M} {r['currency']} {r['mode']:4s} spot {r['spot']:,.0f} "
              f"netGEX {0 if r['net_gex_usd_per_1pct'] is None else r['net_gex_usd_per_1pct'] / 1e6:,.1f}M "
              f"ZG {r['zero_gamma']} CW {r['call_wall']} PW {r['put_wall']}")
    for e in errs:
        print("ERROR", e, file=sys.stderr)
    return 1 if errs and not rows else 0


if __name__ == "__main__":
    sys.exit(main())
