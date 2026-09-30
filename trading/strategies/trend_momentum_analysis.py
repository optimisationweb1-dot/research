"""Diagnostics for family trend_momentum (no selection happens here).

For the IS-selected config of every variant (read from results/trend_momentum_*.json):
  - long / short split IS vs OOS, OOS by half-year, zero-cost (gross) OOS
  - fat-tail stats: median R, share of sum R from the top 5% trades, avg_R without the top 1%
  - concurrency: max simultaneously open positions, worst calendar month (sum R)
  - buy & hold context per symbol (IS, OOS)

    cd trading && python3 -m strategies.trend_momentum_analysis                 # diagnostics
    TM_HOLDOUT_ROOT=/dir python3 -m strategies.trend_momentum_analysis holdout  # out-of-universe test
    python3 -m strategies.trend_momentum_analysis delay                         # entry one bar later

HOLDOUT (pre-registered 27.09.2026, before any holdout data was loaded by this family):
  symbols APT ARB ATOM BCH DOT ETC FIL NEAR OP UNI (Binance USD-M 5m, 2023-11..2026-08, fetched with
  bt.data functions by the oi_flow study; copied to TM_HOLDOUT_ROOT). Every variant is run with its
  IS-selected config, unchanged, for ALL 12 variants (no picking by main-OOS result).
  PASS = t >= 2 over the whole holdout period AND avg_R > 0 in 2025-01..2026-08 at base and harsh
         costs AND >= 6 of 10 symbols positive over the whole period.

EARLY HOLDOUT IN TIME (pre-registered 27.09.2026 after the symbol holdout, before downloading):
  the same 10 main symbols, 2020-01..2022-12 (before IS; covers the 2020 crash, the 2021 bull and the
  2022 bear). Binance USD-M 5m klines + Deribit DVOL (from 2021-03) fetched with bt.data functions into
  TM_EARLY_ROOT (scratch, not trading/data). All 12 IS-selected configs, unchanged.
  PASS = t >= 2 over 2020-2022 AND avg_R > 0 at base and harsh costs AND >= 6 of 10 symbols positive.

    TM_EARLY_ROOT=/dir python3 -m strategies.trend_momentum_analysis early_download
    TM_EARLY_ROOT=/dir python3 -m strategies.trend_momentum_analysis early
"""
import glob
import json
import math
import os
import sys

import numpy as np
import pandas as pd

import strategies.trend_momentum  # noqa: F401  (patches bt.data._asof)
from bt.data import SYMBOLS, load
from bt.engine import IS_END, Costs, summarize
from bt.runner import COST_SCENARIOS, run_config

COST_SCENARIOS["zero"] = Costs(taker=0.0, maker=0.0, slippage=0.0)
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")


def tstat(x):
    x = np.asarray(x, float)
    if len(x) < 2 or x.std(ddof=1) == 0:
        return None
    return round(float(x.mean() / x.std(ddof=1) * math.sqrt(len(x))), 2)


def brief(tr):
    if len(tr) == 0:
        return {"n": 0}
    R = tr["R"].to_numpy()
    return {"n": int(len(R)), "avg_R": round(float(R.mean()), 3), "t": tstat(R), "win": round(100 * float((R > 0).mean()), 1)}


def tails(tr):
    R = np.sort(tr["R"].to_numpy())[::-1]
    if len(R) < 20:
        return {}
    k5, k1 = max(1, int(0.05 * len(R))), max(1, int(0.01 * len(R)))
    pos_sum = R[R > 0].sum()
    return {"median_R": round(float(np.median(R)), 3), "max_R": round(float(R[0]), 1),
            "top5pct_sumR": round(float(R[:k5].sum()), 1), "total_sumR": round(float(R.sum()), 1),
            "top5pct_share_of_gross_wins": round(float(R[:k5].sum() / pos_sum), 2) if pos_sum > 0 else None,
            "avg_R_ex_top1pct": round(float(R[k1:].mean()), 3), "t_ex_top1pct": tstat(R[k1:]),
            "avg_bars": round(float(tr["bars"].mean()), 1)}


def concurrency(tr):
    ev = pd.concat([pd.Series(1, index=tr["t_entry"]), pd.Series(-1, index=tr["t_exit"])]).sort_index()
    open_n = ev.groupby(level=0).sum().cumsum()
    m = tr.groupby(tr["t_exit"].dt.to_period("M"))["R"].sum()
    return {"max_open": int(open_n.max()), "mean_open": round(float(open_n.mean()), 2),
            "worst_month": str(m.idxmin()), "worst_month_sumR": round(float(m.min()), 1),
            "best_month": str(m.idxmax()), "best_month_sumR": round(float(m.max()), 1),
            "share_months_positive": round(float((m > 0).mean()), 2)}


def buy_hold():
    out = {}
    for s in SYMBOLS:
        c = load(s, "1d")["close"]
        is_ = c[c.index < IS_END]
        oos = c[c.index >= IS_END]
        out[s] = {"IS_ret_pct": round(100 * (is_.iloc[-1] / is_.iloc[0] - 1), 1),
                  "OOS_ret_pct": round(100 * (oos.iloc[-1] / is_.iloc[-1] - 1), 1)}
        h = oos.groupby(oos.index.to_period("Q")).last()
        out[s]["OOS_by_quarter_close"] = {str(k): round(float(v), 4) for k, v in h.items()}
    return out


def diag_one(path):
    r = json.load(open(path))
    mod, fn, tf, params, load_kw = r["module"], r["fn"], r["tf"], r["selected_params"], r["load"]
    out = {"file": os.path.basename(path), "fn": fn, "tf": tf, "params": params}
    trs = {c: run_config(mod, fn, SYMBOLS, tf, params, load_kw, c, 2) for c in ("base", "zero")}
    tr = trs["base"]
    tr["half"] = tr["t_entry"].dt.year.astype(str) + "H" + np.where(tr["t_entry"].dt.month <= 6, "1", "2")
    is_, oos = tr[tr["t_entry"] < IS_END], tr[tr["t_entry"] >= IS_END]
    z = trs["zero"]
    out["IS"] = {"all": brief(is_), "long": brief(is_[is_.dir > 0]), "short": brief(is_[is_.dir < 0])}
    out["OOS"] = {"all": brief(oos), "long": brief(oos[oos.dir > 0]), "short": brief(oos[oos.dir < 0])}
    out["OOS_gross_zero_cost"] = brief(z[z["t_entry"] >= IS_END])
    out["IS_gross_zero_cost"] = brief(z[z["t_entry"] < IS_END])
    out["by_half"] = {h: brief(g) for h, g in tr.groupby("half")}
    out["OOS_tails"] = tails(oos)
    out["IS_tails"] = tails(is_)
    out["OOS_concurrency"] = concurrency(oos)
    out["OOS_exit_reasons"] = oos["reason"].value_counts().to_dict()
    out["OOS_long_per_symbol"] = {s: brief(g) for s, g in oos[oos.dir > 0].groupby("symbol")}
    out["OOS_short_per_symbol"] = {s: brief(g) for s, g in oos[oos.dir < 0].groupby("symbol")}
    # fixed-fraction check at lower risk (DD scales roughly with risk)
    out["OOS_at_0.25pct"] = summarize(oos, 0.25)
    return out


HOLD = ["APTUSDT", "ARBUSDT", "ATOMUSDT", "BCHUSDT", "DOTUSDT", "ETCUSDT", "FILUSDT", "NEARUSDT", "OPUSDT", "UNIUSDT"]


def _variants():
    return sorted(glob.glob(os.path.join(RES, "trend_momentum_[a-z]_*.json")))


def holdout():
    import bt.data as D
    root = os.environ["TM_HOLDOUT_ROOT"]
    D.ROOT = root
    out = {"symbols": HOLD, "root": root, "criteria": "t>=2 whole period; 2025-26 avg_R>0 base&harsh; >=6/10 symbols",
           "variants": {}}
    for p in _variants():
        r = json.load(open(p))
        tr = run_config(r["module"], r["fn"], HOLD, r["tf"], r["selected_params"], r["load"], "base", 2)
        th = run_config(r["module"], r["fn"], HOLD, r["tf"], r["selected_params"], r["load"], "harsh", 2)
        o, oh = tr[tr["t_entry"] >= IS_END], th[th["t_entry"] >= IS_END]
        per = {s_: brief(g) for s_, g in tr.groupby("symbol")}
        npos = sum(1 for v in per.values() if v.get("avg_R", 0) > 0)
        whole = summarize(tr, 0.5)
        oos, oosh = summarize(o, 0.5), summarize(oh, 0.5)
        ok = bool((whole.get("t_stat") or 0) >= 2 and oos.get("avg_R", -1) > 0 and oosh.get("avg_R", -1) > 0 and npos >= 6)
        out["variants"][os.path.basename(p)] = {
            "params": r["selected_params"], "tf": r["tf"], "whole": whole, "y2024": brief(tr[tr["t_entry"] < IS_END]),
            "oos_2025_26": oos, "oos_2025_26_harsh": oosh, "per_symbol": per, "symbols_positive": npos,
            "long": brief(tr[tr.dir > 0]), "short": brief(tr[tr.dir < 0]),
            "oos_long": brief(o[o.dir > 0]), "oos_short": brief(o[o.dir < 0]), "PASS": ok}
        print(os.path.basename(p), r["selected_params"], "whole", brief(tr), "oos", brief(o), "harsh", brief(oh),
              "sym+", npos, "PASS" if ok else "fail", flush=True)
    json.dump(out, open(os.path.join(RES, "trend_momentum_holdout.json"), "w"), indent=1, default=str)


def delay():
    """Robustness: act on every entry decision one bar later (stop level as computed at the decision)."""
    out = {}
    for p in _variants():
        r = json.load(open(p))
        params = dict(r["selected_params"], delay=1)
        tr = run_config(r["module"], r["fn"], SYMBOLS, r["tf"], params, r["load"], "base", 2)
        o, i = tr[tr["t_entry"] >= IS_END], tr[tr["t_entry"] < IS_END]
        out[os.path.basename(p)] = {"params": params, "IS": brief(i), "OOS": brief(o),
                                    "OOS_base_delay0": {k: r["selected_OOS"][k] for k in ("n", "avg_R", "t_stat")}}
        print(os.path.basename(p), "delay1 IS", brief(i), "OOS", brief(o), "| delay0 OOS", out[os.path.basename(p)]["OOS_base_delay0"], flush=True)
    json.dump(out, open(os.path.join(RES, "trend_momentum_delay.json"), "w"), indent=1, default=str)


def mtm_daily_R(tr):
    """Daily mark-to-market P&L in R units summed over all open trades (fees booked at exit)."""
    closes = {}
    rows = []
    for sym, g in tr.groupby("symbol"):
        if sym not in closes:
            closes[sym] = load(sym, "1d")["close"]
        cl = closes[sym]
        for r in g.itertuples():
            risk = abs(r.entry - r.stop)
            d0, d1 = r.t_entry.floor("D"), r.t_exit.floor("D")
            path = cl[(cl.index >= d0) & (cl.index < d1)]
            v = list(r.dir * (path.to_numpy() - r.entry) / risk) + [r.R]
            idx = list(path.index) + [d1]
            inc = np.diff(np.r_[0.0, v])
            rows.append(pd.Series(inc, index=idx))
    s_ = pd.concat(rows).groupby(level=0).sum().sort_index()
    full = pd.date_range(s_.index.min(), s_.index.max(), freq="D", tz="UTC")
    return s_.reindex(full, fill_value=0.0)


def mtm_stats(daily, risk_pct=0.5):
    eq = 1 + risk_pct / 100 * daily.cumsum()
    dd = (eq.cummax() - eq) / eq.cummax()
    yrs = len(daily) / 365.0
    return {"days": int(len(daily)), "sum_R": round(float(daily.sum()), 1),
            "ret_pct_simple": round(100 * float(eq.iloc[-1] - 1), 1),
            "ann_ret_pct_simple": round(100 * float(eq.iloc[-1] - 1) / yrs, 1),
            "sharpe_daily_ann": round(float(daily.mean() / daily.std() * math.sqrt(365)), 2) if daily.std() > 0 else None,
            "max_dd_pct_mtm": round(100 * float(dd.max()), 1),
            "worst_day_R": round(float(daily.min()), 1)}


def mtm():
    out, series = {}, {}
    for p in _variants():
        r = json.load(open(p))
        tr = run_config(r["module"], r["fn"], SYMBOLS, r["tf"], r["selected_params"], r["load"], "base", 2)
        dly = mtm_daily_R(tr)
        name = os.path.basename(p)[len("trend_momentum_"):-5]
        series[name] = dly
        out[name] = {"IS": mtm_stats(dly[dly.index < IS_END]), "OOS": mtm_stats(dly[dly.index >= IS_END])}
        print(name, out[name], flush=True)
    df = pd.DataFrame(series).fillna(0.0)
    o = df[df.index >= IS_END]
    out["_corr_OOS_daily_R"] = o.corr().round(2).to_dict()
    json.dump(out, open(os.path.join(RES, "trend_momentum_mtm.json"), "w"), indent=1, default=str)


def pooled():
    """Main 10 + holdout 10 symbols, OOS period 2025-01..2026-08, IS-selected configs (diagnostic)."""
    import bt.data as D
    main_root, hroot = D.ROOT, os.environ["TM_HOLDOUT_ROOT"]
    out = {}
    for p in _variants():
        r = json.load(open(p))
        parts = {}
        for cost in ("base", "harsh"):
            D.ROOT = main_root
            a = run_config(r["module"], r["fn"], SYMBOLS, r["tf"], r["selected_params"], r["load"], cost, 2)
            D.ROOT = hroot
            b = run_config(r["module"], r["fn"], HOLD, r["tf"], r["selected_params"], r["load"], cost, 2)
            t = pd.concat([a, b], ignore_index=True)
            parts[cost] = t[t["t_entry"] >= IS_END]
        o = parts["base"]
        per = o.groupby("symbol")["R"].mean()
        name = os.path.basename(p)[len("trend_momentum_"):-5]
        out[name] = {"params": r["selected_params"], "OOS20": summarize(o, 0.5), "OOS20_harsh": summarize(parts["harsh"], 0.5),
                     "symbols_positive_of_20": int((per > 0).sum()),
                     "long": brief(o[o.dir > 0]), "short": brief(o[o.dir < 0])}
        print(name, brief(o), "harsh", brief(parts["harsh"]), "sym+", int((per > 0).sum()), "/20", flush=True)
    D.ROOT = main_root
    json.dump(out, open(os.path.join(RES, "trend_momentum_pooled20.json"), "w"), indent=1, default=str)


def early_download():
    import bt.data as D
    D.ROOT = os.environ["TM_EARLY_ROOT"]
    for sym in SYMBOLS:
        print(sym, D.download_klines(sym, "5m", "2020-01", "2022-12"), flush=True)
    for cur in ("BTC", "ETH"):
        print(cur, D.download_dvol(cur, "2020-01", "2022-12"), flush=True)


def early():
    import bt.data as D
    D.ROOT = os.environ["TM_EARLY_ROOT"]
    out = {"period": "2020-01..2022-12", "criteria": "t>=2; avg_R>0 base&harsh; >=6/10 symbols", "variants": {}}
    for p in _variants():
        r = json.load(open(p))
        tr = run_config(r["module"], r["fn"], SYMBOLS, r["tf"], r["selected_params"], r["load"], "base", 2)
        th = run_config(r["module"], r["fn"], SYMBOLS, r["tf"], r["selected_params"], r["load"], "harsh", 2)
        per = {s_: brief(g) for s_, g in tr.groupby("symbol")}
        npos = sum(1 for v in per.values() if v.get("avg_R", 0) > 0)
        whole, harsh = summarize(tr, 0.5), summarize(th, 0.5)
        ok = bool((whole.get("t_stat") or 0) >= 2 and whole.get("avg_R", -1) > 0 and harsh.get("avg_R", -1) > 0 and npos >= 6)
        years = {str(y): brief(g) for y, g in tr.groupby(tr["t_entry"].dt.year)}
        name = os.path.basename(p)[len("trend_momentum_"):-5]
        out["variants"][name] = {"params": r["selected_params"], "tf": r["tf"], "whole": whole, "harsh": harsh,
                                 "per_symbol": per, "symbols_positive": npos, "by_year": years,
                                 "long": brief(tr[tr.dir > 0]), "short": brief(tr[tr.dir < 0]),
                                 "tails": tails(tr), "PASS": ok}
        print(name, r["selected_params"], brief(tr), "harsh", brief(th), "sym+", npos, years,
              "PASS" if ok else "fail", flush=True)
    json.dump(out, open(os.path.join(RES, "trend_momentum_early.json"), "w"), indent=1, default=str)


def main():
    if sys.argv[1:2] == ["early_download"]:
        return early_download()
    if sys.argv[1:2] == ["early"]:
        return early()
    if sys.argv[1:2] == ["pooled"]:
        return pooled()
    if sys.argv[1:2] == ["mtm"]:
        return mtm()
    if sys.argv[1:2] == ["holdout"]:
        return holdout()
    if sys.argv[1:2] == ["delay"]:
        return delay()
    files = sys.argv[1:] or _variants()
    res = {"buy_hold": buy_hold(), "variants": {}}
    for p in files:
        d = diag_one(p)
        res["variants"][d["file"]] = d
        print(d["file"], d["params"], "OOS", d["OOS"], "gross", d["OOS_gross_zero_cost"], flush=True)
    out = os.path.join(RES, "trend_momentum_diagnostics.json")
    if len(sys.argv) > 1 and os.path.exists(out):
        old = json.load(open(out))
        old["variants"].update(res["variants"])
        old["buy_hold"] = res["buy_hold"]
        res = old
    json.dump(res, open(out, "w"), indent=1, default=str)
    print("saved", out)


if __name__ == "__main__":
    main()
