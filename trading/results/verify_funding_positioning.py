"""Adversarial verification of the funding_positioning family (claimed best: C_level 4h = rcrowd src=level pct=0.9).

    cd /home/user/research/trading && python3 -m results.verify_funding_positioning all

Does NOT edit bt/*.py or strategies/funding_positioning*.py. Importing strategies.funding_positioning applies
its loader patch (pandas-3 merge_asof fix + metrics avail = ts + 6 min).
Output: results/verify_funding_positioning.json
"""
import json
import math
import sys
import time

import numpy as np
import pandas as pd

import strategies.funding_positioning as F
import bt.data as D
from bt.engine import Costs, simulate, summarize
from bt.features import atr

SYMS = D.SYMBOLS
BASE = Costs()
HARSH = Costs(taker=0.0006, maker=0.0004, slippage=0.0005)
IS_END = pd.Timestamp("2025-01-01", tz="UTC")
ALT_END = pd.Timestamp("2025-07-01", tz="UTC")
OUT = "results/verify_funding_positioning.json"
_CACHE = {}


def load(sym, tf, lag_min=6):
    key = (sym, tf, lag_min)
    if key not in _CACHE:
        F.METRICS_LAG = pd.Timedelta(minutes=lag_min)
        _CACHE[key] = D.load(sym, tf, metrics=True, funding=True)
        F.METRICS_LAG = pd.Timedelta(minutes=6)
    return _CACHE[key]


def rcrowd_days(df, pct=0.9, days=30, stop_atr=2.0, rr=2.0):
    """Exact copy of F.rcrowd(src='level', trend='none') with the lookback window as a parameter."""
    x = F.logpos(df["ls_accounts"])
    p = F.roll_pct(x, F.bars(df, 24 * days))
    L, S = F._apply_trend(df, p >= pct, p <= 1 - pct, "none", 24, 48)
    return F._pack(df, L, S, stop_atr, rr)


def run(fn, params, tf="4h", costs=BASE, hold=None, lag_min=6, delay=0, syms=SYMS):
    hold = hold or getattr(fn, "MAX_HOLD", None) or (18 if tf == "4h" else 72)
    out = []
    for s in syms:
        df = load(s, tf, lag_min)
        sig = fn(df, **params)
        if delay:
            sig = sig.shift(delay)
            sig["signal"] = sig["signal"].fillna(0.0)
            sig["exit_signal"] = sig["exit_signal"].fillna(0.0)
        out.append(simulate(df, sig, costs, hold, None, s))
    out = [o for o in out if len(o)]
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def clustered_t(tr, freq="W"):
    if len(tr) < 3:
        return None
    mu = tr["R"].mean()
    g = (tr["R"] - mu).groupby(tr["t_entry"].dt.tz_convert(None).dt.to_period(freq)).sum()
    G = len(g)
    var = (g ** 2).sum() / len(tr) ** 2 * G / max(G - 1, 1)
    return round(float(mu / math.sqrt(var)), 2) if var > 0 else None


def blk(tr, lo=None, hi=None):
    if len(tr):
        m = np.ones(len(tr), bool)
        if lo is not None:
            m &= (tr["t_entry"] >= lo).to_numpy()
        if hi is not None:
            m &= (tr["t_entry"] < hi).to_numpy()
        tr = tr[m]
    if not len(tr):
        return {"n": 0}
    s = summarize(tr, 0.5)
    s.pop("label", None)
    s["t_cl_week"] = clustered_t(tr)
    s["sym_pos"] = int(sum(g["R"].mean() > 0 for _, g in tr.groupby("symbol")))
    s["n_sym"] = int(tr["symbol"].nunique())
    return s


# ---------------------------------------------------------------- (2)(4)(5) rerun, harsh, stability
def rerun_selected():
    fn = F.rcrowd_4h
    p = {"src": "level", "pct": 0.9}
    tb, th = run(fn, p), run(fn, p, costs=HARSH)
    res = {"base_IS": blk(tb, hi=IS_END), "base_OOS": blk(tb, lo=IS_END), "harsh_IS": blk(th, hi=IS_END),
           "harsh_OOS": blk(th, lo=IS_END)}
    res["per_symbol_OOS_base"] = {s: {k: blk(g, lo=IS_END).get(k) for k in ("n", "avg_R", "t_stat")}
                                  for s, g in tb.groupby("symbol")}
    res["per_symbol_OOS_harsh"] = {s: blk(g, lo=IS_END).get("avg_R") for s, g in th.groupby("symbol")}
    per = {}
    for lab, a, b in [("2024H1", "2024-01-01", "2024-07-01"), ("2024H2", "2024-07-01", "2025-01-01"),
                      ("2025H1", "2025-01-01", "2025-07-01"), ("2025H2", "2025-07-01", "2026-01-01"),
                      ("2026H1", "2026-01-01", "2026-07-01"), ("2026Jul-Aug", "2026-07-01", "2026-09-01")]:
        bb = blk(tb, pd.Timestamp(a, tz="UTC"), pd.Timestamp(b, tz="UTC"))
        hh = blk(th, pd.Timestamp(a, tz="UTC"), pd.Timestamp(b, tz="UTC"))
        per[lab] = {"n": bb.get("n"), "avg_R": bb.get("avg_R"), "t": bb.get("t_stat"), "t_cl": bb.get("t_cl_week"),
                    "harsh_avg_R": hh.get("avg_R"), "sym_pos": bb.get("sym_pos")}
    res["per_halfyear"] = per
    oos = tb[tb["t_entry"] >= IS_END]
    res["OOS_long"] = blk(oos[oos["dir"] > 0])
    res["OOS_short"] = blk(oos[oos["dir"] < 0])
    res["OOS_exit_reasons"] = oos["reason"].value_counts().to_dict()
    res["OOS_avgR_by_reason"] = oos.groupby("reason")["R"].mean().round(3).to_dict()
    # concentration: share of OOS sum_R from top 5% trades / top 10 weeks
    R = np.sort(oos["R"].to_numpy())[::-1]
    wk = oos.groupby(oos["t_entry"].dt.tz_convert(None).dt.to_period("W"))["R"].sum().sort_values(ascending=False)
    res["OOS_concentration"] = {"sum_R": round(float(R.sum()), 1), "top10_weeks_sum_R": round(float(wk.head(10).sum()), 1),
                                "n_weeks": int(len(wk)), "sum_R_without_top10_weeks": round(float(wk.iloc[10:].sum()), 1)}
    return res, tb


def neighbours():
    """OOS of every neighbour (NOT used for selection): pct x window, then exits x hold."""
    rows = []
    for pct in (0.85, 0.875, 0.9, 0.925, 0.95):
        for days in (20, 30, 45, 60):
            tr = run(rcrowd_days, {"pct": pct, "days": days}, hold=18)
            rows.append({"pct": pct, "days": days, "IS": {k: blk(tr, hi=IS_END).get(k) for k in ("n", "avg_R", "t_stat")},
                         "OOS": {k: blk(tr, lo=IS_END).get(k) for k in ("n", "avg_R", "t_stat", "t_cl_week", "sym_pos")}})
    ex = []
    for st in (1.5, 2.0, 2.5, 3.0):
        for rr in (1.5, 2.0, 2.5, 3.0):
            for hold in (12, 18, 30):
                tr = run(rcrowd_days, {"pct": 0.9, "days": 30, "stop_atr": st, "rr": rr}, hold=hold)
                ex.append({"stop_atr": st, "rr": rr, "hold": hold,
                           "IS": {k: blk(tr, hi=IS_END).get(k) for k in ("n", "avg_R", "t_stat")},
                           "OOS": {k: blk(tr, lo=IS_END).get(k) for k in ("n", "avg_R", "t_stat")}})
    def agg(rs):
        v = [r["OOS"]["avg_R"] for r in rs]
        return {"n": len(v), "share_pos": round(float(np.mean([x > 0 for x in v])), 3),
                "median": round(float(np.median(v)), 3), "min": min(v), "max": max(v),
                "share_t_ge_2": round(float(np.mean([(r["OOS"]["t_stat"] or 0) >= 2 for r in rs])), 3)}
    return {"pct_x_days": rows, "pct_x_days_summary": agg(rows), "exits": ex, "exits_summary": agg(ex)}


def timing_stress():
    """Information-lag and entry-delay stress for the selected config (no selection)."""
    p = {"src": "level", "pct": 0.9}
    out = {}
    for lag in (6, 30, 120):
        tr = run(F.rcrowd_4h, p, lag_min=lag)
        out[f"metrics_lag_{lag}min"] = {k: blk(tr, lo=IS_END).get(k) for k in ("n", "avg_R", "t_stat", "t_cl_week")}
    for d in (1, 2):
        tr = run(F.rcrowd_4h, p, delay=d)
        out[f"entry_delay_{d}bar"] = {k: blk(tr, lo=IS_END).get(k) for k in ("n", "avg_R", "t_stat", "t_cl_week")}
    return out


# ---------------------------------------------------------------- (3) alternative split, whole family
ROUND1 = ["Aabs_break", "Aabs_ema", "Aabs_none", "Az_break", "Az_ema", "Az_none", "B_tdiv", "B_topdiv",
          "C_dcrowd", "C_level", "C_resid", "D_oicrowd"]
POSTHOC = ["R2Ffollow", "R2smartcrowd", "R3short"]   # designed after seeing 2025-26; reported, flagged
CONTROL = ["R2ctlPrice"]


def alt_split():
    import glob
    import os
    res = {}
    for p in sorted(glob.glob("results/funding_positioning_*_*h.json")):
        b = os.path.basename(p)[len("funding_positioning_"):-5]
        var, tf = b.rsplit("_", 1)
        if var == "R2sensExits":
            continue
        r = json.load(open(p))
        fn = getattr(F, r["fn"])
        rows = []
        for c in r["configs"]:
            tr = run(fn, c["params"], tf=tf)
            ais, aoos = blk(tr, hi=ALT_END), blk(tr, lo=ALT_END)
            rows.append({"params": c["params"], "altIS": {k: ais.get(k) for k in ("n", "avg_R", "t_stat")},
                         "altOOS": {k: aoos.get(k) for k in ("n", "avg_R", "t_stat")}})
        sc = lambda x: x["altIS"]["t_stat"] if (x["altIS"]["n"] or 0) >= 30 and x["altIS"]["t_stat"] is not None else -1e9
        best = max(rows, key=sc)
        trb = run(fn, best["params"], tf=tf)
        trh = run(fn, best["params"], tf=tf, costs=HARSH)
        o = blk(trb, lo=ALT_END)
        oo = [x["altOOS"]["avg_R"] for x in rows if (x["altOOS"]["n"] or 0) >= 10]
        orig_sel = r["selected_params"]
        res[f"{var}_{tf}"] = {
            "group": "round1" if var in ROUND1 else ("posthoc" if var in POSTHOC else "control"),
            "n_configs": len(rows), "selected_altIS": best["params"], "same_as_original": best["params"] == orig_sel,
            "altIS": blk(trb, hi=ALT_END), "altOOS": o, "altOOS_harsh_avgR": blk(trh, lo=ALT_END).get("avg_R"),
            "share_cfg_altOOS_pos": round(float(np.mean([x > 0 for x in oo])), 3) if oo else None,
            "configs": rows}
        v = res[f"{var}_{tf}"]
        v["verdict"] = verdict(o, v["altOOS_harsh_avgR"], v["share_cfg_altOOS_pos"])
        print(var, tf, best["params"], "altIS", v["altIS"].get("n"), v["altIS"].get("avg_R"), v["altIS"].get("t_stat"),
              "| altOOS", o.get("n"), o.get("avg_R"), o.get("t_stat"), "harsh", v["altOOS_harsh_avgR"], v["verdict"], flush=True)
    r1 = {k: v for k, v in res.items() if v["group"] == "round1"}
    def _sc(k):
        v = r1[k]["altIS"]
        return v.get("t_stat") if v.get("n", 0) >= 30 and v.get("t_stat") is not None else -1e9
    fam = max(r1, key=_sc)
    json.dump(res, open("results/verify_funding_positioning_alt.json", "w"), indent=1, default=str)
    return {"variants": res, "family_pick_by_altIS_t_round1": fam,
            "family_pick_altOOS": res[fam]["altOOS"], "family_pick_verdict": res[fam]["verdict"]}


def verdict(o, harsh, share):
    if not o.get("n") or o.get("avg_R") is None or o["avg_R"] <= 0:
        return "NO_EDGE"
    ok = (o.get("t_stat") or 0) >= 2 and (harsh or -1) > 0 and o.get("sym_pos", 0) >= 6 and (share or 0) >= 0.5
    return "PROMISING" if ok else "WEAK"


# ---------------------------------------------------------------- (6) null tests
def outcomes(df, stop_atr=2.0, rr=2.0, hold=18, costs=BASE):
    """R of a market entry at open[t+1] for a signal at close[t], for every bar and both directions,
    replicating bt.engine.simulate exactly (stop from close[t], target = rr * |close - stop|)."""
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    A = atr(df).to_numpy(float)
    n = len(df)
    Rout = np.full((n, 2), np.nan)
    for j, d in enumerate((1, -1)):
        for t in range(n - 1):
            if not np.isfinite(A[t]) or A[t] <= 0:
                continue
            stop = c[t] - d * stop_atr * A[t]
            target = c[t] + d * rr * abs(c[t] - stop)
            k0 = t + 1
            entry = o[k0] * (1 + d * costs.slippage)
            if (d > 0 and entry <= stop) or (d < 0 and entry >= stop):
                continue
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
                    if (d > 0 and h[k] >= target) or (d < 0 and l[k] <= target):
                        ex, fee_out = target, costs.maker
                        break
                    if k >= n - 1:
                        ex = c[k]
                        break
                    if k - k0 + 1 >= hold:
                        ex = o[k + 1] * (1 - d * costs.slippage)
                        break
                    k += 1
            Rout[t, j] = (d * (ex - entry) - (entry * costs.taker + ex * fee_out)) / risk
    return Rout


def null_tests(n_perm=2000, seed=11):
    rng = np.random.default_rng(seed)
    p = {"src": "level", "pct": 0.9}
    recs, OUTC, VALID, MONTH, IDX = [], {}, {}, {}, {}
    for s in SYMS:
        df = load(s, "4h")
        sig = F.rcrowd_4h(df, **p)
        tr = simulate(df, sig, BASE, 18, None, s)
        Ro = outcomes(df)
        pos = df.index.get_indexer(tr["t_signal"])
        dj = np.where(tr["dir"].to_numpy() > 0, 0, 1)
        rep = Ro[pos, dj]
        assert np.allclose(rep, tr["R"].to_numpy(), atol=1e-9), f"replica mismatch {s}"
        pctl = F.roll_pct(F.logpos(df["ls_accounts"]), F.bars(df, 24 * 30)).to_numpy()
        valid = np.isfinite(pctl) & np.isfinite(Ro).all(axis=1)
        OUTC[s], VALID[s] = Ro, valid
        MONTH[s] = df.index.tz_convert(None).to_period("M").astype(str).to_numpy()
        for k, (ps, d) in enumerate(zip(pos, dj)):
            recs.append((s, int(ps), int(d), MONTH[s][ps], float(tr["R"].iloc[k]), tr["t_entry"].iloc[k] >= IS_END))
    T = pd.DataFrame(recs, columns=["sym", "pos", "dj", "month", "R", "oos"])
    real = {"all": T["R"].mean(), "IS": T.loc[~T.oos, "R"].mean(), "OOS": T.loc[T.oos, "R"].mean()}
    # month -> bar positions (per symbol) for circular shifts; index grid is identical across symbols
    idx0 = load(SYMS[0], "4h").index
    for s in SYMS:
        assert load(s, "4h").index.equals(idx0), f"index grid differs for {s}"
    months = pd.Series(np.arange(len(idx0)), index=idx0.tz_convert(None).to_period("M").astype(str))
    mstart = months.groupby(level=0).min().to_dict()
    mlen = months.groupby(level=0).size().to_dict()
    groups = {k: g for k, g in T.groupby(["sym", "month"])}
    validpos = {(s, m): np.flatnonzero(VALID[s] & (MONTH[s] == m)) for (s, m) in groups}
    oosmask = T["oos"].to_numpy()
    nullA = np.empty((n_perm, 3))
    nullB = np.empty((n_perm, 3))
    Tpos, Tdj, Tsym, Tmon = T["pos"].to_numpy(), T["dj"].to_numpy(), T["sym"].to_numpy(), T["month"].to_numpy()
    order = [(key, g.index.to_numpy()) for key, g in groups.items()]
    ulist = sorted(set(Tmon))
    for i in range(n_perm):
        # A: independent per symbol-month, random bars without replacement, same directions
        Rn = np.full(len(T), np.nan)
        for key, ix in order:
            vp = validpos[key]
            if len(vp) == 0:
                continue
            pick = rng.choice(vp, size=len(ix), replace=len(vp) < len(ix))
            Rn[ix] = OUTC[key[0]][pick, Tdj[ix]]
        nullA[i] = [np.nanmean(Rn), np.nanmean(Rn[~oosmask]), np.nanmean(Rn[oosmask])]
        # B: one circular shift per month common to ALL symbols (keeps cross-sectional clustering)
        sh = {m: rng.integers(0, mlen[m]) for m in ulist}
        Rb = np.full(len(T), np.nan)
        for k in range(len(T)):
            m = Tmon[k]
            q = mstart[m] + (Tpos[k] - mstart[m] + sh[m]) % mlen[m]
            if VALID[Tsym[k]][q]:
                Rb[k] = OUTC[Tsym[k]][q, Tdj[k]]
        nullB[i] = [np.nanmean(Rb), np.nanmean(Rb[~oosmask]), np.nanmean(Rb[oosmask])]
    out = {"n_perm": n_perm, "n_trades": {"all": int(len(T)), "IS": int((~oosmask).sum()), "OOS": int(oosmask.sum())},
           "real_avgR": {k: round(float(v), 4) for k, v in real.items()}}
    for name, arr in (("A_indep_symbol_month", nullA), ("B_common_monthly_shift", nullB)):
        d = {}
        for j, k in enumerate(("all", "IS", "OOS")):
            x = arr[:, j]
            d[k] = {"null_mean": round(float(x.mean()), 4), "null_sd": round(float(x.std(ddof=1)), 4),
                    "null_p95": round(float(np.quantile(x, 0.95)), 4),
                    "p_value": round(float((1 + (x >= real[k]).sum()) / (1 + len(x))), 4),
                    "excess": round(float(real[k] - x.mean()), 4)}
        out[name] = d
    return out


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    try:
        res = json.load(open(OUT))
    except Exception:
        res = {}
    t0 = time.time()
    if what in ("all", "rerun"):
        res["rerun_selected"], _ = rerun_selected()
        print(json.dumps(res["rerun_selected"]["base_OOS"]), flush=True)
    if what in ("all", "timing"):
        res["timing_stress"] = timing_stress()
        print(json.dumps(res["timing_stress"]), flush=True)
    if what in ("all", "neigh"):
        res["neighbours"] = neighbours()
        print(json.dumps(res["neighbours"]["pct_x_days_summary"]), json.dumps(res["neighbours"]["exits_summary"]), flush=True)
    if what in ("all", "alt"):
        res["alt_split"] = alt_split()
        print(res["alt_split"]["family_pick_by_altIS_t_round1"], json.dumps(res["alt_split"]["family_pick_altOOS"]), flush=True)
    if what in ("all", "null"):
        res["null_tests"] = null_tests()
        print(json.dumps(res["null_tests"]), flush=True)
    res["elapsed_s_last"] = round(time.time() - t0, 1)
    with open(OUT, "w") as f:
        json.dump(res, f, indent=1, default=str)


if __name__ == "__main__":
    main()
