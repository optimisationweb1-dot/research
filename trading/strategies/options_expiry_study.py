"""options_expiry: event studies H1-H6 (see research/options_expiry_prereg.md).

    cd trading && python3 -m strategies.options_expiry_study     # -> results/options_expiry_study.json

Single process, no pools (shared machine).
"""
import json
import math
import os

import numpy as np
import pandas as pd

from strategies.options_expiry_calendar import load_calendar

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "results", "options_expiry_study.json")
IS_END = pd.Timestamp("2025-01-01", tz="UTC")
END = pd.Timestamp("2026-09-01", tz="UTC")
GRIDS = {"BTC": [1000, 5000], "ETH": [100, 500]}
RNG = np.random.default_rng(20260930)


# ------------------------------------------------------------------ helpers
def load5(sym):
    k = pd.read_parquet(os.path.join(DATA, "klines", "5m", f"{sym}USDT.parquet"), columns=["open_time", "open", "close"])
    k.index = pd.to_datetime(k["open_time"], unit="ms", utc=True)
    return k[["open", "close"]]


def load_dvol(c):
    d = pd.read_parquet(os.path.join(DATA, "dvol", f"{c}.parquet"))
    # hourly candle stamped ts closes at ts+1h: index by time it becomes known
    s = pd.Series(d["dvol"].to_numpy(), index=pd.DatetimeIndex(d["ts"]) + pd.Timedelta(hours=1))
    return s[~s.index.duplicated()].sort_index()


def nw_t(x, lag):
    """Newey-West t-stat of the mean."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 5:
        return None
    e = x - x.mean()
    v = e @ e / n
    for L in range(1, min(lag, n - 1) + 1):
        w = 1 - L / (lag + 1)
        v += 2 * w * (e[L:] @ e[:-L]) / n
    return float(x.mean() / math.sqrt(v / n)) if v > 0 else None


def tstat(x):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if len(x) < 3 or x.std(ddof=1) == 0:
        return None
    return float(x.mean() / x.std(ddof=1) * math.sqrt(len(x)))


def welch(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    if len(a) < 3 or len(b) < 3:
        return None
    return float((a.mean() - b.mean()) / math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b)))


def perm_p(vals, is_treat, n=5000):
    """Two-sided permutation p for mean(treat)-mean(control), labels shuffled among the pool."""
    vals, is_treat = np.asarray(vals, float), np.asarray(is_treat, bool)
    ok = ~np.isnan(vals)
    vals, is_treat = vals[ok], is_treat[ok]
    k = is_treat.sum()
    if k < 3 or (~is_treat).sum() < 3:
        return None
    obs = vals[is_treat].mean() - vals[~is_treat].mean()
    cnt = 0
    for _ in range(n):
        p = RNG.permutation(len(vals))[:k]
        m = np.zeros(len(vals), bool)
        m[p] = True
        cnt += abs(vals[m].mean() - vals[~m].mean()) >= abs(obs)
    return (cnt + 1) / (n + 1)


def r(x, n=4):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), n)


# ------------------------------------------------------------------ per-day expiry table
def day_table(c):
    k = load5(c)
    cal = load_calendar(c)
    cal = cal[(cal["exp"] >= "2023-01-02") & (cal["exp"] < END)]
    lc = np.log(k["close"])
    ret = lc.diff()
    sig24 = ret.rolling(288, min_periods=200).std()  # at bar open t: std incl bar t (use shift at lookup)
    rows = []
    days = pd.date_range("2023-01-02", "2026-08-31", freq="D", tz="UTC")
    cls = dict(zip(cal["date"], cal["cls"]))
    strikes = dict(zip(cal["date"], cal["strikes"]))
    o, cl = k["open"], k["close"]
    idx = k.index

    def at(ts):
        return o.get(ts, np.nan)

    def twap(t0, t1):  # closes of bars opening in [t0, t1)
        s = cl.loc[t0:t1 - pd.Timedelta(minutes=5)]
        return s.mean() if len(s) >= 5 else np.nan

    def rv(t0, t1):
        s = ret.loc[t0 + pd.Timedelta(minutes=5):t1] if False else ret.loc[t0:t1 - pd.Timedelta(minutes=5)]
        # ret at bar open t = log(close_t/close_{t-1}); bars opening in [t0,t1) -> moves ending in (t0, t1]
        return float((s ** 2).sum()) if len(s) >= 20 else np.nan

    for d in days:
        row = {"date": d, "cls": cls.get(d, "N"), "dow": d.dayofweek}
        H = lambda h, m=0: d + pd.Timedelta(hours=h, minutes=m)
        row["rv_pre"] = rv(H(6), H(8))
        row["rv_post"] = rv(H(8), H(10))
        row["rv_0600_0730"] = float((ret.loc[H(6):H(7, 25)] ** 2).sum())
        row["rv_0730_0800"] = float((ret.loc[H(7, 30):H(7, 55)] ** 2).sum())
        row["ret_00_08"] = math.log(at(H(8)) / at(H(0))) if at(H(0)) > 0 else np.nan
        row["ret_08_16"] = math.log(at(H(16)) / at(H(8))) if at(H(8)) > 0 else np.nan
        # pinning windows: (start, settle-twap window)
        for tag, h0 in (("exp", 6), ("p14", 14), ("p20", 20)):
            p0 = at(H(h0))
            ps = twap(H(h0 + 1, 30), H(h0 + 2))
            prev = H(h0) - pd.Timedelta(minutes=5)
            sg = sig24.get(prev, np.nan)
            row[f"p0_{tag}"], row[f"ps_{tag}"] = p0, ps
            row[f"rvw_{tag}"] = rv(H(h0), H(h0 + 2))
            row[f"sig_{tag}"] = sg * math.sqrt(24) * p0 if sg == sg else np.nan
        row["p16"] = at(H(16))
        lst = strikes.get(d, [])
        for G in GRIDS[c]:
            K0 = round(row["p0_exp"] / G) * G if row["p0_exp"] == row["p0_exp"] else np.nan
            row[f"K0_listed_{G}"] = bool(K0 in set(lst)) if lst else False
        rows.append(row)
    t = pd.DataFrame(rows).set_index("date")
    t["fri"] = t["dow"] == 4
    t["mq"] = t["cls"].isin(["M", "Q"])
    t["is"] = t.index < IS_END
    # rolling baseline of pre-window RV (previous 20 days, same clock window)
    t["rv_pre_norm"] = np.log(t["rv_pre"] / t["rv_pre"].shift(1).rolling(20, min_periods=10).median())
    t["lr_post_pre"] = np.log(t["rv_post"] / t["rv_pre"])
    t["lr_settle_win"] = np.log(t["rv_0730_0800"] / (t["rv_0600_0730"] / 3))  # exploratory, post hoc
    for G in GRIDS[c]:
        for tag in ("exp", "p14", "p20"):
            K0 = (t[f"p0_{tag}"] / G).round() * G
            t[f"conv_{tag}_{G}"] = ((t[f"ps_{tag}"] - K0).abs() - (t[f"p0_{tag}"] - K0).abs()) / t[f"sig_{tag}"]
        for tag, h0 in (("exp", 6), ("p14", 14), ("p20", 20)):
            K0 = (t[f"p0_{tag}"] / G).round() * G
            t[f"convrv_{tag}_{G}"] = ((t[f"ps_{tag}"] - K0).abs() - (t[f"p0_{tag}"] - K0).abs()) / (
                t[f"p0_{tag}"] * np.sqrt(t[f"rvw_{tag}"]))
        t[f"convrv_diff_{G}"] = t[f"convrv_exp_{G}"] - t[[f"convrv_p14_{G}", f"convrv_p20_{G}"]].mean(axis=1)
        t[f"conv_plc_{G}"] = t[[f"conv_p14_{G}", f"conv_p20_{G}"]].mean(axis=1)
        t[f"conv_diff_{G}"] = t[f"conv_exp_{G}"] - t[f"conv_plc_{G}"]
        dist = lambda p: (p / G - (p / G).round()).abs()
        t[f"d_settle_{G}"] = dist(t["ps_exp"])
        t[f"d_16_{G}"] = dist(t["p16"])
    return t


def h1(t):
    out = {}
    for per, m in (("ALL", slice(None)), ("IS", t["is"]), ("OOS", ~t["is"])):
        x = t[m] if per != "ALL" else t
        fri = x[x["fri"]]
        res = {}
        for stat in ("lr_post_pre", "rv_pre_norm", "lr_settle_win"):
            g = {k: x.loc[x["cls"] == k, stat] for k in ("Q", "M", "W", "D")}
            mq = fri.loc[fri["mq"], stat]
            w = fri.loc[~fri["mq"], stat]
            res[stat] = {"mean": {k: r(v.mean()) for k, v in g.items()},
                         "n": {k: int(v.notna().sum()) for k, v in g.items()},
                         "MQ_minus_W": r(mq.mean() - w.mean()), "welch_t": r(welch(mq, w), 2),
                         "perm_p": r(perm_p(fri[stat].to_numpy(), fri["mq"].to_numpy(), 3000), 4),
                         "W_minus_D": r(g["W"].mean() - g["D"].mean()), "welch_t_W_D": r(welch(g["W"], g["D"]), 2),
                         "D_mon_thu_mean": r(x.loc[(x["cls"] == "D") & (x["dow"] <= 3), stat].mean()),
                         "welch_t_W_vs_D_mon_thu": r(welch(g["W"], x.loc[(x["cls"] == "D") & (x["dow"] <= 3), stat]), 2)}
        # ratio in levels for readability
        res["median_rv_ratio_post_pre"] = {k: r(np.exp(x.loc[x["cls"] == k, "lr_post_pre"].median()), 3)
                                           for k in ("Q", "M", "W", "D")}
        out[per] = res
    return out


def h2(t, c):
    out = {}
    for G in GRIDS[c]:
        gg = {}
        for per, m in (("ALL", np.ones(len(t), bool)), ("IS", t["is"].to_numpy()), ("OOS", ~t["is"].to_numpy())):
            x = t[m]
            res = {}
            for name, sel in (("MQ", x["mq"]), ("W", x["cls"] == "W"), ("D", x["cls"] == "D")):
                y = x[sel]
                res[name] = {"n": int(y[f"conv_exp_{G}"].notna().sum()),
                             "conv_exp": r(y[f"conv_exp_{G}"].mean()), "conv_placebo": r(y[f"conv_plc_{G}"].mean()),
                             "diff": r(y[f"conv_diff_{G}"].mean()), "t_diff": r(tstat(y[f"conv_diff_{G}"]), 2),
                             "d_settle": r(y[f"d_settle_{G}"].mean()), "d_16": r(y[f"d_16_{G}"].mean()),
                             "t_d_settle_vs_d16": r(tstat(y[f"d_settle_{G}"] - y[f"d_16_{G}"]), 2),
                             "share_K0_listed": r(y[f"K0_listed_{G}"].mean(), 3),
                             "convrv_exp": r(y[f"convrv_exp_{G}"].mean()),
                             "convrv_diff": r(y[f"convrv_diff_{G}"].mean()), "t_convrv_diff": r(tstat(y[f"convrv_diff_{G}"]), 2)}
            fri = x[x["fri"]]
            res["MQ_vs_W_conv_exp_welch_t"] = r(welch(fri.loc[fri["mq"], f"conv_exp_{G}"],
                                                      fri.loc[~fri["mq"], f"conv_exp_{G}"]), 2)
            res["MQ_vs_D_same_window_welch_t"] = r(welch(x.loc[x["mq"], f"conv_exp_{G}"],
                                                         x.loc[x["cls"] == "D", f"conv_exp_{G}"]), 2)
            res["MQ_vs_D_convrv_welch_t"] = r(welch(x.loc[x["mq"], f"convrv_exp_{G}"],
                                                    x.loc[x["cls"] == "D", f"convrv_exp_{G}"]), 2)
            gg[per] = res
        out[str(G)] = gg
    return out


def h3(t):
    out = {}
    for per, m in (("IS", t["is"]), ("OOS", ~t["is"])):
        x = t[m]
        out[per] = {k: {"n": int((x["cls"] == k).sum()),
                        "ret_00_08_bps": r(1e4 * x.loc[x["cls"] == k, "ret_00_08"].mean(), 1),
                        "t_00_08": r(tstat(x.loc[x["cls"] == k, "ret_00_08"]), 2),
                        "ret_08_16_bps": r(1e4 * x.loc[x["cls"] == k, "ret_08_16"].mean(), 1),
                        "t_08_16": r(tstat(x.loc[x["cls"] == k, "ret_08_16"]), 2)}
                    for k in ("Q", "M", "W", "D")}
        mq = x.loc[x["mq"], "ret_08_16"]
        w = x.loc[x["cls"] == "W", "ret_08_16"]
        out[per]["MQ_vs_W_08_16_welch_t"] = r(welch(mq, w), 2)
    return out


def h1_profile(c):
    """Mean squared 5m return per 15-min bucket 04:00-12:00, relative to the same bucket on Mon-Thu daily days."""
    k = load5(c)
    ret = np.log(k["close"]).diff()
    cal = load_calendar(c)
    cls = dict(zip(cal["date"], cal["cls"]))
    x = pd.DataFrame({"r2": ret ** 2})
    x = x[(x.index >= "2023-01-02") & (x.index < END)]
    x["date"] = x.index.normalize()
    x["cls"] = x["date"].map(cls).fillna("N")
    x["dow"] = x.index.dayofweek
    x["bucket"] = x.index.hour * 4 + x.index.minute // 15
    x = x[(x.index.hour >= 4) & (x.index.hour < 12)]
    x["grp"] = np.where(x["cls"].isin(["M", "Q"]), "MQ", np.where(x["cls"] == "W", "W",
                        np.where(x["dow"] <= 3, "D_mon_thu", "other")))
    out = {}
    for per, m in (("IS", x.index < IS_END), ("OOS", x.index >= IS_END)):
        y = x[m]
        # per-day bucket RV, then median across days (robust to outlier days)
        dd = y.groupby(["grp", "date", "bucket"])["r2"].sum().reset_index()
        med = dd.groupby(["grp", "bucket"])["r2"].median().unstack(0)
        rel = med.div(med["D_mon_thu"], axis=0)
        rel.index = [f"{b // 4:02d}:{(b % 4) * 15:02d}" for b in rel.index]
        out[per] = {g: {i: r(v, 2) for i, v in rel[g].items()} for g in ("MQ", "W")}
    return out


# ------------------------------------------------------------------ DVOL
def hourly(c):
    k = load5(c)
    h = k["open"].resample("1h").first()  # price at the start of hour
    return h.dropna()


def dvol_frame(c):
    px = hourly(c)
    dv = load_dvol(c).reindex(px.index, method="ffill")  # value known at each hour start
    f = pd.DataFrame({"px": px, "dvol": dv})
    lr = np.log(f["px"]).diff()
    ann = math.sqrt(24 * 365) * 100
    f["rv_past30"] = np.sqrt((lr ** 2).rolling(720).sum() / 720) * ann
    f["rv_fwd30"] = np.sqrt((lr ** 2).rolling(720).sum().shift(-720) / 720) * ann  # research only (future)
    f["d24"] = f["dvol"] - f["dvol"].shift(24)
    f["ret24"] = np.log(f["px"] / f["px"].shift(24))
    for d in (1, 3, 7):
        f[f"fwd{d}"] = np.log(f["px"].shift(-24 * d) / f["px"])  # research only
    return f


def h4(f):
    d = f[f.index.hour == 0].dropna(subset=["dvol", "rv_fwd30"])
    d = d[d.index < END - pd.Timedelta(days=30)]
    out = {}
    for per, m in (("IS", d.index < IS_END), ("OOS", d.index >= IS_END)):
        x = d[m]
        vrp = x["dvol"] - x["rv_fwd30"]
        # forecast regression rv_fwd = a + b*dvol
        b = np.polyfit(x["dvol"], x["rv_fwd30"], 1)
        out[per] = {"n_days": int(len(x)), "mean_dvol": r(x["dvol"].mean(), 2), "mean_rv_fwd30": r(x["rv_fwd30"].mean(), 2),
                    "mean_vrp": r(vrp.mean(), 2), "median_vrp": r(vrp.median(), 2),
                    "share_positive": r((vrp > 0).mean(), 3), "nw_t_lag30": r(nw_t(vrp, 30), 2),
                    "var_ratio_dvol2_over_rv2": r((x["dvol"] ** 2).mean() / (x["rv_fwd30"] ** 2).mean(), 3),
                    "slope_rvfwd_on_dvol": r(b[0], 3), "intercept": r(b[1], 2),
                    "corr_dvol_rvfwd": r(np.corrcoef(x["dvol"], x["rv_fwd30"])[0, 1], 3),
                    "corr_rvpast_rvfwd": r(x[["rv_past30", "rv_fwd30"]].dropna().corr().iloc[0, 1], 3)}
    return out


def spike_events(f, thr, fear=True, gap_days=7):
    cand = f[(f["d24"] >= thr) & ((f["ret24"] < 0) if fear else True)].index
    ev, last = [], None
    for ts in cand:
        if last is None or ts - last >= pd.Timedelta(days=gap_days):
            ev.append(ts)
            last = ts
    return pd.DatetimeIndex(ev)


def h5(f):
    thr = {q: float(f.loc[f.index < IS_END, "d24"].quantile(q)) for q in (0.90, 0.95)}
    out = {"thresholds_IS": {str(k): round(v, 2) for k, v in thr.items()}}
    for q, th in thr.items():
        for fear in (True, False):
            ev = spike_events(f, th, fear)
            key = f"q{int(q * 100)}_{'fear' if fear else 'all'}"
            res = {}
            for per, lo, hi in (("IS", f.index.min(), IS_END), ("OOS", IS_END, END)):
                e = ev[(ev >= lo) & (ev < hi)]
                pool = f[(f.index >= lo) & (f.index < hi)]
                rr = {"n": int(len(e))}
                for d in (1, 3, 7):
                    col = f"fwd{d}"
                    base = pool[col].mean()
                    x = f.loc[e, col].dropna()
                    exc = x - base
                    # placebo: random hours from the same period, same count
                    vals = pool[col].dropna().to_numpy()
                    if len(x) >= 3:
                        pl = np.array([RNG.choice(vals, len(x), replace=False).mean() for _ in range(2000)])
                        p = float(((np.abs(pl - base) >= abs(x.mean() - base)).sum() + 1) / 2001)
                    else:
                        p = None
                    rr[f"fwd{d}_mean_pct"] = r(100 * x.mean(), 2)
                    rr[f"fwd{d}_base_pct"] = r(100 * base, 3)
                    rr[f"fwd{d}_excess_t"] = r(tstat(exc), 2)
                    rr[f"fwd{d}_placebo_p"] = r(p, 4)
                    rr[f"fwd{d}_hit"] = r((x > 0).mean(), 3)
                res[per] = rr
            out[key] = res
    return out


def h6(f):
    d = f[f.index.hour == 0].copy()
    d["ret1"] = np.log(d["px"] / d["px"].shift(1))
    d["ret7"] = np.log(d["px"] / d["px"].shift(7))
    d["next"] = d["ret1"].shift(-1)  # research: next day's return
    d["dv_rank"] = d["dvol"].rolling(365, min_periods=300).apply(lambda s: (s[:-1] < s[-1]).mean(), raw=True)
    d["vrp_past"] = d["dvol"] - d["rv_past30"]
    d["trend"] = np.sign(d["ret7"]) * d["next"]
    d["mr"] = -np.sign(d["ret1"]) * d["next"]
    d = d[d.index < END - pd.Timedelta(days=1)]
    isd = d[d.index < IS_END]
    cuts = {"vrp_past": list(isd["vrp_past"].quantile([1 / 3, 2 / 3])),
            "dvol": list(isd["dvol"].quantile([1 / 3, 2 / 3])),
            "dv_rank": [1 / 3, 2 / 3]}
    out = {"tercile_cuts_IS": {k: [round(v, 3) for v in vv] for k, vv in cuts.items()}}
    for reg, cc in cuts.items():
        d[f"ter_{reg}"] = np.select([d[reg] < cc[0], d[reg] < cc[1], d[reg].notna()], [0, 1, 2], np.nan)
        res = {}
        for per, m in (("IS", d.index < IS_END), ("OOS", d.index >= IS_END)):
            x = d[m]
            rr = {}
            for strat in ("trend", "mr"):
                s = {}
                for ter in (0, 1, 2):
                    y = x.loc[x[f"ter_{reg}"] == ter, strat].dropna()
                    s[f"T{ter}"] = {"n": int(len(y)), "mean_bps": r(1e4 * y.mean(), 1), "t": r(tstat(y), 2)}
                hi = x.loc[x[f"ter_{reg}"] == 2, strat]
                lo = x.loc[x[f"ter_{reg}"] == 0, strat]
                s["hi_minus_lo_bps"] = r(1e4 * (hi.mean() - lo.mean()), 1)
                s["welch_t"] = r(welch(hi, lo), 2)
                s["all_mean_bps"] = r(1e4 * x[strat].mean(), 1)
                rr[strat] = s
            res[per] = rr
        out[reg] = res
    return out


def main():
    res = {}
    for c in ("BTC", "ETH"):
        print("==", c, flush=True)
        t = day_table(c)
        t.to_parquet(os.path.join(DATA, "ext", "options_expiry", f"days_{c}.parquet"))
        f = dvol_frame(c)
        res[c] = {"H1": h1(t), "H1_profile": h1_profile(c), "H2": h2(t, c), "H3": h3(t), "H4": h4(f), "H5": h5(f), "H6": h6(f)}
        print(json.dumps(res[c], indent=1)[:200], flush=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(res, fh, indent=1, default=str)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
