"""Audit: lookahead-guard power, stop-first bias on random entries, clustered statistics,
funding and capacity.

    python3 -m strategies.audit_misc guard|ambig|cluster|capacity|funding  -> results/audit_misc.json

Pre-registered before running (27.09.2026):
  ambig   - random market entries (direction random, ~4000 per cell, 2023-01..2026-08), stop k*ATR14,
            target rr*stop, MAX_HOLD 48 bars, every signal simulated independently. Measure the change
            in avg R when ambiguous bars are resolved with 1m data instead of stop-first.
            Grid: tf {5m,15m,1h} x k {0.5,1,2} x rr {1,2,3} on BTCUSDT and ETHUSDT (54 cells).
  cluster - naive iid t of mean R vs t clustered by entry day and a 7-day block bootstrap, for the
            reference Donchian and the best WEAK candidates of other families (oi_flow squeeze-follow,
            impulse control, capit-follow) with the parameters their runners selected on IS.
"""
import json
import math
import os
import sys
import zlib
from dataclasses import replace

import numpy as np
import pandas as pd

from bt.data import load, SYMBOLS, ROOT as DROOT
from bt.engine import check_lookahead
from strategies import audit_bt as A
from strategies import audit_donchian as DC
from strategies.audit_dl import load_ext

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
PATH = os.path.join(OUT, "audit_misc.json")
CUT = pd.Timestamp("2025-01-01", tz="UTC")


# ------------------------------------------------------------------ 1. lookahead guard power

def cheat_filter(df):
    """Donchian signals, minus the ones that lose over the next 6 bars. Written as ~(loser) so the
    last rows (future unknown) keep their signal: the classic 'lookahead that only removes trades'."""
    s = DC.strategy(df)
    fut = df["close"].shift(-6)
    loser = ((s["signal"] > 0) & (fut < df["close"])) | ((s["signal"] < 0) & (fut > df["close"]))
    s.loc[loser, "signal"] = 0.0
    return s


def tail_window_check(strategy, df, n_cuts=40, window=64, min_bars=500, seed=11):
    """Proposed stronger guard: recompute on df[:k+1] and compare the LAST `window` rows, not just row k."""
    full = strategy(df)
    cols = [c for c in ("signal", "stop", "target", "entry_limit", "exit_signal") if c in full]
    rng = np.random.default_rng(seed)
    ks = rng.choice(np.arange(min_bars + window, len(df)), size=n_cuts, replace=False)
    bad = 0
    for k in ks:
        cut = strategy(df.iloc[:k + 1])
        a = full[cols].iloc[k + 1 - window:k + 1].to_numpy(float)
        b = cut[cols].iloc[-window:].to_numpy(float)
        same = np.isclose(a, b, rtol=1e-9, atol=1e-12, equal_nan=True)
        bad += int((~same).any(axis=1).sum())
    return bad


def guard():
    df = load("BTCUSDT", "1h")
    res = {}
    for name, fn in (("honest_donchian", DC.strategy), ("cheat_filter_losers", cheat_filter)):
        try:
            check_lookahead(fn, df)
            passed = True
        except AssertionError:
            passed = False
        tr = A.simulate(df, fn(df), A.BASE, 120, None, "BTCUSDT")
        detections = []
        for seed in range(20):     # how often does bt.engine.check_lookahead catch it with other seeds?
            try:
                check_lookahead(fn, df, seed=seed)
                detections.append(0)
            except AssertionError:
                detections.append(1)
        res[name] = {"bt.engine.check_lookahead_passed(seed=7)": passed,
                     "detected_share_over_20_seeds": float(np.mean(detections)),
                     "proposed_tail_window_mismatched_rows": tail_window_check(fn, df),
                     "backtest": A.summary(tr, name)}
        print(name, res[name], flush=True)
    return res


# ------------------------------------------------------------------ 2. stop-first bias on random entries

def random_signals(df, k, rr, rng, n_target=4000):
    a = A_atr(df)
    p = min(1.0, n_target / len(df))
    pick = rng.random(len(df)) < p
    d = np.where(rng.random(len(df)) < 0.5, 1.0, -1.0)
    c = df["close"].to_numpy(float)
    sig = np.where(pick, d, 0.0)
    sig[:50] = 0
    stop = np.where(sig > 0, c - k * a, np.where(sig < 0, c + k * a, np.nan))
    tgt = np.where(sig > 0, c + rr * k * a, np.where(sig < 0, c - rr * k * a, np.nan))
    return pd.DataFrame({"signal": sig, "stop": stop, "target": tgt}, index=df.index)


def A_atr(df, n=14):
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean().to_numpy(float)


def ambig():
    res = {}
    for sym in ("BTCUSDT", "ETHUSDT"):
        mn = A.Minutes(load_ext(sym, "1m"))
        for tf in ("5m", "15m", "1h"):
            df = load(sym, tf)
            for k in (0.5, 1.0, 2.0):
                for rr in (1.0, 2.0, 3.0):
                    rng = np.random.default_rng(zlib.crc32(f"{sym}{tf}{k}{rr}".encode()))
                    sig = random_signals(df, k, rr, rng)
                    r0 = replace(A.BASE, queue="independent")
                    t0 = A.simulate(df, sig, r0, 48, None, sym)
                    t1, st = A.simulate(df, sig, replace(r0, intrabar="1m"), 48, None, sym, mn, return_stats=True)
                    d = t1["R"].to_numpy() - t0["R"].to_numpy()
                    key = f"{sym}_{tf}_k{k}_rr{rr}"
                    res[key] = {"n": int(len(t0)), "median_stop_pct": round(float(t0["risk_pct"].median()), 3),
                                "share_trades_ambiguous": round(float((np.abs(d) > 1e-12).mean()), 4),
                                "ambiguous_bars": st["ambiguous_bars"], "resolved_target_first": st["changed_by_1m"],
                                "avgR_stop_first": round(float(t0["R"].mean()), 4),
                                "avgR_1m": round(float(t1["R"].mean()), 4),
                                "delta_avgR": round(float(d.mean()), 4)}
                    print(key, res[key], flush=True)
    return res


# ------------------------------------------------------------------ 3. clustered statistics

def stat_block(tr, fund=None, tfmin=60):
    out = {}
    for name, sub in (("ALL", tr), ("OOS", tr[tr["t_entry"] >= CUT]), ("IS", tr[tr["t_entry"] < CUT])):
        if len(sub) < 10:
            out[name] = {"n": int(len(sub))}
            continue
        R = sub["R"].to_numpy()
        row = {"n": int(len(R)), "avg_R": round(float(R.mean()), 4),
               "t_naive": round(float(R.mean() / R.std(ddof=1) * math.sqrt(len(R))), 2),
               "t_cluster_day": A.clustered_t(sub, "1D"), "t_cluster_week": A.clustered_t(sub, "7D"),
               "t_block_boot_7d": A.block_bootstrap_t(sub, 7),
               "share_entries_same_hour_as_other_symbol": round(float(
                   pd.DatetimeIndex(sub["t_entry"]).floor("h").duplicated(keep=False).mean()), 3)}
        if fund is not None:
            fc = np.concatenate([A.funding_cost(g, fund[s], tfmin)[0] for s, g in sub.groupby("symbol", sort=False)])
            Rf = np.concatenate([g["R"].to_numpy() for s, g in sub.groupby("symbol", sort=False)]) - fc
            row["avg_R_after_funding"] = round(float(Rf.mean()), 4)
            row["mean_funding_R"] = round(float(fc.mean()), 4)
        out[name] = row
    return out


def cluster():
    import importlib
    oi = importlib.import_module("strategies.oi_flow")        # patches bt.data merges (pandas-3 fix, lag 6 min)
    fund = {s: pd.read_parquet(os.path.join(DROOT, "funding", f"{s}.parquet")) for s in SYMBOLS}
    cases = [("donchian_1h(reference)", DC.strategy, {}, False),
             ("oi_flow.squeeze follow k1 m2.0", oi.squeeze, {"k_hours": 1, "move_atr": 2.0, "mode": "follow"}, True),
             ("oi_flow.impulse follow k1 m2.0", oi.impulse, {"k_hours": 1, "move_atr": 2.0, "mode": "follow"}, True),
             ("oi_flow.capit follow m2 z-2", oi.capit, {"move_atr": 2.0, "z": -2.0, "mode": "follow"}, True)]
    res = {}
    for name, fn, params, metrics in cases:
        parts = []
        for s in SYMBOLS:
            df = load(s, "1h", metrics=metrics)
            parts.append(A.simulate(df, fn(df, **params), A.BASE, getattr(fn, "MAX_HOLD", None), None, s))
        tr = pd.concat([p for p in parts if len(p)], ignore_index=True)
        res[name] = stat_block(tr, fund, 60)
        print(name, json.dumps(res[name]), flush=True)
    return res


def cluster_fp():
    """funding_positioning C_level (rcrowd_4h, src=level, pct=0.9) - the family's formally PROMISING config."""
    import importlib
    fp = importlib.import_module("strategies.funding_positioning")   # patches bt.data merges itself
    fund = {s: pd.read_parquet(os.path.join(DROOT, "funding", f"{s}.parquet")) for s in SYMBOLS}
    fn = fp.rcrowd_4h
    parts = []
    for s in SYMBOLS:
        df = load(s, "4h", metrics=True, funding=True)
        parts.append(A.simulate(df, fn(df, src="level", pct=0.9), A.BASE, fn.MAX_HOLD, None, s))
    tr = pd.concat([p for p in parts if len(p)], ignore_index=True)
    res = {"funding_positioning.rcrowd_4h level pct0.9": stat_block(tr, fund, 240)}
    res["funding_positioning.rcrowd_4h level pct0.9"]["short_share"] = round(float((tr["dir"] < 0).mean()), 3)
    print(json.dumps(res), flush=True)
    return res


def holdout_cluster():
    """Same statistics on the oi_flow agent's pre-registered holdout symbols (its cached data, read-only)."""
    import importlib
    import bt.data as D
    hroot = os.environ.get("AUDIT_HOLDOUT_ROOT")
    if not hroot or not os.path.isdir(hroot):
        return {"skipped": "set AUDIT_HOLDOUT_ROOT"}
    oi = importlib.import_module("strategies.oi_flow")
    hold = sorted(f[:-8] for f in os.listdir(os.path.join(hroot, "metrics")))
    orig = D.ROOT
    D.ROOT = hroot
    res = {"symbols": hold, "root": hroot}
    try:
        for name, fn, params in (("oi_flow.squeeze follow k1 m2.0", oi.squeeze, {"k_hours": 1, "move_atr": 2.0, "mode": "follow"}),
                                 ("oi_flow.capit follow m2 z-2", oi.capit, {"move_atr": 2.0, "z": -2.0, "mode": "follow"}),
                                 ("oi_flow.impulse follow k1 m2.0", oi.impulse, {"k_hours": 1, "move_atr": 2.0, "mode": "follow"})):
            parts = []
            for s in hold:
                df = load(s, "1h", metrics=True)
                parts.append(A.simulate(df, fn(df, **params), A.BASE, getattr(fn, "MAX_HOLD", None), None, s))
            tr = pd.concat([p for p in parts if len(p)], ignore_index=True)
            tr = tr[tr["t_entry"] >= pd.Timestamp("2024-01-01", tz="UTC")]
            res[name] = stat_block(tr)
            res[name]["short_share"] = round(float((tr["dir"] < 0).mean()), 3)
            print("holdout", name, json.dumps(res[name]), flush=True)
    finally:
        D.ROOT = orig
    return res


# ------------------------------------------------------------------ 4. capacity

def capacity():
    res = {}
    for s in SYMBOLS:
        row = {}
        for tf in ("5m", "1h"):
            df = load(s, tf, start="2025-01-01")
            qv = df["quote_vol"]
            row[f"median_quote_vol_{tf}_usd"] = float(qv.median())
            row[f"p10_quote_vol_{tf}_usd"] = float(qv.quantile(0.10))
        res[s] = row
    # notional at 0.5% risk and a given stop: equity * 0.005 / stop
    rows = {}
    for eq in (10_000, 100_000, 1_000_000):
        for stop in (0.003, 0.01):
            notional = eq * 0.005 / stop
            rows[f"equity_{eq}_stop_{stop * 100:.1f}%"] = {
                "notional_usd": notional,
                "pct_of_median_5m_bar": {s: round(100 * notional / res[s]["median_quote_vol_5m_usd"], 3) for s in SYMBOLS}}
    res["participation"] = rows
    print(json.dumps(rows, indent=0)[:3000], flush=True)
    return res


# ------------------------------------------------------------------ 5. funding regimes

def funding():
    res = {}
    for s in SYMBOLS:
        f = pd.read_parquet(os.path.join(DROOT, "funding", f"{s}.parquet")).set_index("ts")["funding"]
        per_year = (f.groupby(f.index.year).mean() * 3 * 365 * 100).round(2).to_dict()
        roll = f.rolling("30D").sum() * (365 / 30) * 100
        res[s] = {"annualized_mean_pct_by_year": {str(k): v for k, v in per_year.items()},
                  "max_30d_annualized_pct": round(float(roll.max()), 1),
                  "max_30d_end": str(roll.idxmax()),
                  "min_30d_annualized_pct": round(float(roll.min()), 1)}
        print(s, res[s], flush=True)
    return res


def funding_multiday():
    """Multi-day holds: reference Donchian on 4h (n=30, stop 3 ATR, target 3R, MAX_HOLD 60 bars = 10 days),
    10 symbols, R with and without funding (settled Binance rates)."""
    fund = {s: pd.read_parquet(os.path.join(DROOT, "funding", f"{s}.parquet")) for s in SYMBOLS}
    parts = []
    for s in SYMBOLS:
        df = load(s, "4h")
        tr = A.simulate(df, DC.strategy(df, n=30, k_stop=3.0, rr=3.0), A.BASE, 60, None, s)
        fc, ns = A.funding_cost(tr, fund[s], 240)
        tr["funding_R"], tr["settlements"] = fc, ns
        parts.append(tr)
    tr = pd.concat(parts, ignore_index=True)
    out = {}
    for lab, sub in (("ALL", tr), ("LONG", tr[tr.dir > 0]), ("SHORT", tr[tr.dir < 0]),
                     ("2024_LONG", tr[(tr.dir > 0) & (pd.DatetimeIndex(tr.t_entry).year == 2024)])):
        out[lab] = {"n": int(len(sub)), "avg_R": round(float(sub.R.mean()), 4),
                    "avg_R_after_funding": round(float((sub.R - sub.funding_R).mean()), 4),
                    "mean_funding_R": round(float(sub.funding_R.mean()), 4),
                    "median_days_held": round(float(sub.bars.median() * 4 / 24), 2),
                    "mean_settlements": round(float(sub.settlements.mean()), 2),
                    "median_stop_pct": round(float(sub.risk_pct.median()), 2)}
    print(json.dumps(out), flush=True)
    return out


def main():
    out = json.load(open(PATH)) if os.path.exists(PATH) else {}
    fns = {"guard": guard, "ambig": ambig, "cluster": cluster, "holdout_cluster": holdout_cluster, "cluster_fp": cluster_fp, "capacity": capacity, "funding": funding,
           "funding_multiday": funding_multiday}
    for name in (sys.argv[1:] or list(fns)):
        out[name] = fns[name]()
        with open(PATH, "w") as f:
            json.dump(out, f, indent=1, default=str)


if __name__ == "__main__":
    main()
