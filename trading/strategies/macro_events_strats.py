"""macro_events: pre-registered scheduled-event rules (S1-S4) through bt.engine.simulate.

Pre-registration: trading/research/macro_events_prereg.md (22 variants). Release times come from the
official calendars (published ~1 year ahead), so using them inside the strategy is not look-ahead.
All decisions at bar t use rows <= t only (check_lookahead is run on every strategy).

    python3 -m strategies.macro_events_strats          (from trading/, 2 worker processes)
"""
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from bt.data import SYMBOLS, load
from bt.engine import Costs, check_lookahead, simulate, split_summary, summarize
from bt.features import atr

HERE = os.path.dirname(os.path.abspath(__file__))
TRADING = os.path.dirname(HERE)
EV = os.path.join(TRADING, "research", "macro_events_events.csv")
OUT = os.path.join(TRADING, "results", "macro_events_strats.json")
ET = "America/New_York"
COSTS = {"base": Costs(), "harsh": Costs(taker=0.0006, maker=0.0004, slippage=0.0005)}
BUSY_CATS = ["CPI", "NFP", "PPI", "PCE", "FOMC_STATEMENT", "FOMC_MINUTES", "FED_SPEECH"]
SETS = {"HIGH3": ["CPI", "NFP", "FOMC_STATEMENT"], "CPI_FOMC": ["CPI", "FOMC_STATEMENT"],
        "FOMC": ["FOMC_STATEMENT"], "CPI": ["CPI"]}
FIVE = pd.Timedelta(minutes=5)


def _events():
    ev = pd.read_csv(EV)
    ev["t"] = pd.to_datetime(ev["t_publish_utc"], utc=True)
    return ev


def event_times(which):
    ev = _events()
    return sorted(ev.loc[ev["category"].isin(SETS[which]), "t"].tolist())


def busy_dates():
    ev = _events()
    return set(ev.loc[ev["category"].isin(BUSY_CATS), "t"].dt.tz_convert(ET).dt.date)


def placebo_times(which, seed):
    """One random non-event weekday per real event, same NY wall-clock time, within +-60 days."""
    rng = np.random.default_rng(seed)
    busy = busy_dates()
    out = []
    for t0 in event_times(which):
        loc = t0.tz_convert(ET)
        cands = []
        for k in range(-60, 61):
            if k == 0:
                continue
            d = (loc + pd.Timedelta(days=k)).date()
            if d.weekday() >= 5 or d in busy:
                continue
            cands.append(pd.Timestamp(f"{d} {loc.strftime('%H:%M')}", tz=ET).tz_convert("UTC"))
        out.append(cands[rng.integers(len(cands))])
    return sorted(out)


def _pos(idx, times):
    """integer positions of bar opens equal to times (skip missing)."""
    p = idx.get_indexer(pd.DatetimeIndex(times))
    return p[p >= 0]


def _atr1h(df):
    """ATR(14) on 1h bars, known at the close of each hour, mapped onto 5m bar closes."""
    h = df[["open", "high", "low", "close"]].resample("1h", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    a = atr(h, 14)
    a.index = a.index + pd.Timedelta(hours=1)          # available at the hour's close
    close_t = df.index + FIVE
    return pd.Series(a.reindex(close_t, method="ffill").to_numpy(), index=df.index)


def _sig(df):
    return pd.DataFrame({"signal": 0.0, "stop": np.nan, "target": np.nan, "exit_signal": 0.0}, index=df.index)


# ------------------------------------------------------------------ S1 straddle breakout
def s1_breakout(df, times=(), k=1, min_stop=0.003, window=12):
    sig = _sig(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    n = len(df)
    for p in _pos(df.index, times):
        last = p + k - 1                     # range complete at close of bar `last`
        if last >= n:
            continue
        hi, lo = h[p:last + 1].max(), l[p:last + 1].min()
        for j in range(last + 1, min(last + 1 + window, n)):
            if c[j] > hi:
                sig.iat[j, 0] = 1
                sig.iat[j, 1] = min(lo, c[j] * (1 - min_stop))
                break
            if c[j] < lo:
                sig.iat[j, 0] = -1
                sig.iat[j, 1] = max(hi, c[j] * (1 + min_stop))
                break
    return sig


# ------------------------------------------------------------------ S2 fade the first 15m impulse
def _base_med_abs15(df, t0, busy):
    """median |15m return| at the same NY time on up to 40 prior non-event weekdays (past only)."""
    loc = t0.tz_convert(ET)
    ts = []
    for k in range(1, 61):
        d = (loc - pd.Timedelta(days=k)).date()
        if d.weekday() >= 5 or d in busy:
            continue
        ts.append(pd.Timestamp(f"{d} {loc.strftime('%H:%M')}", tz=ET).tz_convert("UTC"))
    i = df.index.get_indexer(pd.DatetimeIndex(ts))
    i = i[(i >= 0) & (i + 2 < len(df))][:40]
    if len(i) < 10:
        return float("nan")
    o, c = df["open"].to_numpy(float), df["close"].to_numpy(float)
    return float(np.median(np.abs(np.log(c[i + 2] / o[i]))))


def s2_fade(df, times=(), m=2.0, busy=frozenset()):
    sig = _sig(df)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    for p in _pos(df.index, times):
        j = p + 2                            # close of 3rd bar = t0+15m
        if j >= len(df):
            continue
        med = _base_med_abs15(df, df.index[p], busy)
        r = math.log(c[j] / o[p])
        if not med or math.isnan(med) or abs(r) < m * med:
            continue
        mid = o[p] + 0.5 * (c[j] - o[p])     # 50% retracement of the impulse
        if r > 0:
            sig.iat[j, 0], sig.iat[j, 1], sig.iat[j, 2] = -1, h[p:j + 1].max() * 1.001, mid
        else:
            sig.iat[j, 0], sig.iat[j, 1], sig.iat[j, 2] = 1, l[p:j + 1].min() * 0.999, mid
    return sig


# ------------------------------------------------------------------ S3 follow the first move
def s3_follow(df, times=(), k=1, atr_mult=2.0):
    sig = _sig(df)
    o, c = df["open"].to_numpy(float), df["close"].to_numpy(float)
    a = _atr1h(df).to_numpy(float)
    for p in _pos(df.index, times):
        j = p + k - 1                        # decided at close of bar j -> entry at open t0+k*5m
        if j >= len(df) or math.isnan(a[j]):
            continue
        d = 1 if c[j] > o[p] else (-1 if c[j] < o[p] else 0)
        if d:
            sig.iat[j, 0], sig.iat[j, 1] = d, c[j] - d * atr_mult * a[j]
    return sig


# ------------------------------------------------------------------ S4 pre-event long
def s4_pre(df, times=(), atr_mult=3.0):
    sig = _sig(df)
    c = df["close"].to_numpy(float)
    a = _atr1h(df).to_numpy(float)
    for t0 in times:
        # decision at close of the bar opening t0-24h05m -> market entry at open t0-24h
        j = df.index.get_indexer([t0 - pd.Timedelta(hours=24) - FIVE])[0]
        if j < 0 or math.isnan(a[j]):
            continue
        sig.iat[j, 0], sig.iat[j, 1] = 1, c[j] - atr_mult * a[j]
        q = df.index.get_indexer([t0 - FIVE])[0]
        if q >= 0:
            sig.iat[q, 3] = 1                # exit at open of the event bar (t0)
    return sig


FUNCS = {"S1": s1_breakout, "S2": s2_fade, "S3": s3_follow, "S4": s4_pre}


def variants():
    v = []
    for es in ["HIGH3", "CPI_FOMC"]:
        for k in [1, 3]:
            for H in [12, 48]:
                v.append(("S1", es, {"k": k}, H))
        for m in [2.0, 3.0]:
            for H in [12, 48]:
                v.append(("S2", es, {"m": m}, H))
    for k in [1, 3]:
        for H in [48, 288]:
            v.append(("S3", "HIGH3", {"k": k}, H))
    v.append(("S4", "FOMC", {}, 300))
    v.append(("S4", "CPI", {}, 300))
    return v


def vname(v):
    s, es, p, H = v
    return f"{s}|{es}|" + ",".join(f"{a}={b}" for a, b in p.items()) + f"|H={H}"


def _run_one(args):
    v, sym, times_key, seed = args
    s, es, p, H = v
    times = event_times(es) if seed is None else placebo_times(es, seed)
    df = load(sym, "5m")
    kw = dict(p, times=times)
    if s == "S2":
        kw["busy"] = busy_dates()
    sig = FUNCS[s](df, **kw)
    out = {}
    for cn, co in COSTS.items():
        tr = simulate(df, sig, co, max_hold=H, symbol=sym)
        tr["cost"] = cn
        out[cn] = tr
    return vname(v), sym, seed, out


def lookahead_checks():
    df = load("BTCUSDT", "5m", start="2024-01-01", end="2024-04-01")
    busy = busy_dates()
    res = {}
    for s, es in [("S1", "HIGH3"), ("S2", "HIGH3"), ("S3", "HIGH3"), ("S4", "FOMC")]:
        times = [t for t in event_times(es) if df.index[0] < t < df.index[-1]]
        kw = {"times": times}
        if s == "S2":
            kw["busy"] = busy
        # choose check points right after events so decisions are actually exercised
        try:
            check_lookahead(FUNCS[s], df, kw, n_checks=12, min_bars=2000)
            res[s] = "ok"
        except AssertionError as e:
            res[s] = f"FAIL {e}"
    return res


def main(n_placebo=int(os.environ.get("MACRO_PLACEBO", 100))):
    out = {"lookahead": lookahead_checks()}
    print(out["lookahead"], flush=True)
    jobs = [(v, sym, None, None) for v in variants() for sym in SYMBOLS]
    trades = {}
    with ProcessPoolExecutor(2) as ex:
        for name, sym, _, res in ex.map(_run_one, jobs, chunksize=4):
            for cn, tr in res.items():
                trades.setdefault((name, cn), []).append(tr)
    rows = []
    allt = []
    for (name, cn), lst in trades.items():
        tr = pd.concat(lst, ignore_index=True)
        tr["variant"] = name
        allt.append(tr)
        ss = split_summary(tr, label=name)
        rows.append({"variant": name, "cost": cn, "IS": ss["IS"], "OOS": ss["OOS"]})
    pd.concat(allt).to_parquet(os.path.join(TRADING, "data", "ext", "macro_events", "strat_trades.parquet"))
    out["variants"] = rows
    # IS selection per strategy family: max IS day-cluster t at base cost, n>=30
    sel = {}
    for fam in ["S1", "S2", "S3", "S4"]:
        cand = [r for r in rows if r["cost"] == "base" and r["variant"].startswith(fam)
                and r["IS"].get("n", 0) >= 30]
        if not cand:
            continue
        best = max(cand, key=lambda r: r["IS"].get("t_stat_day_cluster") or -99)
        sel[fam] = best["variant"]
    out["selected_IS"] = sel
    # placebo for selected variants: same rule on random non-event days (same NY time)
    vmap = {vname(v): v for v in variants()}
    plac = {}
    if n_placebo:
        jobs = [(vmap[nm], sym, None, 1000 + i) for nm in sel.values() for i in range(n_placebo) for sym in SYMBOLS]
        acc = {}
        with ProcessPoolExecutor(2) as ex:
            for name, sym, seed, res in ex.map(_run_one, jobs, chunksize=10):
                acc.setdefault((name, seed), []).append(res["base"])
        for (name, seed), lst in acc.items():
            tr = pd.concat(lst, ignore_index=True)
            if len(tr) == 0:
                continue
            is_ = tr[tr["t_entry"] < pd.Timestamp("2025-01-01", tz="UTC")]["R"].mean()
            oos = tr[tr["t_entry"] >= pd.Timestamp("2025-01-01", tz="UTC")]["R"].mean()
            plac.setdefault(name, []).append((is_, oos, tr["R"].mean()))
        for name, arr in plac.items():
            a = np.array(arr, float)
            act = [r for r in rows if r["variant"] == name and r["cost"] == "base"][0]
            plac[name] = {"n_draws": len(a),
                          "IS_avgR_placebo_mean": round(float(np.nanmean(a[:, 0])), 3),
                          "OOS_avgR_placebo_mean": round(float(np.nanmean(a[:, 1])), 3),
                          "p_IS_ge_actual": round(float(np.nanmean(a[:, 0] >= act["IS"].get("avg_R", np.nan))), 3),
                          "p_OOS_ge_actual": round(float(np.nanmean(a[:, 1] >= act["OOS"].get("avg_R", np.nan))), 3)}
    out["placebo"] = plac
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1, default=str)
    for r in sorted(rows, key=lambda r: (r["variant"], r["cost"])):
        i, o = r["IS"], r["OOS"]
        print(f"{r['variant']:32s} {r['cost']:5s} IS n={i.get('n')} R={i.get('avg_R')} tc={i.get('t_stat_day_cluster')} | "
              f"OOS n={o.get('n')} R={o.get('avg_R')} tc={o.get('t_stat_day_cluster')} pf={o.get('pf')}")
    print("selected", sel)
    print(json.dumps(plac, indent=1))


# ------------------------------------------------------------------ POST-HOC (not pre-registered)
# Added on 30.09.2026 AFTER seeing the event study (CPI pre-4h drift t=4.6 BTC, CPI-day d1 ALL10 +162 bp).
# IS and OOS were both visible in the study, so these results are NOT a clean out-of-sample test.
def p_pre_long(df, times=(), lead_min=240, hold_after_min=0, atr_mult=3.0):
    """long from t0-lead to t0+hold_after (exit_signal), protective stop atr_mult x ATR(14,1h)."""
    sig = _sig(df)
    c = df["close"].to_numpy(float)
    a = _atr1h(df).to_numpy(float)
    for t0 in times:
        j = df.index.get_indexer([t0 - pd.Timedelta(minutes=lead_min) - FIVE])[0]
        if j < 0 or math.isnan(a[j]):
            continue
        sig.iat[j, 0], sig.iat[j, 1] = 1, c[j] - atr_mult * a[j]
        q = df.index.get_indexer([t0 + pd.Timedelta(minutes=hold_after_min) - FIVE])[0]
        if q >= 0:
            sig.iat[q, 3] = 1
    return sig


POSTHOC = [("CPI", {"lead_min": 240, "hold_after_min": 0}), ("CPI", {"lead_min": 60, "hold_after_min": 0}),
           ("CPI", {"lead_min": 240, "hold_after_min": 1440}), ("HIGH3", {"lead_min": 240, "hold_after_min": 0})]


def _run_posthoc(args):
    es, p, seed = args
    times = event_times(es) if seed is None else placebo_times(es, seed)
    out = {}
    for sym in SYMBOLS:
        df = load(sym, "5m")
        sig = p_pre_long(df, times=times, **p)
        for cn, co in COSTS.items():
            if seed is not None and cn == "harsh":
                continue
            out.setdefault(cn, []).append(simulate(df, sig, co, max_hold=400, symbol=sym))
    return es, str(p), seed, {k: pd.concat(v, ignore_index=True) for k, v in out.items()}


def posthoc_main(n_placebo=100):
    df = load("BTCUSDT", "5m", start="2024-01-01", end="2024-06-01")
    check_lookahead(p_pre_long, df, {"times": [t for t in event_times("CPI") if df.index[0] < t < df.index[-1]]},
                    min_bars=2000)
    res = []
    jobs = [(es, p, None) for es, p in POSTHOC] + [(es, p, 2000 + i) for es, p in POSTHOC for i in range(n_placebo)]
    acc = {}
    with ProcessPoolExecutor(2) as ex:
        for es, p, seed, out in ex.map(_run_posthoc, jobs, chunksize=5):
            acc[(es, p, seed)] = out
    cut = pd.Timestamp("2025-01-01", tz="UTC")
    for es, p in POSTHOC:
        act = acc[(es, str(p), None)]
        row = {"variant": f"POSTHOC|{es}|{p}"}
        for cn in COSTS:
            ss = split_summary(act[cn], label=cn)
            row[cn] = ss
        pl = np.array([[acc[(es, str(p), 2000 + i)]["base"].pipe(lambda t: t[t.t_entry < cut]["R"].mean()),
                        acc[(es, str(p), 2000 + i)]["base"].pipe(lambda t: t[t.t_entry >= cut]["R"].mean())]
                       for i in range(n_placebo)])
        row["placebo"] = {"IS_mean": round(float(np.nanmean(pl[:, 0])), 3), "OOS_mean": round(float(np.nanmean(pl[:, 1])), 3),
                          "p_IS": round(float(np.mean(pl[:, 0] >= row["base"]["IS"]["avg_R"])), 3),
                          "p_OOS": round(float(np.mean(pl[:, 1] >= row["base"]["OOS"]["avg_R"])), 3)}
        res.append(row)
        print(json.dumps(row, default=str))
    with open(os.path.join(TRADING, "results", "macro_events_posthoc.json"), "w") as f:
        json.dump(res, f, indent=1, default=str)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "posthoc":
        posthoc_main()
    else:
        main()
