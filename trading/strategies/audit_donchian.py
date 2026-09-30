"""Audit reference strategy: 1h Donchian breakout with ATR stop (market entry).

Fresh close above the highest high of the previous n bars -> long; below the lowest low -> short.
Stop = close -/+ k_stop*ATR, target = close +/- rr*k_stop*ATR, MAX_HOLD bars time exit.
Deliberately simple: used only to cross-check two independent backtest engines.
"""
import numpy as np

from bt.features import atr, donchian, empty_signals

MAX_HOLD = 120


def strategy(df, n=48, atr_n=14, k_stop=2.0, rr=2.0):
    out = empty_signals(df)
    hi, lo = donchian(df, n)
    c = df["close"]
    a = atr(df, atr_n)
    up = (c > hi) & (c.shift(1) <= hi.shift(1))
    dn = (c < lo) & (c.shift(1) >= lo.shift(1))
    sig = np.where(up, 1.0, np.where(dn, -1.0, 0.0))
    out["signal"] = sig
    out["stop"] = np.where(sig > 0, c - k_stop * a, np.where(sig < 0, c + k_stop * a, np.nan))
    out["target"] = np.where(sig > 0, c + rr * k_stop * a, np.where(sig < 0, c - rr * k_stop * a, np.nan))
    return out


strategy.MAX_HOLD = MAX_HOLD
