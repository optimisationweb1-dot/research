"""Adversarial verification of family trend_momentum (step 2: analysis).

Needs $VTM_CACHE/trades_all.parquet from results/verify_trend_momentum_run.py.

    cd /home/user/research/trading && python3 -m results.verify_trend_momentum_analysis
Writes results/verify_trend_momentum.json
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import strategies.trend_momentum as TM  # noqa: E402
from bt.data import SYMBOLS, load  # noqa: E402
from bt.engine import check_lookahead, simulate, summarize  # noqa: E402
from bt.runner import COST_SCENARIOS  # noqa: E402

RES = os.path.dirname(os.path.abspath(__file__))
CACHE = os.environ.get("VTM_CACHE", "/tmp/claude-0/-home-user-research/ea6ba1ab-fe99-5191-91e4-bb9455e40592/scratchpad/vtm")
T0 = pd.Timestamp("2025-01-01", tz="UTC")
T1 = pd.Timestamp("2025-07-01", tz="UTC")
SEL = json.dumps({"K": 72, "z0": 0.5}, sort_keys=True)


def tstat(R):
    R = np.asarray(R, float)
    if len(R) < 2 or R.std(ddof=1) == 0:
        return None
    return float(R.mean() / R.std(ddof=1) * math.sqrt(len(R)))


def br(tr):
    if len(tr) == 0:
        return {"n": 0}
    s = summarize(tr, 0.5)
    return {k: s.get(k) for k in ("n", "win_pct", "avg_R", "t_stat", "t_stat_day_cluster", "ret_pct@0.5%",
                                  "max_dd_pct", "median_stop_pct")}


def verdict(base_oos, harsh_oos, nsym_pos, share_pos):
    a = base_oos.get("avg_R") or 0
    if a <= 0:
        return "NO_EDGE"
    ok = (base_oos.get("t_stat") or 0) >= 2 and (harsh_oos.get("avg_R") or 0) > 0 and nsym_pos >= 6 \
        and share_pos >= 0.5
    return "PROMISING" if ok else "WEAK"


def split_eval(T, is_end, oos_start, oos_end=None):
    """For every variant: select max IS t (n>=30) using entries < is_end; report OOS [oos_start, oos_end)."""
    out = {}
    base, harsh = T[T.costs == "base"], T[T.costs == "harsh"]
    for var, g in base.groupby("variant"):
        rows = []
        for p, gp in g.groupby("params"):
            IS = gp[gp.t_entry < is_end]
            O = gp[gp.t_entry >= oos_start]
            if oos_end is not None:
                O = O[O.t_entry < oos_end]
            t = tstat(IS.R) if len(IS) >= 30 else None
            rows.append({"params": p, "IS_n": len(IS), "IS_avg_R": round(float(IS.R.mean()), 3) if len(IS) else None,
                         "IS_t": round(t, 2) if t is not None else None,
                         "OOS_n": len(O), "OOS_avg_R": round(float(O.R.mean()), 3) if len(O) else None,
                         "OOS_t": round(tstat(O.R), 2) if len(O) > 1 else None})
        best = max(rows, key=lambda r: r["IS_t"] if r["IS_t"] is not None else -1e9)
        gb = g[g.params == best["params"]]
        gh = harsh[(harsh.variant == var) & (harsh.params == best["params"])]
        sel = lambda x: x[(x.t_entry >= oos_start) & ((x.t_entry < oos_end) if oos_end is not None else True)]
        ob, oh = sel(gb), sel(gh)
        per_sym = {s: round(float(x.R.mean()), 3) for s, x in ob.groupby("symbol")}
        npos = sum(v > 0 for v in per_sym.values())
        oos_list = [r["OOS_avg_R"] for r in rows if r["OOS_n"] >= 10]
        share = float(np.mean([x > 0 for x in oos_list])) if oos_list else 0.0
        bo, ho = br(ob), br(oh)
        out[var] = {"selected": best["params"], "IS": br(gb[gb.t_entry < is_end]), "OOS": bo, "OOS_harsh": ho,
                    "OOS_symbols_positive": npos, "OOS_per_symbol": per_sym, "share_configs_OOS_pos": share,
                    "verdict": verdict(bo, ho, npos, share), "grid": rows}
    return out


def lookahead_all():
    res = {}
    for sym in SYMBOLS:
        df = load(sym, "1d")
        for p in ({"K": 72, "z0": 0.5}, {"K": 24, "z0": 1.0}):
            try:
                check_lookahead(TM.tsmom, df, p, n_checks=40, min_bars=150, seed=11, window=400)
                res[f"{sym} {p}"] = "pass"
            except AssertionError as e:
                res[f"{sym} {p}"] = str(e)[:300]
    return res


def mirror_consistency():
    """Every emitted signal must become a trade (or a legit skip), and no exit_signal must hit while flat."""
    rep = {}
    for sym in SYMBOLS:
        df = load(sym, "1d")
        sig = TM.tsmom(df, K=72, z0=0.5)
        tr = simulate(df, sig, COST_SCENARIOS["base"], None, None, sym)
        ns = int((sig.signal != 0).sum())
        reasons = tr.reason.value_counts().to_dict()
        # direction of exit_signal trades must be consistent with z sign flip
        rep[sym] = {"signals": ns, "trades": len(tr), "reasons": reasons}
    return rep


# ---------------------------------------------------------------- null test

def _prep(sym, K=72, z0=0.5, ks=1.0, vol_days=30):
    df = load(sym, "1d")
    c = df["close"]
    lc = np.log(c)
    sg = lc.diff().rolling(vol_days, min_periods=vol_days // 2).std()
    z = ((lc - lc.shift(K)) / (sg * math.sqrt(K))).to_numpy()
    dist = (ks * sg * math.sqrt(min(K, 7))).to_numpy()
    return df, z, dist


def sim_one(o, h, l, c, z, dist, t, d, cost, max_bars=60, hold=None):
    """Engine-equivalent simulation of ONE trade whose signal is at the close of bar t.
    exit: stop (vol-scaled, set at t), exit_signal when z crosses against d (or after `hold` bars
    if hold is given), time exit after max_bars. Returns R or None (entry skipped / no data)."""
    n = len(o)
    if t >= n - 1 or not np.isfinite(dist[t]):
        return None
    stop = c[t] * (1 - d * dist[t])
    k0 = t + 1
    entry = o[k0] * (1 + d * cost.slippage)
    if (d > 0 and entry <= stop) or (d < 0 and entry >= stop):
        return None
    risk = abs(entry - stop)
    if (d > 0 and l[k0] <= stop) or (d < 0 and h[k0] >= stop):
        ex = stop * (1 - d * cost.slippage)
    else:
        k = k0
        while True:
            if k > k0 and ((d > 0 and l[k] <= stop) or (d < 0 and h[k] >= stop)):
                gap = (d > 0 and o[k] < stop) or (d < 0 and o[k] > stop)
                ex = (o[k] if gap else stop) * (1 - d * cost.slippage)
                break
            if k >= n - 1:
                ex = c[k]
                break
            if k - k0 + 1 >= max_bars:
                ex = o[k + 1] * (1 - d * cost.slippage)
                break
            flip = (k - k0 + 1 >= hold) if hold is not None else ((d > 0 and z[k] < 0) or (d < 0 and z[k] > 0))
            if flip:
                ex = o[k + 1] * (1 - d * cost.slippage)
                break
            k += 1
    fees = entry * cost.taker + ex * cost.taker
    return (d * (ex - entry) - fees) / risk


def null_test(T, n_perm=200, seed=1):
    cost = COST_SCENARIOS["base"]
    rng = np.random.default_rng(seed)
    real = T[(T.costs == "base") & (T.variant == "c_tsmom_1d") & (T.params == SEL)].copy()
    data = {s: _prep(s) for s in SYMBOLS}
    # validate the single-trade simulator against the engine on the real trades
    diffs = []
    for _, r in real.iterrows():
        df, z, dist = data[r.symbol]
        t = df.index.get_loc(r.t_signal)
        R = sim_one(df.open.to_numpy(), df.high.to_numpy(), df.low.to_numpy(), df.close.to_numpy(), z, dist, t,
                    int(r.dir), cost)
        diffs.append(abs(R - r.R) if R is not None else np.inf)
    diffs = np.array(diffs)
    out = {"sim_vs_engine_max_abs_diff_R": float(diffs.max()), "sim_vs_engine_n_mismatch_1e-9": int((diffs > 1e-9).sum())}
    real["bars_held"] = real["bars"]
    for label, lo, hi in (("OOS_2025_01", T0, None), ("IS_2023_24", None, T0), ("OOS_2025_07", T1, None)):
        rr = real
        if lo is not None:
            rr = rr[rr.t_entry >= lo]
        if hi is not None:
            rr = rr[rr.t_entry < hi]
        real_avg = float(rr.R.mean())
        res = {}
        for mode in ("same_exit_logic", "same_holding_time", "same_exit_logic_dir_shuffled"):
            means = []
            for _ in range(n_perm):
                Rs = []
                for sym, g in rr.groupby("symbol"):
                    df, z, dist = data[sym]
                    o, h, l, c = (df[x].to_numpy() for x in ("open", "high", "low", "close"))
                    idx = df.index
                    mon = idx.to_period("M")
                    dirs_all = g.dir.to_numpy().copy()
                    if mode == "same_exit_logic_dir_shuffled":
                        dirs_all = rng.permutation(dirs_all)
                    for m, gm in g.groupby(g.t_signal.dt.to_period("M")):
                        pos = np.flatnonzero((mon == m) & np.isfinite(dist) & (np.arange(len(idx)) < len(idx) - 1))
                        if len(pos) == 0:
                            continue
                        ts = rng.choice(pos, size=len(gm), replace=True)
                        dsel = dirs_all[[g.index.get_loc(i) for i in gm.index]]
                        for t, d, hb in zip(ts, dsel, gm.bars.to_numpy()):
                            R = sim_one(o, h, l, c, z, dist, int(t), int(d), cost,
                                        hold=int(hb) if mode == "same_holding_time" else None)
                            if R is not None:
                                Rs.append(R)
                means.append(float(np.mean(Rs)))
            means = np.array(means)
            res[mode] = {"null_mean": round(float(means.mean()), 3), "null_sd": round(float(means.std()), 3),
                         "null_p95": round(float(np.percentile(means, 95)), 3),
                         "p_value": round(float((1 + (means >= real_avg).sum()) / (1 + len(means))), 4)}
        out[label] = {"real_n": len(rr), "real_avg_R": round(real_avg, 3), **res}
        print(label, json.dumps(out[label]), flush=True)
    return out


# ---------------------------------------------------------------- neighbours / funding / stability

def neighbours():
    cost_b, cost_h = COST_SCENARIOS["base"], COST_SCENARIOS["harsh"]
    dfs = {s: load(s, "1d") for s in SYMBOLS}
    base = dict(K=72, z0=0.5, ks=1.0, vol_days=30, max_days=60)
    grid = [dict(base, K=k) for k in (36, 48, 60, 84, 96, 120)] + \
           [dict(base, z0=z) for z in (0.0, 0.25, 0.75, 1.0)] + \
           [dict(base, ks=x) for x in (0.75, 1.5, 2.0)] + \
           [dict(base, vol_days=x) for x in (20, 60)] + \
           [dict(base, max_days=x) for x in (30, 120)] + [base]
    rows = []
    for p in grid:
        parts = [simulate(dfs[s], TM.tsmom(dfs[s], **p), cost_b, None, None, s) for s in SYMBOLS]
        tr = pd.concat(parts, ignore_index=True)
        IS, O = tr[tr.t_entry < T0], tr[tr.t_entry >= T0]
        npos = int((O.groupby("symbol").R.mean() > 0).sum())
        rows.append({"params": p, "IS_n": len(IS), "IS_avg_R": round(float(IS.R.mean()), 3),
                     "IS_t": round(tstat(IS.R), 2), "OOS_n": len(O), "OOS_avg_R": round(float(O.R.mean()), 3),
                     "OOS_t": round(tstat(O.R), 2), "OOS_sym_pos": npos,
                     "OOS_2025": round(float(O[O.t_entry.dt.year == 2025].R.mean()), 3),
                     "OOS_2026": round(float(O[O.t_entry.dt.year == 2026].R.mean()), 3)})
        print(rows[-1], flush=True)
    return rows


def funding_adj(T):
    real = T[(T.costs == "base") & (T.variant == "c_tsmom_1d") & (T.params == SEL)].copy()
    fr = {}
    for s in SYMBOLS:
        f = pd.read_parquet(os.path.join(os.path.dirname(RES), "data", "funding", f"{s}.parquet"))
        fr[s] = f.set_index(pd.to_datetime(f.ts, utc=True))["funding"].sort_index()
    fR = []
    for _, r in real.iterrows():
        f = fr[r.symbol]
        # position held from open of t_entry bar until open of exit bar (exit at open) or intrabar stop
        seg = f[(f.index > r.t_entry) & (f.index <= r.t_exit)]
        paid = r.dir * seg.sum()                         # long pays positive funding
        fR.append(-paid * r.entry / abs(r.entry - r.stop))
    real["fund_R"] = fR
    real["R_net_fund"] = real.R + real.fund_R
    out = {}
    for lab, x in (("IS", real[real.t_entry < T0]), ("OOS", real[real.t_entry >= T0])):
        out[lab] = {"n": len(x), "avg_R": round(float(x.R.mean()), 3), "avg_funding_R": round(float(x.fund_R.mean()), 3),
                    "avg_R_after_funding": round(float(x.R_net_fund.mean()), 3),
                    "t_after_funding": round(tstat(x.R_net_fund), 2),
                    "long_funding_R": round(float(x[x.dir > 0].fund_R.mean()), 3) if (x.dir > 0).any() else None,
                    "short_funding_R": round(float(x[x.dir < 0].fund_R.mean()), 3) if (x.dir < 0).any() else None}
    return out


def stability(T):
    real = T[(T.costs == "base") & (T.variant == "c_tsmom_1d") & (T.params == SEL)].copy()
    y = {str(k): br(g) for k, g in real.groupby(real.t_entry.dt.year)}
    hy = {f"{k.year}H{1 if k.month <= 6 else 2}": None for k in real.t_entry}
    half = {}
    for k, g in real.groupby(real.t_entry.dt.year.astype(str) + "H" + np.where(real.t_entry.dt.month <= 6, "1", "2")):
        half[k] = {"n": len(g), "avg_R": round(float(g.R.mean()), 3), "t": round(tstat(g.R), 2) if len(g) > 2 else None}
    O = real[real.t_entry >= T0]
    sym = {s: {"n": len(g), "avg_R": round(float(g.R.mean()), 3), "IS_avg_R": round(float(real[(real.symbol == s) & (real.t_entry < T0)].R.mean()), 3)}
           for s, g in O.groupby("symbol")}
    ls = {}
    for lab, x in (("IS", real[real.t_entry < T0]), ("OOS", O)):
        for d, g in x.groupby("dir"):
            ls[f"{lab}_{'long' if d > 0 else 'short'}"] = br(g)
    Rs = np.sort(O.R.to_numpy())[::-1]
    tail = {f"OOS_ex_top{k}": {"avg_R": round(float(Rs[k:].mean()), 3), "t": round(tstat(Rs[k:]), 2)} for k in (1, 2, 3, 5, 10)}
    month = O.groupby(O.t_exit.dt.to_period("M")).R.sum()
    return {"per_year": y, "per_half": half, "per_symbol_OOS": sym, "long_short": ls, "tail": tail,
            "OOS_months_positive_share": round(float((month > 0).mean()), 2), "OOS_months": len(month),
            "OOS_top5_R": [round(float(x), 2) for x in Rs[:5]]}


def main():
    T = pd.read_parquet(os.path.join(CACHE, "trades_all.parquet"))
    for c in ("t_entry", "t_exit", "t_signal"):
        T[c] = pd.to_datetime(T[c], utc=True)
    out = {}
    out["orig_split"] = split_eval(T, T0, T0)
    out["alt_split"] = split_eval(T, T1, T1)
    for k in ("orig_split", "alt_split"):
        print("\n==", k)
        for v, r in out[k].items():
            print(f"{v:14s} sel={r['selected']:32s} IS n={r['IS']['n']} R={r['IS'].get('avg_R')} t={r['IS'].get('t_stat')} | "
                  f"OOS n={r['OOS']['n']} R={r['OOS'].get('avg_R')} t={r['OOS'].get('t_stat')} harsh={r['OOS_harsh'].get('avg_R')} "
                  f"sym+={r['OOS_symbols_positive']} share={r['share_configs_OOS_pos']:.2f} {r['verdict']}")
    out["stability"] = stability(T)
    print(json.dumps(out["stability"], indent=0, default=str)[:4000])
    out["funding"] = funding_adj(T)
    print("funding", out["funding"])
    out["lookahead"] = lookahead_all()
    print("lookahead", set(out["lookahead"].values()))
    out["mirror"] = mirror_consistency()
    print("mirror", out["mirror"])
    out["neighbours"] = neighbours()
    out["null"] = null_test(T)
    json.dump(out, open(os.path.join(RES, "verify_trend_momentum.json"), "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
