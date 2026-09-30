"""pump_anatomy: event strategies through bt.engine (1h bars, full USD-M universe incl. delisted).

    python3 -m strategies.pump_anatomy_bt

Rules (chosen from the IS rule table / IS contagion 'self' leg, see report):
  L_fundneg : long at the day close when the last funding print is negative (IS: best fwd7 mean of all rules)
  S_pump20  : short at the day close after a daily close-to-close gain >= +20% (IS 'self' abnormal return < 0)
Both need eligibility known at t: age >= 30 days, median daily quote volume (previous 30 days) >= $2M.
Stop = entry -/+ k * ATR14(daily); no target; MAX_HOLD in 1h bars. Grid k in {2,3} x hold in {72,168}:
the variant is chosen on IS (< 2025-01-01) only; OOS reported for all.
Funding is added post-hoc per trade from the funding prints between entry and exit.
"""
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd

from bt.engine import Costs, check_lookahead, simulate, split_summary
from strategies.pump_anatomy_analysis import RES
from strategies.pump_anatomy_panel import ROOT, load_1h, load_funding

warnings.filterwarnings("ignore")
HARSH = Costs(taker=0.0006, maker=0.0004, slippage=0.0005)


def prep(sym):
    h = load_1h(sym)
    if h is None or len(h) < 24 * 40:
        return None
    df = h[["open", "high", "low", "close", "quote_vol"]].astype(float)
    f = load_funding(sym)
    if f is not None and len(f):
        f = f.sort_values("ts").copy()
        f["ts"] = f["ts"].astype("datetime64[ns, UTC]")
        key = pd.DataFrame({"t": (df.index + pd.Timedelta(hours=1)).astype("datetime64[ns, UTC]")})
        m = pd.merge_asof(key, f.rename(columns={"ts": "t"}), on="t", direction="backward")
        df["fund_last"] = m["funding"].to_numpy()
    else:
        df["fund_last"] = np.nan
    return df


def strat(df, rule="L_fundneg", k=2.0, hold=168):
    day = df.index.floor("1D")
    g = df.groupby(day)
    d = pd.DataFrame({"high": g["high"].max(), "low": g["low"].min(), "close": g["close"].last(),
                      "qv": g["quote_vol"].sum(), "n": g["close"].count()})
    pc = d["close"].shift(1)
    tr = pd.concat([d["high"] - d["low"], (d["high"] - pc).abs(), (d["low"] - pc).abs()], axis=1).max(axis=1)
    d["atr"] = tr.rolling(14, min_periods=10).mean()
    d["ret1"] = d["close"] / pc - 1
    d["med30"] = d["qv"].shift(1).rolling(30, min_periods=20).median()
    d["age"] = np.arange(len(d))
    elig = (d["age"] >= 30) & (d["med30"] >= 2e6) & (d["n"] >= 20)
    # map to the last bar of each COMPLETE day (hour 23 bar; its close = day close)
    last = df.index.hour == 23
    dd = d.reindex(day)
    dd.index = df.index
    out = pd.DataFrame(index=df.index)
    out["signal"] = 0.0
    out["stop"] = np.nan
    el = elig.reindex(day).to_numpy() & last
    c = df["close"].to_numpy()
    atr = dd["atr"].to_numpy()
    if rule == "L_fundneg":
        s = el & (df["fund_last"].to_numpy() < 0)
        out.loc[s, "signal"] = 1.0
        out.loc[s, "stop"] = c[s] - k * atr[s]
    elif rule == "S_pump20":
        s = el & (dd["ret1"].to_numpy() >= 0.20)
        out.loc[s, "signal"] = -1.0
        out.loc[s, "stop"] = c[s] + k * atr[s]
    elif rule == "L_scoreA":
        # precomputed column: 1 if the symbol's score_A was in the day's top decile at the close of that day
        # (walk-forward logit fitted on <= 2024-12-24; cross-sectional rank uses only same-day features)
        s = el & (dd.index.hour == 23) & (df["sA_top"].to_numpy() > 0)
        out.loc[s, "signal"] = 1.0
        out.loc[s, "stop"] = c[s] - k * atr[s]
    out.loc[~np.isfinite(out["stop"]), "signal"] = 0.0
    return out


def add_funding(tr, fund_cache):
    if not len(tr):
        return tr
    fr = []
    for _, t in tr.iterrows():
        f = fund_cache.get(t["symbol"])
        if f is None:
            fr.append(0.0)
            continue
        m = (f["ts"] > t["t_entry"]) & (f["ts"] <= t["t_exit"])
        fr.append(-t["dir"] * float(f.loc[m, "funding"].sum()))
    tr = tr.copy()
    tr["fund_ret_pct"] = 100 * np.array(fr)
    tr["R_fund"] = tr["R"] + tr["fund_ret_pct"] / tr["risk_pct"]
    return tr


def run_one(args):
    sym, rule, k, hold, costs = args
    df = prep(sym)
    if df is None:
        return None
    sig = strat(df, rule, k, hold)
    t = simulate(df, sig, costs, max_hold=hold, symbol=sym)
    return t


def main():
    syms = pd.read_csv(os.path.join(ROOT, "symbols_use.csv"))["symbol"].tolist()
    cls = pd.read_csv(os.path.join(ROOT, "symbol_class.csv"), index_col=0)
    from strategies.pump_anatomy_panel import INDEX_LIKE, TRADFI
    excl = set(INDEX_LIKE) | set(TRADFI) | set(cls.index[cls["we_ratio"] < 0.45])
    syms = [s for s in syms if s not in excl]
    # look-ahead check on two liquid symbols
    for s in ("DOGEUSDT", "WIFUSDT"):
        df = prep(s)
        for rule in ("L_fundneg", "S_pump20"):
            check_lookahead(strat, df, {"rule": rule, "k": 2.0, "hold": 168}, n_checks=8, min_bars=24 * 60)
    print("lookahead OK", flush=True)
    data = {s: prep(s) for s in syms}
    data = {s: d for s, d in data.items() if d is not None}
    fund = {}
    for s in data:
        f = load_funding(s)
        if f is not None:
            fund[s] = f
    rows, keep = [], {}
    for rule in ("L_fundneg", "S_pump20"):
        for k in (2.0, 3.0):
            for hold in (72, 168):
                for cname, costs in (("base", Costs()), ("harsh", HARSH)):
                    parts = []
                    for s, df in data.items():
                        sig = strat(df, rule, k, hold)
                        if (sig["signal"] != 0).any():
                            parts.append(simulate(df, sig, costs, max_hold=hold, symbol=s))
                    tr = pd.concat([x for x in parts if len(x)], ignore_index=True)
                    tr = add_funding(tr, fund)
                    tag = f"{rule}_k{k:g}_h{hold}_{cname}"
                    keep[tag] = tr
                    ss = split_summary(tr, label=tag)
                    tf = tr.assign(R=tr["R_fund"])
                    sf = split_summary(tf, label=tag + "+fund")
                    for per in ("IS", "OOS"):
                        rows.append({"rule": rule, "k": k, "hold_h": hold, "costs": cname, "period": per, **ss[per],
                                     "avg_R_with_funding": sf[per].get("avg_R"),
                                     "t_day_cluster_with_funding": sf[per].get("t_stat_day_cluster")})
                    print(tag, ss["IS"].get("avg_R"), ss["OOS"].get("avg_R"), flush=True)
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(RES, "pump_anatomy_bt_grid.csv"), index=False)
    # IS selection per rule (harsh costs, with funding), report OOS of the chosen variant
    sel = {}
    for rule in ("L_fundneg", "S_pump20"):
        g = t[(t["rule"] == rule) & (t["costs"] == "harsh") & (t["period"] == "IS")]
        best = g.sort_values("avg_R_with_funding", ascending=False).iloc[0]
        o = t[(t["rule"] == rule) & (t["k"] == best["k"]) & (t["hold_h"] == best["hold_h"]) & (t["period"] == "OOS")]
        sel[rule] = {"chosen_on_IS": {"k": float(best["k"]), "hold_h": int(best["hold_h"])},
                     "IS_harsh": best.dropna().to_dict(), "OOS": o.dropna(axis=1).to_dict("records")}
    json.dump(sel, open(os.path.join(RES, "pump_anatomy_bt_selected.json"), "w"), indent=1, default=str)
    for tag, tr in keep.items():
        if tag.endswith("harsh"):
            tr.to_csv(os.path.join(RES, f"pump_anatomy_bt_trades_{tag}.csv.gz"), index=False)
    print(json.dumps(sel, indent=1, default=str))


def main_score():
    """Scanner (model A, primary) as an event strategy: long top-decile names, ATR stop, max hold."""
    sc = pd.read_parquet(os.path.join(ROOT, "scores.parquet"))
    sc["top"] = (sc.groupby("date")["score_A"].rank(pct=True) > 0.9).astype(float)
    top = {s: g.set_index("date")["top"] for s, g in sc.groupby("symbol")}
    fund = {}
    rows, keep = [], {}
    data = {}
    for s in top:
        df = prep(s)
        if df is None:
            continue
        # value for day d placed on the hour-23 bar of day d (known at that bar's close)
        m = top[s].reindex(df.index.floor("1D")).to_numpy()
        df["sA_top"] = np.where(df.index.hour == 23, np.nan_to_num(m), 0.0)
        data[s] = df
        f = load_funding(s)
        if f is not None:
            fund[s] = f
    for k in (2.0, 3.0):
        for hold in (72, 168):
            for cname, costs in (("base", Costs()), ("harsh", HARSH)):
                parts = [simulate(df, strat(df, "L_scoreA", k, hold), costs, max_hold=hold, symbol=s)
                         for s, df in data.items() if df["sA_top"].any()]
                tr = add_funding(pd.concat([x for x in parts if len(x)], ignore_index=True), fund)
                tag = f"L_scoreA_k{k:g}_h{hold}_{cname}"
                ss = split_summary(tr, label=tag)
                sf = split_summary(tr.assign(R=tr["R_fund"]), label=tag + "+fund")
                for per in ("IS", "OOS"):
                    rows.append({"rule": "L_scoreA", "k": k, "hold_h": hold, "costs": cname, "period": per, **ss[per],
                                 "avg_R_with_funding": sf[per].get("avg_R"),
                                 "t_day_cluster_with_funding": sf[per].get("t_stat_day_cluster")})
                print(tag, ss["IS"].get("avg_R"), ss["OOS"].get("avg_R"), flush=True)
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(RES, "pump_anatomy_bt_scoreA.csv"), index=False)
    with pd.option_context("display.width", 250):
        print(t.to_string())


if __name__ == "__main__":
    main_score() if len(sys.argv) > 1 and sys.argv[1] == "score" else main()
