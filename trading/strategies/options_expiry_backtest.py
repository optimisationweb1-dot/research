"""Run S2/S3 through bt.engine with base and harsh costs; IS selection, OOS report.

    cd trading && python3 -m strategies.options_expiry_backtest   # -> results/options_expiry_backtest.json
"""
import json
import os

import numpy as np
import pandas as pd

from bt.data import load
from bt.engine import check_lookahead, simulate, split_summary, summarize, IS_END
from bt.runner import COST_SCENARIOS
from strategies.options_expiry_strats import attach_dvol, dvol_regime, dvol_spike_long

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "results", "options_expiry_backtest.json")
PAIRS = {"BTCUSDT": "BTC", "ETHUSDT": "ETH"}
ALTS = ["SOLUSDT", "XRPUSDT", "DOGEUSDT", "BNBUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "LTCUSDT"]


def frames(tf, syms):
    out = {}
    for s in syms:
        cur = PAIRS.get(s, "BTC")  # alts use BTC DVOL and BTC thresholds (robustness only)
        out[s] = attach_dvol(load(s, tf), cur)
    return out


def run_s2(fr, params, cost):
    parts = []
    for s, df in fr.items():
        sig = dvol_spike_long(df, **params)
        parts.append(simulate(df, sig, COST_SCENARIOS[cost], params.get("hold", 72), None, s))
    parts = [p for p in parts if len(p)]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def run_s3(fr, params, cost):
    parts = []
    for s, df in fr.items():
        sig = dvol_regime(df, **params)
        day = (df.index - df.index[0]).days
        for par in (0, 1):  # engine skips the bar on which a 1-bar trade exits -> run two staggered books
            sg = sig.copy()
            sg.loc[(day % 2) != par, "signal"] = 0.0
            parts.append(simulate(df, sg, COST_SCENARIOS[cost], 1, None, s))
    parts = [p for p in parts if len(p)]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def gross_R(tr):
    """R before fees and slippage (entry/exit prices include slippage; add back approx fees)."""
    if not len(tr):
        return None
    return round(float((tr["dir"] * (tr["exit"] - tr["entry"]) / (tr["entry"] * tr["risk_pct"] / 100)).mean()), 3)


def main():
    res = {}
    # ---------------- S2
    f1 = frames("1h", list(PAIRS))
    check_lookahead(dvol_spike_long, f1["BTCUSDT"], {"q": 95, "hold": 72})
    rows = []
    for q in (90, 95):
        for hold in (24, 72, 168):
            p = {"q": q, "hold": hold}
            tr = run_s2(f1, p, "base")
            ss = split_summary(tr, 0.5, json.dumps(p))
            rows.append({"params": p, **ss})
            print("S2", p, ss["IS"].get("n"), ss["IS"].get("avg_R"), ss["IS"].get("t_stat"), "| OOS",
                  ss["OOS"].get("n"), ss["OOS"].get("avg_R"), ss["OOS"].get("t_stat"), flush=True)
    best = max(rows, key=lambda r: (r["IS"].get("t_stat") or -9) if r["IS"].get("n", 0) >= 20 else -9)
    trh = run_s2(f1, best["params"], "harsh")
    trb = run_s2(f1, best["params"], "base")
    res["S2"] = {"n_configs": len(rows), "selection": "max IS t-stat, IS n>=20 (few events: 2 symbols)",
                 "selected": best["params"], "IS": best["IS"], "OOS": best["OOS"],
                 "OOS_harsh": split_summary(trh, 0.5)["OOS"],
                 "OOS_per_symbol": {s: summarize(g[g.t_entry >= IS_END], 0.5, s) for s, g in trb.groupby("symbol")},
                 "all_configs": rows}
    # ---------------- S3
    fd = frames("1d", list(PAIRS) + ALTS)
    core = {k: fd[k] for k in PAIRS}
    alts = {k: fd[k] for k in ALTS}
    check_lookahead(dvol_regime, core["BTCUSDT"], {"mode": "both"}, min_bars=200)
    rows = []
    for mode in ("both", "mr", "trend"):
        p = {"mode": mode}
        tr = run_s3(core, p, "base")
        ss = split_summary(tr, 0.5, json.dumps(p))
        rows.append({"params": p, **ss, "gross_avg_R_IS": gross_R(tr[tr.t_entry < IS_END]),
                     "gross_avg_R_OOS": gross_R(tr[tr.t_entry >= IS_END])})
        print("S3", p, ss["IS"].get("n"), ss["IS"].get("avg_R"), ss["IS"].get("t_stat"), "| OOS",
              ss["OOS"].get("n"), ss["OOS"].get("avg_R"), ss["OOS"].get("t_stat"), flush=True)
    best = max(rows, key=lambda r: r["IS"].get("t_stat") or -9)
    trb = run_s3(core, best["params"], "base")
    trh = run_s3(core, best["params"], "harsh")
    tra = run_s3(alts, best["params"], "base")
    # unconditional controls: same rules without the DVOL filter (always MR / always trend)
    ctrl = {}
    for mode in ("mr", "trend"):
        cc = {k: v.assign(dvol=(1e9 if mode == "mr" else -1e9)) for k, v in core.items()}
        for v, k in zip(cc.values(), core):
            v.attrs["currency"] = core[k].attrs["currency"]
        ctrl[f"unfiltered_{mode}"] = split_summary(run_s3(cc, {"mode": mode}, "base"), 0.5)
    res["S3"] = {"n_configs": len(rows), "selection": "max IS t-stat", "selected": best["params"],
                 "IS": best["IS"], "OOS": best["OOS"], "OOS_harsh": split_summary(trh, 0.5)["OOS"],
                 "OOS_per_symbol": {s: summarize(g[g.t_entry >= IS_END], 0.5, s) for s, g in trb.groupby("symbol")},
                 "per_year": {str(y): summarize(g, 0.5, str(y)) for y, g in trb.groupby(trb.t_entry.dt.year)},
                 "alts_with_BTC_DVOL": split_summary(tra, 0.5), "controls": ctrl, "all_configs": rows}
    for k in ("S2", "S3"):
        print(k, "SELECTED", res[k]["selected"], "\n IS", res[k]["IS"], "\n OOS", res[k]["OOS"],
              "\n OOS harsh", res[k]["OOS_harsh"])
    print("S3 alts", res["S3"]["alts_with_BTC_DVOL"])
    print("S3 controls", json.dumps(res["S3"]["controls"]))
    with open(OUT, "w") as f:
        json.dump(res, f, indent=1, default=str)


if __name__ == "__main__":
    main()
