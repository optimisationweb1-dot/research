"""Coinbase-premium strategies (pre-registered in research/coinbase_premium_prereg.md).

All follow the bt.engine CONTRACT: decision at the CLOSE of bar t from rows <= t, market entry at open[t+1].
Premium features arrive as columns cbp_<name> via strategies.coinbase_premium_feat.merge_into (value of the
Coinbase hour known at its close). If the columns are missing, the strategy merges them itself, so the
functions also work with bt.engine.run / bt.runner (asset inferred from the `asset` param).

A  premium_long   : long while signal z > z_in; exit when z < 0 or MAX_HOLD; vol-scaled catastrophic stop.
B  premium_short  : mirror image (z < -z_in).
C  donchian_filter: 4h Donchian(20) breakout long, stop 2*ATR(14), exit on 10-bar low; optional premium filter.
D  daily_etf      : 1h bars, decide only at 00:00 UTC: long if P24 > 0 and/or last known ETF flow > 0.
"""
import numpy as np
import pandas as pd

from bt.features import atr, donchian, empty_signals
from strategies.coinbase_premium_feat import merge_etf, merge_into


def _ensure(df, asset, need_etf=False, lag_hours=0):
    if "cbp_L" not in df:
        df = merge_into(df, asset, lag_hours=lag_hours)
    if need_etf and "etf_flow" not in df:
        df = merge_etf(df, asset)
    return df


def _vol_stop_dist(df, hold, k=2.5):
    """k * std of 24h log returns over the previous 30 days, scaled to the holding period."""
    r24 = np.log(df["close"]).diff(24)
    sd = r24.rolling(720, min_periods=360).std()
    return k * sd * np.sqrt(max(1.0, hold / 24)) * df["close"]


def premium_long(df, asset="btc", z_in=1.0, hold=72, sig="L", k_stop=2.5, lag_hours=0):
    df = _ensure(df, asset, lag_hours=lag_hours)
    z = df["cbp_" + sig]
    out = empty_signals(df)
    dist = _vol_stop_dist(df, hold, k_stop)
    on = (z > z_in) & dist.notna()
    out.loc[on, "signal"] = 1.0
    out.loc[on, "stop"] = (df["close"] - dist)[on]
    out["exit_signal"] = (z < 0).astype(float)
    return out


def premium_short(df, asset="btc", z_in=1.0, hold=72, sig="L", k_stop=2.5, lag_hours=0):
    df = _ensure(df, asset, lag_hours=lag_hours)
    z = df["cbp_" + sig]
    out = empty_signals(df)
    dist = _vol_stop_dist(df, hold, k_stop)
    on = (z < -z_in) & dist.notna()
    out.loc[on, "signal"] = -1.0
    out.loc[on, "stop"] = (df["close"] + dist)[on]
    out["exit_signal"] = (z > 0).astype(float)
    return out


def donchian_filter(df, asset="btc", filt="none", n_in=20, n_out=10, k_atr=2.0):
    """filt: none | adj (P24 > 0) | raw (P24raw > 0) | adj_neg (P24 <= 0, the complement)."""
    df = _ensure(df, asset)
    hi, _ = donchian(df, n_in)
    _, lo = donchian(df, n_out)
    a = atr(df, 14)
    out = empty_signals(df)
    on = (df["close"] > hi) & a.notna() & hi.notna()
    if filt == "adj":
        on &= df["cbp_P24"] > 0
    elif filt == "raw":
        on &= df["cbp_P24raw"] > 0
    elif filt == "adj_neg":
        on &= df["cbp_P24"] <= 0
    out.loc[on, "signal"] = 1.0
    out.loc[on, "stop"] = (df["close"] - k_atr * a)[on]
    out["exit_signal"] = (df["close"] < lo).astype(float)
    return out


def daily_etf(df, asset="btc", mode="both", hold=24, k_stop=2.5):
    """mode: both | prem | flow | all (every day, the drift baseline)."""
    df = _ensure(df, asset, need_etf=True)
    out = empty_signals(df)
    at_midnight = (df["close_time"].dt.hour == 0) & (df["close_time"].dt.minute == 0)
    dist = _vol_stop_dist(df, hold, k_stop)
    cond = at_midnight & dist.notna() & df["etf_flow"].notna() & df["cbp_P24"].notna()
    if mode in ("both", "prem"):
        cond &= df["cbp_P24"] > 0
    if mode in ("both", "flow"):
        cond &= df["etf_flow"] > 0
    out.loc[cond, "signal"] = 1.0
    out.loc[cond, "stop"] = (df["close"] - dist)[cond]
    return out

