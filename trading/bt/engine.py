"""Bar backtest engine with explicit no-lookahead contract and realistic fills.

STRATEGY CONTRACT
    strategy(df, **params) -> DataFrame (same index as df) with columns:
        signal        +1 long / -1 short / 0 none. Decided at the CLOSE of bar t,
                      using only rows <= t.
        stop          protective stop price (required when signal != 0)
        target        take-profit price or NaN
        entry_limit   optional limit price; NaN -> market order at open of bar t+1
        exit_signal   optional; 1 = close any open position at open of bar t+1
    Optional attributes on the function: MAX_HOLD (bars), LIMIT_TTL (bars).

FILLS (conservative)
    market entry  : open[t+1] * (1 +/- slippage), taker fee
    limit entry   : bar k in t+1..t+ttl fills if low[k] < limit (long) strictly; price = limit, maker fee
                    If the fill bar also reaches the stop -> stopped out in that bar.
                    Target is not checked on the fill bar.
    stop          : stop price, or open if gapped through; taker fee + slippage
    target        : target price, maker fee (no gap improvement). Stop and target in the same bar -> stop.
    exit_signal / max_hold : next open (taker + slippage)
    One position per symbol at a time; signals while in position are ignored.

check_lookahead() recomputes the strategy on truncated history and fails if any
decision at bar k changes when future bars are removed.
"""
import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

IS_END = pd.Timestamp("2025-01-01", tz="UTC")  # in-sample: before; out-of-sample: from here


@dataclass
class Costs:
    taker: float = 0.0005   # per side, 0.05%  [estimate, BingX/Bitunix VIP0 - verify]
    maker: float = 0.0002   # per side, 0.02%  [estimate - verify]
    slippage: float = 0.0002  # 2 bps on market/stop fills


def _col(sig, name, default=np.nan):
    return sig[name].to_numpy(dtype=float) if name in sig else np.full(len(sig), default)


def simulate(df, sig, costs=Costs(), max_hold=None, limit_ttl=None, symbol=""):
    o, h, l, c = (df[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
    ts = df.index
    s = _col(sig, "signal", 0.0)
    st = _col(sig, "stop")
    tg = _col(sig, "target")
    lim = _col(sig, "entry_limit")
    ex = _col(sig, "exit_signal", 0.0)
    max_hold = max_hold or 10 ** 9
    limit_ttl = limit_ttl or 1
    n = len(df)
    trades = []
    t = 0
    while t < n - 1:
        d = s[t]
        if not d or math.isnan(d) or math.isnan(st[t]):
            t += 1
            continue
        d = 1 if d > 0 else -1
        stop, target = st[t], tg[t]
        # ---- entry
        if not math.isnan(lim[t]):
            px, fill, fee_in = lim[t], None, costs.maker
            for k in range(t + 1, min(t + 1 + limit_ttl, n)):
                if (d > 0 and l[k] < px) or (d < 0 and h[k] > px):
                    fill = k
                    break
            if fill is None:
                t += 1
                continue
            entry, k0 = px, fill
            if (d > 0 and entry <= stop) or (d < 0 and entry >= stop):
                t += 1
                continue
            stopped_on_fill = (d > 0 and l[k0] <= stop) or (d < 0 and h[k0] >= stop)
        else:
            k0 = t + 1
            entry = o[k0] * (1 + d * costs.slippage)
            fee_in = costs.taker
            if (d > 0 and entry <= stop) or (d < 0 and entry >= stop):
                t += 1
                continue
            stopped_on_fill = (d > 0 and l[k0] <= stop) or (d < 0 and h[k0] >= stop)
        risk = abs(entry - stop)
        # ---- manage
        market = math.isnan(lim[t])
        fee_out = costs.taker
        if stopped_on_fill:
            exit_px, exit_k, reason = stop * (1 - d * costs.slippage), k0, "stop"
        else:
            k = k0
            while True:
                later = k > k0
                if later and ((d > 0 and l[k] <= stop) or (d < 0 and h[k] >= stop)):
                    gap = (d > 0 and o[k] < stop) or (d < 0 and o[k] > stop)
                    exit_px, exit_k, reason = (o[k] if gap else stop) * (1 - d * costs.slippage), k, "stop"
                    break
                if (later or market) and not math.isnan(target) and (
                        (d > 0 and h[k] >= target) or (d < 0 and l[k] <= target)):
                    # resting limit at target fills at target even if price gaps through it
                    exit_px, exit_k, reason, fee_out = target, k, "target", costs.maker
                    break
                if k >= n - 1:
                    exit_px, exit_k, reason = c[k], k, "end"
                    break
                if k - k0 + 1 >= max_hold:
                    exit_px, exit_k, reason = o[k + 1] * (1 - d * costs.slippage), k + 1, "time"
                    break
                if ex[k] > 0:
                    exit_px, exit_k, reason = o[k + 1] * (1 - d * costs.slippage), k + 1, "exit_signal"
                    break
                k += 1
        gross = d * (exit_px - entry)
        fees = entry * fee_in + exit_px * fee_out
        trades.append({"symbol": symbol, "dir": d, "t_signal": ts[t], "t_entry": ts[k0], "t_exit": ts[exit_k],
                       "entry": entry, "stop": stop, "target": target, "exit": exit_px, "reason": reason,
                       "risk_pct": 100 * risk / entry, "R": (gross - fees) / risk,
                       "ret_pct": 100 * (gross - fees) / entry, "bars": exit_k - k0 + 1})
        t = exit_k if exit_k > t else t + 1
    return pd.DataFrame(trades)


def check_lookahead(strategy, df, params=None, n_checks=12, min_bars=500, seed=7):
    """Recompute on df[:k+1] and compare the decision at bar k with the full run."""
    params = params or {}
    full = strategy(df, **params)
    rng = np.random.default_rng(seed)
    cols = [c for c in ("signal", "stop", "target", "entry_limit", "exit_signal") if c in full]
    active = np.flatnonzero(full["signal"].fillna(0).to_numpy() != 0)
    active = active[active >= min_bars]
    ks = list(rng.choice(np.arange(min_bars, len(df)), size=min(n_checks, len(df) - min_bars), replace=False))
    if len(active):
        ks += list(rng.choice(active, size=min(n_checks, len(active)), replace=False))
    bad = []
    for k in sorted(set(int(x) for x in ks)):
        cut = strategy(df.iloc[:k + 1], **params)
        for ccol in cols:
            a, b = full[ccol].iloc[k], cut[ccol].iloc[k]
            same = (pd.isna(a) and pd.isna(b)) or (not pd.isna(a) and not pd.isna(b) and
                                                   math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-12))
            if not same:
                bad.append((df.index[k], ccol, a, b))
    if bad:
        raise AssertionError(f"LOOKAHEAD in {getattr(strategy, '__name__', strategy)}: {bad[:5]}")
    return True


def summarize(tr, risk_pct=0.5, label=""):
    if tr is None or len(tr) == 0:
        return {"label": label, "n": 0}
    tr = tr.sort_values("t_exit")
    R = tr["R"].to_numpy()
    eq = np.cumprod(1 + R * risk_pct / 100)
    peak = np.maximum.accumulate(eq)
    months = max(1.0, (tr["t_exit"].max() - tr["t_entry"].min()).days / 30.44)
    sd = R.std(ddof=1) if len(R) > 1 else float("nan")
    pos, neg = R[R > 0].sum(), -R[R < 0].sum()
    return {"label": label, "n": int(len(R)), "trades_per_month": round(len(R) / months, 1),
            "win_pct": round(100 * (R > 0).mean(), 1), "avg_R": round(R.mean(), 3),
            "t_stat": round(R.mean() / sd * math.sqrt(len(R)), 2) if sd and sd > 0 else None,
            "sum_R": round(R.sum(), 1), "pf": round(pos / neg, 2) if neg > 0 else None,
            f"ret_pct@{risk_pct}%": round(100 * (eq[-1] - 1), 1),
            "max_dd_pct": round(100 * (1 - eq / peak).max(), 1),
            "median_stop_pct": round(float(tr["risk_pct"].median()), 3)}


def split_summary(tr, risk_pct=0.5, label=""):
    """In-sample (< 2025-01-01) vs out-of-sample (>= 2025-01-01) by entry time."""
    if tr is None or len(tr) == 0:
        return {"IS": {"label": label, "n": 0}, "OOS": {"label": label, "n": 0}}
    return {"IS": summarize(tr[tr["t_entry"] < IS_END], risk_pct, label + " IS"),
            "OOS": summarize(tr[tr["t_entry"] >= IS_END], risk_pct, label + " OOS")}


def run(strategy, symbols, tf, params=None, costs=Costs(), load_kw=None, check=True, start=None, end=None):
    """Run a strategy over symbols; returns concatenated trades."""
    from .data import load
    params, load_kw = params or {}, load_kw or {}
    out = []
    for i, sym in enumerate(symbols):
        df = load(sym, tf, start=start, end=end, **load_kw)
        if check and i == 0:
            check_lookahead(strategy, df, params)
        sig = strategy(df, **params)
        out.append(simulate(df, sig, costs, getattr(strategy, "MAX_HOLD", None),
                            getattr(strategy, "LIMIT_TTL", None), sym))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()
