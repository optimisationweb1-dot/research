"""IN-SAMPLE ONLY exploration for the session_time family (data is truncated at 2025-01-01
BEFORE any feature is computed; OOS is never loaded here).

    cd trading && python3 -m strategies.session_time_explore

Event studies in basis points (no stops/targets, no costs) plus engine probes on IS with base
and zero costs. Output: results/session_time_explore_IS.json
"""
import json
import math
import sys

import numpy as np
import pandas as pd

import strategies.session_time as st
from bt.data import SYMBOLS, load
from bt.engine import Costs, IS_END, simulate, summarize

ZERO = Costs(0.0, 0.0, 0.0)


def is_load(sym, tf, **kw):
    df = load(sym, tf, **kw)
    return df[df.index < IS_END]


def tstat(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 3 or x.std(ddof=1) == 0:
        return None
    return round(float(x.mean() / x.std(ddof=1) * math.sqrt(len(x))), 2)


def bps_stats(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return {"n": int(len(x)), "mean_bps": round(float(1e4 * x.mean()), 2) if len(x) else None,
            "t": tstat(x), "hit": round(float((x > 0).mean()), 3) if len(x) else None}


def by_year(ts, x):
    s = pd.Series(np.asarray(x, float), index=pd.DatetimeIndex(ts))
    return {str(y): bps_stats(g.to_numpy()) for y, g in s.groupby(s.index.year)}


# ----------------------------------------------------------------------------- E1 hour of day

def e1_hour_of_day():
    rows = []
    for s in SYMBOLS:
        df = is_load(s, "1h")
        r = np.log(df["close"] / df["open"])
        rows.append(pd.DataFrame({"r": r, "h": df.index.hour, "wk": df.index.dayofweek < 5,
                                  "y": df.index.year, "sym": s}))
    d = pd.concat(rows)
    out = {}
    for (wk, h), g in d.groupby(["wk", "h"]):
        out[f"{'wkday' if wk else 'wkend'}_{h:02d}"] = {"all": bps_stats(g["r"]),
                                                        **{str(y): bps_stats(gg["r"]) for y, gg in g.groupby("y")}}
    return out


# ----------------------------------------------------------------------------- E2 Asia range

def e2_asia(tf="15m"):
    ev = []
    for s in SYMBOLS:
        df = is_load(s, tf)
        tfm = st.tf_minutes(df)
        mod, day, ah, al = st.asia_levels(df)
        o, h, l, c = (df[k] for k in ("open", "high", "low", "close"))
        win = (mod >= 420) & (mod < 960) & ah.notna()
        up, dn = win & (c > ah), win & (c < al)
        first = st.first_in_group(up | dn, day)
        rr = st.range_rank(ah - al, day)
        # exit price: close of the bar that ends at 20:00 UTC, same day
        ex_px = c.where(mod == 1200 - tfm)
        ex_by_day = ex_px.groupby(np.asarray(day)).last()
        nxt_open = o.shift(-1)          # analysis only (entry price = next open)
        for kind, mask, sgn in (("break_up", first & up, 1), ("break_dn", first & dn, -1)):
            idx = np.flatnonzero(mask.to_numpy())
            for i in idx:
                e = nxt_open.iloc[i]
                x = ex_by_day.get(day.iloc[i], np.nan)
                rng = ah.iloc[i] - al.iloc[i]
                ev.append({"sym": s, "t": df.index[i], "kind": kind, "ret": sgn * (x / e - 1),
                           "rng_pct": rng / c.iloc[i], "rr": rr.iloc[i], "hour": df.index[i].hour,
                           "dow": df.index[i].dayofweek})
        # sweep events (fade)
        out_close = win & ((c > ah) | (c < al))
        broke = out_close.astype(int).groupby(np.asarray(day)).cumsum() > 0
        sw_s = win & (h > ah) & (c <= ah) & (c >= al) & ~broke
        sw_l = win & (l < al) & (c >= al) & (c <= ah) & ~broke
        f2 = st.first_in_group(sw_s | sw_l, day)
        for kind, mask, sgn in (("sweep_short", f2 & sw_s & ~sw_l, -1), ("sweep_long", f2 & sw_l & ~sw_s, 1)):
            for i in np.flatnonzero(mask.to_numpy()):
                e = nxt_open.iloc[i]
                x = ex_by_day.get(day.iloc[i], np.nan)
                ev.append({"sym": s, "t": df.index[i], "kind": kind, "ret": sgn * (x / e - 1),
                           "rng_pct": (ah.iloc[i] - al.iloc[i]) / c.iloc[i], "rr": rr.iloc[i],
                           "hour": df.index[i].hour, "dow": df.index[i].dayofweek})
    ev = pd.DataFrame(ev)
    out = {"median_asia_range_pct": round(float(100 * ev["rng_pct"].median()), 3)}
    ev["grp"] = np.where(ev["kind"].str.startswith("break"), "break", "sweep")
    for g, gg in ev.groupby("grp"):
        out[g] = {"all": bps_stats(gg["ret"]), "by_year": by_year(gg["t"], gg["ret"]),
                  "narrow(rr<1)": bps_stats(gg.loc[gg["rr"] < 1, "ret"]),
                  "wide(rr>=1)": bps_stats(gg.loc[gg["rr"] >= 1, "ret"]),
                  "weekday": bps_stats(gg.loc[gg["dow"] < 5, "ret"]),
                  "weekend": bps_stats(gg.loc[gg["dow"] >= 5, "ret"]),
                  "entry<10h": bps_stats(gg.loc[gg["hour"] < 10, "ret"]),
                  "entry>=10h": bps_stats(gg.loc[gg["hour"] >= 10, "ret"]),
                  "by_kind": {k: bps_stats(x["ret"]) for k, x in gg.groupby("kind")},
                  "per_symbol_mean_bps": {k: round(1e4 * x["ret"].mean(), 1) for k, x in gg.groupby("sym")}}
    return out


# ----------------------------------------------------------------------------- E3 US ORB

def e3_orb(tf="5m"):
    out = {}
    for or_min in (15, 30, 60):
        ev = []
        for s in SYMBOLS:
            df = is_load(s, tf)
            tfm = st.tf_minutes(df)
            mod, day, dow = st.local_clock(df, "America/New_York")
            td = st.us_trading_day(day, dow)
            in_or = td & (mod >= 570) & (mod < 570 + or_min)
            orh = st.window_level(df["high"], in_or, day, "max")
            orl = st.window_level(df["low"], in_or, day, "min")
            full = st.window_count(in_or, day) >= or_min // tfm
            c, o = df["close"], df["open"]
            win = td & (mod >= 570 + or_min) & (mod < 720) & full
            up, dn = win & (c > orh), win & (c < orl)
            first = st.first_in_group(up | dn, day)
            ex_by_day = c.where(mod == 960 - tfm).groupby(np.asarray(day)).last()
            # also: OR direction (close of OR vs open at 09:30) -> rest of session
            nxt = o.shift(-1)
            for kind, mask, sgn in (("up", first & up, 1), ("dn", first & dn, -1)):
                for i in np.flatnonzero(mask.to_numpy()):
                    ev.append({"sym": s, "t": df.index[i], "kind": kind,
                               "ret": sgn * (ex_by_day.get(day.iloc[i], np.nan) / nxt.iloc[i] - 1),
                               "orw": (orh.iloc[i] - orl.iloc[i]) / c.iloc[i]})
        ev = pd.DataFrame(ev)
        out[f"or{or_min}"] = {"all": bps_stats(ev["ret"]), "by_year": by_year(ev["t"], ev["ret"]),
                              "by_kind": {k: bps_stats(x["ret"]) for k, x in ev.groupby("kind")},
                              "median_or_width_pct": round(float(100 * ev["orw"].median()), 3),
                              "per_symbol_mean_bps": {k: round(1e4 * x["ret"].mean(), 1) for k, x in ev.groupby("sym")}}
    return out


# ----------------------------------------------------------------------------- E4 funding

def e4_funding(tf="15m"):
    rows = []
    for s in SYMBOLS:
        df = is_load(s, tf, funding=True)
        tfm = st.tf_minutes(df)
        c, o = df["close"], df["open"]
        f = df["funding"].shift(1)
        mod_close = (df.index.hour * 60 + df.index.minute + tfm) % 1440
        # bars whose CLOSE is at a settlement time T
        isT = np.isin(mod_close, [0, 480, 960])
        pos = np.flatnonzero(isT)
        k = 60 // tfm
        cc = c.to_numpy(float)
        ff = f.to_numpy(float)
        for p in pos:
            if p - 2 * k < 0 or p + 4 * k >= len(cc):
                continue
            rows.append({"sym": s, "t": df.index[p], "f": ff[p - 2 * k],   # funding known 2h before T
                         "pre2": cc[p] / cc[p - 2 * k] - 1, "pre1": cc[p] / cc[p - k] - 1,
                         "post1": cc[p + k] / cc[p] - 1, "post2": cc[p + 2 * k] / cc[p] - 1,
                         "post4": cc[p + 4 * k] / cc[p] - 1, "T": df.index[p].hour})
    d = pd.DataFrame(rows)
    d["bucket"] = pd.cut(d["f"], [-1, -1e-4, 0, 0.99e-4, 1.01e-4, 2e-4, 1],
                         labels=["f<-0.01%", "-0.01%<=f<0", "0<=f<0.01%", "f=0.01%", "0.01%<f<0.02%", "f>=0.02%"],
                         right=False)
    out = {"bucket_counts": d["bucket"].value_counts().to_dict()}
    for col in ("pre2", "pre1", "post1", "post2", "post4"):
        out[col] = {str(b): {"all": bps_stats(g[col]), "by_year": by_year(g["t"], g[col])}
                    for b, g in d.groupby("bucket", observed=True)}
        out[col]["_unconditional"] = bps_stats(d[col])
    return out


# ----------------------------------------------------------------------------- E5 weekend / CME

def e5_weekend(tf="1h"):
    ev, gaps = [], []
    for s in SYMBOLS:
        df = is_load(s, tf)
        tfm = st.tf_minutes(df)
        dow, key, wh, wl, cnt = st.weekend_levels(df)
        c, o = df["close"], df["open"]
        mod = df.index.hour * 60 + df.index.minute
        full = cnt >= 2 * 1440 // tfm
        win = (dow < 1) & full & wh.notna()
        up, dn = win & (c > wh), win & (c < wl)
        first = st.first_in_group(up | dn, key)
        ex = c.where((dow == 0) & (mod == 1440 - tfm)).groupby(np.asarray(key)).last()
        rr = st.range_rank((wh - wl).where(win), key, days=8)
        nxt = o.shift(-1)
        for kind, mask, sgn in (("up", first & up, 1), ("dn", first & dn, -1)):
            for i in np.flatnonzero(mask.to_numpy()):
                ev.append({"sym": s, "t": df.index[i], "kind": kind, "rr": rr.iloc[i],
                           "ret": sgn * (ex.get(key.iloc[i], np.nan) / nxt.iloc[i] - 1)})
        # CME: weekend return (Fri 16:00 CT -> Sun 17:00 CT) vs next 24h and fill stats
        lmod, lday, ldow = st.local_clock(df, "America/Chicago")
        cm = lmod + tfm
        fri = np.flatnonzero(((ldow == 4) & (cm == 960)).to_numpy())
        sun = np.flatnonzero(((ldow == 6) & (cm == 1020)).to_numpy())
        cc, hh, ll = c.to_numpy(float), df["high"].to_numpy(float), df["low"].to_numpy(float)
        k24 = 1440 // tfm
        for j in sun:
            prev = fri[fri < j]
            if not len(prev) or (df.index[j] - df.index[prev[-1]]) > pd.Timedelta(days=3) or j + k24 >= len(cc):
                continue
            fc = cc[prev[-1]]
            g = cc[j] / fc - 1
            fut = cc[j + k24] / cc[j] - 1
            filled = (ll[j + 1:j + 1 + k24].min() <= fc) if g > 0 else (hh[j + 1:j + 1 + k24].max() >= fc)
            # adverse excursion equal to the gap distance before fill (k=1 stop)
            gaps.append({"sym": s, "t": df.index[j], "gap": g, "next24": fut, "filled24": bool(filled)})
    ev, gaps = pd.DataFrame(ev), pd.DataFrame(gaps)
    out = {"monday_break": {"all": bps_stats(ev["ret"]), "by_year": by_year(ev["t"], ev["ret"]),
                            "narrow": bps_stats(ev.loc[ev["rr"] < 1, "ret"]),
                            "wide": bps_stats(ev.loc[ev["rr"] >= 1, "ret"]),
                            "by_kind": {k: bps_stats(x["ret"]) for k, x in ev.groupby("kind")}}}
    gaps["rev"] = -np.sign(gaps["gap"]) * gaps["next24"]
    out["cme"] = {"n": len(gaps), "median_abs_gap_pct": round(float(100 * gaps["gap"].abs().median()), 3),
                  "corr_gap_next24": round(float(gaps[["gap", "next24"]].corr().iloc[0, 1]), 3)}
    for thr in (0.0, 0.005, 0.01, 0.02):
        g = gaps[gaps["gap"].abs() >= thr]
        out["cme"][f"|gap|>={thr}"] = {"reversal_next24": bps_stats(g["rev"]),
                                       "fill_rate_24h": round(float(g["filled24"].mean()), 3) if len(g) else None,
                                       "by_year": by_year(g["t"], g["rev"])}
    return out


# ----------------------------------------------------------------------------- engine probes

def probe(fn, tf, params, load_kw=None, costs=Costs()):
    parts = []
    for s in SYMBOLS:
        df = is_load(s, tf, **(load_kw or {}))
        parts.append(simulate(df, fn(df, **params), costs, fn.MAX_HOLD, fn.LIMIT_TTL, s))
    return pd.concat(parts, ignore_index=True)


def e6_sessions():
    """Session breakdown of IS trades of the IS-selected volume_absorption signals."""
    bases = {"d_cont_15m": ("climax_cont", "15m", {"k": 3, "r": 1.5, "d": 0.07, "N": 48, "m": 4}),
             "d_cont_5m": ("climax_cont", "5m", {"k": 3, "r": 1.5, "d": 0.1, "N": 48, "m": 4}),
             "c_fade_15m": ("climax_fade", "15m", {"k": 3, "r": 2, "d": 0.07, "conf": 0.618, "m": 1.5}),
             "a_fade_5m": ("absorb", "5m", {"k": 3, "d": 0.25, "m": 3, "r": 1.2}),
             "d_cont_1h": ("climax_cont", "1h", {"k": 3, "r": 1.5, "d": 0.07, "N": 48, "m": 4})}
    out = {}
    for name, (base, tf, p) in bases.items():
        res = {}
        for sess in st.SESSIONS:
            tr = probe(st.sess_filter, tf, {"base": base, "sess": sess, **p})
            trg = probe(st.sess_filter, tf, {"base": base, "sess": sess, **p}, costs=ZERO)
            s = summarize(tr)
            res[sess] = {k: s.get(k) for k in ("n", "win_pct", "avg_R", "t_stat")}
            res[sess]["gross_avg_R"] = round(float(trg["R"].mean()), 3) if len(trg) else None
        out[name] = res
        print(name, json.dumps(res), flush=True)
    return out


def main():
    what = sys.argv[1:] or ["e1", "e2", "e3", "e4", "e5", "e6"]
    path = "results/session_time_explore_IS.json"
    try:
        res = json.load(open(path))
    except Exception:
        res = {}
    fns = {"e1": e1_hour_of_day, "e2": lambda: {tf: e2_asia(tf) for tf in ("15m",)},
           "e3": e3_orb, "e4": e4_funding, "e5": e5_weekend, "e6": e6_sessions}
    for w in what:
        res[w] = fns[w]()
        print(w, "done", flush=True)
        with open(path, "w") as f:
            json.dump(res, f, indent=1, default=str)


if __name__ == "__main__":
    main()
