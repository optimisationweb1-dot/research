"""Strategy D (SMC): liquidity sweep -> CHoCH -> limit order in FVG inside 0.5-0.786 retrace.

Causal state machine: at the close of bar t it may emit a limit order that the
engine tries to fill during the next LIMIT_TTL bars.
"""
import math

import numpy as np

from bt.features import atr, confirmed_swings, empty_signals, rvol

LIMIT_TTL = 24
MAX_HOLD = 288


def strategy(df, piv=5, z0=0.5, z1=0.786, ext=1.272, buf=0.3, min_rr=2.0, fee=0.001, vol_min=0.0, max_setup=96):
    out = empty_signals(df)
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    sh, sl = (x.to_numpy(float) for x in confirmed_swings(df, piv))
    A = atr(df).to_numpy(float)
    rv = rvol(df).fillna(0).to_numpy(float)
    sig, stop, tgt, lim = (np.full(len(df), np.nan) for _ in range(4))
    L = {"s": 0}
    S = {"s": 0}
    for t in range(2, len(df)):
        if L["s"] and t - L["t0"] > max_setup:
            L = {"s": 0}
        if S["s"] and t - S["t0"] > max_setup:
            S = {"s": 0}
        # ---- long
        if L["s"] == 2:
            if l[t] < L["lo"]:
                L = {"s": 0}
            else:
                L["hi"] = max(L["hi"], h[t])
                if l[t] > h[t - 2]:
                    L["fvg"] = (h[t - 2], l[t])
                leg = L["hi"] - L["lo"]
                zhi, zlo = L["hi"] - leg * z0, L["hi"] - leg * z1
                f = L.get("fvg")
                if f and f[0] <= zhi and f[1] >= zlo:
                    entry = min(zhi, f[1])
                    s_ = L["lo"] - buf * A[t]
                    tp = L["lo"] + leg * ext
                    fp = entry * fee
                    if c[t] > entry > s_ and (tp - entry - fp) / (entry - s_ + fp) >= min_rr:
                        sig[t], stop[t], tgt[t], lim[t] = 1, s_, tp, entry
                        L = {"s": 0}
        elif L["s"] == 1:
            L["lo"] = min(L["lo"], l[t])
            if not math.isnan(L["choch"]) and c[t] > L["choch"]:
                L.update(s=2, hi=h[t])
        if not math.isnan(sl[t]) and l[t] < sl[t] < c[t] and rv[t] >= vol_min:
            L = {"s": 1, "lo": l[t], "choch": sh[t], "t0": t}
        # ---- short
        if S["s"] == 2:
            if h[t] > S["hi"]:
                S = {"s": 0}
            else:
                S["lo"] = min(S["lo"], l[t])
                if h[t] < l[t - 2]:
                    S["fvg"] = (h[t], l[t - 2])
                leg = S["hi"] - S["lo"]
                zlo, zhi = S["lo"] + leg * z0, S["lo"] + leg * z1
                f = S.get("fvg")
                if f and f[1] >= zlo and f[0] <= zhi and math.isnan(sig[t]):
                    entry = max(zlo, f[0])
                    s_ = S["hi"] + buf * A[t]
                    tp = S["hi"] - leg * ext
                    fp = entry * fee
                    if c[t] < entry < s_ and (entry - tp - fp) / (s_ - entry + fp) >= min_rr:
                        sig[t], stop[t], tgt[t], lim[t] = -1, s_, tp, entry
                        S = {"s": 0}
        elif S["s"] == 1:
            S["hi"] = max(S["hi"], h[t])
            if not math.isnan(S["choch"]) and c[t] < S["choch"]:
                S.update(s=2, lo=l[t])
        if not math.isnan(sh[t]) and h[t] > sh[t] > c[t] and rv[t] >= vol_min:
            S = {"s": 1, "hi": h[t], "choch": sl[t], "t0": t}
    out["signal"] = np.nan_to_num(sig)
    out["stop"], out["target"], out["entry_limit"] = stop, tgt, lim
    return out


strategy.LIMIT_TTL = LIMIT_TTL
strategy.MAX_HOLD = MAX_HOLD
