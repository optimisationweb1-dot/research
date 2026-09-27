"""IS-only diagnostics for the mean_reversion family (no OOS rows are read here unless --oos).

python3 -m strategies.mean_reversion_analysis events --tf 15m
    Gross forward returns (no costs) after mean-reversion trigger events, signed in the FADE
    direction, in bps and in ATR units, split by regime. Used for design decisions only.
"""
import argparse
import json
import sys

import numpy as np
import pandas as pd

import strategies.mean_reversion as M
from bt.data import SYMBOLS, load
from bt.engine import IS_END
from bt.features import atr, session_vwap


def events_frame(df):
    A = atr(df)
    c, o, h, l = df["close"], df["open"], df["high"], df["low"]
    f = pd.DataFrame(index=df.index)
    f["atr_bps"] = 1e4 * A / c
    n = 20
    m, sd = c.rolling(n).mean(), c.rolling(n).std()
    f["z"] = (c - m) / sd
    f["reenter_s"] = (c.shift(1) > (m + 2 * sd).shift(1)) & (c < m + 2 * sd)
    f["reenter_l"] = (c.shift(1) < (m - 2 * sd).shift(1)) & (c > m - 2 * sd)
    vw = session_vwap(df, "1D")
    f["dev"] = (c - vw) / A
    f["r2"] = M.rsi(c, 2)
    f["m3"] = (c - c.shift(3)) / A
    f["m1"] = (c - c.shift(1)) / A
    f["tr4h"] = M.htf_trend(df, 4, 50)
    f["adx"] = M.adx(df)
    f["dvr"] = M.dvol_rank(df) if "dvol" in df else np.nan
    # realized-vol regime: 1-day realized range vs its 30-day median
    k = M.bars(df, 24)
    rv = (np.log(c).diff() ** 2).rolling(k).sum()
    f["rvr"] = M.roll_rank(rv.iloc[::max(1, k // 24)], 30 * 24).reindex(df.index).ffill()
    er_n = M.bars(df, 12)
    f["er"] = (c - c.shift(er_n)).abs() / c.diff().abs().rolling(er_n).sum()
    for hh in (1, 4, 12, 24):
        f[f"fwd{hh}"] = 1e4 * (c.shift(-hh) - o.shift(-1)) / o.shift(-1)   # from next open (market entry)
    f["fwd0c"] = 1e4 * (o.shift(-1) - c) / c                                 # close -> next open gap
    return f


def summarize_events(sub, sign, col):
    x = sign * sub[col]
    x = x.dropna()
    if len(x) < 20:
        return {"n": int(len(x))}
    return {"n": int(len(x)), "mean_bps": round(float(x.mean()), 1),
            "t": round(float(x.mean() / x.std(ddof=1) * np.sqrt(len(x))), 2),
            "hit": round(float((x > 0).mean()), 3)}


def cmd_events(tf, oos=False):
    frames = []
    for s in SYMBOLS:
        df = load(s, tf, dvol=True)
        f = events_frame(df)
        f["sym"] = s
        f = f[f.index >= IS_END] if oos else f[f.index < IS_END]
        frames.append(f)
    F = pd.concat(frames)
    out = {"tf": tf, "period": "OOS" if oos else "IS", "median_atr_bps": round(float(F["atr_bps"].median()), 1)}

    def ev(name, mask_s, mask_l):
        res = {}
        for col in ("fwd1", "fwd4", "fwd12", "fwd24"):
            a = F[mask_s].assign(sg=-1.0)
            b = F[mask_l].assign(sg=1.0)
            ab = pd.concat([a, b])
            res[col] = summarize_events(ab, ab["sg"], col)
        out[name] = res

    z = F["z"]
    ev("z>=2.5 fade", z >= 2.5, z <= -2.5)
    ev("z>=3 fade", z >= 3, z <= -3)
    ev("bb reenter(20,2)", F["reenter_s"], F["reenter_l"])
    for nm, reg in [("adx<20", F["adx"] < 20), ("adx>=30", F["adx"] >= 30),
                    ("dvolrank<0.5", F["dvr"] < 0.5), ("dvolrank>=0.5", F["dvr"] >= 0.5),
                    ("rvrank<0.5", F["rvr"] < 0.5), ("rvrank>=0.5", F["rvr"] >= 0.5),
                    ("er<0.3", F["er"] < 0.3), ("er>=0.3", F["er"] >= 0.3)]:
        ev(f"bb reenter & {nm}", F["reenter_s"] & reg, F["reenter_l"] & reg)
    d = F["dev"]
    ev("vwap dev>=3", d >= 3, d <= -3)
    ev("vwap dev>=4", d >= 4, d <= -4)
    ev("rsi2 extreme & m3>=1.5 (no trend filter)", (F["r2"] > 90) & (F["m3"] >= 1.5), (F["r2"] < 10) & (F["m3"] <= -1.5))
    ev("rsi2 pullback WITH 4h trend", (F["tr4h"] < 0) & (F["r2"] > 90) & (F["m3"] >= 1.5),
       (F["tr4h"] > 0) & (F["r2"] < 10) & (F["m3"] <= -1.5))
    ev("rsi2 extreme AGAINST 4h trend", (F["tr4h"] > 0) & (F["r2"] > 90) & (F["m3"] >= 1.5),
       (F["tr4h"] < 0) & (F["r2"] < 10) & (F["m3"] <= -1.5))
    ev("1-bar move >=2.5 ATR fade", F["m1"] >= 2.5, F["m1"] <= -2.5)
    # control: pure 4h-trend following on every bar (drift / momentum baseline for the pullback test)
    ev("CONTROL all bars follow 4h trend", F["tr4h"] < 0, F["tr4h"] > 0)
    ev("CONTROL all bars long", pd.Series(False, index=F.index), pd.Series(True, index=F.index))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["events", "probe", "diag"])
    ap.add_argument("--fn", default=None)
    ap.add_argument("--params", default="[{}]", help="JSON list of param dicts")
    ap.add_argument("--tf", default="1h")
    ap.add_argument("--oos", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.cmd == "diag":
        cmd_diag()
        return 0
    if a.cmd == "probe":
        for p in json.loads(a.params):
            cmd_probe(a.fn, a.tf, p)
        return 0
    res = cmd_events(a.tf, a.oos)
    txt = json.dumps(res, indent=1)
    print(txt)
    if a.out:
        with open(a.out, "w") as f:
            f.write(txt)
    return 0



# ------------------------------------------------------------------ IS-only engine probes (design stage)

PROBE_LOG = "results/mean_reversion_isprobes.json"


def _probe_one(args):
    fn, sym, tf, params, cost = args
    from bt.engine import Costs, simulate
    strat = getattr(M, fn)
    df = load(sym, tf, dvol=True)
    df = df[df.index < IS_END]          # IS rows only: OOS is never loaded into the probe
    sig = strat(df, **params)
    c = {"base": Costs(), "zero": Costs(0.0, 0.0, 0.0)}[cost]
    return simulate(df, sig, c, getattr(strat, "MAX_HOLD", None), getattr(strat, "LIMIT_TTL", None), sym)


def is_probe(fn, tf, params, workers=2, log=True):
    from concurrent.futures import ProcessPoolExecutor
    from bt.engine import summarize
    res = {"fn": fn, "tf": tf, "params": params}
    for cost in ("base", "zero"):
        with ProcessPoolExecutor(workers) as ex:
            syms = [x for x in SYMBOLS if not (fn == "residual_follow" and x == "BTCUSDT")]
            parts = list(ex.map(_probe_one, [(fn, s, tf, params, cost) for s in syms]))
        tr = pd.concat([p for p in parts if len(p)], ignore_index=True)
        res[cost] = summarize(tr)
        if cost == "base":
            res["reasons"] = tr["reason"].value_counts().to_dict()
            res["sym_pos"] = int(sum(g["R"].mean() > 0 for _, g in tr.groupby("symbol")))
            res["long"] = round(float(tr.loc[tr.dir > 0, "R"].mean()), 3) if (tr.dir > 0).any() else None
            res["short"] = round(float(tr.loc[tr.dir < 0, "R"].mean()), 3) if (tr.dir < 0).any() else None
    if log:
        import os
        blob = json.load(open(PROBE_LOG)) if os.path.exists(PROBE_LOG) else {"probes": []}
        blob["probes"].append(json.loads(json.dumps(res, default=str)))
        blob["n_probes"] = len(blob["probes"])
        with open(PROBE_LOG, "w") as f:
            json.dump(blob, f, indent=1)
    return res


def cmd_probe(fn, tf, params):
    r = is_probe(fn, tf, params)
    b, z = r["base"], r["zero"]
    print(f"{fn} {tf} {json.dumps(params)} | IS n {b.get('n')} win {b.get('win_pct')} avgR {b.get('avg_R')} t {b.get('t_stat')} "
          f"stop% {b.get('median_stop_pct')} | gross avgR {z.get('avg_R')} t {z.get('t_stat')} | sym+ {r['sym_pos']} "
          f"L {r['long']} S {r['short']} | {r['reasons']}", flush=True)


# ------------------------------------------------------------------ post-hoc diagnostics (no selection)

def _run_full(args):
    fn, sym, tf, params, cost = args
    from bt.engine import Costs, simulate
    strat = getattr(M, fn)
    df = load(sym, tf, dvol=True)
    sig = strat(df, **params)
    c = {"base": Costs(), "zero": Costs(0.0, 0.0, 0.0)}[cost]
    return simulate(df, sig, c, getattr(strat, "MAX_HOLD", None), getattr(strat, "LIMIT_TTL", None), sym)


def cmd_diag(out_path="results/mean_reversion_diagnostics.json", workers=2):
    import glob
    from concurrent.futures import ProcessPoolExecutor
    from bt.engine import summarize
    res = {}
    for f in sorted(glob.glob("results/mean_reversion_*_*.json")):
        if any(x in f for x in ("events", "diagnostics", "isprobes")):
            continue
        r = json.load(open(f))
        name = f.split("mean_reversion_")[1][:-5]
        fn, tf, params = r["fn"], r["tf"], r["selected_params"]
        d = {"fn": fn, "tf": tf, "params": params}
        for cost in ("base", "zero"):
            with ProcessPoolExecutor(workers) as ex:
                parts = list(ex.map(_run_full, [(fn, s, tf, params, cost) for s in r["symbols"]]))
            tr = pd.concat([p for p in parts if len(p)], ignore_index=True)
            oos = tr[tr["t_entry"] >= IS_END]
            d[f"OOS_{cost}"] = summarize(oos)
            d[f"IS_{cost}"] = summarize(tr[tr["t_entry"] < IS_END])
            if cost == "base":
                d["OOS_long"] = summarize(oos[oos.dir > 0])
                d["OOS_short"] = summarize(oos[oos.dir < 0])
                hy = oos["t_entry"].dt.year.astype(str) + "H" + np.where(oos["t_entry"].dt.month <= 6, "1", "2")
                d["OOS_halfyear_avgR"] = {k: round(float(g["R"].mean()), 3) for k, g in oos.groupby(hy)}
                d["OOS_exit_reasons"] = oos["reason"].value_counts().to_dict()
                d["OOS_per_symbol_avgR"] = {k: round(float(g["R"].mean()), 3) for k, g in oos.groupby("symbol")}
                d["cost_R_per_trade_OOS"] = None
            else:
                d["cost_R_per_trade_OOS"] = round(d["OOS_zero"].get("avg_R", 0) - d["OOS_base"].get("avg_R", 0), 3)
        res[name] = d
        print(name, "OOS base", d["OOS_base"].get("avg_R"), "gross", d["OOS_zero"].get("avg_R"),
              "IS gross", d["IS_zero"].get("avg_R"), "L", d["OOS_long"].get("avg_R"), "S", d["OOS_short"].get("avg_R"),
              d["OOS_halfyear_avgR"], flush=True)
    with open(out_path, "w") as fh:
        json.dump(res, fh, indent=1, default=str)


if __name__ == "__main__":
    sys.exit(main())
