"""Reproducible diagnostics for the oi_flow family (reporting only - nothing here selects parameters).

    cd trading
    python3 -m strategies.oi_flow_analysis diagnostics      # IS-selected configs: long/short, OOS half-years, zero-cost R
    OI_FLOW_HOLDOUT_ROOT=/some/tmp/dir python3 -m strategies.oi_flow_analysis download   # 10 unseen symbols
    OI_FLOW_HOLDOUT_ROOT=/some/tmp/dir python3 -m strategies.oi_flow_analysis holdout    # pre-registered holdout
    OI_FLOW_HOLDOUT_ROOT=/some/tmp/dir python3 -m strategies.oi_flow_analysis oisplit    # impulse trades by OI bucket
    OI_FLOW_HOLDOUT_ROOT=/some/tmp/dir python3 -m strategies.oi_flow_analysis robust     # +1 bar OI lag / entry delay

The holdout data is downloaded with bt.data's own functions into OI_FLOW_HOLDOUT_ROOT (not into trading/data).
"""
import glob
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

import bt.data as D
import strategies.oi_flow as F  # also applies the data patches
from bt.engine import IS_END, Costs, check_lookahead, simulate, summarize
from bt.runner import COST_SCENARIOS

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(HERE, "results")
HROOT = os.environ.get("OI_FLOW_HOLDOUT_ROOT", "")
ORIG = D.ROOT
HOLD = "DOTUSDT NEARUSDT ATOMUSDT FILUSDT BCHUSDT ETCUSDT UNIUSDT APTUSDT ARBUSDT OPUSDT".split()
T2024 = pd.Timestamp("2024-01-01", tz="UTC")
HOLDOUT_CFG = [("squeeze", {"k_hours": 1, "move_atr": 2.0, "mode": "follow"}),
               ("capit", {"move_atr": 2.0, "z": -2.0, "mode": "follow"}),
               ("newpos", {"k_hours": 1, "move_atr": 2.0, "mode": "follow"}),
               ("build", {"n_hours": 24, "sq": 0.8}),
               ("impulse", {"k_hours": 1, "move_atr": 2.0, "mode": "follow"})]
SQ = {"k_hours": 1, "move_atr": 2.0, "mode": "follow"}


def pk(s, keys=("n", "win_pct", "avg_R", "t_stat")):
    return {k: s.get(k) for k in keys}


def _load(sym, tf, root):
    D.ROOT = root
    return D.load(sym, tf, metrics=True)


# ---------------------------------------------------------------- diagnostics of IS-selected configs
def _diag_one(a):
    fn, tf, params, sym = a
    df = _load(sym, tf, ORIG)
    f = getattr(F, fn)
    sig = f(df, **params)
    return simulate(df, sig, Costs(), f.MAX_HOLD, None, sym), simulate(df, sig, Costs(0, 0, 0), f.MAX_HOLD, None, sym)


def diagnostics():
    out = {}
    with ProcessPoolExecutor(2) as ex:
        for p in sorted(glob.glob(os.path.join(RES, "oi_flow_*_*m.json")) + glob.glob(os.path.join(RES, "oi_flow_*_1h.json"))):
            r = json.load(open(p))
            if "selected_params" not in r:
                continue
            key = os.path.basename(p)[8:-5]
            parts = list(ex.map(_diag_one, [(r["fn"], r["tf"], r["selected_params"], s) for s in D.SYMBOLS]))
            tr = pd.concat([a for a, b in parts if len(a)])
            g0 = pd.concat([b for a, b in parts if len(b)])
            res = {}
            for part, g in [("IS", tr[tr.t_entry < IS_END]), ("OOS", tr[tr.t_entry >= IS_END])]:
                for d, gg in g.groupby("dir"):
                    res[f"{part}_{'long' if d > 0 else 'short'}"] = pk(summarize(gg, 0.5))
            oos = tr[tr.t_entry >= IS_END]
            hy = oos.t_entry.dt.year.astype(str) + "H" + ((oos.t_entry.dt.month > 6) + 1).astype(str)
            for h, g in oos.groupby(hy):
                res[f"OOS_{h}"] = pk(summarize(g, 0.5))
            res["OOS_exit_reasons"] = oos.reason.value_counts().to_dict()
            res["OOS_median_stop_pct"] = round(float(oos.risk_pct.median()), 3)
            res["IS_gross_zero_cost"] = pk(summarize(g0[g0.t_entry < IS_END], 0.5))
            res["OOS_gross_zero_cost"] = pk(summarize(g0[g0.t_entry >= IS_END], 0.5))
            out[key] = res
            print(key, json.dumps(res), flush=True)
    json.dump(out, open(os.path.join(RES, "oi_flow_diagnostics.json"), "w"), indent=1)


# ---------------------------------------------------------------- holdout
def download():
    assert HROOT, "set OI_FLOW_HOLDOUT_ROOT"
    D.ROOT = HROOT
    for s in HOLD:
        print(s, D.download_klines(s, "5m", start="2023-11", end="2026-08"),
              D.download_metrics(s, start="2024-01", end="2026-08"), flush=True)


def _hold_one(a):
    fn, p, sym = a
    df = _load(sym, "1h", HROOT)
    df = df[df.index >= T2024 - pd.Timedelta(days=40)]
    f = getattr(F, fn)
    sig = f(df, **p)
    sig.loc[sig.index < T2024, "signal"] = 0
    return {c: simulate(df, sig, COST_SCENARIOS[c], f.MAX_HOLD, None, sym) for c in ("base", "harsh")} | \
           {"zero": simulate(df, sig, Costs(0, 0, 0), f.MAX_HOLD, None, sym)}


def holdout():
    assert HROOT, "set OI_FLOW_HOLDOUT_ROOT"
    keys = ("n", "win_pct", "avg_R", "t_stat", "ret_pct@0.5%", "max_dd_pct")
    out = {}
    with ProcessPoolExecutor(2) as ex:
        for fn, p in HOLDOUT_CFG:
            parts = list(ex.map(_hold_one, [(fn, p, s) for s in HOLD]))
            res = {"params": p}
            for c in ("base", "harsh", "zero"):
                tr = pd.concat([x[c] for x in parts if len(x[c])])
                res[c] = {"all_2024_2026": pk(summarize(tr, 0.5), keys),
                          "2024": pk(summarize(tr[tr.t_entry < IS_END], 0.5), keys),
                          "2025_2026": pk(summarize(tr[tr.t_entry >= IS_END], 0.5), keys)}
                if c == "base":
                    ps = {s: summarize(g, 0.5).get("avg_R") for s, g in tr.groupby("symbol")}
                    res["base_per_symbol_avgR"] = ps
                    res["base_symbols_positive"] = int(sum(v > 0 for v in ps.values()))
                    res["base_long"] = pk(summarize(tr[tr.dir > 0], 0.5), keys)
                    res["base_short"] = pk(summarize(tr[tr.dir < 0], 0.5), keys)
            out[fn] = res
            print(fn, json.dumps(res), flush=True)
    json.dump(out, open(os.path.join(RES, "oi_flow_holdout_1h.json"), "w"), indent=1)


# ---------------------------------------------------------------- does OI add information beyond momentum?
def _split_one(a):
    sym, root = a
    df = _load(sym, "1h", root)
    sig = F.impulse(df, k_hours=1, move_atr=2.0, mode="follow")
    sig.loc[sig.index < T2024, "signal"] = 0
    tr = simulate(df, sig, COST_SCENARIOS["base"], F.impulse.MAX_HOLD, None, sym)
    tr["oiz"] = F.oi_z(df, 1).reindex(tr.t_signal).to_numpy()
    return tr


def oisplit():
    out = {}
    sets = [("main10", D.SYMBOLS, ORIG)] + ([("holdout10", HOLD, HROOT)] if HROOT else [])
    with ProcessPoolExecutor(2) as ex:
        for name, syms, root in sets:
            tr = pd.concat(list(ex.map(_split_one, [(s, root) for s in syms])))
            tr = tr[tr.oiz.notna()]
            b = pd.cut(tr.oiz, [-np.inf, -1.5, -0.5, 0.5, 1.5, np.inf],
                       labels=["z<=-1.5 (OI falling)", "-1.5..-0.5", "-0.5..0.5", "0.5..1.5", "z>=1.5 (OI rising)"])
            res = {}
            for per, m in [("2024", tr.t_entry < IS_END), ("2025_26", tr.t_entry >= IS_END)]:
                for lab, g in tr[m].groupby(b[m], observed=True):
                    res[f"{per} {lab}"] = pk(summarize(g, 0.5), ("n", "avg_R", "t_stat"))
            o = tr[tr.t_entry >= IS_END]
            a_, r_ = o[o.oiz <= -1.5].R, o[o.oiz > -1.5].R
            res["2025_26 diff falling-rest"] = {"diff": round(a_.mean() - r_.mean(), 3), "t_welch": round(
                (a_.mean() - r_.mean()) / np.sqrt(a_.var() / len(a_) + r_.var() / len(r_)), 2)}
            out[name] = res
            print(name, json.dumps(res), flush=True)
    json.dump(out, open(os.path.join(RES, "oi_flow_oisplit_1h.json"), "w"), indent=1)


# ---------------------------------------------------------------- timing robustness of squeeze-follow
def _rob_one(a):
    sym, root, mode = a
    df = _load(sym, "1h", root)
    if mode == "oilag":
        df = df.copy()
        df["oi"] = df["oi"].shift(1)
    sig = F.squeeze(df, **SQ)
    if mode == "delay":
        sig = sig.shift(1).fillna({"signal": 0.0, "exit_signal": 0.0})
    return simulate(df, sig, COST_SCENARIOS["base"], F.squeeze.MAX_HOLD, None, sym)


def robust():
    for sym in ("ETHUSDT", "DOGEUSDT"):
        df = _load(sym, "1h", ORIG)
        print("lookahead", sym, check_lookahead(F.squeeze, df, SQ, n_checks=40),
              check_lookahead(F.capit, df, {"move_atr": 2.0, "z": -2.0, "mode": "follow"}, n_checks=40), flush=True)
    out = {}
    sets = [("main10", D.SYMBOLS, ORIG)] + ([("holdout10", HOLD, HROOT)] if HROOT else [])
    with ProcessPoolExecutor(2) as ex:
        for mode in ("base", "oilag", "delay"):
            for name, syms, root in sets:
                tr = pd.concat(list(ex.map(_rob_one, [(s, root, mode) for s in syms])))
                r = {per: pk(summarize(g, 0.5), ("n", "avg_R", "t_stat")) for per, g in
                     [("2024", tr[tr.t_entry < IS_END]), ("2025_26", tr[tr.t_entry >= IS_END])]}
                out[f"{mode} {name}"] = r
                print(mode, name, json.dumps(r), flush=True)
    json.dump(out, open(os.path.join(RES, "oi_flow_robust_1h.json"), "w"), indent=1)


if __name__ == "__main__":
    {"diagnostics": diagnostics, "download": download, "holdout": holdout,
     "oisplit": oisplit, "robust": robust}[sys.argv[1]]()
