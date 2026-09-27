"""Volume absorption family: "big volume enters, the candle looks ordinary" and relatives.

All decisions are taken at the CLOSE of bar t from rows <= t (see bt/engine.py contract).

Common design choices (fixed a priori, not tuned):
  * Volume and range are normalized by TIME-OF-DAY seasonality: value / median of the same
    5m/15m slot over the previous 20 days. Raw RVOL on intraday crypto is dominated by the US
    open, funding times and hourly candle boundaries; a professional compares a bar with the
    same slot on previous days, not with the last few hours.
  * delta share = (taker buy - taker sell) / volume, in [-1, 1]; CLV = (close - low) / range.
  * Stop beyond the structural extreme + buf * ATR(14), with a fee-aware floor: risk >= 0.4%
    of price (= 4x the base round-trip taker cost), so costs stay <= ~0.3R per trade.
  * Target = m * risk from the reference entry (close[t] for market, limit price for limit),
    plus a time exit after MAX_HOLD = 48 bars (4h on 5m, 12h on 15m).
  * If long and short fire on the same bar, no trade.

Strategies (hypotheses a-e of the task):
  absorb       (a) absorption fade; (b) with ctx in {sweep, vwap, swing}; optional OI filter
  climax_fade  (c) climax exhaustion at an N-bar extreme, reversal after a confirmation bar
  climax_cont  (d) climax continuation: N-bar breakout with volume + delta confirmation
  cvd_div      (e) price makes an N-bar high/low but net taker flow since the previous extreme
                   points the other way
"""
import numpy as np
import pandas as pd

from bt.features import atr, confirmed_swings, delta_share, donchian, empty_signals, minute_of_day, session_vwap

MAX_HOLD = 48
LIMIT_TTL = 3
MIN_RISK = 0.004     # fee-aware stop floor, fraction of price
SEASON_DAYS = 20


# ----------------------------------------------------------------------------- features

def seasonal_ratio(x, df, days=SEASON_DAYS):
    """x / median of x at the same minute-of-day over the previous `days` days (causal)."""
    slot = minute_of_day(df)
    base = x.groupby(slot).transform(lambda s: s.shift(1).rolling(days, min_periods=days // 2).median())
    return (x / base.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)


def bars_per_day(df):
    step = pd.Series(df.index[:200]).diff().median()
    return int(round(pd.Timedelta("1D") / step))


def base_features(df):
    rng = df["high"] - df["low"]
    return {
        "rng": rng,
        "srv": seasonal_ratio(df["volume"], df).fillna(0.0),
        "srr": seasonal_ratio(rng, df),
        "ds": delta_share(df),
        "clv": ((df["close"] - df["low"]) / rng).where(rng > 0, 0.5),
        "atr": atr(df),
    }


# ----------------------------------------------------------------------------- orders

def _orders(df, long_m, short_m, stop_l, stop_s, m, lim_l=None, lim_s=None):
    """Build the signal frame; applies the fee-aware stop floor and m*R targets."""
    out = empty_signals(df)
    c = df["close"].to_numpy(float)
    long_m = np.asarray(long_m, bool)
    short_m = np.asarray(short_m, bool)
    both = long_m & short_m
    long_m, short_m = long_m & ~both, short_m & ~both
    ref_l = c if lim_l is None else np.asarray(lim_l, float)
    ref_s = c if lim_s is None else np.asarray(lim_s, float)
    risk_l = np.maximum(ref_l - np.asarray(stop_l, float), MIN_RISK * ref_l)
    risk_s = np.maximum(np.asarray(stop_s, float) - ref_s, MIN_RISK * ref_s)
    long_m &= np.isfinite(risk_l)
    short_m &= np.isfinite(risk_s)
    sig = np.where(long_m, 1.0, np.where(short_m, -1.0, 0.0))
    stop = np.where(long_m, ref_l - risk_l, np.where(short_m, ref_s + risk_s, np.nan))
    tgt = np.where(long_m, ref_l + m * risk_l, np.where(short_m, ref_s - m * risk_s, np.nan))
    out["signal"], out["stop"], out["target"] = sig, stop, tgt
    if lim_l is not None or lim_s is not None:
        out["entry_limit"] = np.where(long_m, ref_l, np.where(short_m, ref_s, np.nan))
    return out


def _set_attrs(fn):
    fn.MAX_HOLD = MAX_HOLD
    fn.LIMIT_TTL = LIMIT_TTL
    return fn


# ----------------------------------------------------------------------------- (a) + (b)

def absorb(df, k=2.0, r=1.2, d=0.15, m=2.0, buf=0.25, ctx="none", N=48, zv=1.5, lim=0.0, oi=0, side=1):
    """Absorption fade.

    Long: seasonal RVOL >= k, seasonal range <= r (the candle looks ordinary), aggressive
    sellers (delta share <= -d) and yet the close is in the upper half (CLV >= 0.5): a passive
    buyer absorbed the market selling. Short is the mirror.
    ctx: none | sweep (bar takes out the prior N-bar low/high and closes back inside) |
         vwap (close is >= zv rolling std below/above the daily VWAP) |
         swing (bar tests/pierces the last confirmed swing low/high, k=5, and closes beyond it).
    oi=1: open interest rose during the bar (new positions were opened into the passive side).
    lim>0: limit entry at close - lim*(close - low) (long) instead of market at next open.
    side=-1: trade WITH the aggressor instead (absorption fails): sellers aggressive + close in
    the upper half -> short. Added after the in-sample event study showed a negative sign.
    """
    f = base_features(df)
    o, h, l, c = (df[x] for x in ("open", "high", "low", "close"))
    core = (f["srv"] >= k) & (f["srr"] <= r)
    L = core & (f["ds"] <= -d) & (f["clv"] >= 0.5)
    S = core & (f["ds"] >= d) & (f["clv"] <= 0.5)
    A = f["atr"]
    if ctx == "sweep":
        dh, dl = donchian(df, N)
        L &= (l < dl) & (c > dl)
        S &= (h > dh) & (c < dh)
    elif ctx == "vwap":
        dev = c - session_vwap(df)
        w = 20 * bars_per_day(df)
        z = dev / dev.rolling(w, min_periods=w // 2).std()
        L &= z <= -zv
        S &= z >= zv
    elif ctx == "swing":
        sh, sl = confirmed_swings(df, 5)
        L &= (l <= sl + 0.25 * A) & (c > sl)
        S &= (h >= sh - 0.25 * A) & (c < sh)
    elif ctx != "none":
        raise ValueError(ctx)
    if oi:
        doi = df["oi"].diff()
        L &= doi > 0
        S &= doi > 0
    if side < 0:
        L, S = S, L
    stop_l, stop_s = l - buf * A, h + buf * A
    lim_l = lim_s = None
    if lim > 0:
        lim_l, lim_s = c - lim * (c - l), c + lim * (h - c)
    return _orders(df, L.fillna(False), S.fillna(False), stop_l, stop_s, m, lim_l, lim_s)


# ----------------------------------------------------------------------------- (c)

def climax_fade(df, k=3.0, r=2.0, d=0.1, conf=0.5, N=48, m=2.0, buf=0.25, lim=0.0):
    """Climax exhaustion fade.

    Bar t-1 (climax, down case): seasonal RVOL >= k, seasonal range >= r, red candle with
    aggressive selling (delta share <= -d) and a new N-bar low. Bar t (confirmation): green
    and closes above low[t-1] + conf * range[t-1]. Long at next open, stop below the lower
    of the two lows. Mirror for up-climax -> short.
    """
    f = base_features(df)
    o, h, l, c = (df[x] for x in ("open", "high", "low", "close"))
    dh, dl = donchian(df, N)
    rng = f["rng"]
    big = (f["srv"] >= k) & (f["srr"] >= r)
    dn = big & (c < o) & (f["ds"] <= -d) & (l < dl)
    up = big & (c > o) & (f["ds"] >= d) & (h > dh)
    L = dn.shift(1, fill_value=False) & (c > o) & (c > l.shift(1) + conf * rng.shift(1))
    S = up.shift(1, fill_value=False) & (c < o) & (c < h.shift(1) - conf * rng.shift(1))
    A = f["atr"]
    lo2 = np.minimum(l, l.shift(1))
    hi2 = np.maximum(h, h.shift(1))
    stop_l, stop_s = lo2 - buf * A, hi2 + buf * A
    lim_l = lim_s = None
    if lim > 0:
        lim_l, lim_s = c - lim * (c - lo2), c + lim * (hi2 - c)
    return _orders(df, L.fillna(False), S.fillna(False), stop_l, stop_s, m, lim_l, lim_s)


# ----------------------------------------------------------------------------- (d)

def climax_cont(df, k=3.0, r=1.5, d=0.15, N=48, m=2.0, buf=0.25, lim=0.0):
    """Climax continuation / breakout.

    Long: close breaks above the prior N-bar high on seasonal RVOL >= k, seasonal range >= r,
    delta share >= d (aggressive buyers drove it) and CLV >= 0.7 (closed near the high).
    Stop below the bar low - buf*ATR. lim>0: limit at close - lim*(close - low) (pullback into
    the breakout bar) instead of market. Mirror for shorts.
    """
    f = base_features(df)
    h, l, c = (df[x] for x in ("high", "low", "close"))
    dh, dl = donchian(df, N)
    big = (f["srv"] >= k) & (f["srr"] >= r)
    L = big & (c > dh) & (f["ds"] >= d) & (f["clv"] >= 0.7)
    S = big & (c < dl) & (f["ds"] <= -d) & (f["clv"] <= 0.3)
    A = f["atr"]
    stop_l, stop_s = l - buf * A, h + buf * A
    lim_l = lim_s = None
    if lim > 0:
        lim_l, lim_s = c - lim * (c - l), c + lim * (h - c)
    return _orders(df, L.fillna(False), S.fillna(False), stop_l, stop_s, m, lim_l, lim_s)


# ----------------------------------------------------------------------------- (e)

def _prior_extreme_idx(x, N, fn):
    """Absolute index of argmax/argmin of x over the previous N bars (excluding t); -1 if n/a."""
    n = len(x)
    idx = np.full(n, -1, dtype=np.int64)
    if n <= N:
        return idx
    win = np.lib.stride_tricks.sliding_window_view(x[:-1], N)   # win[i] = x[i : i+N] -> prior bars of t=i+N
    rel = fn(win, axis=1)
    idx[N:] = np.arange(n - N) + rel
    return idx


def cvd_div(df, N=48, d=0.05, conf=1, m=2.0, buf=0.25, gap=3, lim=0.0):
    """Rolling CVD divergence.

    Short: high[t] exceeds the prior N-bar high (made at bar j, t - j >= gap), but net taker
    flow since j is negative: (CVD[t] - CVD[j]) / volume(j+1..t) <= -d, i.e. price made a
    higher high while CVD made a lower high. conf=1 additionally needs the bar to close back
    below the old high (failed breakout). Stop above high[t] + buf*ATR. Mirror for longs.
    """
    f = base_features(df)
    h, l, c = (df[x].to_numpy(float) for x in ("high", "low", "close"))
    cd = df["delta"].cumsum().to_numpy(float)
    cv = df["volume"].cumsum().to_numpy(float)
    n = len(df)
    t = np.arange(n)
    jh = _prior_extreme_idx(h, N, np.argmax)
    jl = _prior_extreme_idx(l, N, np.argmin)
    okh, okl = jh >= 0, jl >= 0
    jh0, jl0 = np.where(okh, jh, 0), np.where(okl, jl, 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        flow_h = (cd - cd[jh0]) / (cv - cv[jh0])
        flow_l = (cd - cd[jl0]) / (cv - cv[jl0])
    S = okh & (h > h[jh0]) & (t - jh0 >= gap) & (flow_h <= -d)
    L = okl & (l < l[jl0]) & (t - jl0 >= gap) & (flow_l >= d)
    if conf:
        S &= c < h[jh0]
        L &= c > l[jl0]
    A = f["atr"].to_numpy(float)
    stop_l, stop_s = l - buf * A, h + buf * A
    lim_l = lim_s = None
    if lim > 0:
        lim_l, lim_s = c - lim * (c - l), c + lim * (h - c)
    return _orders(df, np.nan_to_num(L).astype(bool), np.nan_to_num(S).astype(bool), stop_l, stop_s, m, lim_l, lim_s)


for _fn in (absorb, climax_fade, climax_cont, cvd_div):
    _set_attrs(_fn)
strategy = absorb
