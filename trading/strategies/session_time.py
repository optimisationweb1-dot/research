"""Session-time family: intraday seasonality and session structure (5m / 15m / 1h).

All decisions are taken at the CLOSE of bar t from rows <= t (bt/engine.py contract).
Session windows are pure calendar functions of the bar timestamp (known in advance), and
every level (session high/low, opening range, weekend range) is built with within-group
cumulative max/min, so a level is only used after its window has fully closed.

Common rules fixed a priori (not tuned):
  * One trade per window (day / session / weekend) and symbol: the FIRST qualifying bar.
  * Market entry at the next open; stop from the session structure, with a fee-aware floor
    MIN_RISK = 0.3% of price (about 2x the base round-trip taker cost incl. slippage);
    if the structural stop is closer than that, the stop is moved out to the floor.
  * Target m * risk from the signal close (m = 0 -> no target, exit on time only).
  * Time exit through exit_signal at the session end (next open after the flagged bar).
  * US times are DST-aware (America/New_York: cash open 09:30 ET = 13:30 UTC in summer,
    14:30 UTC in winter); CME times use America/Chicago. NYSE full-day holidays are skipped.

Strategies (hypotheses a-e of the task):
  asia_break   (a) first close beyond the Asia range (00:00-07:00 UTC) during London/NY
  asia_sweep   (a') London/NY bar pierces the Asia high/low and closes back inside -> fade
  us_orb       (b) US cash-open opening-range breakout (DST-aware)
  funding_drift(c) positioning around funding settlements 00/08/16 UTC, by funding sign
  weekend_break(d) Monday breakout of the weekend (Sat+Sun UTC) range
  cme_gap      (d') Sunday CME reopen: trade toward Friday's CME close (weekend move reversal)
  sess_filter  (e) volume_absorption signals restricted to a session chosen on IS only
  us_clock_drift (f) added after the IS hour-of-day study: short the first US cash hours,
               long after the US close (fixed clock direction)

DATA WORKAROUND (bt/*.py is not edited): bt.data._asof fails under pandas 3 (tz-naive
close_time vs tz-aware avail -> MergeError) for load(funding=True / metrics=True / dvol=True).
Patched below exactly as in strategies/volume_absorption_runner.py; as-of logic unchanged.
"""
import numpy as np
import pandas as pd
from pandas.tseries.holiday import (AbstractHolidayCalendar, GoodFriday, Holiday, USLaborDay,
                                    USMartinLutherKingJr, USMemorialDay, USPresidentsDay,
                                    USThanksgivingDay, nearest_workday)

import bt.data as _data
from bt.features import atr, empty_signals


def _asof_fixed(df, ext, cols, avail_col="avail"):
    left = pd.DataFrame({"open_ts": df.index,
                         "close_time": pd.DatetimeIndex(df["close_time"]).as_unit("ns")})
    right = ext[[avail_col] + cols].copy()
    right[avail_col] = pd.DatetimeIndex(right[avail_col]).as_unit("ns")
    right = right.sort_values(avail_col)
    m = pd.merge_asof(left.sort_values("close_time"), right, left_on="close_time", right_on=avail_col,
                      direction="backward")
    m.index = m["open_ts"]
    out = df.copy()
    for c in cols:
        out[c] = m[c].reindex(out.index).values
    return out


_data._asof = _asof_fixed

MIN_RISK = 0.003
MAX_HOLD = 400          # backstop only; every strategy has its own time exit
LIMIT_TTL = 1


class NYSECalendar(AbstractHolidayCalendar):
    rules = [
        Holiday("NewYearsDay", month=1, day=1, observance=nearest_workday),
        USMartinLutherKingJr, USPresidentsDay, GoodFriday, USMemorialDay,
        Holiday("Juneteenth", month=6, day=19, start_date="2022-06-19", observance=nearest_workday),
        Holiday("July4th", month=7, day=4, observance=nearest_workday),
        USLaborDay, USThanksgivingDay,
        Holiday("Christmas", month=12, day=25, observance=nearest_workday),
    ]


_HOL = pd.DatetimeIndex(NYSECalendar().holidays("2022-01-01", "2027-12-31"))


# ----------------------------------------------------------------------------- helpers

def tf_minutes(df):
    d = pd.Series(df.index[:200]).diff().dropna()
    return int(d.mode().iloc[0] / pd.Timedelta(minutes=1)) if len(d) else 5


def _grp(x, key):
    return x.groupby(key.to_numpy() if hasattr(key, "to_numpy") else key)


def window_level(x, in_win, key, how):
    """Running max/min of x over bars in the window, forward-filled within the group key.
    Value at bar t uses rows <= t only."""
    k = np.asarray(key)
    v = x.where(in_win)
    run = v.groupby(k).cummax() if how == "max" else v.groupby(k).cummin()
    return run.groupby(k).ffill()


def window_count(in_win, key):
    return pd.Series(np.asarray(in_win, float), index=in_win.index).groupby(np.asarray(key)).cumsum()


def first_in_group(cond, key):
    cond = pd.Series(np.asarray(cond, bool), index=cond.index)
    cs = cond.astype(int).groupby(np.asarray(key)).cumsum()
    return cond & (cs == 1)


def local_clock(df, tz):
    """(local minute-of-day, local day key as naive datetime, local weekday) of the bar OPEN."""
    loc = df.index.tz_convert(tz)
    mod = pd.Series(loc.hour * 60 + loc.minute, index=df.index)
    day = pd.Series(loc.tz_localize(None).floor("D"), index=df.index)
    dow = pd.Series(loc.dayofweek, index=df.index)
    return mod, day, dow


def us_trading_day(day, dow):
    return (dow < 5) & ~day.isin(_HOL)


def orders(df, long_m, short_m, stop_l, stop_s, m, exit_flag=None, min_risk=MIN_RISK):
    """Signal frame with fee-aware stop floor and m*R targets (ref = close[t])."""
    out = empty_signals(df)
    c = df["close"].to_numpy(float)
    long_m = np.asarray(long_m, bool)
    short_m = np.asarray(short_m, bool)
    both = long_m & short_m
    long_m, short_m = long_m & ~both, short_m & ~both
    risk_l = np.maximum(c - np.asarray(stop_l, float), min_risk * c)
    risk_s = np.maximum(np.asarray(stop_s, float) - c, min_risk * c)
    long_m &= np.isfinite(risk_l)
    short_m &= np.isfinite(risk_s)
    sig = np.where(long_m, 1.0, np.where(short_m, -1.0, 0.0))
    stop = np.where(long_m, c - risk_l, np.where(short_m, c + risk_s, np.nan))
    tgt = np.full(len(c), np.nan)
    if m and m > 0:
        tgt = np.where(long_m, c + m * risk_l, np.where(short_m, c - m * risk_s, np.nan))
    out["signal"], out["stop"], out["target"] = sig, stop, tgt
    if exit_flag is not None:
        out["exit_signal"] = np.asarray(exit_flag, float)
    return out


def _attrs(fn, max_hold=MAX_HOLD):
    fn.MAX_HOLD = max_hold
    fn.LIMIT_TTL = LIMIT_TTL
    return fn


# ----------------------------------------------------------------------------- (a) Asia range

def asia_levels(df, asia_end_h=7):
    tfm = tf_minutes(df)
    mod = pd.Series(df.index.hour * 60 + df.index.minute, index=df.index)
    day = pd.Series(df.index.tz_localize(None).floor("D"), index=df.index)
    in_asia = mod < asia_end_h * 60
    ah = window_level(df["high"], in_asia, day, "max")
    al = window_level(df["low"], in_asia, day, "min")
    cnt = window_count(in_asia, day)
    full = cnt >= (asia_end_h * 60 // tfm)            # complete Asia window (no data gaps)
    after = mod >= asia_end_h * 60
    ok = after & full
    return mod, day, ah.where(ok), al.where(ok)


def range_rank(rng_day_series, day, days=20):
    """Ratio of today's range to the median range of the previous `days` sessions (causal:
    today's value is final once the window has closed; the median excludes today)."""
    per_day = rng_day_series.groupby(np.asarray(day)).last()
    med = per_day.shift(1).rolling(days, min_periods=days // 2).median()
    ratio = per_day / med
    return pd.Series(ratio.reindex(np.asarray(day)).to_numpy(), index=rng_day_series.index)


def asia_break(df, stop="opp", m=0.0, narrow=0, end_h=20, last_entry_h=16, asia_end_h=7):
    """(a) Asia-range breakout. Window: bars opening in [asia_end_h, last_entry_h) UTC on any day.
    First bar of the day that CLOSES beyond the Asia high (long) or low (short).
    stop: 'opp' = other side of the Asia range, 'mid' = middle of the range.
    narrow=1: only if the Asia range is below the median of the previous 20 days (compression).
    Exit: target m*R (m>0) or at end_h:00 UTC (next open after the flagged bar)."""
    tfm = tf_minutes(df)
    mod, day, ah, al = asia_levels(df, asia_end_h)
    c = df["close"]
    win = (mod >= asia_end_h * 60) & (mod < last_entry_h * 60) & ah.notna()
    up, dn = win & (c > ah), win & (c < al)
    first = first_in_group(up | dn, day)
    L, S = first & up, first & dn
    if narrow:
        rr = range_rank((ah - al), day)
        L &= rr < 1.0
        S &= rr < 1.0
    mid = (ah + al) / 2
    stop_l = al if stop == "opp" else mid
    stop_s = ah if stop == "opp" else mid
    ex = mod == (end_h * 60 - tfm)
    return orders(df, L, S, stop_l, stop_s, m, ex)


def asia_sweep(df, m=1.0, buf=0.25, end_h=20, last_entry_h=16, asia_end_h=7, tgt="R"):
    """(a') Asia-range liquidity sweep fade ("London Judas swing"): first bar of the day in the
    window whose high pierces the Asia high but closes back inside (short), or whose low
    pierces the Asia low and closes back inside (long), with no earlier close outside the
    range that day. Stop beyond the sweep extreme + buf*ATR. Target m*R, or tgt='mid' ->
    the range middle. Exit at end_h UTC."""
    tfm = tf_minutes(df)
    mod, day, ah, al = asia_levels(df, asia_end_h)
    h, l, c = df["high"], df["low"], df["close"]
    A = atr(df)
    win = (mod >= asia_end_h * 60) & (mod < last_entry_h * 60) & ah.notna()
    out_close = win & ((c > ah) | (c < al))
    broke_before = out_close.astype(int).groupby(np.asarray(day)).cumsum() > 0
    sw_s = win & (h > ah) & (c <= ah) & (c >= al)
    sw_l = win & (l < al) & (c >= al) & (c <= ah)
    ev = (sw_s | sw_l) & ~broke_before
    first = first_in_group(ev, day)
    L, S = first & sw_l & ~sw_s, first & sw_s & ~sw_l
    ex = mod == (end_h * 60 - tfm)
    out = orders(df, L, S, l - buf * A, h + buf * A, m if tgt == "R" else 0, ex)
    if tgt == "mid":
        mid = ((ah + al) / 2).to_numpy(float)
        cc = c.to_numpy(float)
        sig = out["signal"].to_numpy()
        ok = ((sig > 0) & (mid > cc)) | ((sig < 0) & (mid < cc))
        out["target"] = np.where(ok, mid, np.nan)
    return out


# ----------------------------------------------------------------------------- (b) US open ORB

def us_orb(df, or_min=30, stop="opp", m=0.0, last_entry_min=150, exit_local_min=960):
    """(b) US cash-open opening-range breakout, DST-aware (America/New_York).
    OR = bars opening in [09:30, 09:30+or_min) ET on NYSE trading days. Entry window:
    [09:30+or_min, 09:30+last_entry_min) ET; first close beyond the OR high/low.
    stop: 'opp' other side of the OR, 'mid' middle. Exit: m*R target or at 16:00 ET."""
    tfm = tf_minutes(df)
    mod, day, dow = local_clock(df, "America/New_York")
    trade_day = us_trading_day(day, dow)
    o0 = 570
    in_or = trade_day & (mod >= o0) & (mod < o0 + or_min)
    orh = window_level(df["high"], in_or, day, "max")
    orl = window_level(df["low"], in_or, day, "min")
    full = window_count(in_or, day) >= (or_min // tfm)
    c = df["close"]
    win = trade_day & (mod >= o0 + or_min) & (mod < o0 + last_entry_min) & full & orh.notna()
    up, dn = win & (c > orh), win & (c < orl)
    first = first_in_group(up | dn, day)
    L, S = first & up, first & dn
    mid = (orh + orl) / 2
    stop_l = orl if stop == "opp" else mid
    stop_s = orh if stop == "opp" else mid
    ex = trade_day & (mod == exit_local_min - tfm)
    return orders(df, L, S, stop_l, stop_s, m, ex)


# ----------------------------------------------------------------------------- (c) funding drift

def funding_drift(df, mode="pre", hold_h=1, thr_pos=0.0002, thr_neg=0.0, k_stop=2.0, contra=0):
    """(c) Funding-settlement drift. Settlements at 00/08/16 UTC (all 10 symbols are 8h).
    f = last SETTLED funding rate known at the previous bar close (the settlement 8h earlier;
    persistence makes it a proxy for the rate about to settle).
    Paying side: longs if f >= thr_pos, shorts if f < thr_neg.
    mode='pre' : enter hold_h before settlement AGAINST the paying side (it unwinds to avoid
                 paying), exit at the settlement time T.
    mode='post': enter at T WITH the paying side (it re-opens after settlement), exit T+hold_h.
    contra=1 flips the direction (tests the opposite sign of the hypothesis).
    Stop: k_stop * ATR(14) * sqrt(hold bars), floor MIN_RISK. No target (time exit)."""
    tfm = tf_minutes(df)
    hb = max(1, int(round(hold_h * 60 / tfm)))
    mod_close = pd.Series((df.index.hour * 60 + df.index.minute + tfm) % 1440, index=df.index)
    f = df["funding"].shift(1)
    pay_long = f >= thr_pos
    pay_short = f < thr_neg
    T = {0, 480, 960}
    if mode == "pre":
        ent = mod_close.isin({(t - hold_h * 60) % 1440 for t in T})
        exf = mod_close.isin(T)
        L, S = ent & pay_short, ent & pay_long
    else:
        ent = mod_close.isin(T)
        exf = mod_close.isin({(t + hold_h * 60) % 1440 for t in T})
        L, S = ent & pay_long, ent & pay_short
    if contra:
        L, S = S, L
    A = atr(df)
    d = k_stop * A * np.sqrt(hb)
    c = df["close"]
    return orders(df, L.fillna(False), S.fillna(False), c - d, c + d, 0, exf)


# ----------------------------------------------------------------------------- (d) weekend

def weekend_levels(df):
    dow = pd.Series(df.index.dayofweek, index=df.index)
    d0 = pd.Series(df.index.tz_localize(None).floor("D"), index=df.index)
    key = d0 - pd.to_timedelta((dow - 5) % 7, unit="D")   # week starting Saturday
    in_we = dow >= 5
    wh = window_level(df["high"], in_we, key, "max")
    wl = window_level(df["low"], in_we, key, "min")
    return dow, key, wh, wl, window_count(in_we, key)


def weekend_break(df, stop="opp", m=0.0, narrow=0, entry_days=1, exit_days=1):
    """(d) Weekend-range breakout. Weekend = Sat 00:00 - Mon 00:00 UTC. Entry window: Monday
    (entry_days=1) or Mon-Tue (2); first close beyond the weekend high/low. Stop: 'opp'/'mid'.
    narrow=1: weekend range below the median of the previous 8 weekends.
    Exit: m*R target or at 00:00 UTC after `exit_days` days from Monday 00:00."""
    tfm = tf_minutes(df)
    dow, key, wh, wl, cnt = weekend_levels(df)
    full = cnt >= (2 * 1440 // tfm)
    c = df["close"]
    win = (dow < entry_days) & full & wh.notna()
    up, dn = win & (c > wh), win & (c < wl)
    first = first_in_group(up | dn, key)
    L, S = first & up, first & dn
    if narrow:
        rr = range_rank((wh - wl).where(win), key, days=8)
        L &= rr < 1.0
        S &= rr < 1.0
    mid = (wh + wl) / 2
    stop_l = wl if stop == "opp" else mid
    stop_s = wh if stop == "opp" else mid
    mod = pd.Series(df.index.hour * 60 + df.index.minute, index=df.index)
    ex = (dow == exit_days - 1) & (mod == 1440 - tfm)
    return orders(df, L, S, stop_l, stop_s, m, ex)


def cme_gap(df, min_gap=0.01, k=1.0, hold_h=24, side=1):
    """(d') Weekend move vs the CME close. Friday CME close = close of the bar ending at Fri
    16:00 CT (America/Chicago); decision at the bar ending at Sun 17:00 CT (CME reopen).
    gap = close / fri_close - 1. If |gap| >= min_gap trade TOWARD the Friday close (side=1,
    folk 'CME gap fill': the weekend move reverses when full liquidity returns) or WITH the
    weekend move (side=-1, 'gap and go'; added after the IS study E5 showed continuation).
    Stop = k * |distance to the Friday close| beyond the entry (floor MIN_RISK).
    side=1 target = the Friday close (gap fill); side=-1 no target. Time exit after hold_h hours."""
    tfm = tf_minutes(df)
    mod, day, dow = local_clock(df, "America/Chicago")
    close_mod = mod + tfm                                 # local minute of the bar close
    fri_bar = (dow == 4) & (close_mod == 960)
    fri_close = df["close"].where(fri_bar).ffill()
    sun_bar = (dow == 6) & (close_mod == 1020)
    c = df["close"]
    gap = c / fri_close - 1
    # Friday close must belong to the same weekend (within 3 days)
    fri_t = pd.Series(df.index.where(fri_bar.to_numpy()), index=df.index).ffill()
    recent = (df.index.to_series() - fri_t) < pd.Timedelta(days=3)
    ok = sun_bar & recent & (gap.abs() >= min_gap)
    dist = (c - fri_close).abs()
    if side > 0:
        L, S = ok & (gap < 0), ok & (gap > 0)
    else:
        L, S = ok & (gap > 0), ok & (gap < 0)
    out = orders(df, L.fillna(False), S.fillna(False), c - k * dist, c + k * dist, 0)
    if side > 0:
        sig = out["signal"].to_numpy()
        out["target"] = np.where(sig != 0, fri_close.to_numpy(float), np.nan)
    # time exit: flag every bar; the engine uses MAX_HOLD for the hold. Implemented via
    # exit flag at signal time + hold_h (per-signal) using a forward-shifted signal mask.
    hb = max(1, int(round(hold_h * 60 / tfm)))
    exf = pd.Series(out["signal"].to_numpy() != 0, index=df.index).shift(hb, fill_value=False)
    out["exit_signal"] = exf.to_numpy(float)
    return out


# ----------------------------------------------------------------------------- (f) US-clock drift

def us_clock_drift(df, mode="open_short", hold_min=120, k_stop=2.0):
    """(f) Added AFTER the in-sample hour-of-day study (E1/E1b, IS only): on NYSE trading days
    crypto drifted down in the first hours of the US cash session and up after the US close
    (the crypto analogue of the equity "intraday vs overnight" tug of war, Lou-Polk-Skouras).
    mode='open_short' : short at 09:30 ET, exit after hold_min minutes.
    mode='close_long' : long at 16:00 ET, exit after hold_min minutes.
    Direction is fixed by the clock. Stop k_stop * ATR(14) * sqrt(hold bars) (floor MIN_RISK),
    no target."""
    tfm = tf_minutes(df)
    hb = max(1, hold_min // tfm)
    mod, day, dow = local_clock(df, "America/New_York")
    td = us_trading_day(day, dow)
    t0 = 570 if mode == "open_short" else 960
    ent = td & (mod == t0 - tfm)                  # bar that CLOSES at t0 -> entry at the t0 open
    exf = td & (mod == t0 + hb * tfm - tfm)       # bar that closes at t0 + hold -> exit at next open
    A = atr(df)
    d = k_stop * A * np.sqrt(hb)
    c = df["close"]
    if mode == "open_short":
        L, S = pd.Series(False, index=df.index), ent
    else:
        L, S = ent, pd.Series(False, index=df.index)
    return orders(df, L, S, c - d, c + d, 0, exf)


# ----------------------------------------------------------------------------- (e) session filter

SESSIONS = ("all", "asia", "london", "ny", "late", "weekend", "active")


def session_mask(df, sess):
    """Session of the signal bar CLOSE (decision time). Weekdays by UTC calendar.
    asia 00:00-07:00 UTC, london 07:00-US open, ny US cash session 09:30-16:00 ET (DST-aware),
    late US close-24:00 UTC, weekend Sat/Sun UTC, active = london + ny."""
    if sess == "all":
        return pd.Series(True, index=df.index)
    tfm = tf_minutes(df)
    ct = df.index + pd.Timedelta(minutes=tfm)
    mod = pd.Series(ct.hour * 60 + ct.minute, index=df.index)
    dow = pd.Series(ct.dayofweek, index=df.index)
    lct = ct.tz_convert("America/New_York")
    lmod = pd.Series(lct.hour * 60 + lct.minute, index=df.index)
    wk = dow < 5
    ny = wk & (lmod > 570) & (lmod <= 960)
    asia = wk & (mod > 0) & (mod <= 420)
    pre_us = wk & (mod > 420) & (lmod <= 570) & (lct.dayofweek.to_numpy() < 5)
    late = wk & ~asia & ~pre_us & ~ny
    m = {"asia": asia, "london": pre_us, "ny": ny, "late": late, "weekend": ~wk,
         "active": pre_us | ny}[sess]
    return m


def sess_filter(df, base="climax_cont", sess="all", **params):
    """(e) Run a volume_absorption signal and keep only entries whose decision bar closes in
    `sess`. Base parameters are the IS-selected ones from the volume_absorption runs."""
    from strategies import volume_absorption as va
    fn = getattr(va, base)
    out = fn(df, **params).copy()
    keep = session_mask(df, sess).to_numpy()
    sig = out["signal"].to_numpy(float)
    drop = (sig != 0) & ~keep
    out.loc[drop, "signal"] = 0.0
    out.loc[drop, ["stop", "target", "entry_limit"]] = np.nan
    return out


for _fn in (asia_break, asia_sweep, us_orb, funding_drift, weekend_break, cme_gap, us_clock_drift):
    _attrs(_fn)
_attrs(sess_filter, 48)   # same time exit as volume_absorption (48 bars)
sess_filter.LIMIT_TTL = 3
strategy = asia_break
