"""Diagnostics: is C_level 4h a disguised short-term price reversal? (no selection; OOS read-only)
    cd trading && python3 -m results.verify_funding_positioning_diag
"""
import json
import numpy as np
import pandas as pd
import strategies.funding_positioning as F
from bt.engine import simulate, Costs
from bt.features import atr
import bt.data as D
from results.verify_funding_positioning import load, blk, run, IS_END, SYMS, BASE

def rev_ctl(df, pct=0.9, k=1, days=30, stop_atr=2.0, rr=2.0):
    """CONTROL: price-only short-horizon twin. 30d percentile of -(k-bar log return) -> same fade mechanics."""
    lc = np.log(df["close"])
    x = -(lc - lc.shift(k))
    p = F.roll_pct(x, F.bars(df, 24 * days))
    L, S = F._apply_trend(df, p >= pct, p <= 1 - pct, "none", 24, 48)
    return F._pack(df, L, S, stop_atr, rr)

def main():
    out = {}
    rows = []
    for s in SYMS:
        df = load(s, "4h")
        sig = F.rcrowd_4h(df, src="level", pct=0.9)
        tr = simulate(df, sig, BASE, 18, None, s)
        lc = np.log(df["close"]); A = atr(df)
        pos = df.index.get_indexer(tr["t_signal"])
        r1 = (lc - lc.shift(1)).to_numpy()[pos]; r6 = (lc - lc.shift(6)).to_numpy()[pos]
        a = (A / df["close"]).to_numpy()[pos]
        tr["ret1_dir"] = tr["dir"].to_numpy() * r1 / a    # signal-bar return in the trade direction, ATR units
        tr["ret6_dir"] = tr["dir"].to_numpy() * r6 / a
        rows.append(tr)
    T = pd.concat(rows, ignore_index=True)
    O = T[T["t_entry"] >= IS_END]
    out["OOS_corr_R_ret1dir"] = round(float(O["R"].corr(O["ret1_dir"])), 3)
    out["OOS_corr_R_ret6dir"] = round(float(O["R"].corr(O["ret6_dir"])), 3)
    out["OOS_share_signal_bar_against_trade"] = round(float((O["ret1_dir"] < 0).mean()), 3)
    q = pd.qcut(O["ret1_dir"], 3, labels=["against", "mid", "with"])
    out["OOS_by_signal_bar_return_tercile"] = {str(k): {kk: blk(g).get(kk) for kk in ("n", "avg_R", "t_stat")} for k, g in O.groupby(q, observed=True)}
    q6 = pd.qcut(O["ret6_dir"], 3, labels=["against", "mid", "with"])
    out["OOS_by_24h_return_tercile"] = {str(k): {kk: blk(g).get(kk) for kk in ("n", "avg_R", "t_stat")} for k, g in O.groupby(q6, observed=True)}
    ctl = {}
    for k in (1, 6):
        tr = run(rev_ctl, {"k": k}, hold=18)
        ctl[f"rev_ctl_k{k}"] = {"IS": {kk: blk(tr, hi=IS_END).get(kk) for kk in ("n", "avg_R", "t_stat")},
                                "OOS": {kk: blk(tr, lo=IS_END).get(kk) for kk in ("n", "avg_R", "t_stat", "t_cl_week", "sym_pos")}}
    out["controls_price_reversal"] = ctl
    # weekly cross-sectional clustering of signals
    wk = O.groupby(O["t_entry"].dt.tz_convert(None).dt.to_period("W")).size()
    out["OOS_trades_per_week"] = {"mean": round(float(wk.mean()), 1), "max": int(wk.max()), "weeks": int(len(wk))}
    same = O.groupby("t_signal")["symbol"].nunique()
    out["OOS_share_trades_with_ge3_symbols_same_bar"] = round(float((O["t_signal"].map(same) >= 3).mean()), 3)
    # signed: net direction per signal bar
    net = O.groupby("t_signal")["dir"].sum()
    out["OOS_share_trades_in_same_side_cluster_ge3"] = round(float((O["t_signal"].map(net.abs()) >= 3).mean()), 3)
    # 1h-bar resolution: is the edge concentrated in the first 4h after entry? use 1h data, same 4h trades
    print(json.dumps(out, indent=1))
    json.dump(out, open("results/verify_funding_positioning_diag.json", "w"), indent=1, default=str)

if __name__ == "__main__":
    main()
