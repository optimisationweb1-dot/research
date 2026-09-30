"""Audit steps 3-5: quantify each execution assumption one at a time (independent simulator).

    python3 -m strategies.audit_assumptions        -> results/audit_assumptions.json

Strategies: strategies.smc (5m, 15m) and strategies.audit_donchian (1h) on BTCUSDT/ETHUSDT,
where 1m klines are cached in data/ext/audit/. Every variant changes ONE rule versus the
engine-equivalent baseline; 'realistic' combines the changes that a live bot would face.
"""
import json
import os
from dataclasses import replace

import numpy as np
import pandas as pd

from bt.data import load, ROOT as DROOT
from strategies import audit_bt as A
from strategies import smc, audit_donchian as DC
from strategies.audit_dl import load_ext

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
CUT = pd.Timestamp("2025-01-01", tz="UTC")
TFMIN = {"5m": 5, "15m": 15, "1h": 60}

VARIANTS = {
    "base(engine)": A.BASE,
    "intrabar_1m": replace(A.BASE, intrabar="1m"),
    "limit_touch(<=)": replace(A.BASE, limit_fill="touch"),
    "limit_through_2bps": replace(A.BASE, limit_fill="through", through_bps=2.0),
    "limit_through_5bps": replace(A.BASE, limit_fill="through", through_bps=5.0),
    "queue_block(realtime)": replace(A.BASE, queue="block"),
    "queue_independent": replace(A.BASE, queue="independent"),
    "zero_costs": replace(A.BASE, taker=0.0, maker=0.0, slip=0.0),
    "fees_bitunix(0.02/0.06)": replace(A.BASE, taker=0.0006, maker=0.0002),
    "slip_0": replace(A.BASE, slip=0.0),
    "slip_5bps": replace(A.BASE, slip=0.0005),
    "slip_10bps": replace(A.BASE, slip=0.001),
    "harsh(engine)": A.HARSH,
    "realistic(1m+block+bitunix+slip3)": replace(A.BASE, intrabar="1m", queue="block", taker=0.0006, maker=0.0002,
                                                 slip=0.0003),
}


def fund_df(sym):
    return pd.read_parquet(os.path.join(DROOT, "funding", f"{sym}.parquet"))


def period_stats(tr, fcost=None):
    out = {}
    for name, mask in (("ALL", None), ("IS", "is"), ("OOS", "oos")):
        if tr is None or len(tr) == 0:
            out[name] = {"n": 0}
            continue
        m = np.ones(len(tr), bool) if mask is None else (
            (tr["t_entry"] < CUT).to_numpy() if mask == "is" else (tr["t_entry"] >= CUT).to_numpy())
        R = tr["R"].to_numpy()[m]
        if fcost is not None:
            R = R - fcost[m]
        n = len(R)
        sd = R.std(ddof=1) if n > 1 else np.nan
        out[name] = {"n": int(n), "avg_R": round(float(R.mean()), 4) if n else None,
                     "t": round(float(R.mean() / sd * np.sqrt(n)), 2) if n > 1 and sd > 0 else None,
                     "sum_R": round(float(R.sum()), 2), "win_pct": round(float((R > 0).mean() * 100), 1) if n else None}
    return out


def run_case(sym, name, fn, tf, minutes):
    df = load(sym, tf)
    sig = fn(df)
    mh, ttl = getattr(fn, "MAX_HOLD", None), getattr(fn, "LIMIT_TTL", None)
    fr = fund_df(sym)
    res = {}
    base_tr = None
    for vname, rules in VARIANTS.items():
        tr, st = A.simulate(df, sig, rules, mh, ttl, sym, minutes if rules.intrabar == "1m" else None,
                            return_stats=True)
        row = period_stats(tr)
        row["sim_stats"] = st
        if len(tr):
            row["median_stop_pct"] = round(float(tr["risk_pct"].median()), 3)
            row["median_bars_held"] = float(tr["bars"].median())
            row["reasons"] = tr["reason"].value_counts().to_dict()
        res[vname] = row
        if vname == "base(engine)":
            base_tr = tr
        if vname.startswith("realistic") and len(tr):
            fc, ns = A.funding_cost(tr, fr, TFMIN[tf])
            res["realistic+funding"] = period_stats(tr, fc)
    # funding on the baseline trades
    if base_tr is not None and len(base_tr):
        fc, ns = A.funding_cost(base_tr, fr, TFMIN[tf])
        res["base+funding"] = period_stats(base_tr, fc)
        res["funding_detail"] = {"mean_R_cost": round(float(fc.mean()), 4),
                                 "mean_R_cost_long": round(float(fc[base_tr["dir"].to_numpy() > 0].mean()), 4)
                                 if (base_tr["dir"] > 0).any() else None,
                                 "mean_R_cost_short": round(float(fc[base_tr["dir"].to_numpy() < 0].mean()), 4)
                                 if (base_tr["dir"] < 0).any() else None,
                                 "mean_settlements_per_trade": round(float(ns.mean()), 2),
                                 "share_trades_with_settlement": round(float((ns > 0).mean()), 3)}
        # trade-level diff of the 1m resolution
    return res


def main():
    out = {}
    cases = [("smc_5m", smc.strategy, "5m"), ("smc_15m", smc.strategy, "15m"), ("donchian_1h", DC.strategy, "1h")]
    for sym in ["BTCUSDT", "ETHUSDT"]:
        mn = A.Minutes(load_ext(sym, "1m"))
        for name, fn, tf in cases:
            r = run_case(sym, name, fn, tf, mn)
            out[f"{sym}_{name}"] = r
            print(sym, name, flush=True)
            for v, row in r.items():
                if isinstance(row, dict) and "ALL" in row:
                    print(f"   {v:38s} ALL n={row['ALL'].get('n')} avgR={row['ALL'].get('avg_R')} "
                          f"| IS {row['IS'].get('n')} {row['IS'].get('avg_R')} | OOS {row['OOS'].get('n')} "
                          f"{row['OOS'].get('avg_R')} t={row['OOS'].get('t')}", flush=True)
            print("   funding:", r.get("funding_detail"), "| 1m stats:", r["intrabar_1m"]["sim_stats"], flush=True)
    with open(os.path.join(OUT, "audit_assumptions.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)


if __name__ == "__main__":
    main()
