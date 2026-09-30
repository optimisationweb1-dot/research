"""Driver for the ml_combo family.

    cd trading
    python3 -m strategies.ml_combo_run wf     --tf 1h --track 1 --aug sym --model small   # walk-forward preds
    python3 -m strategies.ml_combo_run eval   --tf 1h --track 1 --aug sym                 # 2 models x 3 thr
    python3 -m strategies.ml_combo_run verify --tf 1h --track 1                           # causality checks

Selection protocol (inside one variant = track x tf x aug): configs = model {small, large} x threshold
quantile {0.90, 0.95, 0.98}; the threshold value is the quantile of the IS (pre-2025) walk-forward edge
distribution, frozen for OOS. The selected config maximises IS t-stat (IS n >= 30), exactly like bt.runner.
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd

import strategies.ml_combo as M
from bt.engine import IS_END, check_lookahead, simulate, split_summary, summarize
from bt.runner import COST_SCENARIOS, score

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
STRIDE = {"15m": 4, "1h": 2}
QS = [0.90, 0.95, 0.98]
RISK = 0.5


def pred_path(tf, track, aug, model, tag=""):
    return os.path.join(M.SCRATCH, f"preds_{tf}_t{track}_{aug}_{model}{tag}.parquet")


def imp_path(tf, track, aug, model, tag=""):
    return os.path.join(M.SCRATCH, f"imp_{tf}_t{track}_{aug}_{model}{tag}.parquet")


# ------------------------------------------------------------------ walk-forward

def cmd_wf(a):
    P, cols = M.build_panel(a.tf, a.track)
    t0 = time.time()
    if a.per_symbol:
        parts, imps = [], []
        for s in M.SYMBOLS:
            pr, imp, _ = M.walk_forward(P, cols, a.tf, a.track, a.aug, a.model, stride=1, symbols=[s], log=False,
                                        min_rows=2000)
            parts.append(pr)
            imps.append(imp)
            print(f"  per-symbol {s} done {time.time() - t0:.0f}s", flush=True)
        preds, imp = pd.concat(parts, ignore_index=True), pd.concat(imps)
        tag = "_ps"
    else:
        preds, imp, _ = M.walk_forward(P, cols, a.tf, a.track, a.aug, a.model, stride=STRIDE[a.tf])
        tag = ""
    preds.to_parquet(pred_path(a.tf, a.track, a.aug, a.model, tag), index=False)
    imp.reset_index(drop=True).to_parquet(imp_path(a.tf, a.track, a.aug, a.model, tag), index=False)
    print(f"wf done {a.tf} t{a.track} {a.aug} {a.model}{tag}: {len(preds)} preds, {time.time() - t0:.0f}s")


# ------------------------------------------------------------------ evaluation helpers

def day_cluster_t(tr):
    if tr is None or len(tr) < 3:
        return None
    R = tr["R"].to_numpy()
    e = pd.Series(R - R.mean()).groupby(pd.DatetimeIndex(tr["t_entry"]).floor("1D").to_numpy()).sum().to_numpy()
    se = math.sqrt((e ** 2).sum() * len(e) / max(len(e) - 1, 1)) / len(R)
    return round(R.mean() / se, 2) if se > 0 else None


def simulate_all(raw, E, thr, tf, cost_name):
    K, H = M.TF_CFG[tf]["K"], M.TF_CFG[tf]["H"]
    out = []
    for s, df in raw.items():
        sig = M.signals_for_symbol(df, E[E["symbol"] == s], thr, K)
        out.append(simulate(df, sig, COST_SCENARIOS[cost_name], H, None, s))
    out = [o for o in out if len(o)]
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def summ(tr):
    ss = split_summary(tr, RISK)
    for k, part in (("IS", tr[tr["t_entry"] < IS_END] if len(tr) else tr),
                    ("OOS", tr[tr["t_entry"] >= IS_END] if len(tr) else tr)):
        ss[k]["t_day_cluster"] = day_cluster_t(part)
        if len(part):
            ss[k]["long_share"] = round(float((part["dir"] > 0).mean()), 3)
    return ss


def diagnostics(E):
    """Ranking quality of the raw predictions (not used for selection): monthly Spearman IC of the directional
    score vs the realised directional R, AUC of pL, and realised gross R by edge decile."""
    from scipy.stats import spearmanr
    d = E.dropna(subset=["RL", "RS"]).copy()
    d["score"] = d["pL"] - d["pS"]
    d["dirR"] = (d["RL"] - d["RS"]) / 2
    d["month"] = pd.DatetimeIndex(d["ts"]).tz_convert(None).to_period("M")
    ic = d.groupby("month").apply(lambda g: spearmanr(g["score"], g["dirR"]).statistic, include_groups=False)
    out = {}
    for nm, part in (("IS", ic[ic.index < pd.Period("2025-01")]), ("OOS", ic[ic.index >= pd.Period("2025-01")])):
        out[f"IC_{nm}_mean"] = round(float(part.mean()), 4)
        out[f"IC_{nm}_t"] = round(float(part.mean() / part.std(ddof=1) * math.sqrt(len(part))), 2) if len(part) > 2 else None
        out[f"IC_{nm}_months_pos"] = f"{int((part > 0).sum())}/{len(part)}"
    try:
        from sklearn.metrics import roc_auc_score
        for nm, part in (("IS", d[d["ts"] < IS_END]), ("OOS", d[d["ts"] >= IS_END])):
            out[f"AUC_long_{nm}"] = round(float(roc_auc_score(part["RL"] > 0, part["pL"])), 4)
    except Exception as e:  # noqa
        out["auc_error"] = str(e)
    oos = d[d["ts"] >= IS_END].copy()
    oos["best"] = np.where(oos["eL"] >= oos["eS"], oos["RL"], oos["RS"])
    oos["bestE"] = oos[["eL", "eS"]].max(axis=1)
    oos["dec"] = pd.qcut(oos["bestE"].rank(method="first"), 10, labels=False)
    g = oos.groupby("dec").agg(edge=("bestE", "mean"), gross_R=("best", "mean"), costR=("costR", "mean"))
    g["net_R_approx"] = g["gross_R"] - g["costR"]
    out["OOS_deciles_best_side"] = g.round(4).reset_index().to_dict(orient="records")
    return out


def load_raw_all(tf):
    return {s: M.load_raw(s, tf, False)[["open", "high", "low", "close", "volume"]] for s in M.SYMBOLS}


def cmd_eval(a):
    P, cols = M.build_panel(a.tf, a.track)
    raw = load_raw_all(a.tf)
    tag = "_ps" if a.per_symbol else ""
    models = a.models or ["small", "large"]
    rows, cache = [], {}
    diag, imps = {}, {}
    for model in models:
        pp = pred_path(a.tf, a.track, a.aug, model, tag)
        if not os.path.exists(pp):
            print("missing", pp)
            continue
        preds = pd.read_parquet(pp)
        E = M.edges(preds, P)
        diag[model] = diagnostics(E)
        imp = pd.read_parquet(imp_path(a.tf, a.track, a.aug, model, tag))
        mi = imp.mean().sort_values(ascending=False)
        imps[model] = {"top15_gain_share": mi.head(15).round(4).to_dict(), "max_share": round(float(mi.iloc[0]), 4),
                       "n_features": int(len(mi)), "top5_share": round(float(mi.head(5).sum()), 4)}
        is_best = E.loc[E["ts"] < IS_END, ["eL", "eS"]].max(axis=1)
        for q in QS:
            thr = float(is_best.quantile(q))
            params = {"model": model, "q": q, "thr": round(thr, 5)}
            tr = simulate_all(raw, E, thr, a.tf, "base")
            ss = summ(tr)
            rows.append({"params": params, **ss})
            cache[(model, q)] = (E, thr, tr)
            print(json.dumps(params), "IS", ss["IS"].get("n"), ss["IS"].get("avg_R"), ss["IS"].get("t_stat"),
                  "| OOS", ss["OOS"].get("n"), ss["OOS"].get("avg_R"), ss["OOS"].get("t_stat"),
                  ss["OOS"].get("t_day_cluster"), flush=True)
    best = max(rows, key=lambda r: score(r["IS"]))
    E, thr, tr_best = cache[(best["params"]["model"], best["params"]["q"])]
    tr_harsh = simulate_all(raw, E, thr, a.tf, "harsh")
    oos = tr_best[tr_best["t_entry"] >= IS_END] if len(tr_best) else tr_best
    per_symbol = {s: summarize(g, RISK, s) for s, g in oos.groupby("symbol")} if len(oos) else {}
    per_year = {str(y): summarize(g, RISK, str(y)) for y, g in tr_best.groupby(tr_best["t_entry"].dt.year)}
    oos_avg = [r["OOS"].get("avg_R") for r in rows if r["OOS"].get("n", 0) >= 10]
    name = f"t{a.track}_{a.aug}{tag}_{a.tf}"
    result = {
        "family": "ml_combo", "variant": name, "tf": a.tf, "track": a.track, "aug": a.aug,
        "per_symbol_models": bool(a.per_symbol), "bracket": M.TF_CFG[a.tf], "train_stride": STRIDE[a.tf],
        "first_test_month": M.FIRST_TEST[a.track], "train_start": M.TRAIN_START[a.track],
        "n_features": len(cols), "features": cols,
        "n_configs": len(rows), "selection": "max IS t-stat with IS n>=30 (IS = walk-forward preds before 2025-01-01)",
        "selected_params": best["params"], "selected_IS": best["IS"], "selected_OOS": best["OOS"],
        "selected_OOS_harsh_costs": summ(tr_harsh)["OOS"],
        "selected_OOS_per_symbol": per_symbol,
        "oos_symbols_positive": int(sum(1 for v in per_symbol.values() if v.get("avg_R", 0) > 0)),
        "selected_per_year": per_year,
        "all_configs_OOS_avgR": {"median": float(np.median(oos_avg)) if oos_avg else None,
                                 "share_positive": float(np.mean([x > 0 for x in oos_avg])) if oos_avg else None,
                                 "n": len(oos_avg)},
        "diagnostics": diag, "feature_importance_gain": imps,
        "configs": rows,
    }
    print("\nSELECTED", json.dumps(best["params"]))
    print("IS ", json.dumps(best["IS"]))
    print("OOS", json.dumps(best["OOS"]))
    print("OOS harsh", json.dumps(result["selected_OOS_harsh_costs"]))
    print("OOS symbols positive", result["oos_symbols_positive"], "| all-config OOS", json.dumps(result["all_configs_OOS_avgR"]))
    print("diag", json.dumps({m: {k: v for k, v in d.items() if k != "OOS_deciles_best_side"} for m, d in diag.items()}))
    out = os.path.join(RES, f"ml_combo_{name}.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=1, default=str)
    print("saved", out)


# ------------------------------------------------------------------ causality verification

def cmd_verify(a):
    """(1) feature panel: rebuild on history truncated at random bars, compare every feature of every symbol;
    (2) predictions: rebuild panel on data truncated INSIDE month m, retrain month m, compare its predictions
        with the full walk-forward run (must be identical);
    (3) bt.engine.check_lookahead on the end-to-end single-symbol strategy wrapper with a frozen booster."""
    import lightgbm as lgb
    rep = {"tf": a.tf, "track": a.track}
    P, cols = M.build_panel(a.tf, a.track)
    rng = np.random.default_rng(3)
    # (1)
    ts_all = np.sort(P["ts"].unique())
    cuts = [pd.Timestamp(x) for x in rng.choice(ts_all[len(ts_all) // 5:-100], 3, replace=False)]
    worst = 0.0
    for cut in cuts:
        Pc, _ = M.build_panel(a.tf, a.track, truncate_at=cut)
        A = P[P["ts"] <= cut].set_index(["symbol", "ts"])[cols].sort_index()
        B = Pc.set_index(["symbol", "ts"])[cols].sort_index()
        assert A.shape == B.shape, (A.shape, B.shape)
        d = np.nanmax(np.abs(A.to_numpy(np.float64) - B.to_numpy(np.float64)))
        nan_mismatch = int((A.isna().to_numpy() != B.isna().to_numpy()).sum())
        worst = max(worst, d)
        print(f"features cut {cut}: max|diff|={d:.3g} nan-mismatch={nan_mismatch}", flush=True)
        assert d < 1e-5 and nan_mismatch == 0, "feature lookahead"
    rep["feature_check"] = {"cuts": [str(c) for c in cuts], "max_abs_diff": worst}
    # (2)
    m0 = pd.Timestamp("2025-06-01", tz="UTC")
    cut = m0 + pd.Timedelta(days=14, hours=7)
    full, _, _ = M.walk_forward(P, cols, a.tf, a.track, "sym", "small", stride=STRIDE[a.tf], months=[m0], log=False)
    Pc, _ = M.build_panel(a.tf, a.track, truncate_at=cut)
    part, _, _ = M.walk_forward(Pc, cols, a.tf, a.track, "sym", "small", stride=STRIDE[a.tf], months=[m0], log=False)
    j = full.merge(part, on=["symbol", "ts"], suffixes=("_full", "_cut"))
    dmax = float(np.max(np.abs(j[["pL_full", "pS_full"]].to_numpy() - j[["pL_cut", "pS_cut"]].to_numpy())))
    print(f"prediction recompute month {m0:%Y-%m} truncated at {cut}: rows={len(j)} max|diff|={dmax:.3g}", flush=True)
    assert dmax < 1e-6, "prediction lookahead"
    rep["prediction_recompute"] = {"month": str(m0), "truncated_at": str(cut), "rows": len(j), "max_abs_diff": dmax}
    # (3) frozen booster trained on rows < 2025-01-01 (purged), end-to-end wrapper on BTCUSDT
    tm = M.train_mask(P, a.tf, a.track, pd.Timestamp("2025-01-01", tz="UTC"), STRIDE[a.tf])
    X = P.loc[tm, cols].to_numpy(np.float32)
    y = np.concatenate([(P.loc[tm, "RL"] > 0).to_numpy(np.float32), (P.loc[tm, "RS"] > 0).to_numpy(np.float32)])
    bst = M._fit(np.vstack([X, M.mirror(X, cols)]), y, M.MODEL_CFGS["small"], cols)
    mp = os.path.join(M.SCRATCH, f"frozen_{a.tf}_t{a.track}.txt")
    bst.save_model(mp)
    df = M.load_raw("BTCUSDT", a.tf, a.track == 2)
    df = df[df.index >= pd.Timestamp("2024-06-01" if a.track == 2 else "2024-01-01", tz="UTC")]
    df = df[df.index < pd.Timestamp("2025-09-01", tz="UTC")]
    params = {"tf": a.tf, "track": a.track, "aug": "sym", "model_path": mp, "thr": 0.0}
    ok = check_lookahead(M.strategy, df, params, n_checks=4)
    print("bt.engine.check_lookahead:", ok, flush=True)
    rep["engine_check_lookahead"] = {"passed": bool(ok), "symbol": "BTCUSDT", "n_checks": 4,
                                     "period": f"{df.index[0]}..{df.index[-1]}"}
    sig = M.strategy(df, **params)
    rep["engine_check_lookahead"]["signals_in_window"] = int((sig["signal"] != 0).sum())
    out = os.path.join(RES, f"ml_combo_verify_{a.tf}_t{a.track}.json")
    with open(out, "w") as f:
        json.dump(rep, f, indent=1, default=str)
    print("saved", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["wf", "eval", "verify"])
    ap.add_argument("--tf", default="1h")
    ap.add_argument("--track", type=int, default=1)
    ap.add_argument("--aug", default="sym")
    ap.add_argument("--model", default="small")
    ap.add_argument("--models", nargs="*")
    ap.add_argument("--per-symbol", action="store_true")
    a = ap.parse_args()
    {"wf": cmd_wf, "eval": cmd_eval, "verify": cmd_verify}[a.cmd](a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
