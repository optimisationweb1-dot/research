"""Family smc_priceaction: honest tests of the TikTok-style SMC / ICT claims.

All three entry models share ONE causal context, the same one as the reference
strategies/smc.py (so the comparison isolates the ENTRY model, not the setup):

    liquidity sweep : bar wicks below the last confirmed swing low and closes back above it
    CHoCH           : later close above the last confirmed swing high known at the sweep
                      (within MAX_SETUP bars); the lowest low since the sweep = "leg low"
    invalidation    : any low below the leg low kills the setup
(short side is the exact mirror, implemented by running the long machine on negated prices)

Entry models (hypotheses a-c):
    setup="choch" (a)  market order at the open after the CHoCH bar
                        stop struct = leg low - buf*ATR           alt = low of the last 3 bars - buf*ATR (tight)
    setup="ob"    (b)  order block = last down-close candle before the displacement, searched
                        back from the CHoCH bar to leg_low_bar-3, lying in the lower half of the leg.
                        Resting buy limit at the OB high (proximal edge), re-posted every bar
                        (TTL 1) for up to RETEST_BARS bars after the CHoCH.
                        stop struct = OB low - buf*ATR                   alt = leg low - buf*ATR (wide)
    setup="fvg"   (c)  FVG = the most recent bullish gap (low[k] > high[k-2]) formed between the sweep
                        and the CHoCH bar and lying below the CHoCH close. Wait for price to trade
                        into it (low <= top), then a CONFIRMATION candle: bullish (close > open) and
                        close > FVG top. Market entry at the next open. A close below the FVG bottom
                        invalidates it. Up to RETEST_BARS bars after the CHoCH.
                        stop struct = lowest low since the first touch - buf*ATR   alt = leg low - buf*ATR
Filters (hypotheses d-e), param filt in {"none","kz","htf","kz_htf"}:
    kz  : ICT killzones in New York local time (DST-aware): London 02:00-05:00 ET, New York
          07:00-10:00 ET (= 07-10 / 12-15 UTC in winter, 06-09 / 11-14 UTC in summer).
          Checked on the ENTRY bar (the bar that opens at the decision bar's close).
    htf : 4h market-structure bias. 4h bars are resampled from the frame itself; bias = direction
          of the last 4h close beyond the last confirmed 4h swing (pivot 3). A 4h bar is used only
          once it has closed (its nominal close <= the LTF bar close). Longs only if bias=+1.
Targets (hypothesis f): target = ref + rr * (ref - stop), ref = decision close (market) or limit price.
Fee-aware stop floor (fixed a priori, same as session_time): risk is widened to at least
MIN_RISK = 0.3% of price (~2x the base taker round trip incl. slippage), never skipped.

Fixed, not tuned: piv=5, buf=0.3 ATR, MAX_SETUP=96, RETEST_BARS=48, MAX_HOLD=288, MIN_RISK=0.3%.
"""
import math

import numpy as np
import pandas as pd

from bt.features import atr, confirmed_swings, empty_signals

MAX_HOLD = 288
LIMIT_TTL = 1
MAX_SETUP = 96      # sweep -> CHoCH must happen within this many bars (as in smc.py)
RETEST_BARS = 48    # OB / FVG retest must happen within this many bars after the CHoCH
MIN_RISK = 0.003    # 0.3% of price
BUF = 0.3           # ATR buffer beyond structural stops (as in smc.py)
PIV = 5


# ----------------------------------------------------------------------------- filters

def killzone_mask(df):
    """True if the ENTRY bar (opening at this bar's close) starts inside an ICT killzone (NY time)."""
    ct = pd.DatetimeIndex(df["close_time"]).tz_convert("America/New_York")
    hr = np.asarray(ct.hour)
    return ((hr >= 2) & (hr < 5)) | ((hr >= 7) & (hr < 10))


def htf_bias(df, rule="4h", piv=3):
    """4h structure bias (+1 / -1 / 0) known at each LTF bar close. Causal."""
    hb = df[["high", "low", "close"]].resample(rule, label="left", closed="left").agg(
        {"high": "max", "low": "min", "close": "last"}).dropna()
    if len(hb) < 2 * piv + 2:
        return np.zeros(len(df))
    sh, sl = confirmed_swings(hb, piv)
    c = hb["close"]
    b = np.where((c > sh).to_numpy(), 1.0, np.where((c < sl).to_numpy(), -1.0, np.nan))
    bias = pd.Series(b, index=hb.index).ffill().fillna(0.0).to_numpy()
    avail = (hb.index + pd.Timedelta(rule)).as_unit("ns").asi8
    ct = pd.DatetimeIndex(df["close_time"]).as_unit("ns").asi8
    idx = np.searchsorted(avail, ct, side="right") - 1
    return np.where(idx >= 0, bias[np.clip(idx, 0, None)], 0.0)


# ----------------------------------------------------------------------------- core machine

def _long_machine(o, h, l, c, sh, sl, A, setup, stop_mode, rr, allow):
    """Long-side state machine on (possibly negated) prices.
    Returns arrays (sig, stop, target, limit, ref) where ref is the price the order refers to."""
    n = len(c)
    sig = np.zeros(n)
    stp = np.full(n, np.nan)
    tgt = np.full(n, np.nan)
    lim = np.full(n, np.nan)
    ref = np.full(n, np.nan)
    s = 0
    lo = choch = hi = np.nan
    lo_bar = t0 = tc = 0
    px = st_ = tg_ = np.nan          # armed OB order
    fb = ft = np.nan                  # FVG bottom / top
    touched = False
    tlo = np.nan

    def order(t, entry, stop_raw):
        risk = max(entry - stop_raw, MIN_RISK * entry)
        return entry - risk, entry + rr * risk

    for t in range(2, n):
        if s == 1 and t - t0 > MAX_SETUP:
            s = 0
        if s == 2 and t - tc > RETEST_BARS:
            s = 0
        if s == 2:
            if setup == "ob":
                if l[t] < px or l[t] < lo:       # filled by the order posted at t-1, or invalidated
                    s = 0
                elif allow[t]:
                    sig[t], stp[t], tgt[t], lim[t], ref[t] = 1, st_, tg_, px, px
            elif setup == "fvg":
                if l[t] < lo or c[t] < fb:
                    s = 0
                else:
                    if not touched and l[t] <= ft:
                        touched, tlo = True, l[t]
                    elif touched:
                        tlo = min(tlo, l[t])
                    if touched and c[t] > o[t] and c[t] > ft:
                        if allow[t]:
                            raw = (tlo - BUF * A[t]) if stop_mode == "struct" else (lo - BUF * A[t])
                            if raw < c[t]:
                                sp, tp = order(t, c[t], raw)
                                sig[t], stp[t], tgt[t], ref[t] = 1, sp, tp, c[t]
                        s = 0
        elif s == 1:
            if l[t] < lo:
                lo, lo_bar = l[t], t
            if c[t] > choch:
                s, tc, hi = 2, t, h[t]
                if setup == "choch":
                    if allow[t]:
                        raw = (lo - BUF * A[t]) if stop_mode == "struct" else (min(l[t - 2:t + 1]) - BUF * A[t])
                        if raw < c[t]:
                            sp, tp = order(t, c[t], raw)
                            sig[t], stp[t], tgt[t], ref[t] = 1, sp, tp, c[t]
                    s = 0
                elif setup == "ob":
                    mid = lo + 0.5 * (hi - lo)
                    k_ob = -1
                    for k in range(t - 1, max(lo_bar - 3, t0 - 3, 0) - 1, -1):
                        if c[k] < o[k] and l[k] <= mid:
                            k_ob = k
                            break
                    if k_ob < 0 or h[k_ob] >= c[t]:
                        s = 0
                    else:
                        px = h[k_ob]
                        raw = (l[k_ob] - BUF * A[t]) if stop_mode == "struct" else (lo - BUF * A[t])
                        st_, tg_ = order(t, px, raw)
                        if allow[t]:
                            sig[t], stp[t], tgt[t], lim[t], ref[t] = 1, st_, tg_, px, px
                elif setup == "fvg":
                    fb = ft = np.nan
                    for k in range(t, max(t0, 2) - 1, -1):
                        if l[k] > h[k - 2] and l[k] < c[t]:
                            fb, ft = h[k - 2], l[k]
                            break
                    touched, tlo = False, np.nan
                    if math.isnan(ft) or fb <= lo:
                        s = 0
        if s != 2 and not math.isnan(sl[t]) and l[t] < sl[t] < c[t]:
            s, lo, lo_bar, choch, t0 = 1, l[t], t, sh[t], t
            if math.isnan(choch):
                s = 0
    return sig, stp, tgt, lim, ref


def strategy(df, setup="choch", rr=2.0, filt="none", stop="struct"):
    out = empty_signals(df)
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    sh, sl = (x.to_numpy(float) for x in confirmed_swings(df, PIV))
    A = atr(df).to_numpy(float)
    n = len(df)
    kz = killzone_mask(df) if "kz" in filt else np.ones(n, bool)
    bias = htf_bias(df) if "htf" in filt else None
    allow_l = kz & (bias > 0) if bias is not None else kz
    allow_s = kz & (bias < 0) if bias is not None else kz
    L = _long_machine(o, h, l, c, sh, sl, A, setup, stop, rr, allow_l)
    S = _long_machine(-o, -l, -h, -c, -sl, -sh, A, setup, stop, rr, allow_s)
    sl_, ss_ = L[0] > 0, S[0] > 0
    both = sl_ & ss_
    if setup == "ob":   # two resting orders on one bar: keep the one closer to the close
        dl = np.abs(c - L[4]) / c
        ds = np.abs(c + S[4]) / c       # S ref is negated price
        pick_l = both & (dl <= ds)
        sl_ = sl_ & (~both | pick_l)
        ss_ = ss_ & (~both | ~pick_l)
    else:
        sl_, ss_ = sl_ & ~both, ss_ & ~both
    out["signal"] = np.where(sl_, 1.0, np.where(ss_, -1.0, 0.0))
    out["stop"] = np.where(sl_, L[1], np.where(ss_, -S[1], np.nan))
    out["target"] = np.where(sl_, L[2], np.where(ss_, -S[2], np.nan))
    out["entry_limit"] = np.where(sl_, L[3], np.where(ss_, -S[3], np.nan))
    return out


strategy.MAX_HOLD = MAX_HOLD
strategy.LIMIT_TTL = LIMIT_TTL
