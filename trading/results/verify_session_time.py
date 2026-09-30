"""Adversarial verification of the session_time WEAK claim: e_dcont 1h
(sess_filter(climax_cont, k=3, r=1.5, d=0.07, N=48, m=4, sess='ny')).

    cd /home/user/research/trading && python3 results/verify_session_time.py

  1. reproduce all 7 session configs of the 1h grid (base + harsh), compare with the JSON;
  2. stricter look-ahead check (60 truncation points on 3 symbols) + manual same-bar checks;
  3. per-symbol / per-year, day-clustered t;
  4. parameter-neighbour stability (one-at-a-time, NO selection) for sess='ny' and sess='all';
  5. null test: same exit logic (stop = low/high -/+ 0.25 ATR with 0.4% floor, 4R target from the
     signal close, 48-bar time exit, market entry at next open, base costs), same number of
     trades per (symbol, month) and same direction mix per (symbol, month), entry bars drawn at
     random within the month; pool A = bars whose close is in the NY session (the variant's own
     session), pool B = any bar. p = share of permutations with avg_R >= real avg_R.
Output: results/verify_session_time_e_dcont_1h.json
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/user/research/trading")
os.chdir("/home/user/research/trading")

import strategies.session_time as st  # noqa: E402
from strategies import volume_absorption as va  # noqa: E402
from bt.data import SYMBOLS, load  # noqa: E402
from bt.engine import IS_END, check_lookahead, simulate, summarize  # noqa: E402
from bt.features import atr  # noqa: E402
from bt.runner import COST_SCENARIOS  # noqa: E402

ALT_END = pd.Timestamp("2025-07-01", tz="UTC")
SEL = {"base": "climax_cont", "k": 3, "r": 1.5, "d": 0.07, "N": 48, "m": 4, "sess": "ny"}
TF = "1h"
NPERM = int(os.environ.get("NPERM", 1000))
DF = {s: load(s, TF) for s in SYMBOLS}


def run(params, cost="base"):
    parts = []
    for s in SYMBOLS:
        sig = st.sess_filter(DF[s], **params)
        parts.append(simulate(DF[s], sig, COST_SCENARIOS[cost], st.sess_filter.MAX_HOLD, st.sess_filter.LIMIT_TTL, s))
    return pd.concat([p for p in parts if len(p)], ignore_index=True)


def sm(tr):
    s = summarize(tr)
    return {k: s.get(k) for k in ("n", "win_pct", "avg_R", "t_stat", "t_stat_day_cluster", "ret_pct@0.5%",
                                  "max_dd_pct")}


def split3(tr):
    return {"IS": sm(tr[tr.t_entry < IS_END]), "OOS": sm(tr[tr.t_entry >= IS_END]),
            "altOOS_2025H2+": sm(tr[tr.t_entry >= ALT_END])}


# ----------------------------------------------------------------------------- null-test machinery
def replica(o, h, l, c, t, d, stop, target, costs, max_hold=48):
    """Engine-equivalent market-entry trade (bt.engine.simulate, market branch). Returns R or None."""
    n = len(o)
    if t >= n - 1:
        return None
    k0 = t + 1
    entry = o[k0] * (1 + d * costs.slippage)
    if (d > 0 and entry <= stop) or (d < 0 and entry >= stop):
        return None
    risk = abs(entry - stop)
    fee_out = costs.taker
    if (d > 0 and l[k0] <= stop) or (d < 0 and h[k0] >= stop):
        ex = stop * (1 - d * costs.slippage)
    else:
        k = k0
        while True:
            if k > k0 and ((d > 0 and l[k] <= stop) or (d < 0 and h[k] >= stop)):
                gap = (d > 0 and o[k] < stop) or (d < 0 and o[k] > stop)
                ex = (o[k] if gap else stop) * (1 - d * costs.slippage)
                break
            if not math.isnan(target) and ((d > 0 and h[k] >= target) or (d < 0 and l[k] <= target)):
                ex, fee_out = target, costs.maker
                break
            if k >= n - 1:
                ex = c[k]
                break
            if k - k0 + 1 >= max_hold:
                ex = o[k + 1] * (1 - d * costs.slippage)
                break
            k += 1
    return (d * (ex - entry) - entry * costs.taker - ex * fee_out) / risk


def exit_frame(df, m=4.0, buf=0.25):
    A = atr(df).to_numpy(float)
    h, l, c = (df[x].to_numpy(float) for x in ("high", "low", "close"))
    risk_l = np.maximum(c - (l - buf * A), va.MIN_RISK * c)
    risk_s = np.maximum((h + buf * A) - c, va.MIN_RISK * c)
    return {"stop_l": c - risk_l, "stop_s": c + risk_s, "tg_l": c + m * risk_l, "tg_s": c - m * risk_s}


def null_test(real, sess, rng, nperm=NPERM):
    costs = COST_SCENARIOS["base"]
    arrays, pools, efs = {}, {}, {}
    for s in SYMBOLS:
        df = DF[s]
        arrays[s] = tuple(df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
        efs[s] = exit_frame(df)
        ok = np.isfinite(efs[s]["stop_l"]) & (np.arange(len(df)) < len(df) - 1) & (np.arange(len(df)) >= 24 * 25)
        if sess != "all":
            ok &= st.session_mask(df, sess).to_numpy()
        mon = df.index.tz_localize(None).to_period("M").astype(str).to_numpy()
        pools[s] = {mm: np.flatnonzero(ok & (mon == mm)) for mm in np.unique(mon)}
    real = real.copy()
    real["mon"] = real["t_signal"].dt.tz_localize(None).dt.to_period("M").astype(str)
    groups = [(s, mm, g["dir"].to_numpy()) for (s, mm), g in real.groupby(["symbol", "mon"])]
    # sanity: replica on the real signal bars reproduces the engine R
    diffs = []
    for _, row in real.iterrows():
        s = row.symbol
        o, h, l, c = arrays[s]
        t = DF[s].index.get_loc(row.t_signal)
        dd = int(row.dir)
        stop = efs[s]["stop_l"][t] if dd > 0 else efs[s]["stop_s"][t]
        tg = efs[s]["tg_l"][t] if dd > 0 else efs[s]["tg_s"][t]
        diffs.append(abs(replica(o, h, l, c, t, dd, stop, tg, costs) - row.R))
    stats = {"IS": [], "OOS": [], "altOOS": [], "ALL": []}
    for _ in range(nperm):
        Rs, te = [], []
        for s, mm, dirs in groups:
            pool = pools[s].get(mm, np.array([], int))
            if len(pool) == 0:
                continue
            ts = rng.choice(pool, size=min(len(dirs), len(pool)), replace=False)
            dd = rng.permutation(dirs)[:len(ts)]
            o, h, l, c = arrays[s]
            ef = efs[s]
            for t, d in zip(ts, dd):
                d = int(d)
                r = replica(o, h, l, c, t, d, ef["stop_l"][t] if d > 0 else ef["stop_s"][t],
                            ef["tg_l"][t] if d > 0 else ef["tg_s"][t], costs)
                if r is not None:
                    Rs.append(r)
                    te.append(DF[s].index[t + 1])
        Rs, te = np.asarray(Rs), pd.DatetimeIndex(te)
        stats["ALL"].append(Rs.mean())
        stats["IS"].append(Rs[te < IS_END].mean())
        stats["OOS"].append(Rs[te >= IS_END].mean())
        stats["altOOS"].append(Rs[te >= ALT_END].mean())
    real_v = {"ALL": real.R.mean(), "IS": real[real.t_entry < IS_END].R.mean(),
              "OOS": real[real.t_entry >= IS_END].R.mean(), "altOOS": real[real.t_entry >= ALT_END].R.mean()}
    out = {"replica_max_abs_diff_R": float(max(diffs)), "n_perm": nperm, "pool_session": sess}
    for k in stats:
        a = np.asarray(stats[k])
        out[k] = {"real_avgR": round(float(real_v[k]), 4), "null_mean": round(float(a.mean()), 4),
                  "null_sd": round(float(a.std()), 4), "null_p95": round(float(np.quantile(a, 0.95)), 4),
                  "p_value": round(float((1 + (a >= real_v[k]).sum()) / (1 + len(a))), 4)}
    return out


def main():
    res = {}
    # 1. reproduce the 7-config grid
    ref = json.load(open("results/session_time_e_dcont_1h.json"))
    grid = []
    tr_sel = None
    for sess in st.SESSIONS:
        p = dict(SEL, sess=sess)
        tr = run(p)
        th = run(p, "harsh")
        row = {"sess": sess, **split3(tr), "OOS_harsh_avgR": round(float(th[th.t_entry >= IS_END].R.mean()), 3),
               "altOOS_harsh_avgR": round(float(th[th.t_entry >= ALT_END].R.mean()), 3)}
        jr = next(c for c in ref["configs"] if c["params"]["sess"] == sess)
        row["json_IS_OOS_avgR"] = [jr["IS"].get("avg_R"), jr["OOS"].get("avg_R")]
        grid.append(row)
        print("grid", sess, row["IS"]["avg_R"], row["IS"]["t_stat"], "|", row["OOS"]["n"], row["OOS"]["avg_R"],
              row["OOS"]["t_stat"], "harsh", row["OOS_harsh_avgR"], "json", row["json_IS_OOS_avgR"], flush=True)
        if sess == "ny":
            tr_sel, th_sel = tr, th
        if sess == "all":
            tr_all = tr
    res["grid_1h"] = grid
    # 3. per symbol / per year
    o = tr_sel[tr_sel.t_entry >= IS_END]
    res["selected_OOS_per_symbol"] = o.groupby("symbol")["R"].agg(["count", "mean", "sum"]).round(3).to_dict("index")
    res["selected_per_year"] = {str(y): sm(g) for y, g in tr_sel.groupby(tr_sel.t_entry.dt.year)}
    half = tr_sel.t_entry.dt.year.astype(str) + "H" + (1 + (tr_sel.t_entry.dt.month > 6).astype(int)).astype(str)
    res["selected_per_half"] = {k: [int(len(g)), round(float(g.R.mean()), 3)] for k, g in tr_sel.groupby(half)}
    res["selected_OOS_exit_reasons"] = o["reason"].value_counts().to_dict()
    res["selected_OOS_long_short"] = o.groupby("dir")["R"].agg(["count", "mean"]).round(3).to_dict("index")
    # concentration: OOS avg_R without the top-5 days
    daily = o.groupby(o.t_entry.dt.floor("D"))["R"].sum().sort_values(ascending=False)
    res["selected_OOS_top_days"] = {str(k.date()): round(float(v), 2) for k, v in daily.head(8).items()}
    top5 = set(daily.head(5).index)
    rest = o[~o.t_entry.dt.floor("D").isin(top5)]
    res["selected_OOS_avgR_ex_top5_days"] = round(float(rest.R.mean()), 3)
    oa = tr_all[tr_all.t_entry >= IS_END]
    da = oa.groupby(oa.t_entry.dt.floor("D"))["R"].sum().sort_values(ascending=False)
    res["all_OOS_top_days"] = {str(k.date()): round(float(v), 2) for k, v in da.head(8).items()}
    res["all_OOS_avgR_ex_top5_days"] = round(float(oa[~oa.t_entry.dt.floor("D").isin(set(da.head(5).index))].R.mean()), 3)
    res["all_OOS_avgR_ex_top10_days"] = round(float(oa[~oa.t_entry.dt.floor("D").isin(set(da.head(10).index))].R.mean()), 3)
    print("per-year", {k: (v["n"], v["avg_R"]) for k, v in res["selected_per_year"].items()}, flush=True)
    # 2. stricter look-ahead
    la = {}
    for s in ("ETHUSDT", "SOLUSDT", "DOGEUSDT"):
        try:
            check_lookahead(st.sess_filter, DF[s], SEL, n_checks=30, seed=11)
            la[s] = "pass"
        except AssertionError as e:
            la[s] = str(e)[:300]
    res["lookahead_60pts"] = la
    print("lookahead", la, flush=True)
    # 4. neighbours (one at a time, no selection)
    neigh = {"k": [2, 2.5, 3.5, 4], "r": [1.2, 1.25, 1.75, 2.0], "d": [0.0, 0.05, 0.1, 0.15],
             "N": [24, 36, 72, 96], "m": [2, 3, 5, 6], "buf": [0.1, 0.5]}
    nb = []
    for sess in ("ny", "all"):
        for key, vals in neigh.items():
            for v in vals:
                p = dict(SEL, sess=sess, **{key: v})
                tr = run(p)
                x = split3(tr)
                nb.append({"sess": sess, "param": key, "value": v, "IS_avgR": x["IS"]["avg_R"], "IS_t": x["IS"]["t_stat"],
                           "OOS_n": x["OOS"]["n"], "OOS_avgR": x["OOS"]["avg_R"], "OOS_t": x["OOS"]["t_stat"],
                           "OOS_t_daycl": x["OOS"]["t_stat_day_cluster"]})
                print("neigh", sess, key, v, x["IS"]["avg_R"], "|", x["OOS"]["n"], x["OOS"]["avg_R"], x["OOS"]["t_stat"],
                      flush=True)
    res["neighbours"] = nb
    for sess in ("ny", "all"):
        vals = [r["OOS_avgR"] for r in nb if r["sess"] == sess]
        res[f"neighbours_{sess}_OOS_share_positive"] = round(float(np.mean([v > 0 for v in vals])), 3)
        res[f"neighbours_{sess}_OOS_median"] = round(float(np.median(vals)), 3)
    json.dump(res, open("results/verify_session_time_e_dcont_1h.json", "w"), indent=1, default=str)
    # 5. null tests
    rng = np.random.default_rng(20260930)
    res["null_ny_pool_ny"] = null_test(tr_sel, "ny", rng)
    print("null ny/ny", res["null_ny_pool_ny"], flush=True)
    res["null_ny_pool_any"] = null_test(tr_sel, "all", rng)
    print("null ny/any", res["null_ny_pool_any"], flush=True)
    res["null_all_pool_any"] = null_test(tr_all, "all", rng, nperm=min(NPERM, 500))
    print("null all/any", res["null_all_pool_any"], flush=True)
    json.dump(res, open("results/verify_session_time_e_dcont_1h.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
