import json, numpy as np, pandas as pd
from bt.data import load, SYMBOLS
from strategies import audit_bt as A, smc, audit_donchian as DC
from strategies.audit_dl import load_ext
out = {}
# 1) ambiguous bars for SMC on all 10 symbols (bar level)
amb = {}
for tf in ("5m", "15m"):
    for s in SYMBOLS:
        df = load(s, tf)
        tr, st = A.simulate(df, smc.strategy(df), A.BASE, smc.MAX_HOLD, smc.LIMIT_TTL, s, return_stats=True)
        # fill-bar target touches (target reached on the limit-fill bar, engine ignores it)
        h, l = df.high.to_numpy(), df.low.to_numpy()
        ft = 0
        for _, r in tr.iterrows():
            k = r.k_entry
            if (r.dir > 0 and h[k] >= r.target) or (r.dir < 0 and l[k] <= r.target):
                ft += 1
        amb[f"{s}_{tf}"] = {"n": len(tr), "ambiguous_bars": st["ambiguous_bars"], "fill_bar_target_touch": ft}
out["smc_ambiguity_10sym"] = amb
print(json.dumps(amb))
# 2) stop overshoot at 1m resolution
ov = {}
for s in ("BTCUSDT", "ETHUSDT"):
    m1 = load_ext(s, "1m")
    mt = m1.index.asi8 if hasattr(m1.index, 'asi8') else None
    mt = np.asarray(pd.DatetimeIndex(m1.index).as_unit("ns").asi8)
    ml, mh, mc = m1.low.to_numpy(), m1.high.to_numpy(), m1.close.to_numpy()
    for name, fn, tf, tfm in (("smc_5m", smc.strategy, "5m", 5), ("donchian_1h", DC.strategy, "1h", 60)):
        df = load(s, tf)
        tr = A.simulate(df, fn(df), A.BASE, getattr(fn, "MAX_HOLD", None), getattr(fn, "LIMIT_TTL", None), s)
        tr = tr[tr.reason == "stop"]
        o1, o2 = [], []
        for _, r in tr.iterrows():
            t0 = pd.Timestamp(r.t_exit).as_unit("ns").value
            a, b = np.searchsorted(mt, t0), np.searchsorted(mt, t0 + tfm * 60 * 10**9)
            for j in range(a, b):
                if (r.dir > 0 and ml[j] <= r.stop) or (r.dir < 0 and mh[j] >= r.stop):
                    o1.append(r.dir * (r.stop - mc[j]) / r.stop * 1e4)   # minute close beyond stop, bps
                    o2.append(r.dir * (r.stop - (ml[j] if r.dir > 0 else mh[j])) / r.stop * 1e4)  # extreme beyond
                    break
        o1, o2 = np.array(o1), np.array(o2)
        ov[f"{s}_{name}"] = {"n_stops": int(len(o1)), "median_close_beyond_bps": round(float(np.median(o1)), 1),
                             "p90_close_beyond_bps": round(float(np.percentile(o1, 90)), 1),
                             "median_extreme_beyond_bps": round(float(np.median(o2)), 1),
                             "p90_extreme_beyond_bps": round(float(np.percentile(o2, 90)), 1),
                             "median_stop_pct": round(float(tr.risk_pct.median()), 3)}
out["stop_overshoot_1m"] = ov
print(json.dumps(ov))
# 3) manual spot check of 2 SMC trades
df = load("BTCUSDT", "5m")
tr = A.simulate(df, smc.strategy(df), A.BASE, smc.MAX_HOLD, smc.LIMIT_TTL, "BTCUSDT")
spots = []
for i in (10, 100):
    r = tr.iloc[i]
    seg = df.iloc[r.k_signal:r.k_entry + 1][["open", "high", "low", "close"]]
    spots.append({"trade": {k: str(r[k]) for k in ("dir", "t_signal", "t_entry", "t_exit", "entry", "stop", "target", "exit", "reason", "R")},
                  "no_fill_before_fill_bar": bool((seg.low.iloc[1:-1] >= r.entry).all()) if r.dir > 0 else bool((seg.high.iloc[1:-1] <= r.entry).all()),
                  "fill_bar_low_lt_limit": bool(seg.low.iloc[-1] < r.entry) if r.dir > 0 else bool(seg.high.iloc[-1] > r.entry),
                  "exit_bar": df.iloc[r.k_exit][["open", "high", "low", "close"]].to_dict(),
                  "bars_between_no_exit": bool(((df.low.iloc[r.k_entry + 1:r.k_exit] > r.stop) & (df.high.iloc[r.k_entry + 1:r.k_exit] < r.target)).all()) if r.dir > 0 else
                  bool(((df.high.iloc[r.k_entry + 1:r.k_exit] < r.stop) & (df.low.iloc[r.k_entry + 1:r.k_exit] > r.target)).all())})
out["spot_checks"] = spots
print(json.dumps(spots, default=str))
json.dump(out, open("results/audit_quick.json", "w"), indent=1, default=str)
