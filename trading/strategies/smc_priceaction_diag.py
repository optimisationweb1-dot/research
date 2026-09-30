"""Descriptive diagnostics for smc_priceaction (no parameter selection happens here).

D1  CHoCH event study: signed forward return after the CHoCH bar close (entry = next open),
    gross of costs, in bps and in units of the structural risk (entry - leg low), horizons
    12 / 48 / 96 bars; IS vs OOS; pooled mean with a day-clustered (CR0) t-stat.
    Split by killzone / non-killzone, by 4h-bias aligned / against (hypotheses d, e) and by
    ICT "displacement" of the CHoCH bar (range >= 1.5 ATR, body >= 60% of range).
D2  Order-block adverse selection: for every armed OB setup, was the resting limit filled
    within RETEST_BARS? Compare the market-at-CHoCH forward return of filled vs unfilled setups
    and the forward return measured from the fill.
D3  FVG confirmation: same split for the FVG setups that were armed (touched / confirmed / never).

    cd trading && python3 -m strategies.smc_priceaction_diag
"""
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from bt.data import SYMBOLS, load
from bt.engine import IS_END
import strategies.smc_priceaction as S

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
HS = (12, 48, 96)


def _events(sym, tf):
    df = load(sym, tf)
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    n = len(df)
    kz = S.killzone_mask(df)
    bias = S.htf_bias(df)
    A = S.atr(df).to_numpy(float)
    rows = []
    # D1: CHoCH market events (struct stop, rr irrelevant for forward returns)
    sig = S.strategy(df, setup="choch", rr=2.0, filt="none", stop="struct")
    idx = np.flatnonzero(sig["signal"].to_numpy() != 0)
    for t in idx:
        if t + 1 + max(HS) >= n:
            continue
        d = sig["signal"].iat[t]
        e = o[t + 1]
        risk = abs(c[t] - sig["stop"].iat[t])
        r = {"kind": "choch", "symbol": sym, "ts": df.index[t], "dir": d, "kz": bool(kz[t]),
             "aligned": bool(bias[t] * d > 0), "risk_bps": 1e4 * risk / c[t],
             # ICT "displacement": CHoCH bar range >= 1.5 ATR with a body >= 60% of the range
             "disp": bool((h[t] - l[t]) >= 1.5 * A[t] and d * (c[t] - o[t]) >= 0.6 * (h[t] - l[t]))}
        for H in HS:
            fwd = d * (c[t + H] - e)
            r[f"bps{H}"] = 1e4 * fwd / e
            r[f"R{H}"] = fwd / risk
        rows.append(r)
    # D2: OB setups -> filled or not
    sig = S.strategy(df, setup="ob", rr=2.0, filt="none", stop="struct")
    s_ = sig["signal"].to_numpy()
    lim = sig["entry_limit"].to_numpy()
    t = 0
    while t < n:
        if s_[t] == 0:
            t += 1
            continue
        d, px, t_start = s_[t], lim[t], t
        while t + 1 < n and s_[t + 1] == d and lim[t + 1] == px:
            t += 1
        t_end = t
        t += 1
        k = t_end + 1
        if k + max(HS) >= n:
            continue
        filled = (l[k] < px) if d > 0 else (h[k] > px)
        e = o[t_start + 1]
        r = {"kind": "ob", "symbol": sym, "ts": df.index[t_start], "dir": d, "filled": bool(filled),
             "bars_to_fill": int(k - t_start) if filled else None}
        for H in HS:
            r[f"bps{H}_mkt"] = 1e4 * d * (c[t_start + H] - e) / e
            if filled:
                r[f"bps{H}_fill"] = 1e4 * d * (c[k + H] - px) / px if k + H < n else np.nan
        rows.append(r)
    return rows


def _t_day(x, ts, digits=2):
    """Pooled mean and its t-stat with day-clustered (CR0) standard error."""
    s = pd.Series(np.asarray(x, float), index=pd.DatetimeIndex(ts)).dropna()
    if len(s) < 5:
        return None, None, len(s)
    m = s.mean()
    g = (s - m).groupby(s.index.floor("D")).sum()
    se = math.sqrt(float((g ** 2).sum())) / len(s)
    t = m / se if se > 0 else None
    return round(float(m), digits), (round(float(t), 2) if t is not None else None), int(len(s))


def main():
    out = {}
    for tf in ("5m", "15m"):
        with ProcessPoolExecutor(2) as ex:
            parts = list(ex.map(_events, SYMBOLS, [tf] * len(SYMBOLS)))
        ev = pd.DataFrame([r for p in parts for r in p])
        ev["oos"] = ev["ts"] >= IS_END
        res = {}
        ch = ev[ev["kind"] == "choch"].copy()
        for col in ("kz", "aligned", "disp"):
            ch[col] = ch[col].astype(bool)
        for per, g in (("IS", ch[~ch.oos]), ("OOS", ch[ch.oos])):
            blk = {"median_risk_bps": round(float(g["risk_bps"].median()), 1)}
            for lab, sub in (("all", g), ("kz", g[g.kz]), ("non_kz", g[~g.kz]),
                             ("htf_aligned", g[g.aligned]), ("htf_against", g[~g.aligned]),
                             ("long", g[g.dir > 0]), ("short", g[g.dir < 0]),
                             ("displacement", g[g.disp]), ("no_displacement", g[~g.disp])):
                blk[lab] = {}
                for H in HS:
                    m, tt, nn = _t_day(sub[f"bps{H}"], sub["ts"])
                    mR, tR, _ = _t_day(sub[f"R{H}"], sub["ts"], 3)
                    blk[lab][f"H{H}"] = {"n": nn, "mean_bps": m, "t_day": tt, "mean_R": mR, "t_day_R": tR}
            res[f"D1_choch_{per}"] = blk
        ob = ev[ev["kind"] == "ob"].copy()
        ob["filled"] = ob["filled"].astype(bool)
        for per, g in (("IS", ob[~ob.oos]), ("OOS", ob[ob.oos])):
            blk = {"n_setups": int(len(g)), "fill_rate": round(float(g["filled"].mean()), 3)}
            for lab, sub in (("filled", g[g.filled]), ("unfilled", g[~g.filled])):
                blk[lab] = {}
                for H in HS:
                    m, tt, nn = _t_day(sub[f"bps{H}_mkt"], sub["ts"])
                    blk[lab][f"mkt_H{H}"] = {"n": nn, "mean_bps": m, "t_day": tt}
                    if lab == "filled":
                        m2, t2, n2 = _t_day(sub[f"bps{H}_fill"], sub["ts"])
                        blk[lab][f"from_fill_H{H}"] = {"n": n2, "mean_bps": m2, "t_day": t2}
            res[f"D2_ob_{per}"] = blk
        out[tf] = res
        print(tf, json.dumps(res)[:3000], flush=True)
    with open(os.path.join(RES, "smc_priceaction_diagnostics.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
