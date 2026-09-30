"""treasury_flows: event studies (H1), lead-lag (H2), reaction (H3). Pre-registration:
trading/research/treasury_flows_prereg.md.  Run: python3 strategies/treasury_flows_analysis.py [events|leadlag|all]
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TR = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from treasury_flows_prices import load_ext  # noqa: E402
from treasury_flows_stats import EventStudy, nw_ols  # noqa: E402

RES = os.path.join(TR, "results")
H = [1, 24, 72, 168, 336, 720, 1440]
IS_END = pd.Timestamp("2025-01-01", tz="UTC")


def events(include_secondary=False):
    e = pd.read_csv(os.path.join(TR, "research", "treasury_flows_events.csv"))
    e["t"] = pd.to_datetime(e["ann_ts_utc"], utc=True)
    return e if include_secondary else e[e["set"] == "primary"]


def prices():
    b = load_ext("BTCUSDT", "1h")
    e = load_ext("ETHUSDT", "1h")
    lb, le = np.log(b["open"]), np.log(e["open"])
    return lb, le


def fmt(df):
    cols = ["h", "n", "mean_pct", "drift_pct", "abn_pct", "median_pct", "hit_vs_drift", "p_circ", "p_dow", "t_nw"]
    return df[cols].round(3).to_string(index=False)


def run_events():
    ev = events()
    lb, le = prices()
    es_b, es_e, es_rel = EventStudy(lb, H), EventStudy(le, H), EventStudy((le - lb).dropna(), H)
    out = {}

    def rep(name, es, df, weights=None, pre=False):
        r = es.run(df["t"], weights=weights, pre=pre)
        out[name] = r.to_dict("records")
        print(f"\n== {name}  (events={len(df)})")
        print(fmt(r))

    m = ev[ev.ticker == "MSTR"]
    mb = m[m.event_type == "purchase"]
    rep("BTC | MSTR purchase | all [PRIMARY a]", es_b, mb)
    rep("BTC | MSTR purchase | USD-weighted", es_b, mb, weights=mb["usd"])
    rep("BTC | MSTR purchase | IS 2024", es_b, mb[mb.t < IS_END])
    rep("BTC | MSTR purchase | OOS 2025-26", es_b, mb[mb.t >= IS_END])
    big = mb[mb.usd >= mb.usd.quantile(2 / 3)]
    rep("BTC | MSTR purchase | top tercile USD", es_b, big)
    rep("BTC | MSTR no purchase or sale (control)", es_b, m[m.event_type != "purchase"])
    rep("BTC | MSTR purchase | PRE-event run-up", es_b, mb, pre=True)

    eth = ev[(ev.asset == "ETH") & (ev.event_type == "purchase")].copy()
    eth["day"] = eth["t"].dt.floor("D")
    ed = eth.sort_values("t").groupby("day").agg(t=("t", "first"), usd=("usd", "sum"), n=("t", "size")).reset_index()
    rep("ETH | treasury (BMNR+SBET) purchase | all [PRIMARY b]", es_e, ed)
    rep("ETH | treasury | USD-weighted", es_e, ed, weights=ed["usd"])
    rep("ETH | BMNR only", es_e, eth[eth.ticker == "BMNR"])
    rep("ETH-BTC | treasury | market-adjusted", es_rel, ed)
    rep("ETH | treasury | PRE-event run-up", es_e, ed, pre=True)
    bigE = ed[ed.usd >= ed.usd.quantile(2 / 3)]
    rep("ETH | treasury | top tercile USD", es_e, bigE)
    sec = events(include_secondary=True)
    sec = sec[(sec["set"] == "secondary") & (sec.asset == "BTC")]
    rep("BTC | secondary (Metaplanet, GME, Strive) | exploratory", es_b, sec)
    with open(os.path.join(RES, "treasury_flows_eventstudy.json"), "w") as f:
        json.dump(out, f, indent=1, default=float)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "events"
    if what in ("events", "all"):
        run_events()


# ------------------------------------------------------------------ weekly lead-lag (H2, H3)
ANCHOR_H = 14  # Monday 14:00 UTC: after Strategy (~12-13 UTC) and BitMine (~12:45-13:45 UTC) 8-Ks


def etf(asset):
    d = pd.read_csv(os.path.join(TR, "research", f"treasury_flows_etf_{asset.lower()}.csv"), index_col=0)
    d.index = pd.to_datetime(d.index).tz_localize("UTC")
    return d["total_usd"]


def weekly_panel(asset):
    """Rows = weeks, anchored at Monday 14:00 UTC. All flow columns are KNOWN at the row's anchor.
    r0 = log return from this anchor to the next one (first tradeable week after the info)."""
    lb, le = prices()
    lp = lb if asset == "BTC" else le
    ev = events()
    anchors = pd.date_range("2024-01-08 14:00", "2026-09-21 14:00", freq="7D", tz="UTC")
    px = lp.reindex(anchors, method="ffill")
    df = pd.DataFrame(index=anchors)
    df["lp"] = px.values
    df["r0"] = df["lp"].shift(-1) - df["lp"]          # anchor_w -> anchor_{w+1}   (after info)
    df["r_exec"] = df["lp"] - df["lp"].shift(1)       # anchor_{w-1} -> anchor_w (execution week of the flows)
    # treasury USD announced in (anchor_{w-1}, anchor_w]
    tr = ev[(ev.asset == asset)].copy()
    tr["w"] = anchors[np.clip(anchors.searchsorted(tr["t"], side="left"), 0, len(anchors) - 1)]
    df["treas_usd"] = tr.groupby("w")["usd"].sum().reindex(anchors).fillna(0.0)
    if asset == "BTC":
        df.loc[df.index < tr["t"].min(), "treas_usd"] = 0.0
    f = etf(asset)
    avail = f.index + pd.Timedelta(days=2)             # day D known by D+2 00:00 UTC (conservative)
    wf = anchors[np.clip(anchors.searchsorted(avail, side="left"), 0, len(anchors) - 1)]
    df["etf_usd"] = pd.Series(f.values, index=wf).groupby(level=0).sum().reindex(anchors).fillna(0.0)
    if asset == "ETH":
        df = df[df.index >= pd.Timestamp("2024-07-29 14:00", tz="UTC")]
    df["flow_usd"] = df["treas_usd"] + df["etf_usd"]
    return df.dropna(subset=["lp"])


def leadlag(df, fcol, K=8, lags_nw=3, controls=("r_exec",)):
    """b_k from r_{w+k} = a + b*z(flow_w) + c*controls + e, k=0..K-1 (r0 shifted)."""
    z = (df[fcol] - df[fcol].mean()) / df[fcol].std()
    rows = []
    for k in range(K):
        y = df["r0"].shift(-k)
        X = np.column_stack([z] + [df[c] for c in controls])
        r = nw_ols(y.values, X, lags_nw)
        rows.append({"k_week": k, "b_pct_per_sd": 100 * r["coef"][1], "t": r["t"][1], "n": r["n"]})
    # cumulative 0..3 and 4..7 (the "delayed" window) with NW lags
    for a, b in ((0, 4), (4, 8), (0, 8)):
        y = sum(df["r0"].shift(-k) for k in range(a, b))
        X = np.column_stack([z] + [df[c] for c in controls])
        r = nw_ols(y.values, X, b - a + 2)
        rows.append({"k_week": f"cum{a}-{b - 1}", "b_pct_per_sd": 100 * r["coef"][1], "t": r["t"][1], "n": r["n"]})
    return pd.DataFrame(rows)


def reaction(df, fcol, lags_nw=3):
    """flow_w (z) on past returns: r_exec (same week as execution: impact OR reaction), r_{w-2}, sum r_{w-3..w-6},
    and on FUTURE returns r0 (placebo direction)."""
    z = (df[fcol] - df[fcol].mean()) / df[fcol].std()
    past2 = df["r_exec"].shift(1)
    past36 = sum(df["r_exec"].shift(k) for k in range(2, 6))
    out = {}
    for name, X in {"exec_week": [df["r_exec"]], "prior_week(w-2)": [past2], "prior_4w(w-3..w-6)": [past36],
                    "future_week(r0)": [df["r0"]], "future_4w": [sum(df["r0"].shift(-k) for k in range(4))]}.items():
        r = nw_ols(z.values, np.column_stack(X), lags_nw)
        out[name] = {"b_sd_per_10pct": 0.1 * r["coef"][1], "t": r["t"][1], "r2": r["r2"], "n": r["n"]}
    # multivariate: all past together
    r = nw_ols(z.values, np.column_stack([df["r_exec"], past2, past36]), lags_nw)
    out["joint_past"] = {"t_exec": r["t"][1], "t_w-2": r["t"][2], "t_w-3..6": r["t"][3], "r2": r["r2"], "n": r["n"]}
    # persistence of flows
    r = nw_ols(z.values, np.column_stack([z.shift(1)]), lags_nw)
    out["ar1"] = {"b": r["coef"][1], "t": r["t"][1]}
    return out


def run_leadlag():
    out = {}
    for asset in ("BTC", "ETH"):
        df = weekly_panel(asset)
        for per, sub in (("all", df), ("IS<2025", df[df.index < IS_END]), ("OOS>=2025", df[df.index >= IS_END])):
            for fcol in ("etf_usd", "treas_usd", "flow_usd"):
                if sub[fcol].abs().sum() == 0 or len(sub) < 20:
                    continue
                if asset == "ETH" and fcol != "etf_usd" and per == "IS<2025":
                    continue
                ll = leadlag(sub, fcol)
                re_ = reaction(sub, fcol)
                key = f"{asset}|{fcol}|{per}"
                out[key] = {"leadlag": ll.to_dict("records"), "reaction": re_, "weeks": len(sub)}
                print(f"\n== {key}  weeks={len(sub)}  corr(flow, r_exec)={sub[fcol].corr(sub['r_exec']):.2f} "
                      f"corr(flow, r0)={sub[fcol].corr(sub['r0']):.2f}")
                print(ll.round(3).to_string(index=False))
                print({k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in re_.items()})
    with open(os.path.join(RES, "treasury_flows_leadlag.json"), "w") as f:
        json.dump(out, f, indent=1, default=float)


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] in ("leadlag", "all"):
    run_leadlag()


# ------------------------------------------------------------------ H5 absorption, H2b daily residual flows
def absorption(asset, thr_q=0.7, min_hist=26, n_placebo=2000, seed=5):
    df = weekly_panel(asset)
    F4 = df["flow_usd"].rolling(4).sum()
    P4 = df["lp"] - df["lp"].shift(4)
    thr = F4.expanding(min_hist).quantile(thr_q).shift(1)
    y4 = sum(df["r0"].shift(-k) for k in range(4))
    y8 = sum(df["r0"].shift(-k) for k in range(8))
    sigs = {"absorb (flow>=p70 & 4w ret<=0)": (F4 >= thr) & (P4 <= 0),
            "ctl: 4w ret<=0 only": (P4 <= 0) & thr.notna(),
            "ctl: flow>=p70 only": (F4 >= thr),
            "flow>=p70 & 4w ret>0 (chase)": (F4 >= thr) & (P4 > 0)}
    rng = np.random.default_rng(seed)
    rows = []
    valid = thr.notna()
    for name, s in sigs.items():
        s = s & valid
        for hn, y, L in (("next4w", y4, 4), ("next8w", y8, 8)):
            m = valid & y.notna()
            ss, yy = s[m].astype(float).values, y[m].values
            if ss.sum() < 3:
                continue
            r = nw_ols(yy, ss, L)
            diff = r["coef"][1]
            pm = []
            for _ in range(n_placebo):
                sh = np.roll(ss, rng.integers(8, len(ss) - 8))
                pm.append(yy[sh == 1].mean() - yy[sh == 0].mean())
            rows.append({"signal": name, "horizon": hn, "n_sig_weeks": int(ss.sum()), "n_weeks": int(len(ss)),
                         "mean_sig_pct": 100 * yy[ss == 1].mean(), "mean_rest_pct": 100 * yy[ss == 0].mean(),
                         "diff_pct": 100 * diff, "t_nw": r["t"][1], "p_circ": float((np.array(pm) >= diff).mean()),
                         "first_sig": str(df.index[m][ss == 1][0].date()) if ss.sum() else ""})
    return pd.DataFrame(rows)


def daily_residual(asset="BTC"):
    lb, le = prices()
    lp = (lb if asset == "BTC" else le)
    c = lp.resample("1D").last()            # log open of last hour ~ close
    r = c.diff()
    f = etf(asset).reindex(c.index).fillna(0.0)
    z = (f - f.mean()) / f.std()
    X = pd.DataFrame({"r0": r, "r1": r.shift(1), "r2_5": r.shift(2).rolling(4).sum(),
                      "r6_20": r.shift(6).rolling(15).sum(), "z1": z.shift(1)})
    ok = X.notna().all(axis=1) & z.notna()
    start = f[f != 0].index.min()
    ok &= X.index >= start
    fit = nw_ols(z[ok].values, X[ok].values, 5)
    Xc = np.column_stack([np.ones(ok.sum()), X[ok].values])
    u = pd.Series(np.nan, index=z.index)
    u[ok] = z[ok].values - Xc @ fit["coef"]
    out = {"reaction_fit": {"t_r0": fit["t"][1], "t_r1": fit["t"][2], "t_r2_5": fit["t"][3], "t_r6_20": fit["t"][4],
                            "t_z1": fit["t"][5], "r2": fit["r2"], "n": fit["n"]}}
    # forward returns from D+2 00:00 (flow of day D is known) -> tradeable
    for a, b in ((2, 6), (2, 21), (7, 21), (22, 60)):
        fwd = c.shift(-b) - c.shift(-(a - 1))      # close(D+b) - close(D+a-1) = open-ish of D+a
        for name, x in (("flow_z", z), ("resid_u", u)):
            m = x.notna() & fwd.notna() & (x.index >= start)
            for per, mm in (("all", m), ("IS", m & (x.index < IS_END)), ("OOS", m & (x.index >= IS_END))):
                rr = nw_ols(fwd[mm].values, x[mm].values, b - a + 1)
                out[f"{name}->D+{a}..D+{b}|{per}"] = {"b_pct_per_sd": 100 * rr["coef"][1], "t": rr["t"][1], "n": rr["n"]}
    # contemporaneous: residual flows vs same-day return is impossible to separate w/o intraday data -> report corr
    out["corr(flow_z, r0 same day)"] = float(z[ok].corr(r[ok]))
    out["corr(resid_u, r0 same day)"] = float(u[ok].corr(r[ok]))
    return out


def run_h5():
    res = {}
    for asset in ("BTC", "ETH"):
        a = absorption(asset)
        res[f"H5|{asset}"] = a.to_dict("records")
        print(f"\n== H5 absorption {asset}")
        print(a.round(3).to_string(index=False))
        d = daily_residual(asset)
        res[f"H2b|{asset}"] = d
        print(f"\n== H2b daily {asset}")
        for k, v in d.items():
            print(k, {kk: round(vv, 3) for kk, vv in v.items()} if isinstance(v, dict) else round(v, 3))
    with open(os.path.join(RES, "treasury_flows_h5_h2b.json"), "w") as f:
        json.dump(res, f, indent=1, default=float)


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] in ("h5", "all"):
    run_h5()


# ------------------------------------------------------------------ Granger-style joint tests (HAC Wald)
def _wald(y, X, idx, lags_nw=4):
    from scipy import stats
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    ok = np.isfinite(y) & np.isfinite(X).all(axis=1)
    y, X = y[ok], np.column_stack([np.ones(ok.sum()), X[ok]])
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ y
    e = y - X @ b
    u = X * e[:, None]
    S = u.T @ u
    for L in range(1, lags_nw + 1):
        G = u[L:].T @ u[:-L]
        S += (1 - L / (lags_nw + 1)) * (G + G.T)
    V = XtX_inv @ S @ XtX_inv * n / (n - k)
    ii = [i + 1 for i in idx]
    bb = b[ii]
    W = float(bb @ np.linalg.inv(V[np.ix_(ii, ii)]) @ bb)
    return W, float(1 - stats.chi2.cdf(W, len(ii))), float(bb.sum()), n


def granger(asset, fcol, p=4, sub=None):
    df = weekly_panel(asset)
    # execution-week alignment: flows known at anchor_w were executed during week w-1 -> F_exec[w-1]
    F = ((df[fcol] - df[fcol].mean()) / df[fcol].std()).shift(-1)   # F_exec at row w = executed in week w
    r = df["r0"]                                                    # return of week w (anchor_w -> anchor_w+1)
    if sub is not None:
        m = sub(df.index)
        F, r = F[m], r[m]
    Fl = np.column_stack([F.shift(j) for j in range(1, p + 1)])
    rl = np.column_stack([r.shift(j) for j in range(1, p + 1)])
    W1, p1, s1, n1 = _wald(r.values, np.column_stack([Fl, rl]), list(range(p)))       # flows -> returns
    W2, p2, s2, n2 = _wald(F.values, np.column_stack([rl, Fl]), list(range(p)))       # returns -> flows
    c0 = float(pd.Series(F).corr(pd.Series(r)))
    return {"flows->returns p": p1, "sum_b_pct": 100 * s1, "returns->flows p": p2, "sum_b": s2,
            "corr_same_week": c0, "n": n1}


def run_granger():
    out = {}
    for asset, fcols in (("BTC", ("etf_usd", "treas_usd", "flow_usd")), ("ETH", ("etf_usd", "treas_usd", "flow_usd"))):
        for fcol in fcols:
            for per, sub in (("all", None), ("OOS>=2025", lambda ix: ix >= IS_END)):
                g = granger(asset, fcol, sub=sub)
                out[f"{asset}|{fcol}|{per}"] = g
                print(f"{asset:4s} {fcol:10s} {per:10s}", {k: round(v, 3) for k, v in g.items()})
    with open(os.path.join(RES, "treasury_flows_granger.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] in ("granger", "all"):
    run_granger()
