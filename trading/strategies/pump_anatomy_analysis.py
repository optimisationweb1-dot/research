"""pump_anatomy: event anatomy, precision/recall, scanner (walk-forward), portfolios, momentum/reversal.

    python3 -m strategies.pump_anatomy_analysis anatomy
    python3 -m strategies.pump_anatomy_analysis rules
    python3 -m strategies.pump_anatomy_analysis scanner
    python3 -m strategies.pump_anatomy_analysis xsmom
Outputs: trading/results/pump_anatomy_*.csv / .json
"""
import json
import os
import sys

import numpy as np
import pandas as pd

from strategies.pump_anatomy_features import FEATS
from strategies.pump_anatomy_panel import ROOT

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
IS_END = pd.Timestamp("2025-01-01", tz="UTC")
TRAIN_END = pd.Timestamp("2024-12-24", tz="UTC")   # 7d labels fully realised before IS_END
OOS_END = pd.Timestamp("2026-09-01", tz="UTC")
COSTS = {"base": 0.0007, "harsh": 0.0011, "extreme": 0.0025}
RNG = np.random.default_rng(20260927)


def load_panel(cols=None):
    p = pd.read_parquet(os.path.join(ROOT, "panel.parquet"), columns=cols)
    return p


def load_events(tag=""):
    e = pd.read_csv(os.path.join(ROOT, f"events{tag}.csv"), parse_dates=["date", "peak_date", "ign_date"])
    for c in ("date", "peak_date", "ign_date"):
        e[c] = pd.to_datetime(e[c], utc=True)
    return e


def week_block_boot(values, weeks, n=2000, stat=np.nanmean):
    """Bootstrap SE of stat(values) resampling calendar weeks (clusters)."""
    df = pd.DataFrame({"v": values, "w": weeks}).dropna()
    groups = [g["v"].to_numpy() for _, g in df.groupby("w")]
    k = len(groups)
    if k < 5:
        return np.nan
    sums = np.array([g.sum() for g in groups])
    cnts = np.array([len(g) for g in groups])
    idx = RNG.integers(0, k, size=(n, k))
    boots = sums[idx].sum(1) / cnts[idx].sum(1)
    return float(np.std(boots, ddof=1))


def nw_t(x, lags):
    """Newey-West t-stat of the mean of a time series."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 20:
        return np.nan
    u = x - x.mean()
    g0 = (u @ u) / n
    s = g0
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1)
        s += 2 * w * (u[L:] @ u[:-L]) / n
    return float(x.mean() / np.sqrt(s / n)) if s > 0 else np.nan


# ------------------------------------------------------------------ 1) anatomy
def anatomy(p, e, lags=range(0, 15), label=""):
    feats = [f"pr_{f}" for f in FEATS]
    key = p.set_index(["symbol", "date"])[feats + ["fund1", "fund_last", "age", "rvol7", "vcomp", "tshare1",
                                                   "ret7", "rs7", "rs30", "ann14"]]
    rows = []
    for L in lags:
        idx = pd.MultiIndex.from_arrays([e["symbol"], e["date"] - pd.Timedelta(days=L)])
        x = key.reindex(idx)
        wk = (e["date"].dt.tz_localize(None).dt.to_period("W")).astype(str).to_numpy()
        for f in feats:
            v = x[f].to_numpy()
            m = np.nanmean(v)
            se = week_block_boot(v, wk, n=500)
            rows.append({"lag": L, "feature": f[3:], "mean_pct": m, "se": se, "z": (m - 0.5) / se if se else np.nan,
                         "n": int(np.isfinite(v).sum())})
    out = pd.DataFrame(rows)
    out["label"] = label
    return out


def raw_compare(p, e):
    """Raw medians at onset vs eligible panel (same period)."""
    key = p.set_index(["symbol", "date"])
    x = key.reindex(pd.MultiIndex.from_arrays([e["symbol"], e["date"]]))
    base = p[p["elig"] & (p["date"] >= e["date"].min()) & (p["date"] <= e["date"].max())]
    rows = []
    for f in ["rvol1", "rvol7", "tshare1", "tshare7", "fund1", "fund7", "vcomp", "rcomp", "ret1", "ret7", "rs7",
              "rs30", "age", "med30qv", "dist_hi90", "dist_lo90", "h_rvol_max", "ann14"]:
        rows.append({"feature": f, "event_median": float(np.nanmedian(x[f])), "panel_median": float(np.nanmedian(base[f])),
                     "event_mean": float(np.nanmean(x[f])), "panel_mean": float(np.nanmean(base[f]))})
    extra = {
        "share_fund_neg_event": float(np.nanmean(x["fund_last"] < 0)),
        "share_fund_neg_panel": float(np.nanmean(base["fund_last"] < 0)),
        "share_age_lt90_event": float(np.nanmean(x["age"] < 90)),
        "share_age_lt90_panel": float(np.nanmean(base["age"] < 90)),
        "share_ann14_event": float(np.nanmean(x["ann14"] > 0)),
        "share_ann14_panel": float(np.nanmean(base["ann14"] > 0)),
    }
    return pd.DataFrame(rows), extra


def size_buckets(p):
    q = p[p["elig"] & p["y7"].notna()].copy()
    q["size_q"] = q.groupby("date")["size"].transform(lambda x: pd.qcut(x.rank(method="first"), 5, labels=False))
    q["age_b"] = pd.cut(q["age"], [29, 90, 180, 365, 10000], labels=["30-90", "90-180", "180-365", ">365"])
    a = q.groupby("size_q")["y7"].agg(["mean", "size"]).rename(columns={"mean": "pump_rate", "size": "n"})
    b = q.groupby("age_b", observed=True)["y7"].agg(["mean", "size"]).rename(columns={"mean": "pump_rate", "size": "n"})
    return a, b


def run_anatomy():
    p = load_panel()
    e = load_events()
    out = []
    for lab, ee in (("all", e), ("IS", e[e["date"] < IS_END]), ("OOS", e[e["date"] >= IS_END])):
        out.append(anatomy(p, ee, label=lab))
    an = pd.concat(out)
    an.to_csv(os.path.join(RES, "pump_anatomy_profile.csv"), index=False)
    raw, extra = raw_compare(p, e)
    raw.to_csv(os.path.join(RES, "pump_anatomy_raw_onset.csv"), index=False)
    a, b = size_buckets(p)
    res = {"n_events": len(e), "n_IS": int((e["date"] < IS_END).sum()), "n_OOS": int((e["date"] >= IS_END).sum()),
           "base_rate_y7": float(p.loc[p["elig"], "y7"].mean()), **extra,
           "pump_rate_by_size_quintile": a.reset_index().to_dict("records"),
           "pump_rate_by_age": b.reset_index().astype({"age_b": str}).to_dict("records"),
           "post_peak": {"median_ret_peak_to_14d": float(e["ret_peak_to_14d"].median()),
                         "median_ret_peak_to_30d": float(e["ret_peak_to_30d"].median()),
                         "median_base_to_30d_after_peak": float(e["base_to_30d_after_peak"].median()),
                         "share_below_base_30d_after_peak": float((e["base_to_30d_after_peak"] < 0).mean()),
                         "median_days_to_peak": float(e["days_to_peak"].median()),
                         "median_peak_gain": float(e["peak_gain"].median())}}
    with open(os.path.join(RES, "pump_anatomy_anatomy.json"), "w") as f:
        json.dump(res, f, indent=1, default=str)
    print(json.dumps(res, indent=1, default=str)[:3000])
    piv = an[an["label"] == "all"].pivot(index="feature", columns="lag", values="mean_pct")[[0, 1, 3, 7, 14]]
    print(piv.round(3).sort_values(0))
    zz = an[(an["lag"] == 0)].pivot(index="feature", columns="label", values="z")
    print(zz.round(1))



# ------------------------------------------------------------------ 2) rules: precision / recall / lift
RULES = {
    "rvol7>=p90": lambda q: q["pr_rvol7"] >= 0.9,
    "rvol1>=p90": lambda q: q["pr_rvol1"] >= 0.9,
    "h_rvol_max>=p90": lambda q: q["pr_h_rvol_max"] >= 0.9,
    "tshare1>=p90": lambda q: q["pr_tshare1"] >= 0.9,
    "tshare_z>=p90": lambda q: q["pr_tshare_z"] >= 0.9,
    "fund_neg": lambda q: q["fund_last"] < 0,
    "fund1<=p10": lambda q: q["pr_fund1"] <= 0.1,
    "vcomp<=p10": lambda q: q["pr_vcomp"] <= 0.1,
    "rcomp<=p10": lambda q: q["pr_rcomp"] <= 0.1,
    "rs7>=p90": lambda q: q["pr_rs7"] >= 0.9,
    "rs30>=p90": lambda q: q["pr_rs30"] >= 0.9,
    "rs7<=p10": lambda q: q["pr_rs7"] <= 0.1,
    "age<90": lambda q: q["age"] < 90,
    "size<=p20": lambda q: q["pr_size"] <= 0.2,
    "ann14>0": lambda q: q["ann14"] > 0,
    "ret1>=+15%": lambda q: q["ret1"] >= 0.15,
    "rvol7>=p90&fund_neg": lambda q: (q["pr_rvol7"] >= 0.9) & (q["fund_last"] < 0),
    "rvol7>=p80&vcomp<=p30": lambda q: (q["pr_rvol7"] >= 0.8) & (q["pr_vcomp"] <= 0.3),
    "rvol1>=p90&tshare1>=p80": lambda q: (q["pr_rvol1"] >= 0.9) & (q["pr_tshare1"] >= 0.8),
    "fund_neg&rs7>=p70": lambda q: (q["fund_last"] < 0) & (q["pr_rs7"] >= 0.7),
}


def rule_table(q, events, label):
    """q: eligible panel rows with y7 known. events: onsets (symbol, date)."""
    base = q["y7"].mean()
    ek = set(zip(events["symbol"], events["date"]))
    qi = q.set_index(["symbol", "date"])
    rows = []
    for name, fn in RULES.items():
        sig = fn(q).fillna(False).to_numpy()
        n = int(sig.sum())
        prec = float(q["y7"].to_numpy()[sig].mean()) if n else np.nan
        fr7 = q["fwd_ret7_exec"].to_numpy()[sig]
        fr7 = fr7[np.isfinite(fr7)]
        # recall at onset day s and within s-3..s
        s_on = pd.Series(sig, index=qi.index)
        at = s_on.reindex(pd.MultiIndex.from_arrays([events["symbol"], events["date"]]))
        rec0 = float(at.fillna(False).mean())
        win = np.zeros(len(events), bool)
        for L in range(0, 4):
            w = s_on.reindex(pd.MultiIndex.from_arrays([events["symbol"], events["date"] - pd.Timedelta(days=L)]))
            win |= w.fillna(False).to_numpy()
        rows.append({"period": label, "rule": name, "n_signals": n, "signals_per_day": n / q["date"].nunique(),
                     "precision": prec, "base_rate": base, "lift": prec / base if base else np.nan,
                     "recall_at_s": rec0, "recall_s-3..s": float(win.mean()),
                     "fwd7_mean_signal": float(np.mean(fr7)) if len(fr7) else np.nan,
                     "fwd7_median_signal": float(np.median(fr7)) if len(fr7) else np.nan,
                     "fwd7_mean_all": float(np.nanmean(q["fwd_ret7_exec"]))})
    return pd.DataFrame(rows)


def placebo_lift(q, rule, n=200):
    """Null distribution of lift: circularly shift y7 within each symbol by a random offset (>=60 days)."""
    sig = RULES[rule](q).fillna(False).to_numpy()
    y = q["y7"].to_numpy()
    sym = q["symbol"].to_numpy()
    base = np.nanmean(y)
    # positions of each symbol block
    order = np.argsort(sym, kind="stable")
    ys, ss, syms = y[order], sig[order], sym[order]
    bounds = np.flatnonzero(np.r_[True, syms[1:] != syms[:-1], True])
    lifts = []
    for _ in range(n):
        yy = np.empty_like(ys)
        for a, b in zip(bounds[:-1], bounds[1:]):
            L = b - a
            k = RNG.integers(min(60, L - 1), L) if L > 61 else RNG.integers(0, max(L, 1))
            yy[a:b] = np.roll(ys[a:b], k)
        lifts.append(np.nanmean(yy[ss]) / base)
    return np.array(lifts)


def run_rules():
    p = load_panel()
    e = load_events()
    q = p[p["elig"] & p["y7"].notna()].copy()
    out = []
    for lab, qq, ee in (("IS", q[q["date"] < IS_END], e[e["date"] < IS_END]),
                        ("OOS", q[q["date"] >= IS_END], e[e["date"] >= IS_END])):
        out.append(rule_table(qq, ee, lab))
    t = pd.concat(out)
    # placebo p-values for OOS lifts
    qo = q[q["date"] >= IS_END]
    pv = {}
    for r in RULES:
        null = placebo_lift(qo, r, n=100)
        obs = float(t[(t["period"] == "OOS") & (t["rule"] == r)]["lift"].iloc[0])
        pv[r] = float((np.sum(null >= obs) + 1) / (len(null) + 1))
    t["placebo_p_OOS"] = t["rule"].map(pv).where(t["period"] == "OOS")
    t.to_csv(os.path.join(RES, "pump_anatomy_rules.csv"), index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 20):
        print(t.round(4).to_string())


# ------------------------------------------------------------------ 3) portfolios
def portfolio(p, score_col, hold=1, frac=0.1, side="long", min_names=10, elig="elig", cost=0.0007):
    """Daily cross-sectional decile portfolio. Decision at close of day d (features <= d), entry at px_exec[d]
    (01:00 UTC d+1). Returns a daily frame with gross, cost, funding and net returns (earned over d -> d+1).
    hold>1: `hold` overlapping tranches, each 1/hold of capital, weights fixed within the tranche."""
    q = p.loc[p[elig] & p[score_col].notna() & p["px_exec"].notna(), ["date", "symbol", score_col]]
    rk = q.groupby("date")[score_col].rank(pct=True, method="first")
    cnt = q.groupby("date")[score_col].transform("count")
    q = q.assign(rk=rk, cnt=cnt)
    q = q[q["cnt"] >= min_names]
    if side == "long":
        sel = q[q["rk"] > 1 - frac]
        sgn = 1.0
    else:
        sel = q[q["rk"] <= frac]
        sgn = -1.0
    w = sel.assign(w=sgn).pivot_table(index="date", columns="symbol", values="w", aggfunc="first")
    w = w.div(w.abs().sum(1), axis=0)
    dates = pd.date_range(p["date"].min(), p["date"].max(), freq="1D", tz="UTC")
    w = w.reindex(dates).fillna(0.0)
    if hold > 1:
        w = w.rolling(hold, min_periods=1).sum() / hold
    r = p.pivot_table(index="date", columns="symbol", values="r_next", aggfunc="first").reindex(dates)
    f = p.pivot_table(index="date", columns="symbol", values="fund_next", aggfunc="first").reindex(dates)
    cols = w.columns
    r = r.reindex(columns=cols)
    f = f.reindex(columns=cols).fillna(0.0)
    # a position whose next return is unknown (data gap) earns 0
    gross = (w * r.fillna(0.0)).sum(1)
    fund = -(w * f).sum(1)
    turn = w.diff().abs().sum(1)
    turn.iloc[0] = w.iloc[0].abs().sum()
    out = pd.DataFrame({"gross": gross, "fund": fund, "turnover": turn, "names": (w != 0).sum(1)})
    out["cost"] = -turn * cost
    out["net"] = out["gross"] + out["fund"] + out["cost"]
    out = out[(w.abs().sum(1) > 0)]
    return out


def ew_market(p, elig="elig"):
    q = p[p[elig] & p["px_exec"].notna()]
    return q.groupby("date")["r_next"].mean()


def perf(x, lags=3):
    x = x.dropna()
    if len(x) < 30:
        return {"n_days": len(x)}
    eq = np.cumprod(1 + x.to_numpy())
    dd = 1 - eq / np.maximum.accumulate(eq)
    return {"n_days": int(len(x)), "mean_daily_pct": round(100 * x.mean(), 4),
            "ann_ret_pct": round(100 * ((1 + x).prod() ** (365 / len(x)) - 1), 1),
            "sharpe_ann": round(x.mean() / x.std() * np.sqrt(365), 2) if x.std() > 0 else None,
            "t_nw": round(nw_t(x.to_numpy(), lags), 2), "max_dd_pct": round(100 * dd.max(), 1)}


def split_perf(x, lags=3):
    return {"IS": perf(x[x.index < IS_END], lags), "OOS": perf(x[(x.index >= IS_END) & (x.index < OOS_END)], lags)}


def eval_score(p, score_col, holds=(1, 7), label="", mkt=None):
    mkt = ew_market(p) if mkt is None else mkt
    res = []
    for h in holds:
        for cname, c in COSTS.items():
            L = portfolio(p, score_col, hold=h, side="long", cost=c)
            S = portfolio(p, score_col, hold=h, side="short", cost=c)
            ls = (L["net"].reindex(L.index.union(S.index)).fillna(0) + S["net"].reindex(L.index.union(S.index)).fillna(0)) / 2
            ex = L["net"] - mkt.reindex(L.index).fillna(0)
            for nm, x in (("long", L["net"]), ("short", S["net"]), ("long_short", ls), ("long_minus_EW", ex)):
                sp = split_perf(x, lags=h + 2)
                for per in ("IS", "OOS"):
                    res.append({"score": label or score_col, "hold": h, "costs": cname, "leg": nm, "period": per,
                                **sp[per]})
            if cname == "base":
                res.append({"score": label or score_col, "hold": h, "costs": cname, "leg": "turnover/day",
                            "period": "all", "mean_daily_pct": round(float(L["turnover"].mean()), 3)})
                res.append({"score": label or score_col, "hold": h, "costs": cname, "leg": "funding_long/day",
                            "period": "all", "mean_daily_pct": round(100 * float(L["fund"].mean()), 4)})
    return pd.DataFrame(res)


# ------------------------------------------------------------------ 4) scanner (walk-forward)
def scanner_X(q):
    feats = [f"pr_{f}" for f in FEATS if f not in ("ann14",)]
    X = q[feats].fillna(0.5).copy()
    X["young"] = (q["age"] < 90).astype(float)
    X["ann"] = (q["ann14"] > 0).astype(float)
    X["fneg"] = (q["fund_last"] < 0).astype(float)
    return X


def fit_scanner(p):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.metrics import roc_auc_score
    q = p[p["elig"]].copy()
    tr = q[(q["date"] <= TRAIN_END) & q["y7"].notna()]
    X, Xt = scanner_X(q), scanner_X(tr)
    out = {}
    mA = LogisticRegression(C=1.0, max_iter=2000).fit(Xt, tr["y7"].astype(int))
    q["score_A"] = mA.predict_proba(X)[:, 1]
    yr = tr.groupby("date")["fwd_ret7_exec"].rank(pct=True).fillna(0.5)
    mB = Ridge(alpha=1.0).fit(Xt, yr)
    q["score_B"] = mB.predict(X)
    mC = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, random_state=0).fit(Xt, tr["y7"].astype(int))
    q["score_C"] = mC.predict_proba(X)[:, 1]
    coefs = dict(zip(X.columns, np.round(mA.coef_[0], 3)))
    for s in ("score_A", "score_B", "score_C"):
        for per, m in (("IS", q["date"] <= TRAIN_END), ("OOS", q["date"] >= IS_END)):
            mm = m & q["y7"].notna()
            out[f"{s}_{per}_AUC"] = round(float(roc_auc_score(q.loc[mm, "y7"].astype(int), q.loc[mm, s])), 4)
    for s in ("score_A", "score_B", "score_C"):
        p[s] = np.nan
        p.loc[q.index, s] = q[s]
    return p, out, coefs


def topdecile_pr(p, e, score):
    """Precision/recall of 'score in top decile of the day' as a pump detector."""
    q = p[p["elig"] & p[score].notna()].copy()
    q["rk"] = q.groupby("date")[score].rank(pct=True)
    q["sig"] = q["rk"] > 0.9
    rows = []
    for per, m, me in (("IS", q["date"] < IS_END, e["date"] < IS_END), ("OOS", q["date"] >= IS_END, e["date"] >= IS_END)):
        qq = q[m & q["y7"].notna()]
        ee = e[me]
        si = qq.set_index(["symbol", "date"])["sig"]
        at = si.reindex(pd.MultiIndex.from_arrays([ee["symbol"], ee["date"]])).fillna(False)
        rows.append({"score": score, "period": per, "precision": float(qq.loc[qq["sig"], "y7"].mean()),
                     "base_rate": float(qq["y7"].mean()), "recall_at_s": float(at.mean()),
                     "lift": float(qq.loc[qq["sig"], "y7"].mean() / qq["y7"].mean())})
    return rows


def run_scanner():
    p = load_panel()
    e = load_events()
    p, auc, coefs = fit_scanner(p)
    p[["date", "symbol", "score_A", "score_B", "score_C"]].dropna(subset=["score_A"]).to_parquet(
        os.path.join(ROOT, "scores.parquet"), index=False)
    mkt = ew_market(p)
    res = pd.concat([eval_score(p, s, mkt=mkt) for s in ("score_A", "score_B", "score_C")])
    pr = pd.DataFrame(sum([topdecile_pr(p, e, s) for s in ("score_A", "score_B", "score_C")], []))
    res.to_csv(os.path.join(RES, "pump_anatomy_scanner_portfolios.csv"), index=False)
    pr.to_csv(os.path.join(RES, "pump_anatomy_scanner_pr.csv"), index=False)
    with open(os.path.join(RES, "pump_anatomy_scanner.json"), "w") as f:
        json.dump({"auc": auc, "coef_logit_A": coefs, "ew_market": split_perf(mkt)}, f, indent=1)
    print(auc)
    print(coefs)
    print(pr.round(4))
    with pd.option_context("display.width", 250, "display.max_rows", 500):
        print(res[(res["costs"].isin(["base", "harsh"]))].to_string())


# ------------------------------------------------------------------ 5) classic XS momentum / reversal
def run_xsmom():
    p = load_panel()
    mkt = ew_market(p)
    res = []
    for L in (7, 14, 30):
        p[f"mom{L}"] = p[f"ret{L}"]
        res.append(eval_score(p, f"mom{L}", holds=(1, 7), mkt=mkt))
    p["rev1"] = -p["ret1"]
    res.append(eval_score(p, "rev1", holds=(1, 3), mkt=mkt))
    res = pd.concat(res)
    res.to_csv(os.path.join(RES, "pump_anatomy_xsmom.csv"), index=False)
    with pd.option_context("display.width", 250, "display.max_rows", 500):
        print(res[res["costs"].isin(["base", "harsh"]) & res["leg"].isin(["long_short", "long_minus_EW", "long", "short"])].to_string())


if __name__ == "__main__":
    {"anatomy": run_anatomy, "rules": run_rules, "scanner": run_scanner, "xsmom": run_xsmom}[sys.argv[1]]()
