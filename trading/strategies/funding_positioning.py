"""Family funding_positioning: "smart money vs crowd" from free Binance positioning data.

Data (bt.data.load(..., metrics=True, funding=True)):
  funding           last settled 8h funding rate (known at the settlement time)
  ls_accounts       global long/short ACCOUNT ratio (all accounts = crowd, mostly retail)
  top_ls_positions  top-20% traders (by margin) long/short POSITION-size ratio ("smart money" proxy)
  top_ls_accounts   top-20% traders long/short account ratio
  oi                open interest (contracts)
Metrics (LS, OI) exist only from 2024-01 -> in-sample for those = 2024; funding from 2023.

Hypotheses (decision at the CLOSE of bar t; the engine enters at open t+1):
  A  fcrowd   funding extreme (90d z of 24h mean funding) = crowded side; fade it ONLY after price
              confirms the unwind (close breaks the N-bar extreme against the crowd) -> trend-flip filter.
  A0 fcrowd   same, with trend filter "none" = pure contrarian (control) - reported, not selected by OOS.
  B  topdiv   level divergence: z(log top_ls_positions) - z(log ls_accounts) (30d z). Top traders far more
              long than the crowd -> long (follow top); mirror -> short. Direction set a priori.
  C  rcrowd   retail crowding: 30d percentile of the RESIDUAL of log(ls_accounts) after removing its
              mechanical response to the last 24h/72h price move (crowd buys dips). Extreme -> fade.
  D  oicrowd  crowding + leverage build-up: funding z extreme AND OI 3d change z extreme on the same side
              (new leveraged positions pile into the crowded side) + price confirmation -> fade.

Exits for all: stop = stop_atr x ATR(14) from the signal close, target = rr x risk, time exit MAX_HOLD
(set per timeframe to ~3 days). Funding payments are NOT in the engine; funding_pnl() estimates them
per trade post hoc (diagnostic only).

DATA WORKAROUNDS (bt/*.py is not edited; same issues as documented in results/oi_flow.md):
  1) bt.data._asof fails under pandas 3 (tz-naive close_time vs tz-aware avail) -> patched here.
  2) Binance metrics stamped T describe [T, T+5min); bt.data treats them as known at T+1min. We use
     avail = T + 6min (at a bar close the newest usable snapshot is >= 5 minutes old).
"""
import os

import numpy as np
import pandas as pd

import bt.data as _D
from bt.features import atr, empty_signals

METRICS_LAG = pd.Timedelta(minutes=6)


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


def _merge_metrics_conservative(df, symbol):
    mt = pd.read_parquet(os.path.join(_D.ROOT, "metrics", f"{symbol}.parquet"))
    mt["avail"] = mt["ts"] + METRICS_LAG
    cols = ["sum_open_interest", "sum_open_interest_value", "count_toptrader_long_short_ratio",
            "sum_toptrader_long_short_ratio", "count_long_short_ratio", "sum_taker_long_short_vol_ratio"]
    out = _asof_fixed(df, mt, cols)
    return out.rename(columns={"sum_open_interest": "oi", "sum_open_interest_value": "oi_usd",
                               "count_toptrader_long_short_ratio": "top_ls_accounts",
                               "sum_toptrader_long_short_ratio": "top_ls_positions",
                               "count_long_short_ratio": "ls_accounts",
                               "sum_taker_long_short_vol_ratio": "taker_ls_ratio"})


_D._asof = _asof_fixed
_D.merge_metrics = _merge_metrics_conservative


# ------------------------------------------------------------------ helpers

def bar_minutes(df):
    d = pd.Series(df.index[:200]).diff().dropna()
    return int(d.mode().iloc[0] / pd.Timedelta(minutes=1)) if len(d) else 60


def bars(df, hours):
    return max(1, int(round(hours * 60 / bar_minutes(df))))


def roll_z(x, n):
    m = x.rolling(n, min_periods=n // 2).mean()
    s = x.rolling(n, min_periods=n // 2).std()
    return (x - m) / s


def roll_pct(x, n):
    """Percentile rank of x[t] within the previous n values x[t-n..t-1] (causal), in [0, 1]."""
    arr = x.to_numpy(float)
    out = np.full(len(arr), np.nan)
    from numpy.lib.stride_tricks import sliding_window_view
    if len(arr) <= n:
        return pd.Series(out, index=x.index)
    w = sliding_window_view(arr[:-1], n)          # w[i] = arr[i : i+n], compared with arr[i+n]
    cur = arr[n:]
    valid = np.isfinite(w).sum(axis=1)
    less = (w < cur[:, None]).sum(axis=1) + 0.5 * (w == cur[:, None]).sum(axis=1)
    r = np.where((valid >= n // 2) & np.isfinite(cur), less / np.maximum(valid, 1), np.nan)
    out[n:] = r
    return pd.Series(out, index=x.index)


def logpos(s):
    return np.log(s.where(s > 0))


# ------------------------------------------------------------------ features

def funding_z(df, smooth_h=24, days=90):
    """z-score of the smoothed funding (mean over smooth_h hours of as-of settled funding)."""
    f = df["funding"].rolling(bars(df, smooth_h), min_periods=1).mean()
    return roll_z(f, bars(df, 24 * days))


def oi_chg_z(df, k_hours=72, days=30):
    lo = logpos(df["oi"])
    return roll_z(lo - lo.shift(bars(df, k_hours)), bars(df, 24 * days))


def top_crowd_div(df, days=30):
    """Level divergence: z(log top_ls_positions) - z(log ls_accounts), both 30d z."""
    n = bars(df, 24 * days)
    return roll_z(logpos(df["top_ls_positions"]), n) - roll_z(logpos(df["ls_accounts"]), n)


def crowd_residual(df, days=30):
    """log(ls_accounts) minus its rolling-OLS fit on the last 24h and 72h log returns (causal:
    betas estimated from the previous `days` of data only). Positive = crowd more long than the
    recent price path alone would explain."""
    n = bars(df, 24 * days)
    y = logpos(df["ls_accounts"])
    lc = np.log(df["close"])
    x1 = lc - lc.shift(bars(df, 24))
    x2 = lc - lc.shift(bars(df, 72))
    Y = y.to_numpy(float)
    X = np.column_stack([np.ones(len(df)), x1.to_numpy(float), x2.to_numpy(float)])
    ok = np.isfinite(Y) & np.isfinite(X).all(axis=1)
    Yz, Xz = np.where(ok, Y, 0.0), np.where(ok[:, None], X, 0.0)
    # rolling sums of X'X and X'y over the previous n bars (shifted by 1 -> strictly past fit)
    xx = np.einsum("ti,tj->tij", Xz, Xz)
    xy = Xz * Yz[:, None]
    cxx = np.cumsum(xx, axis=0)
    cxy = np.cumsum(xy, axis=0)
    cn = np.cumsum(ok.astype(float))
    res = np.full(len(df), np.nan)
    for t in range(n + 1, len(df)):
        if not ok[t]:
            continue
        a, b = t - 1, t - 1 - n
        cnt = cn[a] - cn[b]
        if cnt < n // 2:
            continue
        A = cxx[a] - cxx[b]
        v = cxy[a] - cxy[b]
        try:
            beta = np.linalg.solve(A + 1e-9 * np.eye(3), v)
        except np.linalg.LinAlgError:
            continue
        res[t] = Y[t] - X[t] @ beta
    return pd.Series(res, index=df.index)


# ------------------------------------------------------------------ packing

def _pack(df, long_m, short_m, stop_atr, rr):
    out = empty_signals(df)
    c = df["close"].to_numpy(float)
    A = atr(df).to_numpy(float)
    long_m = np.asarray(pd.Series(long_m, index=df.index).fillna(False), dtype=bool)
    short_m = np.asarray(pd.Series(short_m, index=df.index).fillna(False), dtype=bool) & ~long_m
    stop = np.where(long_m, c - stop_atr * A, np.where(short_m, c + stop_atr * A, np.nan))
    risk = np.abs(c - stop)
    tgt = np.where(long_m, c + rr * risk, np.where(short_m, c - rr * risk, np.nan))
    ok = np.isfinite(stop) & (risk > 0)
    sig = np.where(long_m, 1.0, np.where(short_m, -1.0, 0.0))
    out["signal"] = np.where(ok, sig, 0.0)
    out["stop"] = np.where(ok, stop, np.nan)
    out["target"] = np.where(ok & np.isfinite(tgt), tgt, np.nan)
    return out


def _edge(mask):
    """True only on the first bar of a run of True (avoid re-firing every bar of a regime)."""
    m = pd.Series(mask).fillna(False).astype(bool)
    return m & ~m.shift(1, fill_value=False)


def _armed(cond, trig, hold):
    """trig fires while cond was true at any of the last `hold` bars (inclusive) - causal."""
    c = pd.Series(cond).fillna(False).astype(float)
    recent = c.rolling(hold, min_periods=1).max() > 0
    return recent & pd.Series(trig).fillna(False).astype(bool)


def _brk(df, n):
    """close breaks the previous n-bar low (dn) / high (up)."""
    lo = df["low"].shift(1).rolling(n).min()
    hi = df["high"].shift(1).rolling(n).max()
    return df["close"] < lo, df["close"] > hi


# ------------------------------------------------------------------ direction filters

def _apply_trend(df, hi, lo, trend, brk_h, arm_h, ema_days=20):
    """hi = crowd long (-> short), lo = crowd short (-> long). Returns (L, S) entry masks.
    none : fade on the first bar of the extreme (pure contrarian).
    break: fade only when, within arm_h hours after the extreme, close breaks the previous brk_h
           low (short) / high (long) -> the crowded side is being forced out (unwind confirmation).
    ema  : fade only in the direction of the higher-timeframe trend (close vs EMA ema_days):
           crowded longs in a downtrend -> short; crowded shorts in an uptrend -> long."""
    if trend == "none":
        return _edge(lo), _edge(hi)
    if trend == "break":
        dn, up = _brk(df, bars(df, brk_h))
        arm = bars(df, arm_h)
        return _edge(_armed(lo, up, arm)), _edge(_armed(hi, dn, arm))
    if trend == "ema":
        e = df["close"].ewm(span=bars(df, 24 * ema_days), adjust=False).mean()
        up = df["close"] > e
        return _edge(lo & up), _edge(hi & ~up)
    raise ValueError(trend)


FUND_LVL = {1: (0.0003, 0.0), 2: (0.0005, -0.0001)}   # (crowded-long >=, crowded-short <=) per 8h


# ------------------------------------------------------------------ (A) funding crowding fade

def fcrowd(df, z=2.0, norm="z", lvl=1, trend="break", brk_h=24, arm_h=48, stop_atr=2.0, rr=2.0, mode="fade"):
    """Crowded longs -> short, crowded shorts -> long.
    norm='z'  : extreme = 90d z-score of the 24h-mean funding beyond +/- z.
    norm='abs': extreme = 24h-mean funding >= FUND_LVL[lvl][0] (crowded longs) or <= FUND_LVL[lvl][1]."""
    if norm == "z":
        fz = funding_z(df)
        hi, lo = fz >= z, fz <= -z
    else:
        f24 = df["funding"].rolling(bars(df, 24), min_periods=1).mean()
        h_, l_ = FUND_LVL[int(lvl)]
        hi, lo = f24 >= h_, f24 <= l_
    L, S = _apply_trend(df, hi, lo, trend, brk_h, arm_h)
    if mode == "follow":   # round 2: exact mirror of the same events (short-squeeze / momentum reading)
        L, S = S, L
    return _pack(df, L, S, stop_atr, rr)


# ------------------------------------------------------------------ (B) top traders vs crowd

def tdiv(df, z=1.0, k_h=24, mode="follow_top", stop_atr=2.0, rr=2.0):
    """Changes-based divergence, both legs required: top traders' position ratio rising
    (30d z of k_h change >= z) while the crowd's account ratio is falling (<= -z) -> long (follow
    top traders); mirror -> short."""
    n, k = bars(df, 24 * 30), bars(df, k_h)
    dt = roll_z(logpos(df["top_ls_positions"]).diff(k), n)
    dc = roll_z(logpos(df["ls_accounts"]).diff(k), n)
    hi = _edge((dt >= z) & (dc <= -z))
    lo = _edge((dt <= -z) & (dc >= z))
    L, S = (hi, lo) if mode == "follow_top" else (lo, hi)
    return _pack(df, L, S, stop_atr, rr)


def topdiv(df, z=2.0, mode="follow_top", stop_atr=2.0, rr=2.0):
    """Level divergence z(log top_ls_positions) - z(log ls_accounts) beyond +/- z."""
    d = top_crowd_div(df)
    hi, lo = _edge(d >= z), _edge(d <= -z)
    L, S = (hi, lo) if mode == "follow_top" else (lo, hi)
    return _pack(df, L, S, stop_atr, rr)


# ------------------------------------------------------------------ (C) retail crowding fade

def rcrowd(df, pct=0.95, src="level", trend="none", brk_h=24, arm_h=48, stop_atr=2.0, rr=2.0, side="both"):
    """Crowd (all-accounts L/S) at an extreme 30d percentile -> fade.
    src='level': raw log(ls_accounts); src='resid': residual after removing the crowd's mechanical
    response to the last 24h/72h price move (crowd_residual); src='price': control twin that uses
    -log(close) instead of positioning (tests whether the crowd adds anything beyond price)."""
    if src == "level":
        x = logpos(df["ls_accounts"])
    elif src == "resid":
        x = crowd_residual(df)
    elif src == "price":      # CONTROL: no positioning data, only where price sits in its 30d range
        x = -np.log(df["close"])   # "crowd long" <-> price near 30d low (the crowd buys dips)
    else:
        raise ValueError(src)
    p = roll_pct(x, bars(df, 24 * 30))
    L, S = _apply_trend(df, p >= pct, p <= 1 - pct, trend, brk_h, arm_h)
    if side == "short":     # round 3 (post hoc, validated on a fresh holdout): fade crowd-long only
        L = L & False
    elif side == "long":
        S = S & False
    return _pack(df, L, S, stop_atr, rr)


def dcrowd(df, z=2.0, k_h=24, stop_atr=2.0, rr=2.0):
    """Crowd FLOW fade: 30d z of the k_h change of log(ls_accounts). Crowd piling into longs
    (z >= z) -> short; crowd piling into shorts (z <= -z) -> long."""
    d = roll_z(logpos(df["ls_accounts"]).diff(bars(df, k_h)), bars(df, 24 * 30))
    return _pack(df, _edge(d <= -z), _edge(d >= z), stop_atr, rr)


def smartcrowd(df, pct=0.9, top_max=0.5, stop_atr=2.0, rr=2.0):
    """Round 2, 'smart vs crowd' proper: crowd at an extreme 30d percentile (as rcrowd level) AND the
    top traders' position ratio NOT on the crowd's side (its 30d percentile <= top_max for a crowd-long
    extreme, >= 1-top_max for a crowd-short extreme) -> fade the crowd."""
    n = bars(df, 24 * 30)
    pc = roll_pct(logpos(df["ls_accounts"]), n)
    pt = roll_pct(logpos(df["top_ls_positions"]), n)
    S = _edge((pc >= pct) & (pt <= top_max))
    L = _edge((pc <= 1 - pct) & (pt >= 1 - top_max))
    return _pack(df, L, S, stop_atr, rr)


# ------------------------------------------------------------------ (D) crowding + OI build-up

def oicrowd(df, z=1.5, zoi=1.0, trend="break", brk_h=24, arm_h=48, stop_atr=2.0, rr=2.0):
    """Funding z >= z AND 72h OI change z >= zoi (new leveraged positions pile into the crowded
    side) -> fade after the price confirmation. Mirror: funding z <= -z with OI rising -> long."""
    fz = funding_z(df)
    oz = oi_chg_z(df)
    hi = (fz >= z) & (oz >= zoi)
    lo = (fz <= -z) & (oz >= zoi)
    L, S = _apply_trend(df, hi, lo, trend, brk_h, arm_h)
    return _pack(df, L, S, stop_atr, rr)


# MAX_HOLD in bars is set per timeframe by thin wrappers (engine reads a function attribute): ~3 days.
def _wrap(fn, hold_bars, name):
    def w(df, **kw):
        return fn(df, **kw)
    w.MAX_HOLD = hold_bars
    w.__name__ = name
    return w


for _f in (fcrowd, tdiv, topdiv, rcrowd, dcrowd, oicrowd, smartcrowd):
    globals()[_f.__name__ + "_1h"] = _wrap(_f, 72, _f.__name__ + "_1h")
    globals()[_f.__name__ + "_4h"] = _wrap(_f, 18, _f.__name__ + "_4h")


# ------------------------------------------------------------------ funding payments (diagnostic)

def funding_pnl(trades):
    """Per-trade funding P&L in R (engine ignores funding). Long pays +rate, short receives it,
    for every settlement strictly inside (t_entry, t_exit]. Uses the settlement rate itself."""
    if trades is None or len(trades) == 0:
        return pd.Series(dtype=float)
    out = np.zeros(len(trades))
    cache = {}
    for i, r in enumerate(trades.itertuples(index=False)):
        if r.symbol not in cache:
            f = pd.read_parquet(os.path.join(_D.ROOT, "funding", f"{r.symbol}.parquet"))
            cache[r.symbol] = (f["ts"].dt.floor("min").dt.tz_convert(None).to_numpy("datetime64[ns]"),
                               f["funding"].to_numpy(float))
        ts, fr = cache[r.symbol]
        te = np.datetime64(pd.Timestamp(r.t_entry).tz_convert(None), "ns")
        tx = np.datetime64(pd.Timestamp(r.t_exit).tz_convert(None), "ns")
        a, b = np.searchsorted(ts, te, "right"), np.searchsorted(ts, tx, "right")
        rate = fr[a:b].sum()
        risk_frac = r.risk_pct / 100
        out[i] = -r.dir * rate / risk_frac
    return pd.Series(out, index=trades.index)
