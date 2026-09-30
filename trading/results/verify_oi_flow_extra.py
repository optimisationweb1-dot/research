"""Extra adversarial checks for oi_flow b1* (squeeze-follow 1h), second verification pass.

    cd /home/user/research/trading
    OI_FLOW_HOLDOUT_ROOT=<dir> python3 results/verify_oi_flow_extra.py

A. Independent merge check: recompute, from the raw metrics parquet and plain timestamp arithmetic,
   which OI stamp each 1h bar may see (latest ts with ts + 6min <= bar close) and compare with df.oi.
   Also re-test the stamp semantics: corr(|dlogOI at stamp T|, |5m return| of the kline opened at T+j).
B. Cluster-preserving null: all real trades that were signalled on the same UTC day are moved TOGETHER
   to one random day of the same month (same symbol, hour of day and direction), 500 permutations.
   This keeps the cross-symbol clustering that the plain per-trade null destroys.
C. Mirror check: fade vs follow OOS of the same trigger (was the follow OOS already implied by the
   fade OOS the agent had seen before round 2?).
Output: results/verify_oi_flow_extra.json. Nothing in bt/ or strategies/ is modified.
"""
import importlib.util
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location("vof", os.path.join(HERE, "results", "verify_oi_flow.py"))
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)
F, D = V.F, V.D
from bt.engine import simulate  # noqa: E402
from bt.runner import COST_SCENARIOS  # noqa: E402

RNG = np.random.default_rng(20260930)
NPERM = 500
T24, T25 = V.T24, V.T25
END = pd.Timestamp("2027-01-01", tz="UTC")


def merge_check(sym):
    df = V.load(sym, V.ORIG)
    mt = pd.read_parquet(os.path.join(V.ORIG, "metrics", f"{sym}.parquet"))
    ts = pd.DatetimeIndex(mt["ts"]).tz_convert("UTC").as_unit("ns")
    oi = mt["sum_open_interest"].to_numpy(float)
    ct = pd.DatetimeIndex(df["close_time"]).tz_convert("UTC").as_unit("ns")
    lim = (ct - pd.Timedelta(minutes=6)).asi8
    pos = np.searchsorted(ts.asi8, lim, side="right") - 1
    exp = np.where(pos >= 0, oi[np.clip(pos, 0, None)], np.nan)
    got = df["oi"].to_numpy(float)
    m = np.isfinite(exp) & np.isfinite(got)
    # stamp semantics on 5m klines
    k5 = D.load(sym, "5m")
    r5 = np.log(k5["close"]).diff().abs()
    d = pd.Series(np.log(oi), index=ts).diff().abs()
    d = d[d.index.to_series().diff() == pd.Timedelta(minutes=5)]
    cors = {}
    for j in (-10, -5, 0, 5, 10):
        rr = r5.reindex(d.index + pd.Timedelta(minutes=j))  # kline OPENED at T+j
        ok = np.isfinite(rr.to_numpy()) & np.isfinite(d.to_numpy())
        cors[f"kline_open_T{j:+d}min"] = round(float(np.corrcoef(d.to_numpy()[ok], rr.to_numpy()[ok])[0, 1]), 3)
    # maximum age of the OI value used at bar close (minutes) and max forward reach
    age = (ct.asi8[m] - ts.asi8[pos[m]]) / 6e10
    return {"bars_compared": int(m.sum()), "mismatch": int((~np.isclose(exp[m], got[m], rtol=1e-12)).sum()),
            "stamp_age_at_close_min": {"min": float(age.min()), "median": float(np.median(age))},
            "corr_abs_dlogOI_vs_abs_ret5m": cors}


def cluster_null(syms, root, a, b):
    real, pools = [], {}
    for s in syms:
        df = V.load(s, root)
        sig = F.squeeze(df, **V.SQ)
        tr = simulate(df, sig, COST_SCENARIOS["base"], F.squeeze.MAX_HOLD, None, s)
        real.append(tr[(tr.t_entry >= a) & (tr.t_entry < b)])
        RL, RS = V.outcomes(df, 1), V.outcomes(df, -1)
        pools[s] = (pd.Series(RL, index=df.index), pd.Series(RS, index=df.index))
    rt = pd.concat(real, ignore_index=True)
    rt["day"] = rt.t_signal.dt.floor("1D")
    rt["hour"] = rt.t_signal - rt["day"]
    days_by_month = {}
    for mo in rt.day.dt.tz_localize(None).dt.to_period("M").unique():
        start = pd.Timestamp(mo.start_time, tz="UTC")
        days_by_month[mo] = pd.date_range(start, start + pd.offsets.MonthEnd(0), freq="1D")
    clusters = [(g.day.iloc[0], g) for _, g in rt.groupby("day")]
    real_mean = float(rt.R.mean())
    nulls = []
    for _ in range(NPERM):
        vals = []
        for day, g in clusters:
            mo = day.tz_localize(None).to_period("M")
            nd = RNG.choice(days_by_month[mo])
            for s, h, d in zip(g.symbol, g.hour, g.dir):
                ser = pools[s][0] if d > 0 else pools[s][1]
                v = ser.get(nd + h, np.nan)
                if np.isfinite(v):
                    vals.append(v)
        nulls.append(np.mean(vals))
    v = np.array(nulls)
    return {"n": int(len(rt)), "n_day_clusters": len(clusters), "real_avg_R": round(real_mean, 4),
            "null_mean": round(float(v.mean()), 4), "null_sd": round(float(v.std()), 4),
            "null_p95": round(float(np.quantile(v, 0.95)), 4),
            "p_value_one_sided": round(float((1 + (v >= real_mean).sum()) / (1 + len(v))), 4)}


def main():
    out = {"merge_check": {}}
    for s in ("BTCUSDT", "ETHUSDT", "DOGEUSDT", "LINKUSDT"):
        out["merge_check"][s] = merge_check(s)
        print("merge", s, json.dumps(out["merge_check"][s]), flush=True)
    out["cluster_null"] = {"main_OOS_2025_26": cluster_null(V.MAIN, V.ORIG, T25, END),
                           "main_altOOS_2025H2_26": cluster_null(V.MAIN, V.ORIG, V.T25H2, END)}
    if V.HROOT:
        out["cluster_null"]["holdout_2025_26"] = cluster_null(V.HOLD, V.HROOT, T25, END)
        out["cluster_null"]["holdout_2024_26"] = cluster_null(V.HOLD, V.HROOT, T24, END)
    print("cluster_null", json.dumps(out["cluster_null"]), flush=True)
    # C. mirror check from the agent's own round-1 file (fade) vs round-2 file (follow)
    r1 = json.load(open(os.path.join(HERE, "results", "oi_flow_squeeze_1h.json")))
    r2 = json.load(open(os.path.join(HERE, "results", "oi_flow_squeezefollow_1h.json")))
    key = lambda p: (p["k_hours"], p["move_atr"])  # noqa: E731
    fade = {key(c["params"]): c for c in r1["configs"]}
    out["mirror"] = {f"k{k}_m{m}": {"fade_IS": fade[(k, m)]["IS"]["avg_R"], "fade_OOS": fade[(k, m)]["OOS"]["avg_R"],
                                    "follow_IS": c["IS"]["avg_R"], "follow_OOS": c["OOS"]["avg_R"]}
                     for c in r2["configs"] for k, m in [key(c["params"])]}
    json.dump(out, open(os.path.join(HERE, "results", "verify_oi_flow_extra.json"), "w"), indent=1, default=str)
    print("done")


if __name__ == "__main__":
    main()
