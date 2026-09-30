"""options_expiry strategies (bt.engine CONTRACT). Pre-registered in research/options_expiry_prereg.md.

S2 dvol_spike_long : 1h bars. DVOL 24h change >= IS quantile threshold while the 24h return < 0
                     ("fear spike"), de-clustered 7 days -> long at next open, stop 3*ATR(24), time exit.
S3 dvol_regime     : 1d bars (00:00 UTC). DVOL at the daily close in the top IS tercile -> fade the
                     day's return (MR); DVOL in the bottom IS tercile -> follow the 7-day return (trend).
                     Hold 1 day (MAX_HOLD=1 -> exit at next open), protective stop 2*ATR(14).
                     Tercile cuts are fixed numbers computed on IS (< 2025-01-01) by options_expiry_study.

DVOL is attached as-of the bar CLOSE (hourly DVOL candle known 1h after its stamp) - own merge,
bt/data.py is not edited (its _asof fails under pandas 3, see results/mean_reversion.md).
"""
import os

import numpy as np
import pandas as pd

from bt.features import atr, empty_signals

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# IS-only constants (results/options_expiry_study.json -> H5.thresholds_IS, H6.tercile_cuts_IS)
SPIKE_THR = {"BTC": {90: 2.74, 95: 4.06}, "ETH": {90: 2.94, 95: 4.28}}
DVOL_CUTS = {"BTC": (50.56, 56.9), "ETH": (56.48, 64.61)}


def attach_dvol(df, currency):
    d = pd.read_parquet(os.path.join(HERE, "data", "dvol", f"{currency}.parquet"))
    known = pd.DatetimeIndex(d["ts"]) + pd.Timedelta(hours=1)
    s = pd.Series(d["dvol"].to_numpy(), index=known)
    s = s[~s.index.duplicated()].sort_index()
    close_t = df.index + (df.index[1] - df.index[0]) if len(df) > 1 else df.index
    out = df.copy()
    out["dvol"] = s.reindex(close_t, method="ffill").to_numpy()
    out.attrs["currency"] = currency
    return out


def _cur(df):
    return df.attrs.get("currency", "BTC")


def dvol_spike_long(df, q=95, hold=72, fear=True, stop_atr=3.0, gap_days=7):
    c = _cur(df)
    sig = empty_signals(df)
    d24 = df["dvol"] - df["dvol"].shift(24)
    r24 = df["close"] / df["close"].shift(24) - 1
    cond = (d24 >= SPIKE_THR[c][q]) & ((r24 < 0) if fear else True)
    a = atr(df, 24)
    idx = np.flatnonzero(cond.fillna(False).to_numpy())
    last = -10 ** 9
    gap = gap_days * 24
    for i in idx:  # causal de-clustering: only past events matter
        if i - last >= gap:
            sig.iloc[i, sig.columns.get_loc("signal")] = 1.0
            sig.iloc[i, sig.columns.get_loc("stop")] = df["close"].iloc[i] - stop_atr * a.iloc[i]
            last = i
    return sig


dvol_spike_long.MAX_HOLD = 72


def dvol_regime(df, mode="both", stop_atr=2.0):
    c = _cur(df)
    lo, hi = DVOL_CUTS[c]
    sig = empty_signals(df)
    r1 = df["close"] / df["open"] - 1
    r7 = df["close"] / df["close"].shift(7) - 1
    a = atr(df, 14)
    dv = df["dvol"]
    s = pd.Series(0.0, index=df.index)
    if mode in ("both", "mr"):
        s = s.where(~(dv >= hi), -np.sign(r1))
    if mode in ("both", "trend"):
        s = s.where(~(dv <= lo), np.sign(r7))
    s = s.fillna(0.0)
    sig["signal"] = s
    sig["stop"] = np.where(s > 0, df["close"] - stop_atr * a, np.where(s < 0, df["close"] + stop_atr * a, np.nan))
    return sig


dvol_regime.MAX_HOLD = 1
