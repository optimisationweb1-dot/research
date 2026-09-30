"""H2b: does price drift toward max pain / the max-OI strike into Deribit expiry?
Uses TRUE per-strike OI at expiry from Deribit settlement records (options_expiry_settlements.py).

    cd trading && python3 -m strategies.options_expiry_maxpain   # -> results/options_expiry_maxpain.json
"""
import json
import math
import os

import numpy as np
import pandas as pd

from strategies.options_expiry_calendar import load_calendar
from strategies.options_expiry_study import load5, tstat, r, IS_END

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SET = os.path.join(HERE, "data", "ext", "options_expiry", "settlements")
OUT = os.path.join(HERE, "results", "options_expiry_maxpain.json")
RNG = np.random.default_rng(7)


def per_expiry(c):
    s = pd.read_parquet(os.path.join(SET, f"{c}.parquet"))
    s = s[(s["expiry"] >= "2023-01-02") & (s["expiry"] < "2026-09-01")]
    cal = load_calendar(c)
    cls = dict(zip(cal["exp"], cal["cls"]))
    k = load5(c)
    o, cl = k["open"], k["close"]
    rows = []
    for e, g in s.groupby("expiry"):
        if e.minute != 0 or e.hour != 8:
            continue
        pos = g.pivot_table(index="strike", columns="cp", values="position", aggfunc="sum").fillna(0.0)
        for col in ("C", "P"):
            if col not in pos:
                pos[col] = 0.0
        K = pos.index.to_numpy(float)
        C, P = pos["C"].to_numpy(float), pos["P"].to_numpy(float)
        if (C + P).sum() <= 0:
            continue
        pay = [(C * np.maximum(S - K, 0)).sum() + (P * np.maximum(K - S, 0)).sum() for S in K]
        mp = K[int(np.argmin(pay))]
        koi = K[int(np.argmax(C + P))]
        settle = float(g["index_price"].median())
        tw = cl.loc[e - pd.Timedelta(minutes=30):e - pd.Timedelta(minutes=5)]
        row = {"expiry": e, "cls": cls.get(e, "?"), "oi_total": float((C + P).sum()), "mp": mp, "koi": koi,
               "settle": settle, "twap_perp": float(tw.mean()) if len(tw) >= 5 else np.nan}
        for h in (24, 2):
            row[f"p0_{h}"] = float(o.get(e - pd.Timedelta(hours=h), np.nan))
        rows.append(row)
    t = pd.DataFrame(rows).set_index("expiry").sort_index()
    t["mq"] = t["cls"].isin(["M", "Q"])
    t["grp"] = np.where(t["mq"], "MQ", t["cls"])
    for h in (24, 2):
        p0 = t[f"p0_{h}"]
        for tgt in ("mp", "koi"):
            dirn = np.sign(t[tgt] - p0)
            t[f"m_{tgt}_{h}"] = dirn * (t["settle"] - p0) / p0
            t[f"mperp_{tgt}_{h}"] = dirn * (t["twap_perp"] - p0) / p0
            t[f"dist0_{tgt}_{h}"] = (t[tgt] - p0).abs() / p0
            # placebo: target of the previous expiry of the same group
            prev = t.groupby("grp")[tgt].shift(1)
            t[f"plc_{tgt}_{h}"] = np.sign(prev - p0) * (t["settle"] - p0) / p0
    return t


def signflip_p(x, n=5000):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if len(x) < 5:
        return None
    obs = abs(x.mean())
    sims = np.abs((x[None, :] * RNG.choice([-1, 1], size=(n, len(x)))).mean(1))
    return float(((sims >= obs).sum() + 1) / (n + 1))


def analyse(t):
    out = {"proxy_check": {"median_abs_bps_settle_vs_perp_twap": r(1e4 * ((t["twap_perp"] - t["settle"]).abs() / t["settle"]).median(), 2)}}
    for per, m in (("IS", t.index < IS_END), ("OOS", t.index >= IS_END)):
        x = t[m]
        res = {}
        for grp in ("MQ", "W", "D"):
            y = x[x["grp"] == grp]
            g = {"n": int(len(y)), "median_dist_mp_24h_pct": r(100 * y["dist0_mp_24"].median(), 2)}
            for tgt in ("mp", "koi"):
                for h in (24, 2):
                    v = y[f"m_{tgt}_{h}"]
                    if tgt == "koi":
                        v = v[y[f"dist0_koi_{h}"] <= 0.03]
                    pl = y[f"plc_{tgt}_{h}"]
                    g[f"{tgt}_{h}h"] = {"n": int(v.notna().sum()), "mean_bps": r(1e4 * v.mean(), 1), "t": r(tstat(v), 2),
                                        "signflip_p": r(signflip_p(v), 4), "hit": r((v > 0).mean(), 3),
                                        "perp_twap_mean_bps": r(1e4 * y[f"mperp_{tgt}_{h}"].mean(), 1),
                                        "placebo_prev_target_mean_bps": r(1e4 * pl.mean(), 1), "placebo_t": r(tstat(pl), 2)}
            res[grp] = g
        out[per] = res
    return out


def main():
    res = {}
    for c in ("BTC", "ETH"):
        t = per_expiry(c)
        t.to_parquet(os.path.join(HERE, "data", "ext", "options_expiry", f"maxpain_{c}.parquet"))
        res[c] = analyse(t)
        print(c, json.dumps(res[c]["proxy_check"]))
        for per in ("IS", "OOS"):
            for grp, g in res[c][per].items():
                print(c, per, grp, g["n"], {k: (v["n"], v["mean_bps"], v["t"], v["signflip_p"], v["placebo_prev_target_mean_bps"])
                                            for k, v in g.items() if isinstance(v, dict)})
    with open(OUT, "w") as f:
        json.dump(res, f, indent=1, default=str)


if __name__ == "__main__":
    main()
