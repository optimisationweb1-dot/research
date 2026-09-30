"""Adversarial verification of the oi_flow claim (b1* squeeze-follow 1h).

    cd /home/user/research/trading
    OI_FLOW_HOLDOUT_ROOT=<dir with holdout parquet> python3 results/verify_oi_flow.py

Nothing in bt/ or strategies/ is modified. The strategy functions are imported unchanged
(importing strategies.oi_flow also applies its data patches: pandas-3 _asof fix, metrics avail=ts+6min).
Output: results/verify_oi_flow.json
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import bt.data as D  # noqa: E402
import strategies.oi_flow as F  # noqa: E402  (applies patches)
from bt.engine import Costs, check_lookahead, simulate, summarize  # noqa: E402
from bt.features import atr  # noqa: E402
from bt.runner import COST_SCENARIOS  # noqa: E402

ORIG = D.ROOT
HROOT = os.environ.get("OI_FLOW_HOLDOUT_ROOT", "")
HOLD = "DOTUSDT NEARUSDT ATOMUSDT FILUSDT BCHUSDT ETCUSDT UNIUSDT APTUSDT ARBUSDT OPUSDT".split()
MAIN = D.SYMBOLS
SQ = {"k_hours": 1, "move_atr": 2.0, "mode": "follow"}
T24 = pd.Timestamp("2024-01-01", tz="UTC")
T25 = pd.Timestamp("2025-01-01", tz="UTC")
T25H2 = pd.Timestamp("2025-07-01", tz="UTC")
RNG = np.random.default_rng(20260927)
NPERM = 200
_CACHE = {}


def load(sym, root, lag_min=None):
    key = (sym, root, lag_min)
    if key in _CACHE:
        return _CACHE[key]
    D.ROOT = root
    if lag_min is not None:
        F.METRICS_LAG = pd.Timedelta(minutes=lag_min)
    try:
        df = D.load(sym, "1h", metrics=True)
    finally:
        F.METRICS_LAG = pd.Timedelta(minutes=6)
        D.ROOT = ORIG
    _CACHE[key] = df
    return df


def tstat(R):
    R = np.asarray(R, float)
    if len(R) < 2 or R.std(ddof=1) == 0:
        return float("nan")
    return float(R.mean() / R.std(ddof=1) * math.sqrt(len(R)))


def cluster_t(tr, key="day"):
    """t-stat of mean R with trades clustered by signal day (cross-symbol co-movement)."""
    if len(tr) < 3:
        return float("nan")
    g = tr.groupby(tr.t_signal.dt.floor("1D")).R
    s, n = g.sum(), g.size()
    N = len(tr)
    m = tr.R.mean()
    e = (s - n * m)  # cluster residual sums
    var = (e ** 2).sum() / N ** 2 * len(s) / (len(s) - 1)
    return float(m / math.sqrt(var))


def pk(tr, risk=0.5):
    s = summarize(tr, risk)
    out = {k: s.get(k) for k in ("n", "win_pct", "avg_R", "t_stat", "ret_pct@0.5%", "max_dd_pct")}
    if len(tr) > 2:
        out["t_cluster_day"] = round(cluster_t(tr), 2)
    return out


def run(fn, params, syms, root, cost="base", start=None, lag_min=None, delay=0):
    f = getattr(F, fn)
    parts = []
    for s in syms:
        df = load(s, root, lag_min)
        sig = f(df, **params)
        if delay:
            sig = sig.shift(delay).fillna({"signal": 0.0, "exit_signal": 0.0})
        if start is not None:
            sig.loc[sig.index < start, "signal"] = 0
        c = COST_SCENARIOS[cost] if isinstance(cost, str) else cost
        parts.append(simulate(df, sig, c, f.MAX_HOLD, None, s))
    parts = [p for p in parts if len(p)]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


# ------------------------------------------------------------ independent-trade outcome arrays (mirror engine)
def outcomes(df, d, stop_atr=2.0, rr=1.5, max_hold=24, costs=Costs()):
    """R of a market trade signalled at the close of every bar t (direction d), engine semantics,
    each trade independent of the others. NaN where no valid trade."""
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    A = atr(df).to_numpy()
    n = len(df)
    stop = c - d * stop_atr * A
    risk0 = np.abs(c - stop)
    target = c + d * rr * risk0
    R = np.full(n, np.nan)
    idx = np.arange(n - 1 - max_hold - 1)  # skip trades that would hit end-of-data
    k0 = idx + 1
    entry = o[k0] * (1 + d * costs.slippage)
    st, tg = stop[idx], target[idx]
    valid = np.isfinite(st) & (risk0[idx] > 0) & ~((d > 0) & (entry <= st)) & ~((d < 0) & (entry >= st))
    exit_px = np.full(len(idx), np.nan)
    fee_out = np.full(len(idx), costs.taker)
    done = ~valid
    for j in range(max_hold):
        k = k0 + j
        if j == 0:
            hit_s = ((d > 0) & (l[k] <= st)) | ((d < 0) & (h[k] >= st))
            m = ~done & hit_s
            exit_px[m] = (st * (1 - d * costs.slippage))[m]
            done |= m
        else:
            hit_s = ((d > 0) & (l[k] <= st)) | ((d < 0) & (h[k] >= st))
            m = ~done & hit_s
            gap = ((d > 0) & (o[k] < st)) | ((d < 0) & (o[k] > st))
            px = np.where(gap, o[k], st) * (1 - d * costs.slippage)
            exit_px[m] = px[m]
            done |= m
        hit_t = ((d > 0) & (h[k] >= tg)) | ((d < 0) & (l[k] <= tg))
        m = ~done & hit_t
        exit_px[m] = tg[m]
        fee_out[m] = costs.maker
        done |= m
        if j + 1 >= max_hold:
            m = ~done
            exit_px[m] = (o[k + 1] * (1 - d * costs.slippage))[m]
            done |= m
    risk = np.abs(entry - st)
    gross = d * (exit_px - entry)
    fees = entry * costs.taker + exit_px * fee_out
    r = (gross - fees) / risk
    r[~valid] = np.nan
    R[idx] = r
    return R


def null_tests(syms, root, periods):
    """(i) random entry bars within symbol-month, same count & direction mix; (ii) conditional null:
    random bars drawn from the no-OI impulse candidates (|1h move| >= 2 ATR) with the same count/direction."""
    res = {}
    real_all, pools = [], {}
    for s in syms:
        df = load(s, root)
        sig = F.squeeze(df, **SQ)
        tr = simulate(df, sig, COST_SCENARIOS["base"], F.squeeze.MAX_HOLD, None, s)
        tr = tr[tr.t_signal >= T24]
        RL, RS = outcomes(df, 1), outcomes(df, -1)
        # engine consistency check on real trades
        pos = df.index.get_indexer(tr.t_signal)
        Rind = np.where(tr.dir.to_numpy() > 0, RL[pos], RS[pos])
        ok = np.isfinite(Rind)
        assert np.allclose(Rind[ok], tr.R.to_numpy()[ok], atol=1e-9), f"outcome mismatch {s}"
        A = atr(df)
        mv = (df.close - df.close.shift(1)) / A
        zo = F.oi_z(df, 1)
        base_ok = (df.index >= T24) & zo.notna().to_numpy() & np.isfinite(RL) & np.isfinite(RS)
        month = df.index.tz_localize(None).to_period("M")
        pools[s] = dict(RL=RL, RS=RS, month=month, base_ok=base_ok,
                        up=base_ok & (mv >= 2.0).to_numpy(), dn=base_ok & (mv <= -2.0).to_numpy())
        tr = tr.assign(month=tr.t_signal.dt.tz_localize(None).dt.to_period("M"))
        real_all.append(tr)
    real = pd.concat(real_all, ignore_index=True)
    for pname, (a, b) in periods.items():
        rt = real[(real.t_entry >= a) & (real.t_entry < b)]
        real_mean = float(rt.R.mean())
        cnt = rt.groupby(["symbol", "month", "dir"]).size()
        nulls = {"random_time": [], "impulse_noOI": []}
        cands = {}
        for (s, mo, d), k in cnt.items():
            P = pools[s]
            inm = (P["month"] == mo)
            c1 = np.flatnonzero(inm & P["base_ok"])
            c2 = np.flatnonzero(inm & (P["up"] if d > 0 else P["dn"]))
            vec = P["RL"] if d > 0 else P["RS"]
            cands[(s, mo, d)] = (k, vec[c1], vec[c2] if len(c2) else vec[c1])
        for p in range(NPERM):
            for kind in nulls:
                vals = []
                for key, (k, r1, r2) in cands.items():
                    pool = r1 if kind == "random_time" else r2
                    vals.append(RNG.choice(pool, size=k, replace=len(pool) < k))
                nulls[kind].append(float(np.concatenate(vals).mean()))
        out = {"real_avg_R": round(real_mean, 4), "n": int(len(rt))}
        for kind, v in nulls.items():
            v = np.array(v)
            out[kind] = {"null_mean": round(float(v.mean()), 4), "null_sd": round(float(v.std()), 4),
                         "p_value_one_sided": round(float((1 + (v >= real_mean).sum()) / (1 + len(v))), 4),
                         "null_p95": round(float(np.quantile(v, 0.95)), 4)}
        res[pname] = out
        print("null", pname, json.dumps(out), flush=True)
    return res


def main():
    out = {}
    # ---- 0. lookahead: engine check on several symbols with many points (truncation-based)
    la = {}
    for s in ("BTCUSDT", "SOLUSDT", "LINKUSDT"):
        df = load(s, ORIG)
        la[s] = bool(check_lookahead(F.squeeze, df, SQ, n_checks=40))
    out["lookahead_check"] = la

    # ---- 1. re-run selected config
    tr = run("squeeze", SQ, MAIN, ORIG)
    trh = run("squeeze", SQ, MAIN, ORIG, "harsh")
    tr0 = run("squeeze", SQ, MAIN, ORIG, Costs(0, 0, 0))
    IS, OOS = tr[tr.t_entry < T25], tr[tr.t_entry >= T25]
    out["rerun"] = {"IS_2024": pk(IS), "OOS_2025_26": pk(OOS),
                    "OOS_harsh": pk(trh[trh.t_entry >= T25]), "OOS_zero_cost": pk(tr0[tr0.t_entry >= T25]),
                    "OOS_long": pk(OOS[OOS.dir > 0]), "OOS_short": pk(OOS[OOS.dir < 0]),
                    "OOS_per_symbol": {s: summarize(g).get("avg_R") for s, g in OOS.groupby("symbol")},
                    "per_halfyear": {h: pk(g) for h, g in tr.groupby(
                        tr.t_entry.dt.year.astype(str) + "H" + ((tr.t_entry.dt.month > 6) + 1).astype(str))},
                    "OOS_exit_reasons": OOS.reason.value_counts().to_dict(),
                    "OOS_symbols_positive": int(sum(summarize(g)["avg_R"] > 0 for _, g in OOS.groupby("symbol")))}
    print("rerun", json.dumps(out["rerun"], default=str), flush=True)

    # ---- 2. alternative split: IS < 2025-07-01, OOS 2025-07..2026-08, re-select on same grids
    grids = {
        "squeeze": [{"k_hours": k, "move_atr": m, "mode": md} for md in ("fade", "follow") for k in (1, 4) for m in (1.25, 2.0)],
        "capit": [{"move_atr": m, "z": z, "mode": md} for md in ("fade", "follow") for m in (2.0, 3.0) for z in (-2.0, -3.0)],
        "newpos": [{"k_hours": k, "move_atr": m, "mode": "follow"} for k in (1, 4) for m in (1.25, 2.0)],
        "impulse": [{"k_hours": k, "move_atr": m, "mode": "follow"} for k in (1, 4) for m in (1.25, 2.0)],
    }
    alt = {}
    for fn, grid in grids.items():
        rows = []
        for p in grid:
            t = run(fn, p, MAIN, ORIG)
            a, b = t[t.t_entry < T25H2], t[t.t_entry >= T25H2]
            rows.append({"params": p, "IS": pk(a), "OOS": pk(b)})
        sel = max(rows, key=lambda r: r["IS"]["t_stat"] if r["IS"]["n"] >= 30 and r["IS"]["t_stat"] is not None else -1e9)
        th = run(fn, sel["params"], MAIN, ORIG, "harsh")
        tb = run(fn, sel["params"], MAIN, ORIG)
        ob = tb[tb.t_entry >= T25H2]
        alt[fn] = {"n_configs": len(rows), "selected": sel["params"], "IS": sel["IS"], "OOS": sel["OOS"],
                   "OOS_harsh": pk(th[th.t_entry >= T25H2]),
                   "OOS_symbols_positive": int(sum(summarize(g)["avg_R"] > 0 for _, g in ob.groupby("symbol"))),
                   "share_configs_OOS_positive": float(np.mean([r["OOS"]["avg_R"] > 0 for r in rows if r["OOS"]["n"] >= 10])),
                   "configs": rows}
        print("alt", fn, json.dumps({k: v for k, v in alt[fn].items() if k != "configs"}), flush=True)
    # fixed claimed config on the alt OOS for reference (not a selection)
    b = tr[tr.t_entry >= T25H2]
    alt["claimed_config_on_alt_OOS"] = pk(b)
    out["alt_split"] = alt

    # ---- 3. parameter neighbours (diagnostic only, no selection)
    neigh = {}
    for m in (1.5, 1.75, 2.0, 2.25, 2.5, 3.0):
        for z in (-1.0, -1.25, -1.5, -2.0, -2.5):
            t = run("squeeze", {**SQ, "move_atr": m, "z": z}, MAIN, ORIG)
            neigh[f"move{m}_z{z}"] = {"IS": summarize(t[t.t_entry < T25]).get("avg_R"),
                                      "OOS": summarize(t[t.t_entry >= T25]).get("avg_R"),
                                      "OOS_t": summarize(t[t.t_entry >= T25]).get("t_stat"),
                                      "OOS_n": int((t.t_entry >= T25).sum())}
    for sa in (1.5, 2.0, 2.5):
        for rr in (1.0, 1.5, 2.0, 3.0):
            t = run("squeeze", {**SQ, "stop_atr": sa, "rr": rr}, MAIN, ORIG)
            neigh[f"stop{sa}_rr{rr}"] = {"IS": summarize(t[t.t_entry < T25]).get("avg_R"),
                                         "OOS": summarize(t[t.t_entry >= T25]).get("avg_R"),
                                         "OOS_t": summarize(t[t.t_entry >= T25]).get("t_stat"),
                                         "OOS_n": int((t.t_entry >= T25).sum())}
    out["neighbours"] = neigh
    oo = [v["OOS"] for v in neigh.values() if v["OOS"] is not None]
    out["neighbours_summary"] = {"n": len(oo), "share_OOS_positive": round(float(np.mean([x > 0 for x in oo])), 2),
                                 "median_OOS_avgR": round(float(np.median(oo)), 3)}
    print("neigh", json.dumps(out["neighbours_summary"]), flush=True)

    # ---- 4. latency: extra 5 / 10 min of metrics latency, 1-bar entry delay
    lat = {}
    for lag in (11, 16):
        t = run("squeeze", SQ, MAIN, ORIG, lag_min=lag)
        lat[f"metrics_avail_ts+{lag}min"] = {"IS": pk(t[t.t_entry < T25]), "OOS": pk(t[t.t_entry >= T25])}
    t = run("squeeze", SQ, MAIN, ORIG, delay=1)
    lat["entry_delay_1bar"] = {"IS": pk(t[t.t_entry < T25]), "OOS": pk(t[t.t_entry >= T25])}
    out["latency"] = lat
    print("latency", json.dumps(lat), flush=True)

    # ---- 5. holdout re-run + cluster t
    if HROOT:
        th = run("squeeze", SQ, HOLD, HROOT, start=T24)
        thh = run("squeeze", SQ, HOLD, HROOT, "harsh", start=T24)
        ti = run("impulse", SQ, HOLD, HROOT, start=T24)
        out["holdout"] = {"all": pk(th), "2024": pk(th[th.t_entry < T25]), "2025_26": pk(th[th.t_entry >= T25]),
                          "harsh_all": pk(thh), "long": pk(th[th.dir > 0]), "short": pk(th[th.dir < 0]),
                          "per_symbol": {s: summarize(g).get("avg_R") for s, g in th.groupby("symbol")},
                          "impulse_ctl_all": pk(ti), "impulse_ctl_2025_26": pk(ti[ti.t_entry >= T25])}
        print("holdout", json.dumps(out["holdout"]), flush=True)
    out["main_cluster_t"] = {"OOS": round(cluster_t(OOS), 2), "IS": round(cluster_t(IS), 2)}

    # ---- 6. null tests
    periods = {"main_OOS_2025_26": (T25, pd.Timestamp("2027-01-01", tz="UTC")),
               "main_all_2024_26": (T24, pd.Timestamp("2027-01-01", tz="UTC")),
               "main_altOOS_2025H2_26": (T25H2, pd.Timestamp("2027-01-01", tz="UTC"))}
    out["null_main"] = null_tests(MAIN, ORIG, periods)
    if HROOT:
        out["null_holdout"] = null_tests(HOLD, HROOT, {"holdout_all_2024_26": periods["main_all_2024_26"],
                                                       "holdout_2025_26": periods["main_OOS_2025_26"]})
    out["n_configs_run_by_verifier"] = {"alt_split_grids": sum(len(g) for g in grids.values()),
                                        "neighbours": len(neigh), "latency": 3, "note": "diagnostics, no selection"}
    json.dump(out, open(os.path.join(HERE, "results", "verify_oi_flow.json"), "w"), indent=1, default=str)
    print("done")


if __name__ == "__main__":
    main()
