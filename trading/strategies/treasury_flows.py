"""treasury_flows strategies (engine contract, daily bars). Pre-registered H4 in
trading/research/treasury_flows_prereg.md.

flow7[D] = sum over the 7 days ending at the CLOSE of daily bar D of:
    US spot ETF net flow of day D-1 (flow of day X is treated as known at X+2 00:00 UTC = close of bar X+1)
  + USD of treasury purchases whose 8-K was accepted before the close of bar D (Strategy for BTC;
    BitMine + SharpLink for ETH).
All inputs are causal: row D depends only on information published by D+1 00:00 UTC.
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TR = os.path.dirname(HERE)
_CACHE = {}


def _flows(asset):
    if asset in _CACHE:
        return _CACHE[asset]
    f = pd.read_csv(os.path.join(TR, "research", f"treasury_flows_etf_{asset.lower()}.csv"), index_col=0)
    f.index = pd.to_datetime(f.index).tz_localize("UTC")
    etf = f["total_usd"].copy()
    etf.index = etf.index + pd.Timedelta(days=1)            # flow of day X counted on bar X+1 (known at its close)
    ev = pd.read_csv(os.path.join(TR, "research", "treasury_flows_events.csv"))
    ev = ev[(ev.asset == asset) & (ev["set"] == "primary")]
    t = pd.to_datetime(ev["ann_ts_utc"], utc=True).dt.floor("D")   # announced during bar D -> known at its close
    tr = ev.groupby(t)["usd"].sum()
    idx = pd.date_range("2023-01-01", "2026-12-31", freq="D", tz="UTC")
    x = etf.reindex(idx).fillna(0.0) + tr.reindex(idx).fillna(0.0)
    first = min(etf.index.min(), tr.index.min() if len(tr) else etf.index.min())
    x[x.index < first] = np.nan
    _CACHE[asset] = x
    return x


def _atr(df, n=14):
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def flow_long(df, asset="BTC", pct=0.8, win=7, min_hist=60, atr_mult=3.0, source="all"):
    """H4: long when 7d cumulative inflow >= expanding pct-quantile of its own history."""
    x = _flows(asset) if source == "all" else _flows_src(asset, source)
    s = x.reindex(df.index)
    f7 = s.rolling(win, min_periods=win).sum()
    thr = f7.expanding(min_hist).quantile(pct)
    sig = (f7 >= thr) & thr.notna()
    out = pd.DataFrame(index=df.index)
    out["signal"] = sig.astype(float)
    out["stop"] = df["close"] - atr_mult * _atr(df)
    return out


def mom_long(df, lookback=14, atr_mult=3.0):
    """Control: price momentum only (14d return > 0), same exits."""
    out = pd.DataFrame(index=df.index)
    out["signal"] = (df["close"] > df["close"].shift(lookback)).astype(float)
    out["stop"] = df["close"] - atr_mult * _atr(df)
    return out


def always_long(df, atr_mult=3.0, start=None):
    """Benchmark: always long with the same exit mechanics (re-enter after each exit)."""
    out = pd.DataFrame(index=df.index)
    s = pd.Series(1.0, index=df.index)
    if start is not None:
        s[df.index < pd.Timestamp(start, tz="UTC")] = 0.0
    out["signal"] = s
    out["stop"] = df["close"] - atr_mult * _atr(df)
    return out


def _flows_src(asset, source):
    """source='etf' or 'treasury' only (diagnostic split)."""
    key = (asset, source)
    if key in _CACHE:
        return _CACHE[key]
    f = pd.read_csv(os.path.join(TR, "research", f"treasury_flows_etf_{asset.lower()}.csv"), index_col=0)
    f.index = pd.to_datetime(f.index).tz_localize("UTC")
    etf = f["total_usd"].copy()
    etf.index = etf.index + pd.Timedelta(days=1)
    ev = pd.read_csv(os.path.join(TR, "research", "treasury_flows_events.csv"))
    ev = ev[(ev.asset == asset) & (ev["set"] == "primary")]
    tr = ev.groupby(pd.to_datetime(ev["ann_ts_utc"], utc=True).dt.floor("D"))["usd"].sum()
    idx = pd.date_range("2023-01-01", "2026-12-31", freq="D", tz="UTC")
    x = (etf if source == "etf" else tr).reindex(idx).fillna(0.0)
    first = (etf if source == "etf" else tr).index.min()
    x[x.index < first] = np.nan
    _CACHE[key] = x
    return x
