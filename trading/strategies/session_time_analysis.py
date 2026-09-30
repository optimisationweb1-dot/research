"""Diagnostics and summary for the session_time family (run AFTER the runner grids).

    cd trading && python3 -m strategies.session_time_analysis

For every results/session_time_<variant>_<tf>.json it re-runs ONLY the IS-selected config
(no new selection) and reports:
  * gross R (zero costs) IS / OOS -> how much of the result is the signal vs the costs;
  * exit reasons;
  * time-clustered t-stat: R of all symbols is SUMMED per entry day (per entry week for the
    weekly strategies) and the t-test is run on these period P&Ls (days without trades are not
    counted, which slightly favours the strategy). Clock-synchronous strategies trade all 10
    symbols at the same moment, so the runner's pooled t overstates significance;
  * entry-delay sensitivity: the same signals entered one bar later (robustness, not selection);
  * verdict by the task criteria.
Output: results/session_time_summary.json

    python3 -m strategies.session_time_analysis holdout

PRE-REGISTERED HOLDOUT (written before it was run): every IS-selected config above, unchanged,
plus one control (sess_filter d_cont 1h with sess='all', i.e. no session restriction), on 20
symbols never used in this family: DOT NEAR ATOM FIL BCH ETC UNI APT ARB OP AAVE CRV HBAR ICP
INJ LDO SEI SUI TRX XLM (Binance USD-M, downloaded by other agents with bt.data's own functions;
data 2023-11..2026-08). Trades from 2024-01-01 (two months of warm-up), reported for 2024 and
for 2025-01..2026-08 separately, base and harsh costs. No parameter is chosen here.
Output: results/session_time_holdout.json
"""
import glob
import json
import math
import os

import numpy as np
import pandas as pd

import strategies.session_time as st
from bt.data import SYMBOLS, load
from bt.engine import Costs, IS_END, simulate, summarize
from bt.runner import COST_SCENARIOS

ZERO = Costs(0.0, 0.0, 0.0)


def run(fn, tf, params, load_kw, costs, delay=0):
    parts = []
    for s in SYMBOLS:
        df = load(s, tf, **load_kw)
        sig = fn(df, **params)
        if delay:
            sig = sig.shift(delay)
            sig["signal"] = sig["signal"].fillna(0.0)
            sig["exit_signal"] = sig["exit_signal"].fillna(0.0)
            # keep the ORIGINAL exit clock for time exits (only the entry is late)
            sig["exit_signal"] = fn(df, **params)["exit_signal"].to_numpy()
        parts.append(simulate(df, sig, costs, fn.MAX_HOLD, fn.LIMIT_TTL, s))
    parts = [p for p in parts if len(p)]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def clustered_t(tr, freq="D"):
    if len(tr) < 3:
        return None, 0
    key = tr["t_entry"].dt.tz_convert("UTC").dt.floor("D") if freq == "D" else \
        tr["t_entry"].dt.tz_convert("UTC").dt.tz_localize(None).dt.to_period("W").astype(str)
    g = tr.groupby(key)["R"].sum()          # P&L per period in R (cluster-robust t of the total)
    if len(g) < 3 or g.std(ddof=1) == 0:
        return None, len(g)
    return round(float(g.mean() / g.std(ddof=1) * math.sqrt(len(g))), 2), int(len(g))


def split(tr):
    return tr[tr["t_entry"] < IS_END], tr[tr["t_entry"] >= IS_END]


def verdict(o, harsh, pos_sym, share):
    if not o or o.get("n", 0) == 0 or o["avg_R"] <= 0:
        return "NO_EDGE"
    ok = (o.get("t_stat") or 0) >= 2 and harsh > 0 and pos_sym >= 6 and (share or 0) >= 0.5
    return "PROMISING" if ok else "WEAK"


def main():
    rows = []
    for path in sorted(glob.glob("results/session_time_*_*.json")):
        name = os.path.basename(path)[len("session_time_"):-5]
        if name.startswith(("explore", "summary")):
            continue
        r = json.load(open(path))
        fn = getattr(st, r["fn"])
        tf, p, lk = r["tf"], r["selected_params"], r["load"]
        net = run(fn, tf, p, lk, COST_SCENARIOS["base"])
        gross = run(fn, tf, p, lk, ZERO)
        late = run(fn, tf, p, lk, COST_SCENARIOS["base"], delay=1)
        n_is, n_oos = split(net)
        g_is, g_oos = split(gross)
        l_is, l_oos = split(late)
        freq = "W" if r["fn"] in ("cme_gap", "weekend_break") else "D"
        per_sym = r["selected_OOS_per_symbol"]
        pos_sym = sum(1 for v in per_sym.values() if v.get("n", 0) and v["avg_R"] > 0)
        share = r["all_configs_OOS_avgR"]["share_positive"]
        o = r["selected_OOS"]
        harsh = r["selected_OOS_harsh_costs"].get("avg_R", float("nan"))
        row = {
            "variant": name, "fn": r["fn"], "tf": tf, "n_configs": r["n_configs"], "selected_params": p,
            "IS": {k: r["selected_IS"].get(k) for k in ("n", "win_pct", "avg_R", "t_stat", "ret_pct@0.5%",
                                                        "max_dd_pct", "median_stop_pct")},
            "OOS": {k: o.get(k) for k in ("n", "win_pct", "avg_R", "t_stat", "ret_pct@0.5%", "max_dd_pct",
                                          "median_stop_pct", "trades_per_month")},
            "OOS_harsh_avg_R": harsh,
            "OOS_symbols_positive": pos_sym,
            "OOS_per_symbol_avgR": {s: v.get("avg_R") for s, v in per_sym.items()},
            "share_configs_OOS_positive": share,
            "all_configs": [{"params": c["params"], "IS_avgR": c["IS"].get("avg_R"), "IS_t": c["IS"].get("t_stat"),
                             "OOS_avgR": c["OOS"].get("avg_R"), "OOS_t": c["OOS"].get("t_stat"),
                             "IS_n": c["IS"].get("n"), "OOS_n": c["OOS"].get("n")} for c in r["configs"]],
            "gross_avgR_IS": round(float(g_is["R"].mean()), 3) if len(g_is) else None,
            "gross_avgR_OOS": round(float(g_oos["R"].mean()), 3) if len(g_oos) else None,
            "gross_ret_bps_OOS": round(float(100 * g_oos["ret_pct"].mean()), 1) if len(g_oos) else None,
            "clustered_t_IS": clustered_t(n_is, freq), "clustered_t_OOS": clustered_t(n_oos, freq),
            "late1bar_avgR_IS": round(float(l_is["R"].mean()), 3) if len(l_is) else None,
            "late1bar_avgR_OOS": round(float(l_oos["R"].mean()), 3) if len(l_oos) else None,
            "exit_reasons_OOS": n_oos["reason"].value_counts(normalize=True).round(3).to_dict() if len(n_oos) else {},
            "per_year": {y: {k: v.get(k) for k in ("n", "avg_R", "t_stat")} for y, v in r["selected_per_year"].items()},
        }
        row["verdict"] = verdict(o, harsh, pos_sym, share)
        rows.append(row)
        print(name, tf, row["verdict"], "IS", row["IS"]["avg_R"], row["IS"]["t_stat"], "| OOS", o.get("avg_R"),
              o.get("t_stat"), "harsh", harsh, "sym+", pos_sym, "share", share, "| gross IS/OOS",
              row["gross_avgR_IS"], row["gross_avgR_OOS"], "| clT", row["clustered_t_IS"], row["clustered_t_OOS"],
              "| late", row["late1bar_avgR_OOS"], flush=True)
    total = sum(r["n_configs"] for r in rows)
    out = {"n_variants": len(rows), "n_configs_total": total, "variants": rows}
    with open("results/session_time_summary.json", "w") as f:
        json.dump(out, f, indent=1, default=str)
    print("total configs", total)


SCR = "/tmp/claude-0/-home-user-research/ea6ba1ab-fe99-5191-91e4-bb9455e40592/scratchpad"
HOLD_SETS = {os.path.join(SCR, "fp_hdata"): "DOTUSDT NEARUSDT ATOMUSDT FILUSDT BCHUSDT ETCUSDT UNIUSDT APTUSDT ARBUSDT OPUSDT".split(),
             os.path.join(SCR, "fp_hdata2"): "AAVEUSDT CRVUSDT HBARUSDT ICPUSDT INJUSDT LDOUSDT SEIUSDT SUIUSDT TRXUSDT XLMUSDT".split()}
T2024 = pd.Timestamp("2024-01-01", tz="UTC")


def _hold_one(a):
    import bt.data as D
    fnname, tf, params, load_kw, root, sym = a
    D.ROOT = root
    df = D.load(sym, tf, **load_kw)
    fn = getattr(st, fnname)
    sig = fn(df, **params).copy()
    sig.loc[sig.index < T2024, "signal"] = 0.0
    return {c: simulate(df, sig, COST_SCENARIOS[c], fn.MAX_HOLD, fn.LIMIT_TTL, sym) for c in ("base", "harsh")}


def holdout():
    from concurrent.futures import ProcessPoolExecutor
    summ = json.load(open("results/session_time_summary.json"))
    cfgs = [(v["variant"], v["fn"], v["tf"], v["selected_params"]) for v in summ["variants"]]
    ctl = dict(next(v for v in summ["variants"] if v["variant"] == "e_dcont_1h")["selected_params"], sess="all")
    cfgs.append(("CONTROL_e_dcont_1h_all", "sess_filter", "1h", ctl))
    out = {}
    with ProcessPoolExecutor(2) as ex:
        for name, fnname, tf, p in cfgs:
            lk = {"funding": True} if fnname == "funding_drift" else {}
            jobs = [(fnname, tf, p, lk, root, s) for root, syms in HOLD_SETS.items() for s in syms]
            res = list(ex.map(_hold_one, jobs))
            base = pd.concat([r["base"] for r in res if len(r["base"])], ignore_index=True)
            harsh = pd.concat([r["harsh"] for r in res if len(r["harsh"])], ignore_index=True)
            freq = "W" if fnname in ("cme_gap", "weekend_break") else "D"
            row = {"fn": fnname, "tf": tf, "params": p}
            for lab, m in (("2024", base["t_entry"] < IS_END), ("2025_26", base["t_entry"] >= IS_END)):
                b = base[m]
                hz = harsh[(harsh["t_entry"] >= IS_END) == (lab == "2025_26")]
                s = summarize(b)
                row[lab] = {k: s.get(k) for k in ("n", "win_pct", "avg_R", "t_stat", "ret_pct@0.5%", "max_dd_pct")}
                row[lab]["harsh_avg_R"] = round(float(hz["R"].mean()), 3) if len(hz) else None
                row[lab]["clustered_t"] = clustered_t(b, freq)
                row[lab]["symbols_positive"] = int((b.groupby("symbol")["R"].mean() > 0).sum()) if len(b) else 0
                row[lab]["symbols_traded"] = int(b["symbol"].nunique()) if len(b) else 0
            out[name] = row
            print(name, tf, "2024", row["2024"].get("n"), row["2024"].get("avg_R"), row["2024"].get("t_stat"),
                  "| 2025-26", row["2025_26"].get("n"), row["2025_26"].get("avg_R"), row["2025_26"].get("t_stat"),
                  "harsh", row["2025_26"].get("harsh_avg_R"), "sym+", row["2025_26"]["symbols_positive"],
                  "/", row["2025_26"]["symbols_traded"], "clT", row["2025_26"]["clustered_t"], flush=True)
    with open("results/session_time_holdout.json", "w") as f:
        json.dump(out, f, indent=1, default=str)


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["holdout"]:
        holdout()
    elif sys.argv[1:] != ["decay"]:
        main()


# ----------------------------------------------------------------------------- post-hoc decay
def decay():
    """POST-HOC description (no selection): the IS event-study patterns that motivated (b), (c),
    (d') and (f) re-measured in bps, IS (2023-24) vs OOS (2025-01..2026-08), on the 10 main symbols.
    Daily cross-sectional averages (EW over symbols) so the t-stat is not inflated by correlation."""
    from strategies.session_time_explore import bps_stats
    wins = {"US 09:30-11:30 ET": (570, 690), "US 16:00-20:00 ET": (960, 1200)}
    out = {}
    per = {k: [] for k in wins}
    orb, fund, cme = [], [], []
    for s in SYMBOLS:
        df = load(s, "15m", funding=True)
        mod, day, dow = st.local_clock(df, "America/New_York")
        td = st.us_trading_day(day, dow)
        o, c = df["open"], df["close"]
        for k, (a, b) in wins.items():
            pa = o.where(td & (mod == a)).groupby(day.to_numpy()).last()
            pb = o.where(td & (mod == b)).groupby(day.to_numpy()).last()
            r = (pb / pa - 1).dropna()
            per[k].append(pd.Series(r.values, index=pd.to_datetime(r.index)))
        # funding f<-0.01%: return over the 2h before settlement
        tfm = 15
        mc = (df.index.hour * 60 + df.index.minute + tfm) % 1440
        pos = np.flatnonzero(np.isin(mc, [0, 480, 960]))
        cc = c.to_numpy(float)
        ff = df["funding"].shift(1).to_numpy(float)
        for p in pos[pos >= 8]:
            if ff[p - 8] < -1e-4:
                fund.append((df.index[p], cc[p] / cc[p - 8] - 1))
        # CME weekend gap continuation over 8h (1h bars)
        h1 = load(s, "1h")
        lmod, lday, ldow = st.local_clock(h1, "America/Chicago")
        cm = lmod + 60
        c1 = h1["close"].to_numpy(float)
        fri = np.flatnonzero(((ldow == 4) & (cm == 960)).to_numpy())
        sun = np.flatnonzero(((ldow == 6) & (cm == 1020)).to_numpy())
        for j in sun:
            pr = fri[fri < j]
            if not len(pr) or j + 8 >= len(c1):
                continue
            g = c1[j] / c1[pr[-1]] - 1
            if abs(g) >= 0.01:
                cme.append((h1.index[j], np.sign(g) * (c1[j + 8] / c1[j] - 1)))
    for k in wins:
        d = pd.concat(per[k])
        ew = d.groupby(level=0).mean()
        out[k] = {"IS": bps_stats(ew[ew.index < "2025-01-01"].values),
                  "OOS": bps_stats(ew[ew.index >= "2025-01-01"].values)}
    for name, ev in (("funding<-0.01%: 2h pre-settlement return", fund),
                     ("CME |gap|>=1%: 8h continuation (signed)", cme)):
        e = pd.DataFrame(ev, columns=["t", "r"])
        e["k"] = e["t"].dt.floor("D")
        ew = e.groupby("k")["r"].mean()
        out[name] = {"IS": bps_stats(ew[ew.index < IS_END].values), "OOS": bps_stats(ew[ew.index >= IS_END].values)}
    for k, v in out.items():
        print(k, "| IS", v["IS"], "| OOS", v["OOS"])
    json.dump(out, open("results/session_time_decay.json", "w"), indent=1)


if __name__ == "__main__" and __import__("sys").argv[1:] == ["decay"]:
    decay()
