"""macro_events: intraday event study of scheduled macro releases on Binance USD-M perps (5m).

Pre-registration: trading/research/macro_events_prereg.md (H1-H5).
Unit = event. Returns are log returns between bar OPEN prices (open of the 5m bar starting at t is the
price at t). Release times are at :00/:30, so t0 is always a bar open: nothing after t0 leaks into "pre".

Baseline for every event: pseudo-events at the same New York wall-clock time on weekdays within +-60 days
that have no scheduled release (CPI/NFP/PPI/PCE/FOMC/minutes) on the same NY date.
Placebo: 2000 draws, one random baseline day per event -> distribution of the cross-event statistic.

    python3 -m strategies.macro_events_study      (from trading/)
"""
import json
import math
import os

import numpy as np
import pandas as pd

from bt.data import SYMBOLS, load

HERE = os.path.dirname(os.path.abspath(__file__))
TRADING = os.path.dirname(HERE)
EV = os.path.join(TRADING, "research", "macro_events_events.csv")
RES = os.path.join(TRADING, "results")
ET = "America/New_York"
HIGH = ["CPI", "NFP", "FOMC_STATEMENT", "PCE", "PPI", "FOMC_MINUTES", "FED_SPEECH"]
SCHED_DAYS_CATS = ["CPI", "NFP", "PPI", "PCE", "FOMC_STATEMENT", "FOMC_MINUTES", "FED_SPEECH"]
WINDOWS = {  # minutes relative to t0
    "pre24h": (-1440, 0), "pre4h": (-240, 0), "pre1h": (-60, 0), "pre15": (-15, 0),
    "r5": (0, 5), "r15": (0, 15), "r30": (0, 30), "r60": (0, 60),
    "post15_60": (15, 60), "post15_240": (15, 240), "post15_1440": (15, 1440),
    "post60_1440": (60, 1440), "d1": (0, 1440), "fomc_stmt": (0, 30), "fomc_pres": (30, 90),
}
RNG = np.random.default_rng(20260927)
N_PLACEBO = 2000


# ------------------------------------------------------------------ data
def price_panel(symbols=SYMBOLS):
    """Open prices on a common 5m grid (UTC) -> DataFrame [time x symbol]."""
    cols = {}
    for s in symbols:
        df = load(s, "5m")
        cols[s] = df["open"]
    P = pd.DataFrame(cols)
    return P


def lr(P, t_a, t_b):
    """log return between open prices at t_a and t_b (vectorised over symbols); NaN if missing."""
    try:
        return np.log(P.loc[t_b].to_numpy(float) / P.loc[t_a].to_numpy(float))
    except KeyError:
        return np.full(P.shape[1], np.nan)


def placebo_mean_draws(bases, n=N_PLACEBO):
    """bases: list of 1-d arrays (baseline values per event). One random draw per event, n times;
    returns the n cross-event means."""
    M = np.empty((len(bases), n))
    for i, b in enumerate(bases):
        b = np.asarray(b, float)
        b = b[~np.isnan(b)]
        M[i] = b[RNG.integers(len(b), size=n)] if len(b) else np.nan
    return np.nanmean(M, axis=0)


def nw_t(x, lags=3):
    """Newey-West t-stat of the mean of a time-ordered series."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 5:
        return float("nan")
    e = x - x.mean()
    s = (e @ e) / n
    for L in range(1, min(lags, n - 1) + 1):
        w = 1 - L / (lags + 1)
        s += 2 * w * (e[L:] @ e[:-L]) / n
    return float(x.mean() / math.sqrt(s / n)) if s > 0 else float("nan")


def ols_hac(y, x, lags=3):
    """y = a + b x; returns b, t_b (Newey-West), n, r2."""
    y, x = np.asarray(y, float), np.asarray(x, float)
    m = ~(np.isnan(y) | np.isnan(x))
    y, x = y[m], x[m]
    n = len(y)
    if n < 8:
        return dict(b=None, t=None, n=n)
    X = np.column_stack([np.ones(n), x])
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ y
    u = y - X @ b
    S = (X * u[:, None]).T @ (X * u[:, None]) / n
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1)
        G = (X[L:] * u[L:, None]).T @ (X[:-L] * u[:-L, None]) / n
        S += w * (G + G.T)
    V = n * XtX_inv @ S @ XtX_inv
    r2 = 1 - (u @ u) / ((y - y.mean()) @ (y - y.mean()))
    return dict(b=float(b[1]), t=float(b[1] / math.sqrt(V[1, 1])), n=int(n), r2=round(float(r2), 3))


# ------------------------------------------------------------------ core
def event_days(ev):
    d = pd.to_datetime(ev.loc[ev["category"].isin(SCHED_DAYS_CATS), "t_publish_utc"], utc=True)
    return set(d.dt.tz_convert(ET).dt.date)


def baseline_times(t0, busy, P_index, span_days=60):
    """Same NY wall-clock time on weekdays within +-span_days, no scheduled release that NY date."""
    loc = t0.tz_convert(ET)
    out = []
    for k in range(-span_days, span_days + 1):
        if k == 0:
            continue
        d = (loc + pd.Timedelta(days=k))
        # rebuild the same wall-clock time on that date (handles DST)
        dl = pd.Timestamp(d.date()).replace(hour=loc.hour, minute=loc.minute).tz_localize(ET)
        if dl.weekday() >= 5 or dl.date() in busy:
            continue
        tu = dl.tz_convert("UTC")
        if tu - pd.Timedelta(days=1) < P_index[0] or tu + pd.Timedelta(days=1) > P_index[-1]:
            continue
        out.append(tu)
    return out


_CACHE = {}


def compute_returns(P, times):
    """dict window -> array [n_times x n_sym]"""
    if "V" not in _CACHE or _CACHE["id"] is not P:
        _CACHE.update(V=P.to_numpy(float), id=P)
    V = _CACHE["V"]
    times = pd.DatetimeIndex(times)
    out = {}
    for w, (a, b) in WINDOWS.items():
        ia = P.index.get_indexer(times + pd.Timedelta(minutes=a))
        ib = P.index.get_indexer(times + pd.Timedelta(minutes=b))
        r = np.log(V[ib] / V[ia])
        r[(ia < 0) | (ib < 0)] = np.nan
        out[w] = r
    return out


def run():
    ev = pd.read_csv(EV)
    ev["t0"] = pd.to_datetime(ev["t_publish_utc"], utc=True)
    P = price_panel()
    syms = list(P.columns)
    busy = event_days(ev)
    sched = ev[ev["category"].isin(HIGH + ["FOMC_PRESSER"])].copy()
    sched = sched[(sched["t0"] >= P.index[0] + pd.Timedelta(days=1)) &
                  (sched["t0"] <= P.index[-1] - pd.Timedelta(days=1))].reset_index(drop=True)

    rows = []  # per event x symbol x window (actual + baseline mean/abs)
    base_store = {}
    for i, r in sched.iterrows():
        t0 = r["t0"]
        act = compute_returns(P, [t0])
        bts = baseline_times(t0, busy, P.index)
        base = compute_returns(P, bts)
        base_store[r["event_id"]] = base
        for w in WINDOWS:
            a = act[w][0]
            bm = np.nanmean(base[w], axis=0)
            ba = np.nanmean(np.abs(base[w]), axis=0)
            for j, s in enumerate(syms):
                rows.append(dict(event_id=r["event_id"], category=r["category"], t0=t0, sym=s, window=w,
                                 r=a[j], base_mean=bm[j], base_abs=ba[j], n_base=len(bts)))
    long = pd.DataFrame(rows)
    return ev, sched, long, base_store, syms


def placebo_p(stat_actual, draws):
    draws = np.asarray(draws)
    return float((np.sum(draws >= stat_actual) + 1) / (len(draws) + 1))


def analyse(ev, sched, long, base_store, syms):
    out = {"n_events": sched.groupby("category").size().to_dict(), "symbols": syms}
    sched = sched.set_index("event_id")
    L = long.copy()
    L["year_split"] = np.where(L["t0"] < pd.Timestamp("2025-01-01", tz="UTC"), "IS_2023_24", "OOS_2025_26")
    alts = [s for s in syms if s not in ("BTCUSDT", "ETHUSDT")]

    # ---------- H1: volatility expansion (abs return ratio vs baseline, placebo p)
    vol = []
    for cat in ["CPI", "NFP", "FOMC_STATEMENT", "FOMC_PRESSER", "PCE", "PPI", "FOMC_MINUTES", "FED_SPEECH"]:
        ids = sched.index[sched["category"] == cat]
        for w in ["r5", "r15", "r30", "r60", "fomc_pres"] if cat == "FOMC_STATEMENT" else ["r5", "r15", "r30", "r60"]:
            for grp, gs in [("BTC", ["BTCUSDT"]), ("ETH", ["ETHUSDT"]), ("ALTS8", alts)]:
                sub = L[(L["event_id"].isin(ids)) & (L["window"] == w) & (L["sym"].isin(gs))]
                if sub.empty:
                    continue
                ev_abs = sub.groupby("event_id")["r"].apply(lambda x: np.nanmean(np.abs(x)))
                ev_base = sub.groupby("event_id")["base_abs"].mean()
                ratio = float(ev_abs.mean() / ev_base.mean())
                # placebo: one random baseline day per event
                gi = [syms.index(s) for s in gs]
                bases = [np.nanmean(np.abs(base_store[e][w][:, gi]), axis=1) for e in ev_abs.index]
                p = placebo_p(ev_abs.mean(), placebo_mean_draws(bases))
                vol.append(dict(category=cat, window=w, group=grp, n=int(len(ev_abs)),
                                mean_abs_event_bp=round(1e4 * ev_abs.mean(), 1),
                                mean_abs_base_bp=round(1e4 * ev_base.mean(), 1), ratio=round(ratio, 2),
                                placebo_p=round(p, 4)))
    out["H1_vol"] = vol

    # ---------- H4 / drift: signed abnormal returns per window (event - baseline mean), NW t, placebo p
    drift = []
    for cat in ["CPI", "NFP", "FOMC_STATEMENT", "PCE", "PPI", "FOMC_MINUTES"]:
        ids = sched.index[sched["category"] == cat]
        for w in ["pre24h", "pre4h", "pre1h", "r15", "r60", "post15_240", "post15_1440", "d1"]:
            for grp, gs in [("BTC", ["BTCUSDT"]), ("ETH", ["ETHUSDT"]), ("ALL10", syms)]:
                sub = L[(L["event_id"].isin(ids)) & (L["window"] == w) & (L["sym"].isin(gs))]
                e = sub.groupby("event_id").agg(r=("r", "mean"), b=("base_mean", "mean"), t0=("t0", "first"))
                e = e.sort_values("t0")
                ab = (e["r"] - e["b"]).to_numpy()
                gi = [syms.index(s) for s in gs]
                bases = [np.nanmean(base_store[x][w][:, gi], axis=1) - np.nanmean(base_store[x][w][:, gi])
                         for x in e.index]
                draws = placebo_mean_draws(bases)
                p2 = float((np.sum(np.abs(draws) >= abs(np.nanmean(ab))) + 1) / (len(draws) + 1))
                is_m = e["t0"] < pd.Timestamp("2025-01-01", tz="UTC")
                drift.append(dict(category=cat, window=w, group=grp, n=int(len(e)),
                                  mean_abn_bp=round(1e4 * np.nanmean(ab), 1), nw_t=round(nw_t(ab), 2),
                                  hit_pos=round(float(np.mean(ab > 0)), 2), placebo_p_2s=round(p2, 4),
                                  IS_mean_bp=round(1e4 * np.nanmean(ab[is_m.to_numpy()]), 1),
                                  OOS_mean_bp=round(1e4 * np.nanmean(ab[~is_m.to_numpy()]), 1)))
    out["H4_drift"] = drift

    # ---------- H3: continuation / reversal of the first 15 minutes (and first 5)
    cont = []
    for cat_set_name, cats in [("CPI", ["CPI"]), ("NFP", ["NFP"]), ("FOMC", ["FOMC_STATEMENT"]),
                               ("PCE", ["PCE"]), ("PPI", ["PPI"]), ("HIGH3", ["CPI", "NFP", "FOMC_STATEMENT"])]:
        ids = sched.index[sched["category"].isin(cats)]
        for first in ["r5", "r15"]:
            fw = WINDOWS[first][1]
            for post in ["post15_60", "post15_240", "post15_1440"]:
                for grp, gs in [("BTC", ["BTCUSDT"]), ("ETH", ["ETHUSDT"]), ("ALL10", syms)]:
                    gi = [syms.index(s) for s in gs]
                    x = L[(L["event_id"].isin(ids)) & (L["window"] == first) & (L["sym"].isin(gs))]
                    y = L[(L["event_id"].isin(ids)) & (L["window"] == post) & (L["sym"].isin(gs))]
                    m = x.merge(y, on=["event_id", "sym"], suffixes=("_x", "_y")).sort_values("t0_x")
                    m["f"] = np.sign(m["r_x"]) * m["r_y"]  # follow-the-first-move P&L (gross, log)
                    e = m.groupby("event_id").agg(f=("f", "mean"), t0=("t0_x", "first")).sort_values("t0")
                    # baseline: same statistic on pseudo-events
                    bstat = []
                    for x_id in e.index:
                        B = base_store[x_id]
                        bf = np.nanmean(np.sign(B[first][:, gi]) * B[post][:, gi], axis=1)
                        bstat.append(bf)
                    base_mean = float(np.mean([np.nanmean(b) for b in bstat]))
                    draws = placebo_mean_draws(bstat)
                    fm = float(e["f"].mean())
                    p2 = float((np.sum(np.abs(draws - base_mean) >= abs(fm - base_mean)) + 1) / (len(draws) + 1))
                    is_m = (e["t0"] < pd.Timestamp("2025-01-01", tz="UTC")).to_numpy()
                    cont.append(dict(events=cat_set_name, first=first, post=post, group=grp, n=int(len(e)),
                                     follow_mean_bp=round(1e4 * fm, 1), nw_t=round(nw_t(e["f"].to_numpy()), 2),
                                     hit=round(float((e["f"] > 0).mean()), 2),
                                     base_follow_bp=round(1e4 * base_mean, 1), placebo_p_2s=round(p2, 4),
                                     IS_bp=round(1e4 * e["f"][is_m].mean(), 1),
                                     OOS_bp=round(1e4 * e["f"][~is_m].mean(), 1)))
    out["H3_continuation"] = cont

    # ---------- FOMC: statement move vs press-conference move
    ids = sched.index[sched["category"] == "FOMC_STATEMENT"]
    fo = []
    for grp, gs in [("BTC", ["BTCUSDT"]), ("ETH", ["ETHUSDT"]), ("ALL10", syms)]:
        x = L[(L["event_id"].isin(ids)) & (L["window"] == "fomc_stmt") & (L["sym"].isin(gs))].groupby("event_id")["r"].mean()
        y = L[(L["event_id"].isin(ids)) & (L["window"] == "fomc_pres") & (L["sym"].isin(gs))].groupby("event_id")["r"].mean()
        z = L[(L["event_id"].isin(ids)) & (L["window"] == "post60_1440") & (L["sym"].isin(gs))].groupby("event_id")["r"].mean()
        fo.append(dict(group=grp, n=int(len(x)), corr_stmt_pres=round(float(np.corrcoef(x, y)[0, 1]), 2),
                       follow_pres_bp=round(1e4 * float(np.mean(np.sign(x) * y)), 1),
                       nw_t=round(nw_t((np.sign(x) * y).to_numpy()), 2),
                       follow_next23h_bp=round(1e4 * float(np.mean(np.sign(x + y) * z)), 1),
                       nw_t_23h=round(nw_t((np.sign(x + y) * z).to_numpy()), 2)))
    out["FOMC_stmt_vs_presser"] = fo

    # ---------- H2: direction vs surprise
    sur = []
    cpi = sched[sched["category"] == "CPI"]
    for w in ["r5", "r15", "r60", "d1"]:
        for grp, gs in [("BTC", ["BTCUSDT"]), ("ETH", ["ETHUSDT"]), ("ALL10", syms)]:
            y = L[(L["event_id"].isin(cpi.index)) & (L["window"] == w) & (L["sym"].isin(gs))].groupby("event_id")["r"].mean()
            dd = cpi.join(y.rename("y"), how="inner").sort_values("t0")
            for xname in ["core_surprise_nowcast", "dgs2_change_bp"]:
                res = ols_hac(1e4 * dd["y"].to_numpy(), pd.to_numeric(dd[xname], errors="coerce").to_numpy())
                sur.append(dict(events="CPI", window=w, group=grp, x=xname, **res))
    for cat in ["FOMC_STATEMENT", "NFP"]:
        e = sched[sched["category"] == cat]
        for w in ["r15", "r60", "d1"]:
            y = L[(L["event_id"].isin(e.index)) & (L["window"] == w) & (L["sym"] == "BTCUSDT")].groupby("event_id")["r"].mean()
            dd = e.join(y.rename("y"), how="inner").sort_values("t0")
            res = ols_hac(1e4 * dd["y"].to_numpy(), pd.to_numeric(dd["dgs2_change_bp"], errors="coerce").to_numpy())
            sur.append(dict(events=cat, window=w, group="BTC", x="dgs2_change_bp", **res))
    out["H2_surprise"] = sur

    # ---------- alt beta on event windows vs baseline (which coins amplify macro shocks)
    beta = []
    for cat in ["CPI", "FOMC_STATEMENT", "NFP"]:
        ids = sched.index[sched["category"] == cat]
        w = "r30"
        sub = L[(L["event_id"].isin(ids)) & (L["window"] == w)].pivot_table(index="event_id", columns="sym", values="r")
        for s in syms:
            if s == "BTCUSDT":
                continue
            x, y = sub["BTCUSDT"].to_numpy(), sub[s].to_numpy()
            bb = np.concatenate([base_store[e][w][:, [syms.index("BTCUSDT"), syms.index(s)]] for e in ids])
            bb = bb[~np.isnan(bb).any(axis=1)]
            beta.append(dict(category=cat, sym=s, beta_event=round(float(np.polyfit(x, y, 1)[0]), 2),
                             beta_base=round(float(np.polyfit(bb[:, 0], bb[:, 1], 1)[0]), 2),
                             corr_event=round(float(np.corrcoef(x, y)[0, 1]), 2)))
    out["alt_beta_r30"] = beta
    return out


def dvol_study(ev, sched):
    """H5: DVOL change into and out of events vs baseline pseudo-events (same NY time)."""
    root = os.path.join(TRADING, "data", "dvol")
    busy = event_days(ev)
    res = []
    for cur in ["BTC", "ETH"]:
        dv = pd.read_parquet(os.path.join(root, f"{cur}.parquet"))
        s = pd.Series(dv["dvol"].to_numpy(), index=pd.to_datetime(dv["ts"], utc=True) + pd.Timedelta(hours=1))
        s = s[~s.index.duplicated()].sort_index()  # value known at candle close

        def at(t):
            i = s.index.searchsorted(t, side="right") - 1
            return s.iloc[i] if i >= 0 else np.nan

        for cat in ["CPI", "FOMC_STATEMENT", "NFP", "PCE"]:
            e = sched[sched["category"] == cat]
            pre, post, bpre, bpost, ts = [], [], [], [], []
            for _, r in e.iterrows():
                t0 = r["t0"]
                if t0 < s.index[0] + pd.Timedelta(days=2):
                    continue
                pre.append(at(t0) - at(t0 - pd.Timedelta(hours=24)))
                post.append(at(t0 + pd.Timedelta(hours=2)) - at(t0))
                bt = baseline_times(t0, busy, s.index)
                bpre.append(np.nanmean([at(b) - at(b - pd.Timedelta(hours=24)) for b in bt]))
                bpost.append(np.nanmean([at(b + pd.Timedelta(hours=2)) - at(b) for b in bt]))
                ts.append(t0)
            pre, post, bpre, bpost = map(np.array, (pre, post, bpre, bpost))
            res.append(dict(cur=cur, category=cat, n=int(len(pre)),
                            pre24h_dvol_pts=round(float(np.nanmean(pre)), 2),
                            base_pre24h=round(float(np.nanmean(bpre)), 2),
                            pre_abn_t=round(nw_t(pre - bpre), 2),
                            post2h_dvol_pts=round(float(np.nanmean(post)), 2),
                            base_post2h=round(float(np.nanmean(bpost)), 2),
                            post_abn_t=round(nw_t(post - bpost), 2)))
    return res


def main():
    ev, sched, long, base_store, syms = run()
    out = analyse(ev, sched, long, base_store, syms)
    out["H5_dvol"] = dvol_study(ev, sched)
    long.to_parquet(os.path.join(TRADING, "data", "ext", "macro_events", "event_returns_long.parquet"))
    with open(os.path.join(RES, "macro_events_study.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)
    for k in ["H1_vol", "H4_drift", "H3_continuation", "FOMC_stmt_vs_presser", "H2_surprise", "alt_beta_r30", "H5_dvol"]:
        print("=====", k)
        print(pd.DataFrame(out[k]).to_string())


if __name__ == "__main__":
    main()
