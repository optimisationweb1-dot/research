"""Family mean_reversion: volatility bands and exhaustion (15m / 1h).

All decisions are taken at the CLOSE of bar t from rows <= t (bt/engine.py contract).

Hypotheses
  a  vwap_fade     price > k*ATR away from the UTC-session VWAP, extension has stalled
                   (bar closes against the move) -> fade toward VWAP
  b  bb_revert     close re-enters a Bollinger band (n, z) after a close outside it, only in a
                   range regime (ADX low or DVOL low) -> fade toward the middle band
  c  rsi_pullback  extreme short-horizon move (RSI(2) extreme AND >= m*ATR over 3 bars) AGAINST
                   the 4h trend (4h close vs EMA) -> buy the dip in an uptrend / sell the rip
                   in a downtrend
  d  wick_reject   bar trades to a new N-bar extreme, closes back inside the prior range with a
                   long wick (>= w of range, range >= r*ATR) -> fade the failed breakout

Design choices fixed a priori (not tuned; see results/mean_reversion.md)
  * Mean reversion is liquidity provision, so entries are PASSIVE: a limit at close[t] -/+ lim*ATR
    (engine: fills only if price trades strictly through it within LIMIT_TTL bars, maker fee;
    the trades where price runs away immediately are missed - honest adverse selection).
    lim < 0 switches to a market order at open[t+1] (taker + slippage).
  * Fee-aware filter: the distance from the entry to the target must be >= MIN_TGT of price
    (0.4% ~ 3x the base taker round trip, 10x a maker round trip).
  * Stops are structural (beyond the extreme of the last 3 bars) + buf*ATR, with a floor of
    1 ATR from the entry; targets are the mean (VWAP / middle band) or an ATR/R multiple.
  * If long and short fire on the same bar -> no trade.

DATA WORKAROUND (bt/*.py is not edited): bt.data._asof fails under pandas 3
(tz-naive close_time vs tz-aware avail) so load(..., dvol=True) raises MergeError.
It is patched here (same fix as strategies/oi_flow.py). DVOL availability itself
(hourly candle known 1h after its stamp) is kept as in bt.data.
"""
import numpy as np
import pandas as pd

import bt.data as _D
from bt.features import atr, empty_signals, session_vwap

LIMIT_TTL = 2
MAX_HOLD = 24
MIN_TGT = 0.004


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


# ------------------------------------------------------------------ features (all causal)

def bar_minutes(df):
    d = pd.Series(df.index[:200]).diff().dropna()
    return int(d.mode().iloc[0] / pd.Timedelta(minutes=1)) if len(d) else 15


def bars(df, hours):
    return max(1, int(round(hours * 60 / bar_minutes(df))))


def rsi(x, n):
    d = x.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def adx(df, n=14):
    h, l, c = df["high"], df["low"], df["close"]
    up, dn = h.diff(), -l.diff()
    pdm = up.where((up > dn) & (up > 0), 0.0)
    mdm = dn.where((dn > up) & (dn > 0), 0.0)
    a = atr(df, n)
    pdi = 100 * pdm.ewm(alpha=1 / n, adjust=False).mean() / a
    mdi = 100 * mdm.ewm(alpha=1 / n, adjust=False).mean() / a
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False).mean()


def roll_rank(x, n):
    """Percentile rank of x[t] within the previous n values (x[t-n..t-1]); causal."""
    arr = x.to_numpy(float)
    out = np.full(len(arr), np.nan)
    # vectorized via sliding windows on a strided view (n <= a few thousand)
    from numpy.lib.stride_tricks import sliding_window_view
    if len(arr) > n:
        w = sliding_window_view(arr[:-1], n)            # windows ending at t-1
        cur = arr[n:]
        valid = np.isfinite(w).sum(axis=1)
        less = (w < cur[:, None]).sum(axis=1)
        r = np.where(valid >= n // 2, less / np.maximum(valid, 1), np.nan)
        r[~np.isfinite(cur)] = np.nan
        out[n:] = r
    return pd.Series(out, index=x.index)


def htf_trend(df, hours=4, n=50):
    """+1 if the last COMPLETED higher-TF bar closed above its EMA(n), -1 if below."""
    c = df["close"].resample(f"{hours}h", label="left", closed="left").last().dropna()
    e = c.ewm(span=n, adjust=False).mean()
    tr = np.sign(c - e)
    h = pd.DataFrame({"avail": (tr.index + pd.Timedelta(hours=hours)).astype("datetime64[ns, UTC]"),
                      "tr": tr.to_numpy()})
    left = pd.DataFrame({"pos": np.arange(len(df)),
                         "ct": (df.index + pd.Timedelta(minutes=bar_minutes(df))).astype("datetime64[ns, UTC]")})
    m = pd.merge_asof(left, h, left_on="ct", right_on="avail", direction="backward")
    return pd.Series(m["tr"].to_numpy(), index=df.index)


def dvol_rank(df, days=60):
    """Percentile of DVOL within the previous `days` days (hourly sampling)."""
    if "dvol" not in df:
        raise KeyError("dvol column missing - run with --load '{\"dvol\": true}'")
    # hourly sub-sample anchored on absolute time (truncation-invariant): bars whose close is on the hour
    ct = df.index + pd.Timedelta(minutes=bar_minutes(df))
    s = df["dvol"][(ct.minute == 0)]
    r = roll_rank(s, 24 * days)
    return r.reindex(df.index).ffill()


# ------------------------------------------------------------------ order packing

def _pack(df, L, S, A, lim, stop_l, stop_s, tgt_l, tgt_s, min_tgt=MIN_TGT, min_stop_atr=1.0):
    """L/S boolean masks; stops/targets are Series of absolute prices.
    Entry reference = limit price (lim >= 0) or close (market). Enforces stop >= min_stop_atr*ATR
    from entry, target on the right side and >= min_tgt of price away."""
    out = empty_signals(df)
    c = df["close"]
    L = L.fillna(False).astype(bool)
    S = S.fillna(False).astype(bool)
    both = L & S
    L, S = L & ~both, S & ~both
    if lim is not None and lim >= 0:
        e_l, e_s = c - lim * A, c + lim * A
    else:
        e_l, e_s = c, c
    stop_l = np.minimum(stop_l, e_l - min_stop_atr * A)
    stop_s = np.maximum(stop_s, e_s + min_stop_atr * A)
    okL = L & (tgt_l - e_l >= min_tgt * e_l)
    okS = S & (e_s - tgt_s >= min_tgt * e_s)
    sig = np.where(okL, 1.0, np.where(okS, -1.0, 0.0))
    out["signal"] = sig
    out["stop"] = np.where(okL, stop_l, np.where(okS, stop_s, np.nan))
    out["target"] = np.where(okL, tgt_l, np.where(okS, tgt_s, np.nan))
    if lim is not None and lim >= 0:
        out["entry_limit"] = np.where(okL, e_l, np.where(okS, e_s, np.nan))
    bad = (out["signal"] != 0) & ~np.isfinite(out["stop"])
    out.loc[bad, "signal"] = 0.0
    return out


def session_mask(df, session="all"):
    """'all' -> every bar; 'quiet' -> decision bar closes in 00:00-08:00 UTC (Asia) or on a weekend;
    'active' -> the complement (weekday 08:00-24:00 UTC)."""
    if session == "all":
        return pd.Series(True, index=df.index)
    ct = df.index + pd.Timedelta(minutes=bar_minutes(df))
    q = pd.Series((ct.hour < 8) | (ct.dayofweek >= 5), index=df.index)
    return q if session == "quiet" else ~q


def _first_per_day(mask, df):
    """Keep only the first True of each UTC day (one fade per direction per session)."""
    m = mask.fillna(False).astype(bool)
    day = df.index.floor("1D")
    return m & (m.astype(int).groupby(day).cumsum() == 1)


# ------------------------------------------------------------------ (a) session VWAP deviation fade

def vwap_fade(df, k=3.0, buf=0.5, tgt_frac=1.0, lim=0.0, warm_h=2, once=1, session="all"):
    """Short when close is >= k ATR above the UTC-day VWAP in the last 3 bars, still >= k-1 ATR above,
    and bar t closes down (close < open and close < close[t-1]) - the push stalled. Mirror for longs.
    Target = close - tgt_frac*(close - VWAP). Stop = extreme of last 3 bars + buf*ATR."""
    A = atr(df)
    c, o, h, l = df["close"], df["open"], df["high"], df["low"]
    vw = session_vwap(df, "1D")
    dev = (c - vw) / A
    mins = df.index.hour * 60 + df.index.minute + bar_minutes(df)   # minutes of session at bar close
    warm = mins >= warm_h * 60
    ext_up = dev.rolling(3).max() >= k
    ext_dn = dev.rolling(3).min() <= -k
    S = ext_up & (dev >= k - 1) & (c < o) & (c < c.shift(1)) & warm
    L = ext_dn & (dev <= -(k - 1)) & (c > o) & (c > c.shift(1)) & warm
    ses = session_mask(df, session)
    S, L = S & ses, L & ses
    if once:
        S, L = _first_per_day(S, df), _first_per_day(L, df)
    hi3, lo3 = h.rolling(3).max(), l.rolling(3).min()
    tgt_s = c - tgt_frac * (c - vw)
    tgt_l = c + tgt_frac * (vw - c)
    return _pack(df, L, S, A, lim, lo3 - buf * A, hi3 + buf * A, tgt_l, tgt_s)


vwap_fade.MAX_HOLD = MAX_HOLD
vwap_fade.LIMIT_TTL = LIMIT_TTL


# ------------------------------------------------------------------ (b) Bollinger re-entry in a range regime

def bb_revert(df, n=20, z=2.0, regime="adx20", buf=0.5, lim=0.0, tgt_frac=1.0, session="all"):
    """Close re-enters the (n, z) Bollinger band after a close outside it -> fade to the middle band.
    regime: 'adxNN' -> ADX(14) < NN (trend strength low); 'dvolNN' -> DVOL 60-day percentile < NN/100
    (implied vol low vs the last 60 days); 'none' -> no filter (control)."""
    A = atr(df)
    c, h, l = df["close"], df["high"], df["low"]
    m = c.rolling(n).mean()
    sd = c.rolling(n).std()
    up, dn = m + z * sd, m - z * sd
    S = (c.shift(1) > up.shift(1)) & (c < up)
    L = (c.shift(1) < dn.shift(1)) & (c > dn)
    if regime.startswith("adx"):
        ok = adx(df) < float(regime[3:])
    elif regime.startswith("dvol"):
        ok = dvol_rank(df) < float(regime[4:]) / 100
    else:
        ok = pd.Series(True, index=df.index)
    ok = ok & session_mask(df, session)
    S, L = S & ok, L & ok
    hi3, lo3 = h.rolling(3).max(), l.rolling(3).min()
    tgt_s = c - tgt_frac * (c - m)
    tgt_l = c + tgt_frac * (m - c)
    return _pack(df, L, S, A, lim, lo3 - buf * A, hi3 + buf * A, tgt_l, tgt_s)


bb_revert.MAX_HOLD = MAX_HOLD
bb_revert.LIMIT_TTL = LIMIT_TTL


# ------------------------------------------------------------------ (c) RSI(2) pullback with the 4h trend

def rsi_pullback(df, th=10.0, move=1.5, ema_n=50, tgt_atr=1.5, stop_atr=2.5, lim=0.0, session="all"):
    """Long: 4h trend up (last completed 4h close > EMA(ema_n) on 4h) AND RSI(2) < th AND the 3-bar move
    <= -move*ATR. Short mirror. Target = entry + tgt_atr*ATR, stop = entry - stop_atr*ATR."""
    A = atr(df)
    c = df["close"]
    r2 = rsi(c, 2)
    m3 = (c - c.shift(3)) / A
    tr = htf_trend(df, 4, ema_n)
    L = (tr > 0) & (r2 < th) & (m3 <= -move)
    S = (tr < 0) & (r2 > 100 - th) & (m3 >= move)
    ses = session_mask(df, session)
    L, S = L & ses, S & ses
    # first bar of an episode only
    L &= ~L.shift(1, fill_value=False)
    S &= ~S.shift(1, fill_value=False)
    e_l = c - lim * A if lim is not None and lim >= 0 else c
    e_s = c + lim * A if lim is not None and lim >= 0 else c
    return _pack(df, L, S, A, lim, e_l - stop_atr * A, e_s + stop_atr * A, e_l + tgt_atr * A, e_s - tgt_atr * A)


rsi_pullback.MAX_HOLD = MAX_HOLD
rsi_pullback.LIMIT_TTL = LIMIT_TTL


# ------------------------------------------------------------------ (d) long-wick rejection at N-bar extremes

def wick_reject(df, n=48, w=0.6, r=1.5, buf=0.25, rr=1.5, lim=0.0, session="all"):
    """Bar t makes a new n-bar high (high > max of previous n highs), closes back below that prior high,
    upper wick >= w of the bar range and range >= r*ATR(prev) -> short. Mirror for lows.
    Stop = wick extreme + buf*ATR; target = rr * risk from the entry reference."""
    A = atr(df)
    Ap = A.shift(1)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    ph, pl = h.shift(1).rolling(n).max(), l.shift(1).rolling(n).min()
    rng = (h - l)
    uw = (h - np.maximum(o, c)) / rng.replace(0, np.nan)
    lw = (np.minimum(o, c) - l) / rng.replace(0, np.nan)
    big = rng >= r * Ap
    S = (h > ph) & (c < ph) & (uw >= w) & big
    L = (l < pl) & (c > pl) & (lw >= w) & big
    ses = session_mask(df, session)
    L, S = L & ses, S & ses
    stop_s, stop_l = h + buf * A, l - buf * A
    e_l = c - lim * A if lim is not None and lim >= 0 else c
    e_s = c + lim * A if lim is not None and lim >= 0 else c
    risk_l = e_l - np.minimum(stop_l, e_l - A)
    risk_s = np.maximum(stop_s, e_s + A) - e_s
    return _pack(df, L, S, A, lim, stop_l, stop_s, e_l + rr * risk_l, e_s - rr * risk_s)


wick_reject.MAX_HOLD = MAX_HOLD
wick_reject.LIMIT_TTL = LIMIT_TTL


# ------------------------------------------------------------------ LEAD (outside the MR family): alt residual vs BTC
# IS event study (2023-2024 only) showed that FADING an alt's 4h idiosyncratic move (residual vs BTC)
# loses in both IS years, i.e. residuals CONTINUE. Tested separately as a clearly labelled lead;
# it does not count toward the mean_reversion family verdict.

_BTC_CACHE = {}


def _btc_returns(tf_minutes):
    if tf_minutes not in _BTC_CACHE:
        tf = {5: "5m", 15: "15m", 60: "1h", 240: "4h"}[tf_minutes]
        b = _D.load("BTCUSDT", tf)
        _BTC_CACHE[tf_minutes] = np.log(b["close"]).diff()
    return _BTC_CACHE[tf_minutes]


def residual_z(df, k_hours=4, beta_days=7):
    """z of the k-bar alt return net of beta*BTC return; beta and residual sd over the previous beta_days."""
    r = np.log(df["close"]).diff()
    rb = _btc_returns(bar_minutes(df)).reindex(df.index)
    n, k = bars(df, 24 * beta_days), bars(df, k_hours)
    beta = r.rolling(n).cov(rb) / rb.rolling(n).var()
    e1 = r - beta * rb
    res = r.rolling(k).sum() - beta * rb.rolling(k).sum()
    return res / (e1.rolling(n).std() * np.sqrt(k))


def residual_follow(df, k_hours=4, z=3.0, stop_atr=2.0, rr=1.5, mode="follow"):
    """Alt residual vs BTC over k hours crosses |z| -> follow it (mode='fade' trades against it).
    Market entry at open t+1, stop stop_atr*ATR, target rr*risk. No signals on BTC itself."""
    out = empty_signals(df)
    if _looks_like_btc(df):          # no residual for BTC itself
        return out
    A = atr(df)
    c = df["close"]
    rz = residual_z(df, k_hours)
    up = (rz >= z) & ~(rz.shift(1) >= z)
    dn = (rz <= -z) & ~(rz.shift(1) <= -z)
    L, S = (up, dn) if mode == "follow" else (dn, up)
    stop_l, stop_s = c - stop_atr * A, c + stop_atr * A
    return _pack(df, L, S, A, -1, stop_l, stop_s, c + rr * stop_atr * A, c - rr * stop_atr * A,
                 min_tgt=0.0, min_stop_atr=0.0)


def _looks_like_btc(df):
    rb = _btc_returns(bar_minutes(df)).reindex(df.index)
    r = np.log(df["close"]).diff()
    m = r.notna() & rb.notna()
    return bool(m.sum() > 100 and np.allclose(r[m].to_numpy()[:500], rb[m].to_numpy()[:500]))


residual_follow.MAX_HOLD = MAX_HOLD
