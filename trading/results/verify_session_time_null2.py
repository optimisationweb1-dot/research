"""Clustered null test for e_dcont 1h (supplements verify_session_time.py).

The per-symbol null in verify_session_time.py draws entry times independently per symbol, which
destroys the cross-symbol clustering of the real signals (market-wide impulse hours: several coins
break out in the same hour). Its null distribution is therefore too narrow for the real statistic.
Here every distinct real signal HOUR in a month is mapped to ONE random hour of the same month
(from the pool: NY-session hours for sess='ny', any hour for sess='all'), shared by all symbols
that signalled in that hour; directions are shuffled within the month. Exits identical (replica of
the engine, verified to 1e-15 R). p = share of permutations with avg_R >= real.
Also: leave-one-day-out sensitivity of the OOS avg_R.
Output: results/verify_session_time_null2.json
"""
import importlib.util
import json
import os

import numpy as np
import pandas as pd

os.chdir("/home/user/research/trading")
sp = importlib.util.spec_from_file_location("v", "results/verify_session_time.py")
v = importlib.util.module_from_spec(sp)
sp.loader.exec_module(v)
NPERM = int(os.environ.get("NPERM", 1000))


def clustered_null(real, sess, rng, nperm=NPERM):
    costs = v.COST_SCENARIOS["base"]
    arr = {s: tuple(v.DF[s][x].to_numpy(float) for x in ("open", "high", "low", "close")) for s in v.SYMBOLS}
    ef = {s: v.exit_frame(v.DF[s]) for s in v.SYMBOLS}
    ref = v.DF["BTCUSDT"]
    ok = np.ones(len(ref), bool)
    if sess != "all":
        ok &= v.st.session_mask(ref, sess).to_numpy()
    ok &= np.arange(len(ref)) >= 24 * 25
    ok &= np.arange(len(ref)) < len(ref) - 2
    mon = ref.index.tz_localize(None).to_period("M").astype(str).to_numpy()
    pool = {mm: ref.index[np.flatnonzero(ok & (mon == mm))] for mm in np.unique(mon)}
    real = real.copy()
    real["mon"] = real["t_signal"].dt.tz_localize(None).dt.to_period("M").astype(str)
    months = []
    for mm, g in real.groupby("mon"):
        stamps = [list(zip(gg.symbol, gg.index)) for _, gg in g.groupby("t_signal")]
        months.append((mm, stamps, g["dir"].to_numpy()))
    idx = {s: v.DF[s].index for s in v.SYMBOLS}
    res = {"IS": [], "OOS": [], "altOOS": []}
    for _ in range(nperm):
        Rs, te = [], []
        for mm, stamps, dirs in months:
            P = pool.get(mm)
            if P is None or len(P) == 0:
                continue
            draws = P[rng.choice(len(P), size=len(stamps), replace=len(P) < len(stamps))]
            dd = iter(rng.permutation(dirs))
            for ts, members in zip(draws, stamps):
                for s, _ in members:
                    d = int(next(dd))
                    t = idx[s].get_indexer([ts])[0]
                    if t < 0:
                        continue
                    o, h, l, c = arr[s]
                    e = ef[s]
                    r = v.replica(o, h, l, c, t, d, e["stop_l"][t] if d > 0 else e["stop_s"][t],
                                  e["tg_l"][t] if d > 0 else e["tg_s"][t], costs)
                    if r is not None and np.isfinite(r):
                        Rs.append(r)
                        te.append(idx[s][t + 1])
        Rs, te = np.asarray(Rs), pd.DatetimeIndex(te)
        res["IS"].append(Rs[te < v.IS_END].mean())
        res["OOS"].append(Rs[te >= v.IS_END].mean())
        res["altOOS"].append(Rs[te >= v.ALT_END].mean())
    real_v = {"IS": real[real.t_entry < v.IS_END].R.mean(), "OOS": real[real.t_entry >= v.IS_END].R.mean(),
              "altOOS": real[real.t_entry >= v.ALT_END].R.mean()}
    out = {"n_perm": nperm, "pool": sess}
    for k, a in res.items():
        a = np.asarray(a)
        out[k] = {"real_avgR": round(float(real_v[k]), 4), "null_mean": round(float(a.mean()), 4),
                  "null_sd": round(float(a.std()), 4), "null_p95": round(float(np.quantile(a, 0.95)), 4),
                  "p_value": round(float((1 + (a >= real_v[k]).sum()) / (1 + len(a))), 4)}
    return out


def lodo(tr):
    o = tr[tr.t_entry >= v.IS_END]
    day = o.t_entry.dt.floor("D")
    daily = o.groupby(day)["R"].agg(["sum", "count"]).sort_values("sum", ascending=False)
    out = {"OOS_avgR": round(float(o.R.mean()), 3), "n_days": int(len(daily))}
    for k in (1, 2, 3, 5, 10):
        top = set(daily.index[:k])
        out[f"ex_top{k}_days"] = round(float(o[~day.isin(top)].R.mean()), 3)
    out["top_day_trades"] = {str(d.date()): [int(r["count"]), round(float(r["sum"]), 2)] for d, r in daily.head(3).iterrows()}
    return out


def main():
    rng = np.random.default_rng(777)
    out = {}
    for sess in ("ny", "all"):
        tr = v.run(dict(v.SEL, sess=sess))
        out[f"lodo_{sess}"] = lodo(tr)
        print("lodo", sess, out[f"lodo_{sess}"], flush=True)
        out[f"clustered_null_{sess}"] = clustered_null(tr, sess, rng, NPERM if sess == "ny" else min(NPERM, 500))
        print("cnull", sess, out[f"clustered_null_{sess}"], flush=True)
    json.dump(out, open("results/verify_session_time_null2.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
