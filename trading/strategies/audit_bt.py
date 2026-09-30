"""Independent minimal backtester for the audit. Does NOT import bt.engine.

Written from the contract text in bt/engine.py's docstring (signal at close of t,
market entry at open t+1 with slippage, limit entry within TTL bars on a strict
touch, stop-first on ambiguous bars, target at maker, time/exit_signal at next open,
one position per symbol). Extra switches let the audit vary one assumption at a time:

    Rules.limit_fill : "strict" (low < px), "touch" (low <= px), "through" (low <= px*(1-bps))
    Rules.queue      : "first"  - bt.engine behaviour: a later signal is looked at only if the
                                   earlier pending limit never fills (uses the future to decide)
                       "block"  - real-time rule: a pending limit blocks new signals until it
                                   fills or expires
                       "independent" - every signal simulated on its own (no position limit)
    Rules.intrabar   : "stop_first" - bar-level, stop wins when stop and target share a bar
                       "1m"         - resolve the order of events with 1-minute bars
    Rules.target_on_fill_bar : check the target on the limit-fill bar (bt.engine: no)
"""
import math
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Rules:
    taker: float = 0.0005
    maker: float = 0.0002
    slip: float = 0.0002
    limit_fill: str = "strict"
    through_bps: float = 0.0
    queue: str = "first"
    intrabar: str = "stop_first"
    target_on_fill_bar: bool = False
    stop_gap_on_entry_bar: bool = False   # contract text is silent; engine: no gap check on entry bar


BASE = Rules()
HARSH = Rules(taker=0.0006, maker=0.0004, slip=0.0005)


class Minutes:
    """1m bars used to order events inside a coarser bar."""

    def __init__(self, m1):
        self.t = np.asarray(pd.DatetimeIndex(m1.index).as_unit("ns").asi8)
        self.o, self.h, self.l, self.c = (m1[k].to_numpy(float) for k in ("open", "high", "low", "close"))

    def span(self, t0_ns, tf_ns):
        a = int(np.searchsorted(self.t, t0_ns, "left"))
        b = int(np.searchsorted(self.t, t0_ns + tf_ns, "left"))
        return a, b


class Sim:
    def __init__(self, df, sig, rules=BASE, max_hold=None, limit_ttl=None, symbol="", minutes=None):
        self.o, self.h, self.l, self.c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        self.ts = df.index
        self.t_ns = np.asarray(pd.DatetimeIndex(df.index).as_unit("ns").asi8)
        self.tf_ns = int(np.median(np.diff(self.t_ns[:1000]))) if len(df) > 1 else 0
        self.n = len(df)
        get = lambda k, dflt: sig[k].to_numpy(float) if k in sig else np.full(self.n, dflt)
        self.sg, self.st, self.tg = get("signal", 0.0), get("stop", np.nan), get("target", np.nan)
        self.lm, self.ex = get("entry_limit", np.nan), get("exit_signal", 0.0)
        self.r = rules
        self.max_hold = max_hold if max_hold else 10 ** 9
        self.ttl = limit_ttl if limit_ttl else 1
        self.sym = symbol
        self.mn = minutes
        self.stats = {"ambiguous_bars": 0, "resolved_1m": 0, "unresolved_1m": 0, "changed_by_1m": 0,
                      "signals": 0, "skipped_busy": 0, "no_fill": 0, "bad_side": 0}

    # ------------------------------------------------------------------ helpers
    def _fills(self, d, px, lo, hi):
        r = self.r
        if r.limit_fill == "strict":
            return lo < px if d > 0 else hi > px
        if r.limit_fill == "touch":
            return lo <= px if d > 0 else hi >= px
        b = r.through_bps * 1e-4
        return lo <= px * (1 - b) if d > 0 else hi >= px * (1 + b)

    def _stop_px(self, d, stop, opn, allow_gap):
        gapped = allow_gap and ((d > 0 and opn < stop) or (d < 0 and opn > stop))
        return (opn if gapped else stop) * (1 - d * self.r.slip)

    def _walk_minutes(self, k, d, stop, target, fill_px=None):
        """Order stop/target inside bar k with 1m data. fill_px: limit entry filled inside this bar.
        Returns ('stop', px) / ('target', px) / None (neither) / 'nodata'."""
        a, b = self.mn.span(self.t_ns[k], self.tf_ns)
        if b - a < 1:
            return "nodata"
        mo, mh, ml = self.mn.o, self.mn.h, self.mn.l
        j = a
        if fill_px is not None:
            while j < b and not self._fills(d, fill_px, ml[j], mh[j]):
                j += 1
            if j == b:
                return "nodata"
            # fill minute: stop is exact (price crosses the limit before the stop); target not checked
            if (d > 0 and ml[j] <= stop) or (d < 0 and mh[j] >= stop):
                return ("stop", stop * (1 - d * self.r.slip))
            j += 1
        first_minute = fill_px is None
        while j < b:
            hs = (d > 0 and ml[j] <= stop) or (d < 0 and mh[j] >= stop)
            ht = not math.isnan(target) and ((d > 0 and mh[j] >= target) or (d < 0 and ml[j] <= target))
            if hs:
                return ("stop", self._stop_px(d, stop, mo[j], True))
            if ht:
                return ("target", target)
            j += 1
            first_minute = False
        return None

    # ------------------------------------------------------------------ one trade
    def _manage(self, k0, d, entry, stop, target, market, fill_px):
        o, h, l, c = self.o, self.h, self.l, self.c
        k = k0
        while True:
            first = k == k0
            hs = (d > 0 and l[k] <= stop) or (d < 0 and h[k] >= stop)
            tgt_ok = market or not first or self.r.target_on_fill_bar
            ht = tgt_ok and not math.isnan(target) and ((d > 0 and h[k] >= target) or (d < 0 and l[k] <= target))
            use_1m = self.r.intrabar == "1m" and self.mn is not None
            if hs and ht:
                self.stats["ambiguous_bars"] += 1
            # the fill bar of a limit entry can hide a target hit even when bar-level says "no target"
            probe_fill_target = use_1m and first and not market and not math.isnan(target) and \
                ((d > 0 and h[k] >= target) or (d < 0 and l[k] <= target))
            if use_1m and ((hs and ht) or probe_fill_target):
                res = self._walk_minutes(k, d, stop, target, None if (market or not first) else fill_px)
                if res == "nodata" or res is None:
                    self.stats["unresolved_1m"] += 1
                else:
                    self.stats["resolved_1m"] += 1
                    kind, px = res
                    if kind == "target" and hs:
                        self.stats["changed_by_1m"] += 1
                    if kind == "target" and not hs and first and not market:
                        self.stats["changed_by_1m"] += 1
                    fee = self.r.maker if kind == "target" else self.r.taker
                    return k, px, kind, fee
            if hs:
                allow_gap = (not first) or (market and self.r.stop_gap_on_entry_bar)
                return k, self._stop_px(d, stop, o[k], allow_gap), "stop", self.r.taker
            if ht:
                return k, target, "target", self.r.maker
            if k >= self.n - 1:
                return k, c[k], "end", self.r.taker
            if k - k0 + 1 >= self.max_hold:
                return k + 1, o[k + 1] * (1 - d * self.r.slip), "time", self.r.taker
            if self.ex[k] > 0:
                return k + 1, o[k + 1] * (1 - d * self.r.slip), "exit_signal", self.r.taker
            k += 1

    def _try(self, t):
        """Attempt the order from signal bar t. Returns trade dict, or ('nofill', last_bar) / None."""
        d = 1 if self.sg[t] > 0 else -1
        stop, target, px = self.st[t], self.tg[t], self.lm[t]
        market = math.isnan(px)
        if market:
            k0 = t + 1
            entry = self.o[k0] * (1 + d * self.r.slip)
            fee_in = self.r.taker
        else:
            k0 = None
            for k in range(t + 1, min(t + 1 + self.ttl, self.n)):
                if self._fills(d, px, self.l[k], self.h[k]):
                    k0 = k
                    break
            if k0 is None:
                self.stats["no_fill"] += 1
                return ("nofill", min(t + self.ttl, self.n - 1))
            entry, fee_in = px, self.r.maker
        if (d > 0 and entry <= stop) or (d < 0 and entry >= stop):
            self.stats["bad_side"] += 1
            return ("bad", k0)
        ek, xp, why, fee_out = self._manage(k0, d, entry, stop, target, market, None if market else px)
        risk = abs(entry - stop)
        pnl = d * (xp - entry) - (entry * fee_in + xp * fee_out)
        return {"symbol": self.sym, "dir": d, "t_signal": self.ts[t], "t_entry": self.ts[k0], "t_exit": self.ts[ek],
                "k_signal": t, "k_entry": k0, "k_exit": ek, "entry": entry, "stop": stop, "target": target,
                "exit": xp, "reason": why, "risk_pct": 100 * risk / entry, "R": pnl / risk,
                "R_gross": d * (xp - entry) / risk, "ret_pct": 100 * pnl / entry, "bars": ek - k0 + 1,
                "market": market}

    def run(self):
        out = []
        t = 0
        busy_until = -1          # last bar index at which signals are ignored
        while t < self.n - 1:
            s = self.sg[t]
            if not s or math.isnan(s) or math.isnan(self.st[t]):
                t += 1
                continue
            self.stats["signals"] += 1
            if self.r.queue == "independent":
                res = self._try(t)
                if isinstance(res, dict):
                    out.append(res)
                t += 1
                continue
            res = self._try(t)
            if isinstance(res, dict):
                out.append(res)
                # flat after an intrabar exit at bar e -> the signal at close of e is allowed;
                # open-price exits at bar e also allow the signal at e (same as the contract's
                # "decided at close" timing: the position was closed at the open of e).
                nxt = res["k_exit"]
                self.stats["skipped_busy"] += int(np.count_nonzero(np.nan_to_num(self.sg[t + 1:nxt])))
                t = nxt if nxt > t else t + 1
            elif self.r.queue == "block" and res[0] == "nofill":
                last = res[1]
                self.stats["skipped_busy"] += int(np.count_nonzero(np.nan_to_num(self.sg[t + 1:last])))
                t = last if last > t else t + 1
            else:
                t += 1
        return pd.DataFrame(out)


def simulate(df, sig, rules=BASE, max_hold=None, limit_ttl=None, symbol="", minutes=None, return_stats=False):
    s = Sim(df, sig, rules, max_hold, limit_ttl, symbol, minutes)
    tr = s.run()
    return (tr, s.stats) if return_stats else tr


# ---------------------------------------------------------------------- statistics

def summary(tr, label=""):
    if tr is None or len(tr) == 0:
        return {"label": label, "n": 0}
    R = tr["R"].to_numpy()
    sd = R.std(ddof=1) if len(R) > 1 else float("nan")
    return {"label": label, "n": int(len(R)), "win_pct": round(100 * float((R > 0).mean()), 1),
            "avg_R": round(float(R.mean()), 4), "t": round(float(R.mean() / sd * math.sqrt(len(R))), 2) if sd > 0 else None,
            "sum_R": round(float(R.sum()), 2)}


def clustered_t(tr, freq="1D"):
    """t-stat of mean R with trades clustered by entry day (cross-symbol correlation)."""
    if tr is None or len(tr) < 3:
        return None
    R = tr["R"].to_numpy()
    g = pd.DatetimeIndex(tr["t_entry"]).floor(freq)
    e = pd.Series(R - R.mean()).groupby(np.asarray(g)).sum().to_numpy()
    var = (e ** 2).sum() / len(R) ** 2
    G = len(e)
    var *= G / (G - 1) if G > 1 else 1
    return round(float(R.mean() / math.sqrt(var)), 2) if var > 0 else None


def block_bootstrap_t(tr, block_days=7, n_boot=2000, seed=1):
    """Mean R / bootstrap SE, resampling calendar blocks of entries (all symbols together)."""
    if tr is None or len(tr) < 10:
        return None
    rng = np.random.default_rng(seed)
    R = tr["R"].to_numpy()
    b = pd.DatetimeIndex(tr["t_entry"]).floor(f"{block_days}D")
    keys, inv = np.unique(np.asarray(b), return_inverse=True)
    sums = np.bincount(inv, weights=R)
    cnts = np.bincount(inv)
    G = len(keys)
    idx = rng.integers(0, G, size=(n_boot, G))
    means = sums[idx].sum(1) / cnts[idx].sum(1)
    se = means.std(ddof=1)
    return round(float(R.mean() / se), 2) if se > 0 else None


def is_oos(tr, label=""):
    cut = pd.Timestamp("2025-01-01", tz="UTC")
    if tr is None or len(tr) == 0:
        return {"IS": {"n": 0}, "OOS": {"n": 0}}
    a, b = tr[tr["t_entry"] < cut], tr[tr["t_entry"] >= cut]
    return {"IS": summary(a, label + " IS"), "OOS": summary(b, label + " OOS")}


# ---------------------------------------------------------------------- funding

def funding_cost(tr, fund, tf_minutes):
    """Funding paid per trade in R (positive = cost). fund: DataFrame ts, funding (rate per settlement).
    A position pays at settlement f if entry < f and f < exit time (intrabar exits: end of the exit bar,
    open exits: the exit bar's open, inclusive)."""
    if tr is None or len(tr) == 0:
        return np.array([]), np.array([])
    fts = np.asarray(pd.DatetimeIndex(fund["ts"]).as_unit("ns").asi8)
    fr = fund["funding"].to_numpy(float)
    cs = np.concatenate([[0.0], np.cumsum(fr)])
    te = np.asarray(pd.DatetimeIndex(tr["t_entry"]).as_unit("ns").asi8)
    tx = np.asarray(pd.DatetimeIndex(tr["t_exit"]).as_unit("ns").asi8)
    intrabar = tr["reason"].isin(["stop", "target"]).to_numpy()
    tf = int(tf_minutes * 60e9)
    # limit fills happen inside the entry bar -> after a settlement stamped at the bar open
    a = np.searchsorted(fts, te, "right")
    b = np.where(intrabar, np.searchsorted(fts, tx + tf, "left"), np.searchsorted(fts, tx, "right"))
    b = np.maximum(a, b)
    rate_sum = cs[b] - cs[a]
    nset = b - a
    price = tr["entry"].to_numpy(float)
    risk = price * tr["risk_pct"].to_numpy(float) / 100
    return tr["dir"].to_numpy() * rate_sum * price / risk, nset
