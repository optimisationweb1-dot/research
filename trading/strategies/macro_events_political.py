"""macro_events: unscheduled political/regulatory news on 1m bars (H6 + 'fast reaction' cells).

Pre-registration: trading/research/macro_events_prereg.md, section 'Внеплановые'.
Samples
  A  curated events from macro_events_events.csv with time_precision in {exact, approx} and category in
     POLITICAL/TARIFF/ETF/REGULATORY; ex-ante class direction_exante (+1/-1/0) set from the headline text.
  B  systematic: every first post of a 60-min burst in the Truth Social keyword sample
     (macro_events_truth_posts.csv, 2024-01..2025-10), no direction label.
Prices: Binance USD-M 1m klines (data.binance.vision monthly), BTC ETH SOL XRP DOGE.
Reference price p0 = open of the 1m bar containing t0 (seconds truncated, so p0 is up to 59 s BEFORE t0).
Entry after latency L: open of the first 1m bar starting >= t0 + L min (true wall-clock latency >= L min).

    python3 -m strategies.macro_events_political      (from trading/)
"""
import json
import math
import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from bt.data import _klines_month

HERE = os.path.dirname(os.path.abspath(__file__))
TRADING = os.path.dirname(HERE)
EV = os.path.join(TRADING, "research", "macro_events_events.csv")
TP = os.path.join(TRADING, "research", "macro_events_truth_posts.csv")
DIR1M = os.path.join(TRADING, "data", "ext", "macro_events", "1m")
OUT = os.path.join(TRADING, "results", "macro_events_political.json")
SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
COST_RT = {"base": 2 * (0.0005 + 0.0002), "harsh": 2 * (0.0006 + 0.0005)}
RNG = np.random.default_rng(20260930)
HORIZ = [1, 2, 5, 15, 60, 240]


def months_needed(times):
    ms = set()
    for t in times:
        for d in (t - pd.Timedelta(days=31), t, t + pd.Timedelta(days=1)):
            ms.add(d.strftime("%Y-%m"))
    return sorted(ms)


def fetch(sym, m):
    os.makedirs(DIR1M, exist_ok=True)
    p = os.path.join(DIR1M, f"{sym}-{m}.parquet")
    if os.path.exists(p):
        return p
    df = _klines_month(sym, "1m", m)
    if df is None:
        return None
    df = df[["open_time", "open", "high", "low", "close"]].astype(float)
    df["open_time"] = df["open_time"].astype("int64")
    df.to_parquet(p)
    return p


def load1m(sym, ms):
    parts = [pd.read_parquet(os.path.join(DIR1M, f"{sym}-{m}.parquet")) for m in ms
             if os.path.exists(os.path.join(DIR1M, f"{sym}-{m}.parquet"))]
    df = pd.concat(parts).drop_duplicates("open_time").sort_values("open_time")
    df.index = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    return df


def _p(idx_ns, o, t_ns):
    """open price of the 1m bar starting exactly at t_ns (NaN if the bar is missing)."""
    i = np.searchsorted(idx_ns, t_ns)
    j = np.minimum(i, len(idx_ns) - 1)
    return np.where(idx_ns[j] == t_ns, o[j], np.nan)


MIN = 60_000_000_000
OFFS = np.array([0] + HORIZ + [-60], dtype=np.int64)


def rets(o, idx, t0):
    """log returns from open(floor(t0)) to open(floor(t0)+h) for h in HORIZ and pre-60.
    Latency legs: entry at the first 1m open >= t0 + L minutes (full L minutes after the headline,
    seconds included), exit H minutes later; eL = move from floor(t0) to that entry.
    idx: int64 ns array of 1m bar open times."""
    b = (t0.value // MIN) * MIN
    p = _p(idx, o, b + OFFS * MIN)
    if np.isnan(p).any():
        return None
    r = {f"r{h}": math.log(p[i + 1] / p[0]) for i, h in enumerate(HORIZ)}
    r["pre60"] = math.log(p[0] / p[-1])
    for L in (1, 2, 5):
        e = -(-(t0.value + L * MIN) // MIN) * MIN
        q = _p(idx, o, np.array([e, e + 60 * MIN, e + 240 * MIN], dtype=np.int64))
        r[f"e{L}"] = math.log(q[0] / p[0]) if not np.isnan(q[0]) else np.nan
        r[f"L{L}H60"] = math.log(q[1] / q[0]) if not np.isnan(q[:2]).any() else np.nan
        r[f"L{L}H240"] = math.log(q[2] / q[0]) if not np.isnan(q[[0, 2]]).any() else np.nan
    return r


def baseline(o, idx, t0, k=30):
    """same minute-of-day on the previous k days (all days: crypto trades 24/7)."""
    out = []
    for d in range(1, k + 1):
        r = rets(o, idx, t0 - pd.Timedelta(days=d))
        if r:
            out.append(r)
    return pd.DataFrame(out)


def nw_t(x, lags=2):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 5:
        return float("nan")
    e = x - x.mean()
    s = (e @ e) / n
    for L in range(1, min(lags, n - 1) + 1):
        s += 2 * (1 - L / (lags + 1)) * (e[L:] @ e[:-L]) / n
    return float(x.mean() / math.sqrt(s / n)) if s > 0 else float("nan")


def build(sample):
    """sample: DataFrame with t (UTC), dir (ex-ante, may be 0/NaN), id. Returns long frame per sym."""
    ms = months_needed(sample["t"])
    jobs = [(s, m) for s in SYMS for m in ms]
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(lambda a: fetch(*a), jobs))
    rows = []
    for s in SYMS:
        df = load1m(s, ms)
        o, idx = df["open"].to_numpy(float), df.index.as_unit("ns").asi8
        for _, e in sample.iterrows():
            r = rets(o, idx, e["t"])
            if r is None:
                continue
            b = baseline(o, idx, e["t"])
            if len(b) < 10:
                continue
            row = {"id": e["id"], "t": e["t"], "sym": s, "dir": e["dir"]}
            row.update(r)
            for h in HORIZ:
                row[f"base_abs_r{h}"] = b[f"r{h}"].abs().mean()
            # placebo draw pool: store baseline |r15| and follow-trade legs for random draws
            row["_b"] = b
            rows.append(row)
    return rows


def summarize_sample(rows, name, directional):
    df = pd.DataFrame([{k: v for k, v in r.items() if k != "_b"} for r in rows])
    out = {"name": name, "n_events": int(df["id"].nunique()), "n_rows": len(df)}
    ev = df.groupby("id")
    # absolute impact vs baseline (per event averaged across symbols)
    imp = []
    for h in HORIZ:
        a = ev[f"r{h}"].apply(lambda x: x.abs().mean())
        bb = ev[f"base_abs_r{h}"].mean()
        imp.append({"h_min": h, "mean_abs_bp": round(1e4 * a.mean(), 1), "base_abs_bp": round(1e4 * bb.mean(), 1),
                    "ratio": round(a.mean() / bb.mean(), 2)})
    out["abs_impact"] = imp
    # placebo for |r15|: one random baseline day per (event,sym), 1000 draws, event-mean
    acts = df.groupby("id")["r15"].apply(lambda x: x.abs().mean()).mean()
    draws = []
    byid = {}
    for r in rows:
        byid.setdefault(r["id"], []).append(r["_b"]["r15"].abs().to_numpy())
    for _ in range(1000):
        vals = [np.mean([b[RNG.integers(len(b))] for b in lst]) for lst in byid.values()]
        draws.append(np.mean(vals))
    out["placebo_abs_r15"] = {"actual_bp": round(1e4 * acts, 1), "placebo_mean_bp": round(1e4 * np.mean(draws), 1),
                              "p": round(float(np.mean(np.array(draws) >= acts)), 4)}
    # share of the 60-min move already done before entry at L (events with |r60| > 2x base)
    big = df[df["r60"].abs() > 2 * df["base_abs_r60"]]
    out["share_of_r60_done_before_L"] = {f"L{L}": round(float((big[f"e{L}"] / big["r60"]).clip(-2, 2).median()), 2)
                                         for L in (1, 2, 5)} | {"n_rows": len(big)}
    # fast-reaction trades
    cells = []
    modes = ["momentum"] + (["exante"] if directional else [])
    for mode in modes:
        for L in (1, 2, 5):
            for H in (60, 240):
                x = df.copy()
                if mode == "exante":
                    x = x[x["dir"].fillna(0) != 0]
                    d = np.sign(x["dir"])
                else:
                    d = np.sign(x[f"e{L}"])
                g = d * x[f"L{L}H{H}"]
                x = x.assign(g=g)
                for cn, c in COST_RT.items():
                    net = (x["g"] - c).groupby(x["id"]).mean()     # per event, averaged over symbols
                    net = net.sort_index()
                    tt = x.groupby("id")["t"].first().sort_index()
                    cells.append({"mode": mode, "L": L, "H": H, "cost": cn, "n_events": int(net.notna().sum()),
                                  "mean_net_bp": round(1e4 * net.mean(), 1), "hit": round(float((net > 0).mean()), 2),
                                  "nw_t": round(nw_t(net.to_numpy()), 2),
                                  "IS_bp": round(1e4 * net[tt < pd.Timestamp("2025-01-01", tz="UTC")].mean(), 1),
                                  "OOS_bp": round(1e4 * net[tt >= pd.Timestamp("2025-01-01", tz="UTC")].mean(), 1)})
    out["fast_reaction"] = cells
    return out, df


def main():
    ev = pd.read_csv(EV)
    ev["t"] = pd.to_datetime(ev["t_publish_utc"], utc=True)
    A = ev[ev["category"].isin(["POLITICAL", "TARIFF", "ETF", "REGULATORY"]) &
           ev["time_precision"].isin(["exact", "approx"])].copy()
    A = A.rename(columns={"event_id": "id", "direction_exante": "dir"})[["id", "t", "dir", "description", "time_precision"]]
    tp = pd.read_csv(TP)
    tp["t"] = pd.to_datetime(tp["ts"], utc=True, format="mixed")
    B = tp[tp["cluster_first"]].copy()
    B["dir"] = np.nan
    B["id"] = B["id"].astype(str)
    res = {}
    rowsA = build(A)
    res["A_curated"], dfA = summarize_sample(rowsA, "A curated exact/approx", True)
    # per-event table (BTC and 5-coin mean) for the report
    per = dfA.groupby("id").agg(t=("t", "first"), dir=("dir", "first"), r1=("r1", "mean"), r5=("r5", "mean"),
                                r15=("r15", "mean"), r60=("r60", "mean"), r240=("r240", "mean"), pre60=("pre60", "mean"))
    per = per.join(A.set_index("id")[["description", "time_precision"]])
    for c in ["r1", "r5", "r15", "r60", "r240", "pre60"]:
        per[c] = (1e4 * per[c]).round(0)
    res["A_per_event_bp_5coin_mean"] = per.reset_index().astype({"t": str}).to_dict("records")
    # directional mean for ex-ante labelled events
    lab = dfA[dfA["dir"] != 0]
    g = lab.groupby("id").apply(lambda x: pd.Series({h: (np.sign(x["dir"]) * x[h]).mean()
                                                     for h in ["r1", "r5", "r15", "r60", "r240"]}))
    res["A_signed_by_exante_bp"] = {h: {"mean": round(1e4 * g[h].mean(), 1), "nw_t": round(nw_t(g[h].to_numpy()), 2),
                                        "hit": round(float((g[h] > 0).mean()), 2), "n": int(g[h].notna().sum())}
                                    for h in g.columns}
    rowsB = build(B)
    res["B_truth_systematic"], dfB = summarize_sample(rowsB, "B Truth Social keyword posts (cluster-first)", False)
    # by keyword group, |r15| ratio
    kw = tp.set_index(tp["id"].astype(str))[[c for c in tp if c.startswith("kw_")]]
    dfB = dfB.join(kw, on="id")
    grp = {}
    for c in kw.columns:
        x = dfB[dfB[c] == True]
        if x["id"].nunique() < 5:
            continue
        a = x.groupby("id")["r15"].apply(lambda s: s.abs().mean())
        b = x.groupby("id")["base_abs_r15"].mean()
        grp[c] = {"n_events": int(x["id"].nunique()), "abs_r15_bp": round(1e4 * a.mean(), 1),
                  "base_bp": round(1e4 * b.mean(), 1), "ratio": round(a.mean() / b.mean(), 2),
                  "share_ratio_gt2": round(float((a / b > 2).mean()), 2)}
    res["B_by_keyword"] = grp
    # top-10 posts by |r15| BTC
    btc = dfB[dfB["sym"] == "BTCUSDT"].copy()
    btc["abs15"] = btc["r15"].abs()
    top = btc.sort_values("abs15", ascending=False).head(10)
    top = top.join(tp.set_index(tp["id"].astype(str))[["url", "txt"]], on="id")
    res["B_top10_btc_abs_r15"] = [{"t": str(r.t), "r15_bp": round(1e4 * r.r15, 0), "r60_bp": round(1e4 * r.r60, 0),
                                   "url": r.url, "txt": r.txt[:140]} for r in top.itertuples()]
    with open(OUT, "w") as f:
        json.dump(res, f, indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k != "A_per_event_bp_5coin_mean"}, indent=1, default=str)[:12000])


if __name__ == "__main__":
    main()
