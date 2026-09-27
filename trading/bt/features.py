"""Causal feature helpers: every value at row t uses rows <= t only.

Never use shift(-k), centered windows, or full-sample statistics (mean/std over
the whole frame) inside a strategy. Normalize with rolling windows.
"""
import numpy as np
import pandas as pd


def atr(df, n=14):
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def ema(x, n):
    return x.ewm(span=n, adjust=False).mean()


def rvol(df, n=96):
    """Volume relative to the rolling median of the previous n bars."""
    return df["volume"] / df["volume"].shift(1).rolling(n, min_periods=n // 2).median()


def rrange(df, n=96):
    rng = df["high"] - df["low"]
    return rng / rng.shift(1).rolling(n, min_periods=n // 2).median()


def delta_share(df):
    return (df["delta"] / df["volume"]).replace([np.inf, -np.inf], np.nan).fillna(0)


def cvd(df, n=None):
    """Cumulative volume delta; rolling sum if n is given."""
    return df["delta"].cumsum() if n is None else df["delta"].rolling(n).sum()


def zscore(x, n):
    m = x.rolling(n, min_periods=n // 2).mean()
    s = x.rolling(n, min_periods=n // 2).std()
    return (x - m) / s


def confirmed_swings(df, k=5):
    """Swing high/low confirmed k bars later. Returns (last_swing_high, last_swing_low)
    known at each bar's close: a pivot at bar j becomes visible at bar j+k."""
    h, l = df["high"], df["low"]
    win = 2 * k + 1
    is_ph = h.rolling(win).max() == h.shift(k)
    is_pl = l.rolling(win).min() == l.shift(k)
    sh = h.shift(k).where(is_ph).ffill()
    sl = l.shift(k).where(is_pl).ffill()
    return sh, sl


def donchian(df, n):
    """Highest high / lowest low of the PREVIOUS n bars (excludes current bar)."""
    return df["high"].shift(1).rolling(n).max(), df["low"].shift(1).rolling(n).min()


def session_vwap(df, anchor="1D"):
    tp = (df["high"] + df["low"] + df["close"]) / 3
    key = df.index.floor(anchor)
    pv = (tp * df["volume"]).groupby(key).cumsum()
    v = df["volume"].groupby(key).cumsum()
    return pv / v


def minute_of_day(df):
    return df.index.hour * 60 + df.index.minute


def empty_signals(df):
    return pd.DataFrame({"signal": 0.0, "stop": np.nan, "target": np.nan, "entry_limit": np.nan,
                         "exit_signal": 0.0}, index=df.index)
