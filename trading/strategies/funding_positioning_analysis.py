"""Summary + diagnostics for the funding_positioning family.

    cd trading && python3 -m strategies.funding_positioning_analysis summary
    cd trading && python3 -m strategies.funding_positioning_analysis diag

summary: one row per variant/tf from results/funding_positioning_<variant>_<tf>.json with the verdict.
diag   : re-runs the IS-selected config of every variant (base costs) and reports, without any
         re-selection: long vs short, funding-adjusted R (the engine ignores funding payments),
         exit reasons, IS/OOS by half-year. Written to results/funding_positioning_diagnostics.json.
"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

import strategies.funding_positioning as F  # noqa: F401  (patches the loader)
from bt.data import SYMBOLS
from bt.engine import IS_END, summarize
from bt.runner import run_config

RES = "results"
SKIP = ("is_explore", "diagnostics", "summary", "holdout", "robust", "attribution", "baseline", "holdout2")


def files():
    out = []
    for p in sorted(glob.glob(f"{RES}/funding_positioning_*_*.json")):
        b = os.path.basename(p)[len("funding_positioning_"):-5]
        if any(k in b for k in SKIP):
            continue
        variant, tf = b.rsplit("_", 1)
        out.append((variant, tf, p))
    return out


def verdict(r):
    o, h = r["selected_OOS"], r["selected_OOS_harsh_costs"]
    if not o.get("n") or o.get("avg_R") is None or o["avg_R"] <= 0:
        return "NO_EDGE"
    sym = sum(1 for s in r["selected_OOS_per_symbol"].values() if s.get("avg_R", -1) > 0)
    share = r["all_configs_OOS_avgR"]["share_positive"] or 0
    ok = (o.get("t_stat") or 0) >= 2 and (h.get("avg_R") or -1) > 0 and sym >= 6 and share >= 0.5
    return "PROMISING" if ok else "WEAK"


def row(variant, tf, r):
    i, o, h = r["selected_IS"], r["selected_OOS"], r["selected_OOS_harsh_costs"]
    sym = sum(1 for s in r["selected_OOS_per_symbol"].values() if s.get("avg_R", -1) > 0)
    fixed = {k: v for k, v in r["selected_params"].items()}
    return {"variant": variant, "tf": tf, "fn": r["fn"], "params": fixed, "n_configs": r["n_configs"],
            "IS_n": i.get("n"), "IS_win": i.get("win_pct"), "IS_avgR": i.get("avg_R"), "IS_t": i.get("t_stat"),
            "IS_ret": i.get("ret_pct@0.5%"), "IS_dd": i.get("max_dd_pct"),
            "OOS_n": o.get("n"), "OOS_win": o.get("win_pct"), "OOS_avgR": o.get("avg_R"), "OOS_t": o.get("t_stat"),
            "OOS_ret": o.get("ret_pct@0.5%"), "OOS_dd": o.get("max_dd_pct"), "OOS_harsh_avgR": h.get("avg_R"),
            "OOS_sym_pos": sym, "share_cfg_pos": r["all_configs_OOS_avgR"]["share_positive"],
            "median_cfg_OOS_avgR": r["all_configs_OOS_avgR"]["median"],
            "configs_OOS": [(c["params"], c["IS"].get("avg_R"), c["IS"].get("t_stat"), c["OOS"].get("n"),
                             c["OOS"].get("avg_R"), c["OOS"].get("t_stat")) for c in r["configs"]],
            "verdict": verdict(r)}


def summary():
    rows = [row(v, tf, json.load(open(p))) for v, tf, p in files()]
    n_total = sum(r["n_configs"] for r in rows)
    print(f"{'variant':12s} {'tf':3s} {'IS n':>5s} {'IS R':>7s} {'IS t':>6s} | {'OOS n':>5s} {'win':>5s} "
          f"{'avgR':>7s} {'t':>6s} {'ret':>7s} {'dd':>6s} {'harsh':>7s} sym share verdict  params")
    for r in rows:
        print(f"{r['variant']:12s} {r['tf']:3s} {r['IS_n'] or 0:5d} {r['IS_avgR'] or 0:7.3f} {r['IS_t'] or 0:6.2f} | "
              f"{r['OOS_n'] or 0:5d} {r['OOS_win'] or 0:5.1f} {r['OOS_avgR'] or 0:7.3f} {r['OOS_t'] or 0:6.2f} "
              f"{r['OOS_ret'] or 0:7.1f} {r['OOS_dd'] or 0:6.1f} {r['OOS_harsh_avgR'] or 0:7.3f} {r['OOS_sym_pos']:3d} "
              f"{r['share_cfg_pos'] if r['share_cfg_pos'] is not None else float('nan'):5.2f} {r['verdict']:9s} {r['params']}")
    print("total configs:", n_total)
    with open(f"{RES}/funding_positioning_summary.json", "w") as f:
        json.dump({"n_configs_total": n_total, "rows": rows}, f, indent=1, default=str)
    return rows


def half(ts):
    return f"{ts.year}H{1 if ts.month <= 6 else 2}"


def diag(only=None):
    out = {}
    for v, tf, p in files():
        if only and v not in only:
            continue
        r = json.load(open(p))
        tr = run_config("strategies.funding_positioning", r["fn"], SYMBOLS, tf, r["selected_params"],
                        r["load"], "base", 2)
        if not len(tr):
            continue
        tr["fundR"] = F.funding_pnl(tr).to_numpy()
        tr["R_f"] = tr["R"] + tr["fundR"]
        oos = tr[tr["t_entry"] >= IS_END]
        iss = tr[tr["t_entry"] < IS_END]
        d = {"params": r["selected_params"]}
        for name, part in (("IS", iss), ("OOS", oos)):
            if not len(part):
                continue
            d[name] = {
                "long": summarize(part[part["dir"] > 0], 0.5, "long"),
                "short": summarize(part[part["dir"] < 0], 0.5, "short"),
                "avgR_with_funding": round(float(part["R_f"].mean()), 3),
                "t_with_funding": round(float(part["R_f"].mean() / part["R_f"].std(ddof=1) * np.sqrt(len(part))), 2)
                if len(part) > 1 else None,
                "mean_fundR": round(float(part["fundR"].mean()), 4),
                "exit_reasons": part["reason"].value_counts().to_dict(),
                "median_bars": float(part["bars"].median()),
                "by_half": {h: {"n": int(len(g)), "avg_R": round(float(g["R"].mean()), 3)}
                            for h, g in part.groupby(part["t_entry"].map(half))},
            }
        out[f"{v}_{tf}"] = d
        print(v, tf, json.dumps({k: (d[k]["long"].get("avg_R"), d[k]["long"].get("n"), d[k]["short"].get("avg_R"),
                                     d[k]["short"].get("n"), d[k]["avgR_with_funding"]) for k in ("IS", "OOS") if k in d}),
              flush=True)
    path = f"{RES}/funding_positioning_diagnostics.json"
    old = json.load(open(path)) if os.path.exists(path) else {}
    old.update(out)
    with open(path, "w") as f:
        json.dump(old, f, indent=1, default=str)


def _main_basic():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"
    if cmd == "summary":
        summary()
    elif cmd == "diag":
        diag(sys.argv[2:] or None)


# ================================================================ round-2 validation
# PRE-REGISTERED before any holdout data was loaded (27.09.2026): exact configs, no re-selection.
HOLD = "DOTUSDT NEARUSDT ATOMUSDT FILUSDT BCHUSDT ETCUSDT UNIUSDT APTUSDT ARBUSDT OPUSDT".split()
HROOT = os.environ.get("FP_HOLDOUT_ROOT", "")
PREREG = [
    ("C_level_4h", "rcrowd", "4h", {"src": "level", "pct": 0.9}),
    ("C_level_1h", "rcrowd", "1h", {"src": "level", "pct": 0.9}),
    ("ctlPrice_4h", "rcrowd", "4h", {"src": "price", "pct": 0.9}),
    ("smartcrowd_4h", "smartcrowd", "4h", {"pct": 0.9, "top_max": 0.5}),
    ("Ffollow_1h", "fcrowd", "1h", {"norm": "z", "trend": "ema", "mode": "follow", "z": 2.0}),
    ("Ffollow_4h", "fcrowd", "4h", {"norm": "z", "trend": "ema", "mode": "follow", "z": 2.0}),
]


def _trades(fn, tf, params, symbols, root=None, costs="base", delay=0):
    import bt.data as D
    from bt.engine import simulate
    from bt.runner import COST_SCENARIOS
    orig = D.ROOT
    if root:
        D.ROOT = root
    try:
        f = getattr(F, f"{fn}_{tf}")
        out = []
        for s in symbols:
            df = D.load(s, tf, metrics=True, funding=True)
            sig = f(df, **params)
            if delay:
                sig = sig.shift(delay)
                sig["signal"] = sig["signal"].fillna(0.0)
                sig["exit_signal"] = sig["exit_signal"].fillna(0.0)
            out.append(simulate(df, sig, COST_SCENARIOS[costs], f.MAX_HOLD, None, s))
        tr = pd.concat([o for o in out if len(o)], ignore_index=True)
        tr["fundR"] = F.funding_pnl(tr).to_numpy() if not root else _fund_holdout(tr, root)
        return tr
    finally:
        D.ROOT = orig


def _fund_holdout(tr, root):
    import bt.data as D
    orig = D.ROOT
    D.ROOT = root
    try:
        return F.funding_pnl(tr).to_numpy()
    finally:
        D.ROOT = orig


def clustered_t(tr, freq="W"):
    """t-stat of the mean R with trades clustered by entry week (trades across symbols are correlated)."""
    if len(tr) < 3:
        return None
    g = tr.groupby(tr["t_entry"].dt.to_period(freq))["R"]
    s, n = g.sum(), g.count()
    mu = tr["R"].mean()
    # cluster-robust variance of the mean: sum_c (sum_i (R_i - mu))^2 / N^2
    dev = g.apply(lambda x: (x - mu).sum())
    var = (dev ** 2).sum() / len(tr) ** 2 * len(s) / max(len(s) - 1, 1)
    return round(float(mu / np.sqrt(var)), 2) if var > 0 else None


def _block(tr, label):
    if not len(tr):
        return {"n": 0}
    s = summarize(tr, 0.5, label)
    s["t_clustered_week"] = clustered_t(tr)
    s["avgR_with_funding"] = round(float((tr["R"] + tr["fundR"]).mean()), 3)
    s["long"] = {k: summarize(tr[tr["dir"] > 0], 0.5).get(k) for k in ("n", "avg_R", "t_stat")}
    s["short"] = {k: summarize(tr[tr["dir"] < 0], 0.5).get(k) for k in ("n", "avg_R", "t_stat")}
    s["sym_pos"] = int(sum(g["R"].mean() > 0 for _, g in tr.groupby("symbol")))
    s["n_sym"] = int(tr["symbol"].nunique())
    return s


def validate():
    """Main-universe robustness (entry delay, harsh costs, clustering, halves) + pre-registered holdout."""
    T24 = pd.Timestamp("2024-01-01", tz="UTC")
    out = {"prereg": [(a, b, c, d) for a, b, c, d in PREREG]}
    for name, fn, tf, p in PREREG:
        r = {}
        tr = _trades(fn, tf, p, SYMBOLS)
        r["main_IS"] = _block(tr[tr["t_entry"] < IS_END], "IS")
        r["main_IS_2024"] = _block(tr[(tr["t_entry"] >= T24) & (tr["t_entry"] < IS_END)], "IS2024")
        r["main_OOS"] = _block(tr[tr["t_entry"] >= IS_END], "OOS")
        r["main_OOS_by_half"] = {h: {"n": int(len(g)), "avg_R": round(float(g["R"].mean()), 3)}
                                 for h, g in tr[tr["t_entry"] >= IS_END].groupby(tr["t_entry"].map(half))}
        r["main_OOS_per_symbol"] = {s: round(float(g["R"].mean()), 3)
                                    for s, g in tr[tr["t_entry"] >= IS_END].groupby("symbol")}
        trd = _trades(fn, tf, p, SYMBOLS, delay=1)
        r["main_OOS_delay1bar"] = _block(trd[trd["t_entry"] >= IS_END], "OOS delay")
        if HROOT:
            th = _trades(fn, tf, p, HOLD, root=HROOT)
            thh = _trades(fn, tf, p, HOLD, root=HROOT, costs="harsh")
            th = th[th["t_entry"] >= T24]
            thh = thh[thh["t_entry"] >= T24]
            r["holdout_2024"] = _block(th[th["t_entry"] < IS_END], "H2024")
            r["holdout_2025_26"] = _block(th[th["t_entry"] >= IS_END], "H2025")
            r["holdout_all"] = _block(th, "Hall")
            r["holdout_2025_26_harsh_avgR"] = round(float(thh[thh["t_entry"] >= IS_END]["R"].mean()), 3)
            r["holdout_per_symbol_2025_26"] = {s: round(float(g["R"].mean()), 3)
                                               for s, g in th[th["t_entry"] >= IS_END].groupby("symbol")}
        out[name] = r
        brief = {k: (v.get("n"), v.get("avg_R"), v.get("t_stat"), v.get("t_clustered_week"))
                 for k, v in r.items() if isinstance(v, dict) and "n" in v}
        print(name, json.dumps(brief), flush=True)
    with open(f"{RES}/funding_positioning_holdout.json", "w") as f:
        json.dump(out, f, indent=1, default=str)


def attribution():
    """C_level 4h: is the crowd signal just price? Bucket trades by the 30d price percentile at the
    signal bar (aligned = price already at the 30d extreme in the trade direction)."""
    import bt.data as D
    res = {}
    for tf in ("4h", "1h"):
        rows = []
        for s in SYMBOLS:
            df = D.load(s, tf, metrics=True, funding=True)
            n = F.bars(df, 24 * 30)
            pc = F.roll_pct(F.logpos(df["ls_accounts"]), n)
            pp = F.roll_pct(np.log(df["close"]), n)
            ok = pc.notna() & pp.notna()
            rows.append(pd.DataFrame({"pc": pc[ok], "pp": pp[ok], "sym": s}))
        P = pd.concat(rows)
        res[f"corr_crowdpct_pricepct_{tf}"] = round(float(P["pc"].corr(P["pp"], method="spearman")), 3)
        tr = _trades("rcrowd", tf, {"src": "level", "pct": 0.9}, SYMBOLS)
        pps = []
        for s, g in tr.groupby("symbol"):
            df = D.load(s, tf, metrics=True, funding=True)
            pp = F.roll_pct(np.log(df["close"]), F.bars(df, 24 * 30))
            pps.append(pp.reindex(g["t_signal"]).to_numpy())
        tr = tr.sort_values(["symbol"]).reset_index(drop=True)
        tr["pp"] = np.concatenate([pps[i] for i in range(len(pps))])
        # momentum-aligned: short with price in bottom third / long with price in top third
        tr["bucket"] = np.where(((tr["dir"] < 0) & (tr["pp"] <= 1 / 3)) | ((tr["dir"] > 0) & (tr["pp"] >= 2 / 3)),
                                "momentum_aligned", np.where(((tr["dir"] < 0) & (tr["pp"] >= 2 / 3)) |
                                                             ((tr["dir"] > 0) & (tr["pp"] <= 1 / 3)),
                                                             "counter_trend", "middle"))
        b = {}
        for per, part in (("IS", tr[tr["t_entry"] < IS_END]), ("OOS", tr[tr["t_entry"] >= IS_END])):
            b[per] = {k: {"n": int(len(g)), "avg_R": round(float(g["R"].mean()), 3),
                          "t": round(float(g["R"].mean() / g["R"].std(ddof=1) * np.sqrt(len(g))), 2) if len(g) > 2 else None}
                      for k, g in part.groupby("bucket")}
        res[f"C_level_{tf}_by_price_state"] = b
        print(tf, res[f"corr_crowdpct_pricepct_{tf}"], json.dumps(b), flush=True)
    with open(f"{RES}/funding_positioning_attribution.json", "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] in ("validate", "attribution"):
    {"validate": validate, "attribution": attribution}[sys.argv[1]]()


if __name__ == "__main__" and (len(sys.argv) == 1 or sys.argv[1] in ("summary", "diag")):
    _main_basic()


# ================================================================ drift baseline for one-sided variants
def always(df, side=-1, every_h=0, stop_atr=2.0, rr=2.0):
    """CONTROL: enter `side` at every bar (re-enter right after each exit), same exits as the family.
    Its avg R is the drift/beta baseline that a one-sided signal must beat."""
    m = pd.Series(True, index=df.index)
    if every_h:
        m = pd.Series(np.arange(len(df)) % F.bars(df, every_h) == 0, index=df.index)
    return F._pack(df, m & (side > 0), m & (side < 0), stop_atr, rr)


def baseline():
    import bt.data as D
    from bt.engine import simulate
    from bt.runner import COST_SCENARIOS
    T24 = pd.Timestamp("2024-01-01", tz="UTC")
    roots = [("main", SYMBOLS, D.ROOT), ("holdout1", HOLD, HROOT)]
    if os.environ.get("FP_HOLDOUT2_ROOT"):
        roots.append(("holdout2", HOLD2, os.environ["FP_HOLDOUT2_ROOT"]))
    out = {}
    for tf, hold in (("4h", 18), ("1h", 72)):
        for side in (-1, 1):
            for name, syms, root in roots:
                if not root:
                    continue
                orig = D.ROOT
                D.ROOT = root
                parts = []
                for s in syms:
                    try:
                        df = D.load(s, tf, metrics=True, funding=True)
                    except FileNotFoundError:
                        continue
                    sig = always(df, side)
                    parts.append(simulate(df, sig, COST_SCENARIOS["base"], hold, None, s))
                D.ROOT = orig
                tr = pd.concat(parts, ignore_index=True)
                tr = tr[tr["t_entry"] >= T24]
                r = {}
                for per, part in (("2024", tr[tr["t_entry"] < IS_END]), ("2025_26", tr[tr["t_entry"] >= IS_END])):
                    r[per] = {"n": int(len(part)), "avg_R": round(float(part["R"].mean()), 3)}
                key = f"{tf}_{'short' if side < 0 else 'long'}_{name}"
                out[key] = r
                print(key, json.dumps(r), flush=True)
    with open(f"{RES}/funding_positioning_baseline.json", "w") as f:
        json.dump(out, f, indent=1)


HOLD2 = "TRXUSDT XLMUSDT HBARUSDT AAVEUSDT INJUSDT SUIUSDT LDOUSDT CRVUSDT ICPUSDT SEIUSDT".split()

if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "baseline":
    baseline()


# ================================================================ holdout 2 (fresh symbols, registered after holdout 1)
PREREG2 = [
    ("C_level_4h", "rcrowd", "4h", {"src": "level", "pct": 0.9}),
    ("R3short_4h", "rcrowd", "4h", {"src": "level", "pct": 0.9, "side": "short"}),
    ("R3short_1h", "rcrowd", "1h", {"src": "level", "pct": 0.9, "side": "short"}),
    ("C_level_1h", "rcrowd", "1h", {"src": "level", "pct": 0.9}),
]


def validate2():
    root = os.environ["FP_HOLDOUT2_ROOT"]
    import bt.data as D
    syms = [s for s in HOLD2 if os.path.exists(os.path.join(root, "klines", "5m", f"{s}.parquet"))
            and os.path.exists(os.path.join(root, "metrics", f"{s}.parquet"))]
    T24 = pd.Timestamp("2024-01-01", tz="UTC")
    out = {"prereg": PREREG2, "symbols": syms}
    for name, fn, tf, p in PREREG2:
        th = _trades(fn, tf, p, syms, root=root)
        thh = _trades(fn, tf, p, syms, root=root, costs="harsh")
        th, thh = th[th["t_entry"] >= T24], thh[thh["t_entry"] >= T24]
        r = {"holdout2_2024": _block(th[th["t_entry"] < IS_END], "2024"),
             "holdout2_2025_26": _block(th[th["t_entry"] >= IS_END], "2025_26"),
             "holdout2_all": _block(th, "all"),
             "holdout2_2025_26_harsh_avgR": round(float(thh[thh["t_entry"] >= IS_END]["R"].mean()), 3),
             "holdout2_per_symbol_2025_26": {s: round(float(g["R"].mean()), 3)
                                             for s, g in th[th["t_entry"] >= IS_END].groupby("symbol")}}
        out[name] = r
        print(name, json.dumps({k: (v.get("n"), v.get("avg_R"), v.get("t_stat"), v.get("t_clustered_week"),
                                    v.get("long"), v.get("short"), v.get("sym_pos"))
                                for k, v in r.items() if isinstance(v, dict) and "n" in v}),
              "harsh", r["holdout2_2025_26_harsh_avgR"], flush=True)
    with open(f"{RES}/funding_positioning_holdout2.json", "w") as f:
        json.dump(out, f, indent=1, default=str)


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "validate2":
    validate2()
