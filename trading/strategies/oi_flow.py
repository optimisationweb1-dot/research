"""Family oi_flow: open interest + taker order flow = footprint of large players.

Hypotheses (all decisions at the CLOSE of bar t, entries at open t+1 by the engine):
  a  cont    fresh positioning: N-bar range breakout + OI rising (z of dlogOI) + rolling delta same side
  b  squeeze price move with OI FALLING (short covering / long liquidation) -> direction chosen on IS
  c  capit   capitulation: sharp move + large OI drop + volume spike -> fade (mean reversion)
  d  build   OI build-up inside a compression -> breakout in the direction of delta
  e  taker   taker buy/sell ratio extremes -> fade or follow (direction chosen on IS)

DATA WORKAROUNDS (bt/*.py is not edited, see results/oi_flow.md):
  1) bt.data._asof fails under pandas 3 (tz-naive close_time vs tz-aware avail) -> patched here.
  2) Binance metrics stamped T describe the 5-min window [T, T+5) (taker ratio at stamp T correlates
     0.80 with kline delta of the bar OPENED at T; |dOI| peaks at the same bar). bt.data treats the
     stamp as known at T+1min, i.e. zero latency at bar close. We use avail = T + 5min + 1min
     (conservative: at bar close the newest usable OI is 5 minutes old).
"""
import numpy as np
import pandas as pd

import bt.data as _D
from bt.features import atr, donchian, empty_signals

METRICS_LAG = pd.Timedelta(minutes=6)


def _asof_fixed(df, ext, cols, avail_col="avail"):
    ct = pd.to_datetime(df["close_time"])
    if ct.dt.tz is None:
        ct = ct.dt.tz_localize("UTC")
    left = pd.DataFrame({"pos": np.arange(len(df)), "close_time": ct.dt.tz_convert("UTC").astype("datetime64[ns, UTC]").to_numpy()})
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
    import os
    path = os.path.join(_D.ROOT, "metrics", f"{symbol}.parquet")
    mt = pd.read_parquet(path)
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


# ------------------------------------------------------------------ features

def bar_minutes(df):
    d = pd.Series(df.index[:200]).diff().dropna()
    return int(d.mode().iloc[0] / pd.Timedelta(minutes=1)) if len(d) else 15


def bars(df, hours):
    return max(1, int(round(hours * 60 / bar_minutes(df))))


def roll_z(x, n):
    m = x.rolling(n, min_periods=n // 2).mean()
    s = x.rolling(n, min_periods=n // 2).std()
    return (x - m) / s


def oi_z(df, k, zdays=30):
    """z-score of the k-bar change of log OI (contracts), normalized over ~zdays."""
    lo = np.log(df["oi"].where(df["oi"] > 0))
    d = lo - lo.shift(k)
    return roll_z(d, bars(df, 24 * zdays))


def flow_share(df, k):
    """Rolling taker delta / volume over k bars, in [-1, 1]."""
    return df["delta"].rolling(k).sum() / df["volume"].rolling(k).sum()


def vol_ratio(df, k, days=10):
    """k-bar volume sum relative to its rolling median (previous values only)."""
    v = df["volume"].rolling(k).sum()
    return v / v.shift(k).rolling(bars(df, 24 * days), min_periods=bars(df, 24 * days) // 2).median()


def _pack(df, long_m, short_m, A, stop_atr, rr, stop_long=None, stop_short=None):
    out = empty_signals(df)
    c = df["close"]
    long_m = long_m.fillna(False).astype(bool)
    short_m = short_m.fillna(False).astype(bool) & ~long_m
    sl_l = c - stop_atr * A if stop_long is None else stop_long
    sl_s = c + stop_atr * A if stop_short is None else stop_short
    sig = np.where(long_m, 1.0, np.where(short_m, -1.0, 0.0))
    stop = np.where(long_m, sl_l, np.where(short_m, sl_s, np.nan))
    risk = np.abs(c.to_numpy() - stop)
    tgt = np.where(long_m, c + rr * risk, np.where(short_m, c - rr * risk, np.nan))
    ok = np.isfinite(stop) & (risk > 0)
    out["signal"] = np.where(ok, sig, 0.0)
    out["stop"] = np.where(ok, stop, np.nan)
    out["target"] = np.where(ok & np.isfinite(tgt), tgt, np.nan)
    return out


# ------------------------------------------------------------------ (a) fresh positioning continuation

def cont(df, n_hours=12, z=1.5, k_hours=2, flow=0.03, stop_atr=2.0, rr=2.0):
    """Close breaks the previous n-bar range, OI rose over the last k bars (z >= z)
    and taker delta over the same k bars agrees -> follow."""
    n, k = bars(df, n_hours), bars(df, k_hours)
    A = atr(df)
    hi, lo = donchian(df, n)
    zo = oi_z(df, k)
    fs = flow_share(df, k)
    c = df["close"]
    fresh_up = (c > hi) & (c.shift(1) <= hi.shift(1))
    fresh_dn = (c < lo) & (c.shift(1) >= lo.shift(1))
    L = fresh_up & (zo >= z) & (fs >= flow)
    S = fresh_dn & (zo >= z) & (fs <= -flow)
    return _pack(df, L, S, A, stop_atr, rr)


cont.MAX_HOLD = 48


# ------------------------------------------------------------------ (b) squeeze: move with OI falling

def squeeze(df, k_hours=4, move_atr=2.5, z=-1.5, mode="fade", stop_atr=2.0, rr=1.5):
    """Price moved >= move_atr x ATR x sqrt(k) over k bars while OI FELL (z <= z): positions are being
    closed (short covering on the way up, long liquidation on the way down).
    mode='fade' trades against the move, 'follow' with it."""
    k = bars(df, k_hours)
    A = atr(df)
    c = df["close"]
    mv = (c - c.shift(k)) / (A * np.sqrt(k))
    zo = oi_z(df, k)
    trig = zo <= z
    up = trig & (mv >= move_atr)
    dn = trig & (mv <= -move_atr)
    # only the first bar of a new episode
    up &= ~up.shift(1, fill_value=False)
    dn &= ~dn.shift(1, fill_value=False)
    if mode == "fade":
        L, S = dn, up
    else:
        L, S = up, dn
    return _pack(df, L, S, A, stop_atr, rr)


squeeze.MAX_HOLD = 24


def newpos(df, k_hours=4, move_atr=2.5, z=1.5, mode="follow", stop_atr=2.0, rr=1.5):
    """Mirror quadrant of (b): price moved with OI RISING (new positions)."""
    k = bars(df, k_hours)
    A = atr(df)
    c = df["close"]
    mv = (c - c.shift(k)) / (A * np.sqrt(k))
    zo = oi_z(df, k)
    trig = zo >= z
    up = trig & (mv >= move_atr)
    dn = trig & (mv <= -move_atr)
    up &= ~up.shift(1, fill_value=False)
    dn &= ~dn.shift(1, fill_value=False)
    L, S = (up, dn) if mode == "follow" else (dn, up)
    return _pack(df, L, S, A, stop_atr, rr)


newpos.MAX_HOLD = 24


# ------------------------------------------------------------------ (c) capitulation / liquidation cascade

def capit(df, k_hours=1, move_atr=3.0, z=-2.0, vr=2.5, stop_atr=1.0, rr=1.5, both=1, mode="fade"):
    """Sharp k-bar move (>= move_atr x ATR x sqrt(k)), big OI drop (z <= z) and a volume spike (k-bar volume
    >= vr x median) = forced closing. Fade it: long after a down-cascade (short after an up-squeeze
    when both=1). Stop beyond the cascade extreme + stop_atr*ATR."""
    k = bars(df, k_hours)
    A = atr(df)
    c = df["close"]
    mv = (c - c.shift(k)) / (A.shift(k) * np.sqrt(k))
    zo = oi_z(df, k)
    vx = vol_ratio(df, k)
    trig = (zo <= z) & (vx >= vr)
    dn = trig & (mv <= -move_atr)
    up = trig & (mv >= move_atr) & bool(both)
    dn &= ~dn.shift(1, fill_value=False)
    up &= ~up.shift(1, fill_value=False)
    ext_lo = df["low"].rolling(k).min()
    ext_hi = df["high"].rolling(k).max()
    if mode == "fade":
        return _pack(df, dn, up, A, stop_atr, rr, stop_long=ext_lo - stop_atr * A, stop_short=ext_hi + stop_atr * A)
    # follow (added in round 2 after IS fade was negative): ATR stop from the close
    return _pack(df, up, dn, A, 2.0, rr)


capit.MAX_HOLD = 24


# ------------------------------------------------------------------ (d) OI build-up in compression

def build(df, n_hours=12, sq=0.6, z=1.0, k_hours=1, flow=0.05, rr=2.0, buf_atr=0.2):
    """Compression: range of the previous n bars <= sq x its 30-day rolling median, while OI over
    those n bars rose (z >= z). Entry on the first close outside that range, only if the taker
    delta of the last k bars points the same way. Stop at the opposite side of the box."""
    n, k = bars(df, n_hours), bars(df, k_hours)
    A = atr(df)
    hi, lo = donchian(df, n)
    width = hi - lo
    wmed = width.rolling(bars(df, 24 * 30), min_periods=bars(df, 24 * 15)).median()
    tight = (width <= sq * wmed)
    zo = oi_z(df, n).shift(1)          # OI build-up during the box (up to the previous bar)
    fs = flow_share(df, k)
    c = df["close"]
    setup = tight & (zo >= z)
    L = setup & (c > hi) & (fs >= flow)
    S = setup & (c < lo) & (fs <= -flow)
    return _pack(df, L, S, A, 0, rr, stop_long=lo - buf_atr * A, stop_short=hi + buf_atr * A)


build.MAX_HOLD = 48


# ------------------------------------------------------------------ (e) taker ratio extremes

def taker(df, k_hours=4, z=2.5, mode="fade", src="klines", stop_atr=2.0, rr=1.5):
    """z-score (30d) of the k-bar log taker buy/sell ratio. mode='fade' trades against an extreme,
    'follow' with it. src='klines' uses kline taker volumes (available from 2023, IS = 2023-2024);
    src='metrics' uses Binance taker_ls_ratio snapshots (2024+)."""
    k = bars(df, k_hours)
    A = atr(df)
    if src == "klines":
        b = df["buy_vol"].rolling(k).sum()
        s = df["sell_vol"].rolling(k).sum()
        x = np.log(b / s)
    else:
        x = np.log(df["taker_ls_ratio"].where(df["taker_ls_ratio"] > 0)).rolling(k).mean()
    zz = roll_z(x, bars(df, 24 * 30))
    hi = (zz >= z) & ~(zz.shift(1) >= z)
    lo = (zz <= -z) & ~(zz.shift(1) <= -z)
    L, S = (lo, hi) if mode == "fade" else (hi, lo)
    return _pack(df, L, S, A, stop_atr, rr)


taker.MAX_HOLD = 24


# ------------------------------------------------------------------ (f) top traders vs crowd positioning

def smart(df, k_hours=24, z=2.0, mode="follow_top", stop_atr=2.0, rr=2.0):
    """Divergence between large accounts' position ratio (top_ls_positions) and the crowd's
    account ratio (ls_accounts): d = z(dlog top) - z(dlog crowd) over k bars (30d z).
    follow_top: long when top traders add longs relative to the crowd, short in the mirror."""
    k = bars(df, k_hours)
    A = atr(df)
    n = bars(df, 24 * 30)
    top = np.log(df["top_ls_positions"].where(df["top_ls_positions"] > 0))
    crowd = np.log(df["ls_accounts"].where(df["ls_accounts"] > 0))
    d = roll_z(top - top.shift(k), n) - roll_z(crowd - crowd.shift(k), n)
    hi = (d >= z) & ~(d.shift(1) >= z)
    lo = (d <= -z) & ~(d.shift(1) <= -z)
    L, S = (hi, lo) if mode == "follow_top" else (lo, hi)
    return _pack(df, L, S, A, stop_atr, rr)


smart.MAX_HOLD = 48


# ------------------------------------------------------------------ round-2 control: impulse without OI filter

def impulse(df, k_hours=1, move_atr=2.0, mode="follow", stop_atr=2.0, rr=1.5):
    """Control for (b)/(c): the same k-bar impulse (>= move_atr x ATR x sqrt(k)) with NO OI condition.
    If OI-conditioned variants do not beat this, OI adds no information."""
    k = bars(df, k_hours)
    A = atr(df)
    c = df["close"]
    mv = (c - c.shift(k)) / (A * np.sqrt(k))
    up = (mv >= move_atr)
    dn = (mv <= -move_atr)
    up &= ~up.shift(1, fill_value=False)
    dn &= ~dn.shift(1, fill_value=False)
    L, S = (up, dn) if mode == "follow" else (dn, up)
    return _pack(df, L, S, A, stop_atr, rr)


impulse.MAX_HOLD = 24
