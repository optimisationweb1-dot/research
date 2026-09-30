"""Backtests of the Coinbase-premium strategies through bt.engine (costs base/harsh, IS/OOS, placebo).

    OMP_NUM_THREADS=2 python3 -m strategies.coinbase_premium_backtest

Selection rule (as bt.runner): max IS t-stat with IS n >= 30, per family and asset. Everything is written to
results/coinbase_premium_backtest.json (+ a flat CSV of every config).
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd

from bt.data import load
from bt.engine import IS_END, Costs, check_lookahead, simulate, split_summary, summarize
from strategies import coinbase_premium as S
from strategies.coinbase_premium_feat import HERE, features, load_table, merge_etf, merge_into

RES = os.path.join(HERE, "results")
COSTS = {"base": Costs(), "harsh": Costs(taker=0.0006, maker=0.0004, slippage=0.0005)}
SYM = {"btc": "BTCUSDT", "eth": "ETHUSDT"}
RNG = np.random.default_rng(7)
CBP = ["cbp_P24", "cbp_P24raw", "cbp_L", "cbp_R", "cbp_D", "cbp_P", "cbp_U"]


def feature_causality_check(n=15):
    """features() at time t must not change when later premium rows are removed."""
    p = load_table()
    full = features(p, "btc")
    ks = RNG.choice(np.arange(3000, len(p) - 10), n, replace=False)
    for k in ks:
        cut = features(p.iloc[:k + 1], "btc").iloc[-1]
        a = full.iloc[k]
        for c in full.columns:
            if not ((pd.isna(a[c]) and pd.isna(cut[c])) or math.isclose(a[c], cut[c], rel_tol=1e-9, abs_tol=1e-12)):
                raise AssertionError(f"feature lookahead {c} at {p.index[k]}: {a[c]} vs {cut[c]}")
    return True


def frames():
    out = {}
    for a, sym in SYM.items():
        d1 = merge_etf(merge_into(load(sym, "1h"), a), a)
        d4 = merge_into(load(sym, "4h"), a)
        out[a] = {"1h": d1, "4h": d4}
    return out


def run_one(fn, df, params, max_hold, cost="base", sym=""):
    sig = fn(df, **params)
    return simulate(df, sig, COSTS[cost], max_hold, None, sym)


def ss(tr):
    return split_summary(tr, 0.5)


def family(name, fn, grid, fr, tf, hold_key="hold", note=""):
    res = {"family": name, "note": note, "assets": {}}
    for a in SYM:
        df = fr[a][tf]
        first = grid[0]
        check_lookahead(fn, df, {"asset": a, **first}, n_checks=8)
        rows = []
        for params in grid:
            mh = params.get(hold_key) if hold_key else None
            tr = run_one(fn, df, {"asset": a, **params}, mh, "base", SYM[a])
            s = ss(tr)
            rows.append({"params": params, "IS": s["IS"], "OOS": s["OOS"]})
            print(name, a, params, "IS", s["IS"].get("n"), s["IS"].get("avg_R"), s["IS"].get("t_stat"),
                  "| OOS", s["OOS"].get("n"), s["OOS"].get("avg_R"), s["OOS"].get("t_stat"), flush=True)
        ok = [r for r in rows if r["IS"].get("n", 0) >= 30 and r["IS"].get("t_stat") is not None]
        best = max(ok, key=lambda r: r["IS"]["t_stat"]) if ok else None
        entry = {"configs": rows, "n_configs": len(rows)}
        if best:
            mh = best["params"].get(hold_key) if hold_key else None
            trh = run_one(fn, df, {"asset": a, **best["params"]}, mh, "harsh", SYM[a])
            trb = run_one(fn, df, {"asset": a, **best["params"]}, mh, "base", SYM[a])
            entry.update({"selected": best["params"], "sel_IS": best["IS"], "sel_OOS": best["OOS"],
                          "sel_OOS_harsh": ss(trh)["OOS"], "sel_IS_harsh": ss(trh)["IS"],
                          "per_year": {str(y): summarize(g, 0.5, str(y)) for y, g in
                                       trb.groupby(trb["t_entry"].dt.year)}})
            oos_all = [r["OOS"].get("avg_R") for r in rows if r["OOS"].get("n", 0) >= 10]
            entry["all_OOS_avgR"] = {"median": float(np.median(oos_all)) if oos_all else None,
                                     "share_pos": float(np.mean([x > 0 for x in oos_all])) if oos_all else None}
        res["assets"][a] = entry
    return res


def shifted(df, k):
    d = df.copy()
    for c in CBP:
        if c in d:
            d[c] = np.roll(d[c].to_numpy(), k)
    return d


def placebo(fn, fr, tf, params_by_asset, hold_key="hold", n=200, cost="base"):
    """Circularly shift all premium columns (>= 30 days), re-run the selected config; compare avg R."""
    out = {}
    for a, params in params_by_asset.items():
        if params is None:
            continue
        df = fr[a][tf]
        mh = params.get(hold_key) if hold_key else None
        act = ss(run_one(fn, df, {"asset": a, **params}, mh, cost, SYM[a]))
        bars_30d = 720 if tf == "1h" else 180
        dist = {"IS": [], "OOS": []}
        for _ in range(n):
            k = int(RNG.integers(bars_30d, len(df) - bars_30d))
            s = ss(run_one(fn, shifted(df, k), {"asset": a, **params}, mh, cost, SYM[a]))
            for per in dist:
                dist[per].append(s[per].get("avg_R", np.nan) if s[per].get("n", 0) else np.nan)
        o = {}
        for per in dist:
            x = np.array(dist[per], float)
            x = x[~np.isnan(x)]
            av = act[per].get("avg_R")
            o[per] = {"actual_avg_R": av, "placebo_mean": round(float(x.mean()), 4), "placebo_sd": round(float(x.std()), 4),
                      "p_one_sided": float(np.mean(x >= av)) if av is not None else None, "n_placebo": len(x)}
        out[a] = {"params": params, **o}
        print("placebo", fn.__name__, a, params, o, flush=True)
    return out


def split_by_premium(fr, n_shift=1000):
    """C: base Donchian trades, split by the premium sign known at the signal bar."""
    out = {}
    for a in SYM:
        df = fr[a]["4h"]
        tr = run_one(S.donchian_filter, df, {"asset": a, "filt": "none"}, None, "base", SYM[a])
        res = {}
        for col in ["cbp_P24", "cbp_P24raw"]:
            prem = df[col]
            tr["pos"] = prem.reindex(tr["t_signal"]).to_numpy() > 0
            for per, m in [("IS", tr.t_entry < IS_END), ("OOS", tr.t_entry >= IS_END)]:
                t = tr[m]
                g1, g0 = t[t.pos].R, t[~t.pos].R
                diff = g1.mean() - g0.mean()
                se = math.sqrt(g1.var(ddof=1) / len(g1) + g0.var(ddof=1) / len(g0)) if len(g1) > 1 and len(g0) > 1 else np.nan
                pl = []
                arr = prem.to_numpy()
                idx = df.index.get_indexer(t["t_signal"])
                for _ in range(n_shift):
                    k = int(RNG.integers(180, len(df) - 180))
                    pos = np.roll(arr, k)[idx] > 0
                    if pos.sum() > 1 and (~pos).sum() > 1:
                        pl.append(t.R.to_numpy()[pos].mean() - t.R.to_numpy()[~pos].mean())
                pl = np.array(pl)
                res[f"{col}_{per}"] = {"n_pos": int(len(g1)), "n_neg": int(len(g0)),
                                       "avgR_pos": round(g1.mean(), 3), "avgR_neg": round(g0.mean(), 3),
                                       "diff": round(diff, 3), "t_welch": round(diff / se, 2) if se else None,
                                       "placebo_p_one_sided": float(np.mean(pl >= diff))}
        out[a] = res
        print("split", a, res, flush=True)
    return out


def main():
    feature_causality_check()
    print("feature causality check passed", flush=True)
    fr = frames()
    zgrid = [{"z_in": z, "hold": h} for z in (0.5, 1.0, 1.5) for h in (24, 72, 168)]
    out = {"costs": {k: vars(v) for k, v in COSTS.items()}, "families": {}}
    out["families"]["A_long_L"] = family("A_long_L", S.premium_long, [{"sig": "L", **g} for g in zgrid], fr, "1h",
                                         note="pre-registered")
    out["families"]["B_short_L"] = family("B_short_L", S.premium_short, [{"sig": "L", **g} for g in zgrid], fr, "1h",
                                          note="pre-registered")
    # post-hoc: other signals with the same grid (P uses share thresholds)
    ph = [{"sig": s, **g} for s in ("R", "U") for g in zgrid] + \
         [{"sig": "P", "z_in": z, "hold": h} for z in (0.1, 0.2, 0.3) for h in (24, 72, 168)]
    out["families"]["Astar_long_RUP"] = family("Astar_long_RUP", S.premium_long, ph, fr, "1h",
                                               note="POST-HOC: signals chosen after seeing IS (and OOS) regressions")
    out["families"]["C_donchian"] = family("C_donchian", S.donchian_filter,
                                           [{"filt": f} for f in ("none", "adj", "raw", "adj_neg")], fr, "4h",
                                           hold_key=None, note="pre-registered; 'none' is the baseline")
    out["families"]["D_daily_etf"] = family("D_daily_etf", S.daily_etf,
                                            [{"mode": m, "hold": h} for m in ("both", "prem", "flow", "all")
                                             for h in (24, 72)], fr, "1h", note="pre-registered; 'all' = drift baseline")
    out["C_split_by_premium"] = split_by_premium(fr)
    sel = lambda fam: {a: out["families"][fam]["assets"][a].get("selected") for a in SYM}
    out["placebo"] = {
        "A_long_L": placebo(S.premium_long, fr, "1h", sel("A_long_L")),
        "B_short_L": placebo(S.premium_short, fr, "1h", sel("B_short_L")),
        "Astar_long_RUP": placebo(S.premium_long, fr, "1h", sel("Astar_long_RUP")),
    }
    # timing robustness for the selected A configs: +1h extra lag of the premium
    rob = {}
    for a in SYM:
        p = sel("A_long_L")[a]
        if p:
            d = merge_etf(merge_into(load(SYM[a], "1h"), a, lag_hours=1), a)
            rob[a] = {"params": p, "lag1h": ss(run_one(S.premium_long, d, {"asset": a, **p}, p["hold"], "base", SYM[a]))}
    out["A_lag1h"] = rob
    with open(os.path.join(RES, "coinbase_premium_backtest.json"), "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    flat = []
    for fam, v in out["families"].items():
        for a, e in v["assets"].items():
            for r in e["configs"]:
                flat.append({"family": fam, "asset": a, "params": json.dumps(r["params"]),
                             **{f"IS_{k}": r["IS"].get(k) for k in ("n", "avg_R", "t_stat", "win_pct", "pf")},
                             **{f"OOS_{k}": r["OOS"].get(k) for k in ("n", "avg_R", "t_stat", "win_pct", "pf")}})
    pd.DataFrame(flat).to_csv(os.path.join(RES, "coinbase_premium_backtest_configs.csv"), index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
