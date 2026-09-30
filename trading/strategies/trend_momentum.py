"""Family trend_momentum: classic trend-following / time-series momentum baselines.

All decisions at the CLOSE of bar t; the engine enters at open t+1 (taker).

  a  donchian      N-bar close breakout, stop = k*ATR(20), trailing exit on the opposite M=N/2 channel.
  b  ema_pullback  EMA fast/slow trend; entry after a pullback that touched the fast EMA, on a
                   resumption bar (close beyond previous bar's extreme); stop k*ATR; exit on close
                   through the slow EMA.
  c  tsmom         time-series momentum: z = log(c/c[t-K]) / (sigma_bar*sqrt(K)); enter when |z| > z0,
                   exit when the sign of the K-bar return flips; vol-scaled stop ks*sigma*sqrt(min(K, 7d)).
  d  mtf           completed-4h EMA trend filter + lower-tf (15m/1h) N-bar breakout entry; stop
                   k*ATR(4h); exit when price closes through the last m4 completed 4h bars' channel or
                   the 4h trend flips.
  e  donchian(regime=...)  (a) with a volatility regime filter: Deribit DVOL or 7-day realized vol,
                   percentile inside the trailing 90 days, below/above the median.

ENGINE WORKAROUNDS (bt/*.py is not edited):
  1) exit_signal in bt.engine closes a position of ANY direction, while trailing exits are
     direction-specific. Each strategy therefore mirrors the engine's position bookkeeping
     causally (_mirror): it knows at bar t whether the engine holds a long/short (entry at open t+1,
     stop hit when low/high crosses the stop, same-bar re-entry rules) and emits exit_signal only for
     the position that is open. The mirror uses only bars <= t (check_lookahead passes).
  2) Time exit is implemented through exit_signal as max_days * bars_per_day, so one function
     works for every timeframe (engine MAX_HOLD is a fixed bar count).
  3) bt.data._asof fails under pandas 3 (tz-naive close_time vs tz-aware avail) -> patched here,
     needed for load(dvol=True).
"""
import math

import numpy as np
import pandas as pd

import bt.data as _D
from bt.features import atr, donchian as _donch, ema, empty_signals


# --------------------------------------------------------------------------- data workaround

def _asof_fixed(df, ext, cols, avail_col="avail"):
    ct = pd.to_datetime(df["close_time"])
    if ct.dt.tz is None:
        ct = ct.dt.tz_localize("UTC")
    left = pd.DataFrame({"pos": np.arange(len(df)),
                         "close_time": ct.dt.tz_convert("UTC").astype("datetime64[ns, UTC]").to_numpy()})
    left["close_time"] = pd.to_datetime(left["close_time"], utc=True).astype("datetime64[ns, UTC]")
    right = ext[[avail_col] + cols].copy()
    right[avail_col] = pd.to_datetime(right[avail_col], utc=True).astype("datetime64[ns, UTC]")
    right = right.sort_values(avail_col)
    m = pd.merge_asof(left.sort_values("close_time"), right, left_on="close_time", right_on=avail_col,
                      direction="backward").sort_values("pos")
    out = df.copy()
    for c in cols:
        out[c] = m[c].to_numpy()
    return out


_D._asof = _asof_fixed


# --------------------------------------------------------------------------- helpers

def _bar_dt(df):
    d = pd.Series(df.index[1:201]) - pd.Series(df.index[:200])
    return d.median() if len(d) else pd.Timedelta("1h")


def _bpd(df):
    return max(1, int(round(pd.Timedelta("1D") / _bar_dt(df))))


def _shift(x, d, fill):
    x = np.asarray(x)
    if d <= 0:
        return x
    out = np.empty_like(x)
    out[:d] = fill
    out[d:] = x[:-d]
    return out


def _mirror(df, go_long, go_short, stop_long, stop_short, exit_long, exit_short, max_bars, delay=0):
    """Replicate bt.engine.simulate's position state causally and emit the signal frame.

    go_*/exit_* boolean arrays, stop_* price arrays, all decided at the close of bar t.
    delay > 0 (robustness diagnostic only): entry decisions and their stop levels are acted on
    `delay` bars later.
    """
    go_long, go_short = _shift(go_long, delay, False), _shift(go_short, delay, False)
    stop_long, stop_short = _shift(stop_long, delay, np.nan), _shift(stop_short, delay, np.nan)
    o = df["open"].to_numpy(float).tolist()
    h = df["high"].to_numpy(float).tolist()
    l = df["low"].to_numpy(float).tolist()
    gl, gs = np.asarray(go_long, bool).tolist(), np.asarray(go_short, bool).tolist()
    sl, ss = np.asarray(stop_long, float).tolist(), np.asarray(stop_short, float).tolist()
    xl, xs = np.asarray(exit_long, bool).tolist(), np.asarray(exit_short, bool).tolist()
    n = len(o)
    sig = np.zeros(n)
    stp = np.full(n, np.nan)
    ex = np.zeros(n)
    pos, k0, stop, pend, pstop = 0, -1, math.nan, 0, math.nan
    for t in range(n):
        if pend:                                   # market entry at open of t
            d, pend = pend, 0
            e = o[t]
            if not ((d > 0 and e <= pstop) or (d < 0 and e >= pstop)):
                pos, k0, stop = d, t, pstop
                if (d > 0 and l[t] <= stop) or (d < 0 and h[t] >= stop):
                    pos = 0                        # stopped on the fill bar; signal at t allowed
        elif pos:
            if (pos > 0 and l[t] <= stop) or (pos < 0 and h[t] >= stop):
                pos = 0                            # stopped at t; engine re-checks signal at t
        if pos:
            if t - k0 + 1 >= max_bars or (pos > 0 and xl[t]) or (pos < 0 and xs[t]):
                ex[t] = 1.0                        # exit at open t+1; next signal allowed at t+1
                pos = 0
            continue
        if gl[t] and sl[t] == sl[t] and not gs[t]:
            sig[t], stp[t], pend, pstop = 1.0, sl[t], 1, sl[t]
        elif gs[t] and ss[t] == ss[t] and not gl[t]:
            sig[t], stp[t], pend, pstop = -1.0, ss[t], -1, ss[t]
    out = empty_signals(df)
    out["signal"], out["stop"], out["exit_signal"] = sig, stp, ex
    return out


def _side(go_long, go_short, side):
    if side == "long":
        go_short = np.zeros(len(go_short), bool)
    elif side == "short":
        go_long = np.zeros(len(go_long), bool)
    return go_long, go_short


def _pct_rank(x, w, minp):
    return x.rolling(w, min_periods=minp).rank(pct=True)


def _regime_mask(df, regime, bpd):
    if regime in (None, "none"):
        return np.ones(len(df), bool)
    src, lvl = regime.split("_")
    w, minp = 90 * bpd, 30 * bpd
    if src == "dvol":
        x = df["dvol"]
    elif src == "rv":
        x = np.log(df["close"]).diff().rolling(7 * bpd, min_periods=3 * bpd).std()
    else:
        raise ValueError(regime)
    p = _pct_rank(x, w, minp)
    m = (p <= 0.5) if lvl == "lo" else (p > 0.5)
    return m.fillna(False).to_numpy(bool)


# --------------------------------------------------------------------------- (a) + (e)

def donchian(df, n=55, k=2.0, m=None, atr_n=20, max_days=60, side="both", regime="none", delay=0):
    bpd = _bpd(df)
    c = df["close"]
    hi, lo = _donch(df, n)
    mm = m or max(2, n // 2)
    xhi, xlo = _donch(df, mm)
    a = atr(df, atr_n)
    ok = _regime_mask(df, regime, bpd)
    gl = ((c > hi).to_numpy() & ok)
    gs = ((c < lo).to_numpy() & ok)
    gl, gs = _side(gl, gs, side)
    return _mirror(df, gl, gs, (c - k * a).to_numpy(), (c + k * a).to_numpy(),
                   (c < xlo).to_numpy(), (c > xhi).to_numpy(), max_days * bpd, delay)


# --------------------------------------------------------------------------- (b)

def ema_pullback(df, pair="20_100", k=2.0, lookback=5, atr_n=20, max_days=60, side="both", delay=0):
    bpd = _bpd(df)
    fast, slow = (int(x) for x in pair.split("_"))
    c, h, l = df["close"], df["high"], df["low"]
    ef, es = ema(c, fast), ema(c, slow)
    a = atr(df, atr_n)
    warm = np.arange(len(df)) >= slow
    up = (ef > es) & (c > es)
    dn = (ef < es) & (c < es)
    touch_l = (l <= ef).astype(float).rolling(lookback, min_periods=1).max() > 0
    touch_s = (h >= ef).astype(float).rolling(lookback, min_periods=1).max() > 0
    gl = (up & touch_l & (c > h.shift(1)) & (c > ef)).to_numpy() & warm
    gs = (dn & touch_s & (c < l.shift(1)) & (c < ef)).to_numpy() & warm
    gl, gs = _side(gl, gs, side)
    return _mirror(df, gl, gs, (c - k * a).to_numpy(), (c + k * a).to_numpy(),
                   (c < es).to_numpy(), (c > es).to_numpy(), max_days * bpd, delay)


# --------------------------------------------------------------------------- (c)

def tsmom(df, K=72, z0=1.0, ks=1.0, vol_days=30, max_days=60, side="both", delay=0):
    bpd = _bpd(df)
    c = df["close"]
    lc = np.log(c)
    w = vol_days * bpd
    sig = lc.diff().rolling(w, min_periods=w // 2).std()
    z = (lc - lc.shift(K)) / (sig * math.sqrt(K))
    dist = ks * sig * math.sqrt(min(K, 7 * bpd))
    gl = (z > z0).to_numpy()
    gs = (z < -z0).to_numpy()
    gl, gs = _side(gl, gs, side)
    return _mirror(df, gl, gs, (c * (1 - dist)).to_numpy(), (c * (1 + dist)).to_numpy(),
                   (z < 0).to_numpy(), (z > 0).to_numpy(), max_days * bpd, delay)


# --------------------------------------------------------------------------- (d)

def _htf(df, rule="4h"):
    """Completed higher-timeframe bars; returns (frame indexed by HTF close time)."""
    ht = df.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna(subset=["open"])
    ht.index = ht.index + pd.Timedelta(rule)       # stamp = HTF close time
    return ht


def _to_ltf(s, df):
    ct = df.index + _bar_dt(df)
    return s.reindex(ct, method="ffill").to_numpy(float)


def mtf(df, n=20, htf="ema20_50", k=2.0, m4=10, atr_n=20, max_days=60, side="both", delay=0):
    bpd = _bpd(df)
    c = df["close"]
    ht = _htf(df, "4h")
    f, s = (int(x) for x in htf.replace("ema", "").split("_"))
    ef, es = ema(ht["close"], f), ema(ht["close"], s)
    warm = pd.Series(np.arange(len(ht)) >= s, index=ht.index)
    up4 = _to_ltf(((ef > es) & warm).astype(float), df) > 0.5
    dn4 = _to_ltf(((ef < es) & warm).astype(float), df) > 0.5
    a4 = _to_ltf(atr(ht, atr_n), df)
    clo4 = _to_ltf(ht["low"].rolling(m4).min(), df)
    chi4 = _to_ltf(ht["high"].rolling(m4).max(), df)
    hi, lo = _donch(df, n)
    cc = c.to_numpy(float)
    gl = (c > hi).to_numpy() & up4
    gs = (c < lo).to_numpy() & dn4
    gl, gs = _side(gl, gs, side)
    xl = (cc < clo4) | ~up4
    xs = (cc > chi4) | ~dn4
    return _mirror(df, gl, gs, cc - k * a4, cc + k * a4, xl, xs, max_days * bpd, delay)


# the engine's MAX_HOLD stays unset (time exit is done via exit_signal)
for _f in (donchian, ema_pullback, tsmom, mtf):
    _f.MAX_HOLD = None
