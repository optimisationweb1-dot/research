"""Statistical tests for the Coinbase-premium study (pre-registered in research/coinbase_premium_prereg.md).

    python3 -m strategies.coinbase_premium_analysis tests      # H1-H3 predictive regressions + placebo
    python3 -m strategies.coinbase_premium_analysis weekly     # H4 delayed effect (weekly anchors)
    python3 -m strategies.coinbase_premium_analysis etf        # H5 nowcast of ETF flows, H6 combo
    python3 -m strategies.coinbase_premium_analysis treasury   # H7 premium before treasury purchase 8-Ks
    python3 -m strategies.coinbase_premium_analysis context    # monthly regime table (narrative)

Returns: log close->close of Binance USD-M perps, from the close of hour t (when the premium of hour t is
known) to t+h. Newey-West (Bartlett, lags = h) for overlapping windows; placebo = circular shifts of the
signal within the period (keeps the signal's autocorrelation, destroys its timing).
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd

from strategies.coinbase_premium_feat import HERE, etf_daily, features, load_table

RES = os.path.join(HERE, "results")
IS_END = pd.Timestamp("2025-01-01", tz="UTC")
END = pd.Timestamp("2026-09-01", tz="UTC")
HORIZONS = [4, 24, 72, 168]
SIGNALS = ["L", "R", "D", "P", "U"]
RNG = np.random.default_rng(20260927)


# ----------------------------------------------------------------- statistics

def _lrv(s, L):
    """Bartlett long-run variance of a mean-zero series (sum form / T)."""
    T = len(s)
    n = 1 << int(math.ceil(math.log2(2 * T)))
    fs = np.fft.rfft(s, n)
    ac = np.fft.irfft(fs * np.conj(fs), n)[:L + 1]
    w = 1 - np.arange(1, L + 1) / (L + 1)
    return (ac[0] + 2 * np.sum(w * ac[1:L + 1])) / T


def nw_slope(x, y, L):
    """Simple regression y = a + b x; returns b, NW t-stat (Bartlett lags L)."""
    xc = x - x.mean()
    sxx = np.dot(xc, xc)
    b = np.dot(xc, y) / sxx
    u = y - y.mean() - b * xc
    s = xc * u
    T = len(x)
    var_b = _lrv(s, L) * T / sxx ** 2
    return b, b / math.sqrt(var_b) if var_b > 0 else float("nan")


def nw_ols(y, X, L):
    """Multiple regression with constant prepended; returns beta, NW t-stats."""
    X = np.column_stack([np.ones(len(y)), X])
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ y
    u = y - X @ b
    S = X * u[:, None]
    O = S.T @ S
    for j in range(1, L + 1):
        G = S[j:].T @ S[:-j]
        O += (1 - j / (L + 1)) * (G + G.T)
    V = XtX_inv @ O @ XtX_inv
    return b, b / np.sqrt(np.diag(V))


def nw_mean(y, L):
    """Mean with NW t-stat."""
    y = np.asarray(y, float)
    m = y.mean()
    v = _lrv(y - m, L) / len(y)
    return m, m / math.sqrt(v) if v > 0 else float("nan")


def placebo_t(x, y, L, n=500, min_shift=720):
    T = len(x)
    ts = []
    for _ in range(n):
        k = int(RNG.integers(min_shift, T - min_shift))
        ts.append(nw_slope(np.roll(x, k), y, L)[1])
    return np.array(ts)


def holm(pvals):
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    run = 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (m - r) * p[i]))
        adj[i] = run
    return adj


def norm_p2(t):
    return math.erfc(abs(t) / math.sqrt(2))


# ----------------------------------------------------------------- data

def panel(a):
    """Hourly frame: features for asset a + forward log returns of its perp (and BTC for market adj)."""
    p = load_table()
    f = features(p, a)
    lp = np.log(p[f"bnf_{a}"])
    lb = np.log(p["bnf_btc"])
    for h in HORIZONS + [336, 720]:
        f[f"y{h}"] = lp.shift(-h) - lp
        f[f"yb{h}"] = lb.shift(-h) - lb
        f[f"end{h}"] = f.index + pd.Timedelta(hours=h + 1)  # window ends at close of hour t+h
    f["past24"] = lp - lp.shift(24)
    f["past168"] = lp - lp.shift(168)
    f["r1"] = lp - lp.shift(1)
    return f


def period_mask(f, period, h):
    t_close = f.index + pd.Timedelta(hours=1)
    if period == "IS":
        return (t_close < IS_END) & (f[f"end{h}"] <= IS_END)
    if period == "OOS":
        return (t_close >= IS_END) & (f[f"end{h}"] <= END)
    return f[f"end{h}"] <= END


# ----------------------------------------------------------------- H1-H3

def run_tests(n_placebo=500):
    out = {"notes": "b in bps of forward log return per 1 unit of signal (z); t_nw lags=h; "
                    "placebo p = share |t_shift| >= |t_obs| (circular shifts >= 30d)", "rows": []}
    for a in ["btc", "eth", "sol"]:
        f = panel(a)
        sigs = SIGNALS if a != "sol" else ["L"]
        for s in sigs:
            for h in HORIZONS:
                for period in ["IS", "OOS"]:
                    m = period_mask(f, period, h)
                    d = f.loc[m, [s, f"y{h}", f"yb{h}"]].dropna()
                    x, y = d[s].to_numpy(), d[f"y{h}"].to_numpy()
                    b, t = nw_slope(x, y, h)
                    # non-overlapping check
                    xn, yn = x[::h], y[::h]
                    bn, tn = nw_slope(xn, yn, 0) if len(xn) > 10 else (np.nan, np.nan)
                    # rank-based robustness: Spearman-like (ranks of x)
                    xr = pd.Series(x).rank().to_numpy()
                    xr = (xr - xr.mean()) / xr.std()
                    br, tr = nw_slope(xr, y, h)
                    # clipped z
                    bc, tc = nw_slope(np.clip(x, -3, 3), y, h)
                    # 1h extra lag
                    d2 = f.loc[m, [f"y{h}"]].join(f[s].shift(1).rename("xl")).dropna()
                    bl, tl = nw_slope(d2["xl"].to_numpy(), d2[f"y{h}"].to_numpy(), h)
                    row = {"asset": a, "signal": s, "h": h, "period": period, "n": len(x),
                           "b_bps": round(b * 1e4, 2), "t_nw": round(t, 2), "p_nw": norm_p2(t),
                           "t_nonoverlap": round(tn, 2), "n_nonoverlap": len(xn),
                           "t_rank": round(tr, 2), "t_clip3": round(tc, 2), "t_lag1h": round(tl, 2),
                           "uncond_bps": round(y.mean() * 1e4, 1)}
                    if a == "eth":
                        yx = y - d[f"yb{h}"].to_numpy()
                        bx, tx = nw_slope(x, yx, h)
                        row.update({"b_ethbtc_bps": round(bx * 1e4, 2), "t_ethbtc": round(tx, 2)})
                    if n_placebo:
                        pt = placebo_t(x, y, h, n_placebo)
                        row["p_placebo"] = float(np.mean(np.abs(pt) >= abs(t)))
                        row["placebo_t_sd"] = round(float(pt.std()), 2)
                    out["rows"].append(row)
                    print(a, s, h, period, row["n"], row["b_bps"], row["t_nw"], row.get("p_placebo"), flush=True)
    rows = pd.DataFrame(out["rows"])
    for period in ["IS", "OOS"]:
        mm = (rows.period == period) & rows.asset.isin(["btc", "eth"])
        rows.loc[mm, "p_holm"] = holm(rows.loc[mm, "p_nw"].to_numpy())
    out["rows"] = json.loads(rows.to_json(orient="records"))

    # quintiles of L (descriptive, period-specific cutoffs)
    q = {}
    for a in ["btc", "eth"]:
        f = panel(a)
        for h in [24, 72]:
            for period in ["IS", "OOS"]:
                m = period_mask(f, period, h)
                d = f.loc[m, ["L", f"y{h}"]].dropna()
                d["q"] = pd.qcut(d["L"], 5, labels=False) + 1
                g = d.groupby("q")[f"y{h}"].mean().mul(1e4).round(1)
                sub = d[d.q.isin([1, 5])]
                b, t = nw_slope((sub.q == 5).astype(float).to_numpy(), sub[f"y{h}"].to_numpy(), h)
                q[f"{a}_h{h}_{period}"] = {"quintile_mean_bps": g.to_dict(), "uncond_bps": round(d[f"y{h}"].mean() * 1e4, 1),
                                           "Q5_minus_Q1_bps": round(b * 1e4, 1), "t_nw": round(t, 2)}
    out["quintiles_L"] = q

    # H3: control for past returns
    h3 = []
    for a in ["btc", "eth"]:
        f = panel(a)
        for h in [24, 72]:
            for period in ["IS", "OOS"]:
                m = period_mask(f, period, h)
                d = f.loc[m, ["L", "past24", "past168", f"y{h}"]].dropna()
                b, t = nw_ols(d[f"y{h}"].to_numpy(), d[["L", "past24", "past168"]].to_numpy(), h)
                h3.append({"asset": a, "h": h, "period": period, "b_L_bps": round(b[1] * 1e4, 2), "t_L": round(t[1], 2),
                           "b_past24": round(b[2], 4), "t_past24": round(t[2], 2),
                           "b_past168": round(b[3], 4), "t_past168": round(t[3], 2)})
    out["H3_controls"] = h3

    # contemporaneous relation (explains the past): premium vs same-hour and past-24h return
    cont = []
    for a in ["btc", "eth"]:
        f = panel(a)
        for period in ["IS", "OOS"]:
            m = period_mask(f, period, 4)
            d = f.loc[m, ["prem", "r1", "P24", "past24", "L"]].dropna()
            cont.append({"asset": a, "period": period,
                         "corr_prem_vs_same_hour_ret": round(d.prem.corr(d.r1), 3),
                         "corr_P24_vs_past24h_ret": round(d.P24.corr(d.past24), 3),
                         "corr_L_vs_past24h_ret": round(d.L.corr(d.past24), 3)})
    out["contemporaneous"] = cont
    with open(os.path.join(RES, "coinbase_premium_tests.json"), "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    rows.to_csv(os.path.join(RES, "coinbase_premium_tests.csv"), index=False)
    return out


# ----------------------------------------------------------------- H4 weekly

def run_weekly():
    out = []
    for a in ["btc", "eth"]:
        f = panel(a)
        # Monday 00:00 UTC anchors: use the row of hour 23:00 Sunday (known at Monday 00:00)
        anchors = f[(f.index.dayofweek == 6) & (f.index.hour == 23)]
        for h, lags in [(168, 0), (336, 1), (720, 4)]:
            for period in ["IS", "OOS"]:
                m = period_mask(anchors, period, h) if f"end{h}" in anchors else None
                d = anchors.loc[m, ["W", f"y{h}"]].dropna()
                b, t = nw_slope(d["W"].to_numpy(), d[f"y{h}"].to_numpy(), lags)
                pt = []
                x, y = d["W"].to_numpy(), d[f"y{h}"].to_numpy()
                for _ in range(1000):
                    k = int(RNG.integers(4, len(x) - 4))
                    pt.append(nw_slope(np.roll(x, k), y, lags)[1])
                out.append({"asset": a, "h_hours": h, "period": period, "n_weeks": len(d), "b_bps": round(b * 1e4, 1),
                            "t_nw": round(t, 2), "p_placebo": float(np.mean(np.abs(pt) >= abs(t)))})
                print(out[-1], flush=True)
    with open(os.path.join(RES, "coinbase_premium_weekly.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    return out


# ----------------------------------------------------------------- H5 / H6 ETF

def run_etf():
    res = {"H5_nowcast": [], "H6_combo": []}
    p = load_table()
    for a in ["btc", "eth"]:
        f = features(p, a)
        lp = np.log(p[f"bnf_{a}"])
        flows = etf_daily(a)
        us = f[(f.index.hour >= 14) & (f.index.hour <= 19)]
        day = us.groupby(us.index.normalize()).agg(prem_us=("prem", "mean"))
        raw_us = p.loc[us.index, f"prem_raw_{a}"]
        day["prem_raw_us"] = raw_us.groupby(raw_us.index.normalize()).mean()
        # same-day US-session return 14:00->20:00 UTC close
        r = (lp.shift(-6) - lp)[(lp.index.hour == 13)]
        r.index = r.index.normalize()
        day["ret_us"] = r
        day["ret_day"] = (lp.shift(-24) - lp)[lp.index.hour == 23].rename(lambda x: (x + pd.Timedelta(hours=1)).normalize())
        d = day.join(flows.rename("flow"), how="inner").dropna()
        d["flow_next"] = d["flow"].shift(-1)
        for period, mm in [("IS", d.index < IS_END), ("OOS", d.index >= IS_END), ("ALL", d.index == d.index)]:
            x = d[mm]
            if len(x) < 30:
                continue
            fz = x["flow"] / 1e6
            b1, t1 = nw_slope(x["prem_us"].to_numpy() * 1e4, fz.to_numpy(), 5)
            bm, tm = nw_ols(fz.to_numpy(), np.column_stack([x["prem_us"] * 1e4, x["ret_us"] * 100, x["ret_day"] * 100]), 5)
            xn = x.dropna(subset=["flow_next"])
            bn, tn = nw_ols((xn["flow_next"] / 1e6).to_numpy(),
                            np.column_stack([xn["prem_us"] * 1e4, xn["flow"] / 1e6, xn["ret_day"] * 100]), 5)
            res["H5_nowcast"].append({
                "asset": a, "period": period, "n_days": len(x),
                "corr_prem_us_vs_flow": round(x["prem_us"].corr(x["flow"]), 3),
                "spearman_prem_us_vs_flow": round(x["prem_us"].rank().corr(x["flow"].rank()), 3),
                "corr_prem_raw_us_vs_flow": round(x["prem_raw_us"].corr(x["flow"]), 3),
                "corr_ret_us_vs_flow": round(x["ret_us"].corr(x["flow"]), 3),
                "flow_musd_per_bp_prem": round(b1, 1), "t_simple": round(t1, 2),
                "partial_t_prem_ctrl_ret": round(tm[1], 2), "partial_b_prem_musd_per_bp": round(bm[1], 1),
                "t_ret_us": round(tm[2], 2), "t_ret_day": round(tm[3], 2),
                "next_day_flow_t_prem": round(tn[1], 2), "next_day_flow_t_flow": round(tn[2], 2)})
            print(res["H5_nowcast"][-1], flush=True)

        # H6: daily decision at 00:00 UTC using the row of hour 23:00 (known at 00:00)
        g = f[f.index.hour == 23].copy()
        g.index = g.index + pd.Timedelta(hours=1)
        for h in [24, 72]:
            g[f"y{h}"] = (lp.shift(-h) - lp).reindex(g.index - pd.Timedelta(hours=1)).to_numpy()
        # last flow known at 00:00 of day X: flow of day <= X-2
        fl = flows.copy()
        fl.index = fl.index + pd.Timedelta(days=2)
        g["flow_known"] = fl.reindex(g.index, method="ffill")
        g = g.dropna(subset=["flow_known", "P24"])
        for h in [24, 72]:
            for period, mm in [("IS", g.index + pd.Timedelta(hours=h) <= IS_END),
                               ("OOS", (g.index >= IS_END) & (g.index + pd.Timedelta(hours=h) <= END))]:
                x = g[mm].dropna(subset=[f"y{h}"])
                y = x[f"y{h}"]
                conds = {"both": (x.P24 > 0) & (x.flow_known > 0), "prem_only": x.P24 > 0,
                         "flow_only": x.flow_known > 0, "neither": (x.P24 <= 0) & (x.flow_known <= 0)}
                row = {"asset": a, "h": h, "period": period, "n_days": len(x), "uncond_bps": round(y.mean() * 1e4, 1)}
                lags = max(0, h // 24 - 1)
                for k, c in conds.items():
                    if c.sum() < 5:
                        continue
                    b, t = nw_slope(c.astype(float).to_numpy(), y.to_numpy(), lags)
                    row[f"{k}_n"] = int(c.sum())
                    row[f"{k}_mean_bps"] = round(y[c].mean() * 1e4, 1)
                    row[f"{k}_diff_vs_rest_bps"] = round(b * 1e4, 1)
                    row[f"{k}_t"] = round(t, 2)
                res["H6_combo"].append(row)
                print(row, flush=True)
    with open(os.path.join(RES, "coinbase_premium_etf.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=str)
    return res


# ----------------------------------------------------------------- H7 treasury

def run_treasury(n_placebo=2000):
    ev = pd.read_csv(os.path.join(HERE, "research", "treasury_flows_events.csv"))
    ev = ev[ev.event_type == "purchase"].copy()
    ev["ts"] = pd.to_datetime(ev["ann_ts_utc"], utc=True)
    p = load_table()
    out = []
    groups = {"MSTR_btc": (ev.company.str.startswith("Strategy"), "btc"),
              "BMNR_eth": (ev.company.str.startswith("BitMine"), "eth"),
              "SBET_eth": (ev.company.str.startswith("SharpLink"), "eth"),
              "ETHtreas_eth": (ev.asset == "ETH", "eth")}
    for name, (mask, a) in groups.items():
        e = ev[mask & (ev.ts < END)]
        prem = p[f"prem_{a}"]
        # 120h mean premium strictly before publication (hours whose close <= ts)
        pre = prem.rolling(120, min_periods=90).mean()
        pre_known = pre.copy()
        pre_known.index = pre_known.index + pd.Timedelta(hours=1)  # value known at ts+1h
        dates = e.ts.dt.floor("h")
        dates = dates[(dates > prem.index[0] + pd.Timedelta(days=10))].drop_duplicates()
        vals = pre_known.reindex(dates).dropna()
        span = pre_known.dropna()
        span = span[(span.index >= vals.index.min()) & (span.index <= vals.index.max())]
        base = span.mean()
        obs = vals.mean() - base
        # placebo: circularly shift the whole date set inside the span (keeps spacing)
        L = (span.index[-1] - span.index[0]).total_seconds() / 3600
        pl = []
        for _ in range(n_placebo):
            k = pd.Timedelta(hours=int(RNG.integers(24 * 7, int(L) - 24 * 7)))
            sh = span.index[0] + ((vals.index - span.index[0] + k) % pd.Timedelta(hours=int(L)))
            pl.append(span.reindex(sh.floor("h")).mean() - base)
        pl = np.array(pl)
        pl = pl[~np.isnan(pl)]
        # size relation (explains the past): premium vs USD size
        es = e.assign(h=e.ts.dt.floor("h")).drop_duplicates("h").set_index("h")
        es["pre"] = pre_known.reindex(es.index)
        es = es.dropna(subset=["pre", "usd"])
        rho = es["pre"].rank().corr(es["usd"].rank()) if len(es) > 5 else float("nan")
        out.append({"group": name, "asset": a, "n_events": len(vals), "from": str(vals.index.min()),
                    "to": str(vals.index.max()), "pre120h_mean_bps": round(vals.mean() * 1e4, 2),
                    "baseline_bps": round(base * 1e4, 2), "diff_bps": round(obs * 1e4, 2),
                    "placebo_p_one_sided": float(np.mean(pl >= obs)), "placebo_sd_bps": round(pl.std() * 1e4, 2),
                    "spearman_pre_vs_usd_size": round(rho, 3)})
        print(out[-1], flush=True)
    with open(os.path.join(RES, "coinbase_premium_treasury.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    return out


# ----------------------------------------------------------------- context table

def run_context():
    p = load_table()
    rows = []
    fb, fe = etf_daily("btc"), etf_daily("eth")
    for a in ["btc", "eth"]:
        m = pd.DataFrame({"prem_bps": p[f"prem_{a}"] * 1e4, "prem_raw_bps": p[f"prem_raw_{a}"] * 1e4,
                          "usdt_dev_bps": (p["usdt"] - 1) * 1e4})
        mm = m.resample("MS").mean()
        px = p[f"bnf_{a}"].resample("MS").last()
        mm["ret_pct"] = (px / px.shift(1) - 1) * 100
        mm["next_ret_pct"] = mm["ret_pct"].shift(-1)
        fl = (fb if a == "btc" else fe).resample("MS").sum() / 1e9
        mm["etf_flow_bn"] = fl
        mm["share_hours_pos"] = (p[f"prem_{a}"] > 0).resample("MS").mean()
        mm["asset"] = a
        rows.append(mm)
    t = pd.concat(rows)
    t.index = t.index.strftime("%Y-%m")
    t.round(3).to_csv(os.path.join(RES, "coinbase_premium_monthly.csv"))
    corr = {}
    for a in ["btc", "eth"]:
        x = t[t.asset == a].dropna(subset=["prem_bps", "ret_pct"])
        corr[a] = {"corr_month_prem_vs_same_month_ret": round(x.prem_bps.corr(x.ret_pct), 3),
                   "corr_month_prem_vs_next_month_ret": round(x.prem_bps.corr(x.next_ret_pct), 3),
                   "corr_month_prem_vs_etf_flow": round(x.prem_bps.corr(x.etf_flow_bn), 3),
                   "corr_month_raw_vs_same_month_ret": round(x.prem_raw_bps.corr(x.ret_pct), 3),
                   "corr_month_raw_vs_next_month_ret": round(x.prem_raw_bps.corr(x.next_ret_pct), 3),
                   "n_months": len(x)}
    print(json.dumps(corr, indent=1))
    with open(os.path.join(RES, "coinbase_premium_monthly_corr.json"), "w") as fh:
        json.dump(corr, fh, indent=1)
    return t, corr




# ----------------------------------------------------------------- post-hoc (labelled, not pre-registered)

def run_posthoc():
    """POST-HOC robustness, decided after seeing run_tests(): yearly stability, USDC-depeg exclusion,
    pooled BTC+ETH (equal-weight) regression."""
    out = {"yearly": [], "ex_usdc_depeg": [], "pooled": []}
    fb, fe = panel("btc"), panel("eth")
    for a, f in [("btc", fb), ("eth", fe)]:
        for s in ["L", "U", "P"]:
            for yr in [2023, 2024, 2025, 2026]:
                h = 24
                m = (f.index.year == yr) & (f[f"end{h}"] <= END)
                d = f.loc[m, [s, f"y{h}"]].dropna()
                b, t = nw_slope(d[s].to_numpy(), d[f"y{h}"].to_numpy(), h)
                out["yearly"].append({"asset": a, "signal": s, "year": yr, "h": h, "n": len(d),
                                      "b_bps": round(b * 1e4, 2), "t_nw": round(t, 2)})
        # exclude 2023-03-01..2023-03-31 (USDC depeg, USDT-USD up to +150 bps)
        for s in ["R", "U", "L"]:
            for h in [24, 72]:
                m = period_mask(f, "IS", h) & ~((f.index >= pd.Timestamp("2023-03-01", tz="UTC")) &
                                                 (f.index < pd.Timestamp("2023-04-01", tz="UTC")))
                d = f.loc[m, [s, f"y{h}"]].dropna()
                b, t = nw_slope(d[s].to_numpy(), d[f"y{h}"].to_numpy(), h)
                out["ex_usdc_depeg"].append({"asset": a, "signal": s, "h": h, "period": "IS ex 2023-03",
                                             "b_bps": round(b * 1e4, 2), "t_nw": round(t, 2)})
    for s in ["L", "U", "P"]:
        for h in [4, 24, 72]:
            for period in ["IS", "OOS"]:
                m = period_mask(fb, period, h)
                x = ((fb[s] + fe[s]) / 2)[m]
                y = ((fb[f"y{h}"] + fe[f"y{h}"]) / 2)[m]
                d = pd.concat([x.rename("x"), y.rename("y")], axis=1).dropna()
                b, t = nw_slope(d.x.to_numpy(), d.y.to_numpy(), h)
                pt = placebo_t(d.x.to_numpy(), d.y.to_numpy(), h, 300)
                out["pooled"].append({"signal": s, "h": h, "period": period, "n": len(d), "b_bps": round(b * 1e4, 2),
                                      "t_nw": round(t, 2), "p_placebo": float(np.mean(np.abs(pt) >= abs(t)))})
                print(out["pooled"][-1], flush=True)
    with open(os.path.join(RES, "coinbase_premium_posthoc.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "tests"
    {"tests": run_tests, "weekly": run_weekly, "etf": run_etf, "treasury": run_treasury,
     "context": run_context, "posthoc": run_posthoc}[cmd]()
