"""Adversarial verification of the ml_combo family (claimed WEAK, best variant t1_raw_1h).

    cd /home/user/research/trading
    python3 results/verify_ml_combo.py replicate   # rebuild 1h track-1 panel + walk-forward raw small/large from scratch
    python3 results/verify_ml_combo.py analyze     # re-select, alt split, harsh, stability, null tests -> JSON

Nothing in bt/*.py or strategies/ml_combo*.py is modified. A separate cache dir is used so the original
agent's cached panel/predictions are not overwritten (they are only read, to compare).
"""
import json
import math
import os
import sys
import time

VCACHE = "/tmp/claude-0/-home-user-research/ea6ba1ab-fe99-5191-91e4-bb9455e40592/scratchpad/verify_ml_combo"
ORIG = "/tmp/claude-0/-home-user-research/ea6ba1ab-fe99-5191-91e4-bb9455e40592/scratchpad/ml_combo"
os.environ["ML_COMBO_CACHE"] = VCACHE
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import strategies.ml_combo as M  # noqa: E402
from bt.engine import Costs, simulate, summarize  # noqa: E402
from bt.features import atr  # noqa: E402
from bt.runner import COST_SCENARIOS, score  # noqa: E402

RES = os.path.dirname(os.path.abspath(__file__))
QS = [0.90, 0.95, 0.98]
RISK = 0.5
IS1 = pd.Timestamp("2025-01-01", tz="UTC")
IS2 = pd.Timestamp("2025-07-01", tz="UTC")
STRIDE = {"15m": 4, "1h": 2}

VARIANTS = [  # (name, tf, track, aug, models, tag)
    ("t1_raw_1h", "1h", 1, "raw", ["small", "large"], ""),
    ("t1_sym_1h", "1h", 1, "sym", ["small", "large"], ""),
    ("t2_raw_1h", "1h", 2, "raw", ["small", "large"], ""),
    ("t2_sym_1h", "1h", 2, "sym", ["small", "large"], ""),
    ("t1_raw_15m", "15m", 1, "raw", ["small", "large"], ""),
    ("t1_sym_15m", "15m", 1, "sym", ["small", "large"], ""),
    ("t2_raw_15m", "15m", 2, "raw", ["small", "large"], ""),
    ("t2_sym_15m", "15m", 2, "sym", ["small", "large"], ""),
    ("t1_sym_ps_1h", "1h", 1, "sym", ["ps"], "_ps"),
]


def ppath(d, tf, track, aug, model, tag=""):
    return os.path.join(d, f"preds_{tf}_t{track}_{aug}_{model}{tag}.parquet")


def log(*a):
    print(*a, flush=True)


# ------------------------------------------------------------------ (2) replication from scratch

def cmd_replicate():
    os.makedirs(VCACHE, exist_ok=True)
    rep = {}
    t0 = time.time()
    P, cols = M.build_panel("1h", 1, use_cache=False)  # rebuilds from raw data, writes into VCACHE
    log(f"panel rebuilt {P.shape} {time.time() - t0:.0f}s")
    Po = pd.read_parquet(os.path.join(ORIG, "panel_1h_t1.parquet"))
    a = P.set_index(["symbol", "ts"]).sort_index()
    b = Po.set_index(["symbol", "ts"]).sort_index()
    cc = [c for c in a.columns if c in b.columns]
    same_shape = a.shape == b.shape
    d = np.nanmax(np.abs(a[cc].to_numpy(np.float64) - b.loc[a.index, cc].to_numpy(np.float64)))
    nanmis = int((a[cc].isna().to_numpy() != b.loc[a.index, cc].isna().to_numpy()).sum())
    rep["panel_vs_original"] = {"shape_new": list(a.shape), "shape_orig": list(b.shape), "same_shape": same_shape,
                                "max_abs_diff": float(d), "nan_mismatch": nanmis}
    log("panel compare", rep["panel_vs_original"])
    for model in ("small", "large"):
        t1 = time.time()
        preds, _, _ = M.walk_forward(P, cols, "1h", 1, "raw", model, stride=STRIDE["1h"], log=False)
        preds.to_parquet(ppath(VCACHE, "1h", 1, "raw", model), index=False)
        po = pd.read_parquet(ppath(ORIG, "1h", 1, "raw", model))
        j = preds.merge(po, on=["symbol", "ts"], suffixes=("_new", "_orig"))
        dm = float(np.max(np.abs(j[["pL_new", "pS_new"]].to_numpy() - j[["pL_orig", "pS_orig"]].to_numpy())))
        rep[f"preds_raw_{model}"] = {"rows_new": len(preds), "rows_orig": len(po), "rows_joined": len(j),
                                     "max_abs_diff": dm, "secs": round(time.time() - t1)}
        log(model, rep[f"preds_raw_{model}"])
    with open(os.path.join(RES, "verify_ml_combo_replicate.json"), "w") as f:
        json.dump(rep, f, indent=1, default=str)


# ------------------------------------------------------------------ helpers

_RAW = {}


def raw_all(tf):
    if tf not in _RAW:
        _RAW[tf] = {s: M.load_raw(s, tf, False)[["open", "high", "low", "close", "volume"]] for s in M.SYMBOLS}
    return _RAW[tf]


_PAN = {}


def panel_meta(tf, track):
    key = (tf, track)
    if key not in _PAN:
        _PAN[key] = pd.read_parquet(os.path.join(ORIG, f"panel_{tf}_t{track}.parquet"),
                                    columns=["symbol", "ts", "costR", "RL", "RS"])
    return _PAN[key]


def edges_for(tf, track, aug, model, tag, src=ORIG):
    preds = pd.read_parquet(ppath(src, tf, track, aug, model, tag))
    return M.edges(preds, panel_meta(tf, track))


def sim_all(tf, E, thr, cost):
    K, H = M.TF_CFG[tf]["K"], M.TF_CFG[tf]["H"]
    out = []
    for s, df in raw_all(tf).items():
        sig = M.signals_for_symbol(df, E[E["symbol"] == s], thr, K)
        out.append(simulate(df, sig, COST_SCENARIOS[cost], H, None, s))
    out = [o for o in out if len(o)]
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["t_entry", "R", "symbol", "dir"])


def day_t(tr):
    if len(tr) < 3:
        return None
    R = tr["R"].to_numpy()
    e = pd.Series(R - R.mean()).groupby(pd.DatetimeIndex(tr["t_entry"]).floor("1D").to_numpy()).sum().to_numpy()
    se = math.sqrt((e ** 2).sum() * len(e) / max(len(e) - 1, 1)) / len(R)
    return round(R.mean() / se, 2) if se > 0 else None


def S(tr, lo=None, hi=None):
    part = tr
    if lo is not None:
        part = part[part["t_entry"] >= lo]
    if hi is not None:
        part = part[part["t_entry"] < hi]
    s = summarize(part, RISK) if len(part) else {"n": 0}
    s.pop("label", None)
    if len(part):
        s["t_day"] = day_t(part)
        s["long_share"] = round(float((part["dir"] > 0).mean()), 3)
    return s


def sym_pos(tr):
    if not len(tr):
        return 0, {}
    g = tr.groupby("symbol")["R"].agg(["count", "mean"])
    return int((g["mean"] > 0).sum()), {k: (int(v["count"]), round(float(v["mean"]), 3)) for k, v in g.iterrows()}


def evaluate_split(split_end, oos_end=None, variants=VARIANTS, log_rows=True):
    """Re-run the family's selection protocol with IS = entries < split_end.
    Threshold = q-quantile of walk-forward edges with ts < split_end; select max IS t (n>=30) inside each variant;
    best variant = max IS t among the selected. Reports OOS = [split_end, oos_end)."""
    res = {}
    for name, tf, track, aug, models, tag in variants:
        rows = []
        for model in models:
            if not os.path.exists(ppath(ORIG, tf, track, aug, model, tag)):
                log("missing", name, model)
                continue
            E = edges_for(tf, track, aug, model, tag)
            best = E.loc[E["ts"] < split_end, ["eL", "eS"]].max(axis=1)
            for q in QS:
                thr = float(best.quantile(q))
                tr = sim_all(tf, E, thr, "base")
                r = {"model": model, "q": q, "thr": round(thr, 5), "IS": S(tr, None, split_end),
                     "OOS": S(tr, split_end, oos_end), "_E": E, "_tr": tr}
                rows.append(r)
                if log_rows:
                    log(name, model, q, "IS", r["IS"].get("n"), r["IS"].get("avg_R"), r["IS"].get("t_stat"),
                        "| OOS", r["OOS"].get("n"), r["OOS"].get("avg_R"), r["OOS"].get("t_stat"))
        sel = max(rows, key=lambda r: score(r["IS"]))
        trh = sim_all(tf, sel["_E"], sel["thr"], "harsh")
        oos_tr = sel["_tr"][(sel["_tr"]["t_entry"] >= split_end) &
                            ((sel["_tr"]["t_entry"] < oos_end) if oos_end is not None else True)]
        npos, per_sym = sym_pos(oos_tr)
        oos_avgs = [r["OOS"].get("avg_R") for r in rows if r["OOS"].get("n", 0) >= 10]
        share = float(np.mean([x > 0 for x in oos_avgs])) if oos_avgs else None
        o, h = sel["OOS"], S(trh, split_end, oos_end)
        if not o.get("n") or o.get("avg_R", 0) <= 0:
            verdict = "NO_EDGE"
        elif (o.get("t_stat") or 0) >= 2 and h.get("avg_R", 0) > 0 and npos >= 6 and (share or 0) >= 0.5:
            verdict = "PROMISING"
        else:
            verdict = "WEAK"
        res[name] = {"selected": {"model": sel["model"], "q": sel["q"], "thr": sel["thr"]},
                     "IS": sel["IS"], "OOS": o, "OOS_harsh": h, "oos_symbols_positive": npos,
                     "oos_per_symbol": per_sym, "share_configs_oos_positive": share, "verdict": verdict,
                     "configs": [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows],
                     "_sel": sel}
    order = sorted(res, key=lambda k: score(res[k]["IS"]), reverse=True)
    return res, order


# ------------------------------------------------------------------ vectorised engine-equivalent bracket R

def bracket_net_R(df, K, H, costs):
    """Net R (engine rules, market entry at open[t+1], stop/target = close_t -/+ K*ATR14, max hold H) of a long
    and a short signal at EVERY bar t. NaN where the engine would skip the trade."""
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    A = atr(df, 14).to_numpy(float)
    n = len(c)
    out = {}
    for d in (1, -1):
        stop = c - d * K * A
        tgt = c + d * K * A
        ent = np.full(n, np.nan)
        ent[:-1] = o[1:] * (1 + d * costs.slippage)
        valid = (d * (ent - stop) > 0) & ~np.isnan(A)
        done = ~valid
        ex = np.full(n, np.nan)
        fee_out = np.full(n, costs.taker)
        t = np.arange(n)
        for j in range(1, H + 1):
            k = t + j
            ok = k < n
            kk = np.where(ok, k, n - 1)
            oj, hj, lj, cj = o[kk], h[kk], l[kk], c[kk]
            m = ~done & ok
            hit = m & ((lj <= stop) if d > 0 else (hj >= stop))
            gap = (j > 1) & ((oj < stop) if d > 0 else (oj > stop))
            px = np.where(gap, oj, stop) * (1 - d * costs.slippage)
            ex = np.where(hit, px, ex)
            done |= hit
            m = ~done & ok
            th = m & ((hj >= tgt) if d > 0 else (lj <= tgt))
            ex = np.where(th, tgt, ex)
            fee_out = np.where(th, costs.maker, fee_out)
            done |= th
            # end of data: engine exits at close of last bar (taker, no slippage)
            m = ~done & ok & (kk >= n - 1)
            ex = np.where(m, cj, ex)
            done |= m
            if j == H:
                ke = t + H + 1
                ok2 = ~done & (ke < n)
                ex = np.where(ok2, o[np.where(ke < n, ke, n - 1)] * (1 - d * costs.slippage), ex)
                done |= ok2
        risk = np.abs(ent - stop)
        gross = d * (ex - ent)
        fees = ent * costs.taker + ex * fee_out
        R = np.where(valid, (gross - fees) / risk, np.nan)
        out["RL" if d > 0 else "RS"] = R
    out["stop_pct"] = K * A / c
    return pd.DataFrame(out, index=df.index)


def null_tests(tr, tf, cost, lo, hi, n_perm=2000, seed=11):
    """Keep exit logic, trades per month, per-symbol/month direction counts; randomise entry times.
    (a) independent: each trade -> random bar of the same symbol & month, same direction;
    (b) clustered: every distinct signal timestamp (with its whole set of symbol/direction trades) is moved to one
        random bar of the same month -> preserves cross-symbol same-time clustering;
    (c) vol-matched: like (a) but the random bar must lie in the same stop%-tercile (per symbol-month)."""
    K, H = M.TF_CFG[tf]["K"], M.TF_CFG[tf]["H"]
    raw = raw_all(tf)
    tabs = {s: bracket_net_R(df, K, H, COST_SCENARIOS[cost]) for s, df in raw.items()}
    part = tr[(tr["t_entry"] >= lo) & (tr["t_entry"] < hi)].copy()
    # engine-equivalence check of the per-bar table
    chk = []
    for s, g in part.groupby("symbol"):
        tb = tabs[s]
        v = np.where(g["dir"] > 0, tb["RL"].reindex(g["t_signal"]).to_numpy(), tb["RS"].reindex(g["t_signal"]).to_numpy())
        chk.append(np.abs(v - g["R"].to_numpy()))
    chk = np.concatenate(chk)
    real = float(part["R"].mean())
    rng = np.random.default_rng(seed)
    part["month"] = pd.DatetimeIndex(part["t_signal"]).tz_convert(None).to_period("M")
    # pools
    pools = {}
    for s, tb in tabs.items():
        t = tb[(tb.index >= lo - pd.Timedelta(days=31)) & (tb.index < hi)].copy()
        t["month"] = t.index.tz_convert(None).to_period("M")
        t["terc"] = t.groupby("month")["stop_pct"].transform(lambda x: pd.qcut(x.rank(method="first"), 3, labels=False))
        pools[s] = t
    real_terc = []
    for _, r in part.iterrows():
        real_terc.append(pools[r["symbol"]].at[r["t_signal"], "terc"])
    part["terc"] = real_terc

    def sample_a(match_vol):
        arrs = []
        for (s, mth, d, tc), g in part.groupby(["symbol", "month", "dir", "terc"] if match_vol
                                               else ["symbol", "month", "dir", pd.Series(0, index=part.index)]):
            pool = pools[s]
            sel = pool["month"] == mth
            if match_vol:
                sel &= pool["terc"] == tc
            vals = pool.loc[sel, "RL" if d > 0 else "RS"].to_numpy()
            vals = vals[~np.isnan(vals)]
            arrs.append(vals[rng.integers(0, len(vals), size=(n_perm, len(g)))])
        return np.concatenate(arrs, axis=1).mean(axis=1)

    null_a = sample_a(False)
    null_c = sample_a(True)
    # (b) clustered
    grid_ts = pd.DatetimeIndex(sorted(set().union(*[set(p.index) for p in pools.values()])))
    gmonth = grid_ts.tz_convert(None).to_period("M")
    RLw = pd.DataFrame({s: pools[s]["RL"] for s in pools}).reindex(grid_ts)
    RSw = pd.DataFrame({s: pools[s]["RS"] for s in pools}).reindex(grid_ts)
    sym_idx = {s: i for i, s in enumerate(RLw.columns)}
    RLa, RSa = RLw.to_numpy(), RSw.to_numpy()
    sums = np.zeros(n_perm)
    cnts = np.zeros(n_perm)
    for mth, gm in part.groupby("month"):
        rows_m = np.flatnonzero(gmonth == mth)
        for _, gt in gm.groupby("t_signal"):
            shift = rows_m[rng.integers(0, len(rows_m), size=n_perm)]
            for _, r in gt.iterrows():
                arr = RLa if r["dir"] > 0 else RSa
                v = arr[shift, sym_idx[r["symbol"]]]
                ok = ~np.isnan(v)
                sums += np.where(ok, v, 0)
                cnts += ok
    null_b = sums / np.maximum(cnts, 1)
    p = lambda nul: float((1 + (nul >= real).sum()) / (1 + len(nul)))
    return {"period": f"{lo.date()}..{hi.date()}", "cost": cost, "n_trades": int(len(part)), "real_avg_R": round(real, 4),
            "engine_equivalence_max_abs_diff": float(np.nanmax(chk)), "engine_equivalence_nan": int(np.isnan(chk).sum()),
            "n_perm": n_perm,
            "null_independent": {"mean": round(float(null_a.mean()), 4), "sd": round(float(null_a.std()), 4),
                                 "p_value": p(null_a)},
            "null_clustered_timestamps": {"mean": round(float(null_b.mean()), 4), "sd": round(float(null_b.std()), 4),
                                          "p_value": p(null_b)},
            "null_vol_matched": {"mean": round(float(null_c.mean()), 4), "sd": round(float(null_c.std()), 4),
                                 "p_value": p(null_c)}}


# ------------------------------------------------------------------ analysis

def strip(res):
    return {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in res.items()}


def cmd_analyze():
    out = {}
    END = pd.Timestamp("2026-09-01", tz="UTC")
    # --- (2b) evaluate the replicated predictions exactly like the original eval
    rep_rows = []
    for model in ("small", "large"):
        pr = ppath(VCACHE, "1h", 1, "raw", model)
        if not os.path.exists(pr):
            continue
        E = edges_for("1h", 1, "raw", model, "", src=VCACHE)
        best = E.loc[E["ts"] < IS1, ["eL", "eS"]].max(axis=1)
        for q in QS:
            thr = float(best.quantile(q))
            tr = sim_all("1h", E, thr, "base")
            rep_rows.append({"model": model, "q": q, "thr": round(thr, 5), "IS": S(tr, None, IS1), "OOS": S(tr, IS1)})
            log("replicated", model, q, rep_rows[-1]["IS"].get("n"), rep_rows[-1]["IS"].get("t_stat"),
                rep_rows[-1]["OOS"].get("n"), rep_rows[-1]["OOS"].get("avg_R"), rep_rows[-1]["OOS"].get("t_stat"))
    out["replicated_t1_raw_1h_from_scratch"] = rep_rows

    # --- original split, all 9 variants from the original cached predictions
    res1, order1 = evaluate_split(IS1)
    out["split_2025_01"] = {"variant_order_by_IS_t": order1, "variants": strip(res1)}
    fam1 = order1[0]
    log("orig split best variant", fam1, res1[fam1]["selected"], res1[fam1]["OOS"])

    # --- (3) alternative split
    res2, order2 = evaluate_split(IS2)
    out["split_2025_07"] = {"variant_order_by_IS_t": order2, "variants": strip(res2)}
    fam2 = order2[0]
    log("alt split best variant", fam2, res2[fam2]["selected"], res2[fam2]["OOS"], res2[fam2]["OOS_harsh"])

    # --- (5) stability of the claimed config t1_raw_1h large q=0.98 (original split)
    sel = res1["t1_raw_1h"]["_sel"]
    tr = sel["_tr"]
    stab = {"per_year": {str(y): S(g) for y, g in tr.groupby(tr["t_entry"].dt.year)},
            "per_half": {f"{y}H{1 + (m > 6)}": S(g) for (y, m), g in
                         tr.groupby([tr["t_entry"].dt.year, np.where(tr["t_entry"].dt.month > 6, 7, 1)])},
            "oos_per_symbol": sym_pos(tr[tr["t_entry"] >= IS1])[1],
            "oos_by_direction": {("long" if d > 0 else "short"): S(g, IS1) for d, g in tr.groupby("dir")},
            "oos_excluding_best_month": None}
    oo = tr[tr["t_entry"] >= IS1].copy()
    oo["m"] = pd.DatetimeIndex(oo["t_entry"]).tz_convert(None).to_period("M")
    bym = oo.groupby("m")["R"].agg(["count", "sum", "mean"])
    stab["oos_by_month"] = {str(k): [int(v["count"]), round(float(v["sum"]), 2)] for k, v in bym.iterrows()}
    top = bym["sum"].idxmax()
    stab["oos_excluding_best_month"] = {"month": str(top), **S(oo[oo["m"] != top])}
    top2 = bym["sum"].nlargest(2).index
    stab["oos_excluding_best_2_months"] = {"months": [str(x) for x in top2], **S(oo[~oo["m"].isin(top2)])}
    # parameter neighbours (diagnostic only, NOT used for selection): q grid around 0.98, both models
    E_l = edges_for("1h", 1, "raw", "large", "")
    E_s = edges_for("1h", 1, "raw", "small", "")
    neigh = []
    for model, E in (("large", E_l), ("small", E_s)):
        best = E.loc[E["ts"] < IS1, ["eL", "eS"]].max(axis=1)
        for q in (0.95, 0.96, 0.97, 0.975, 0.98, 0.985, 0.99):
            thr = float(best.quantile(q))
            t2 = sim_all("1h", E, thr, "base")
            neigh.append({"model": model, "q": q, "IS": {k: S(t2, None, IS1).get(k) for k in ("n", "avg_R", "t_stat")},
                          "OOS": {k: S(t2, IS1).get(k) for k in ("n", "avg_R", "t_stat", "t_day")}})
            log("neighbour", model, q, neigh[-1]["IS"], neigh[-1]["OOS"])
    stab["param_neighbours_diagnostic"] = neigh
    out["stability_t1_raw_1h_large_q098"] = stab

    # --- (6) null tests on the claimed config (and on the alt-split selection)
    nulls = {"claimed_OOS_base": null_tests(tr, "1h", "base", IS1, END),
             "claimed_IS_base": null_tests(tr, "1h", "base", pd.Timestamp("2023-01-01", tz="UTC"), IS1)}
    trh = sim_all("1h", sel["_E"], sel["thr"], "harsh")
    nulls["claimed_OOS_harsh"] = null_tests(trh, "1h", "harsh", IS1, END)
    s2 = res2[fam2]["_sel"]
    tf2 = [v for v in VARIANTS if v[0] == fam2][0][1]
    nulls[f"altsplit_{fam2}_OOS_base"] = null_tests(s2["_tr"], tf2, "base", IS2, END)
    for k, v in nulls.items():
        log("null", k, json.dumps(v))
    out["null_tests"] = nulls
    with open(os.path.join(RES, "verify_ml_combo.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)
    log("saved", os.path.join(RES, "verify_ml_combo.json"))


if __name__ == "__main__":
    {"replicate": cmd_replicate, "analyze": cmd_analyze}[sys.argv[1]]()
