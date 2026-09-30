"""pump_anatomy: OI build-up before pumps (H7) on a case-control sample (metrics are daily files).

    python3 -m strategies.pump_anatomy_oi pairs     -> data/ext/pump_anatomy/oi_pairs.csv (events + controls)
    python3 -m strategies.pump_anatomy_data metrics data/ext/pump_anatomy/oi_pairs_dl.csv
    python3 -m strategies.pump_anatomy_oi analyse

Cases: pump onsets (L1, +40%/7d) from 2024-01-15. Controls: random eligible symbol-days from the same
period (2 per case), drawn without looking at outcomes. OI snapshot = last 5-min row of the day
(create_time < next 00:00 UTC), i.e. known at the day close. Days fetched: d-7, d-3, d.
"""
import os
import sys

import numpy as np
import pandas as pd

from strategies.pump_anatomy_analysis import IS_END, RES, load_events, load_panel, week_block_boot
from strategies.pump_anatomy_panel import ROOT

LAGS = (0, 3, 7)
START = pd.Timestamp("2024-01-15", tz="UTC")


def make_pairs():
    rng = np.random.default_rng(7)
    e = load_events()
    e = e[e["date"] >= START][["symbol", "date"]].assign(case=1)
    p = load_panel(["date", "symbol", "elig"])
    pool = p[p["elig"] & (p["date"] >= START) & (p["date"] <= "2026-08-24")]
    c = pool.sample(n=2 * len(e), random_state=11)[["symbol", "date"]].assign(case=0)
    s = pd.concat([e, c], ignore_index=True)
    s.to_csv(os.path.join(ROOT, "oi_pairs.csv"), index=False)
    dl = []
    for _, r in s.iterrows():
        for L in LAGS:
            dl.append((r["symbol"], (r["date"] - pd.Timedelta(days=L)).strftime("%Y-%m-%d")))
    pd.DataFrame(dl, columns=["symbol", "date"]).drop_duplicates().to_csv(os.path.join(ROOT, "oi_pairs_dl.csv"), index=False)
    print(len(e), "cases", len(c), "controls", len(dl), "day-files")


def oi_at(sym, date_str, cache):
    if sym not in cache:
        path = os.path.join(ROOT, "metrics", f"{sym}.parquet")
        cache[sym] = pd.read_parquet(path) if os.path.exists(path) else None
    m = cache[sym]
    if m is None or "sum_open_interest_value" not in m:
        return np.nan, np.nan
    g = m[m["date"] == date_str]
    g = g[pd.to_numeric(g["sum_open_interest"], errors="coerce") > 0]
    if not len(g):
        return np.nan, np.nan
    g = g.sort_values("create_time")
    last = g.iloc[-1]
    return float(last["sum_open_interest"]), float(last["sum_open_interest_value"])


def analyse():
    s = pd.read_csv(os.path.join(ROOT, "oi_pairs.csv"))
    s["date"] = pd.to_datetime(s["date"], utc=True)
    p = load_panel(["date", "symbol", "close", "med30qv", "fund_last", "pr_rvol7"]).set_index(["symbol", "date"])
    cache = {}
    rows = []
    for _, r in s.iterrows():
        rec = {"symbol": r["symbol"], "date": r["date"], "case": r["case"]}
        for L in LAGS:
            d = r["date"] - pd.Timedelta(days=L)
            oi, oiv = oi_at(r["symbol"], d.strftime("%Y-%m-%d"), cache)
            rec[f"oi{L}"], rec[f"oiv{L}"] = oi, oiv
            rec[f"c{L}"] = p["close"].get((r["symbol"], d), np.nan)
        rec["med30qv"] = p["med30qv"].get((r["symbol"], r["date"]), np.nan)
        rows.append(rec)
    x = pd.DataFrame(rows)
    # contracts OI (coins) is price-free: OI build-up in units vs price change
    x["oi_chg7"] = np.log(x["oi0"] / x["oi7"])
    x["oi_chg3"] = np.log(x["oi0"] / x["oi3"])
    x["px_chg7"] = np.log(x["c0"] / x["c7"])
    x["px_chg3"] = np.log(x["c0"] / x["c3"])
    x["oi_minus_px7"] = x["oi_chg7"] - x["px_chg7"]
    x["oiv_to_vol"] = x["oiv0"] / x["med30qv"]
    x.to_csv(os.path.join(RES, "pump_anatomy_oi_sample.csv"), index=False)
    out = []
    wk = x["date"].dt.tz_localize(None).dt.to_period("W").astype(str).to_numpy()
    for per, m in (("IS(2024)", x["date"] < IS_END), ("OOS", x["date"] >= IS_END), ("all", x["date"].notna())):
        for f in ("oi_chg7", "oi_chg3", "px_chg7", "oi_minus_px7", "oiv_to_vol"):
            a = x.loc[m & (x["case"] == 1), f].replace([np.inf, -np.inf], np.nan)
            b = x.loc[m & (x["case"] == 0), f].replace([np.inf, -np.inf], np.nan)
            # rank of each case value within the control distribution (0.5 = no difference)
            bb = np.sort(b.dropna().to_numpy())
            pr = np.searchsorted(bb, a.dropna().to_numpy()) / max(len(bb), 1)
            se = week_block_boot(pr, wk[(m & (x["case"] == 1)).to_numpy()][a.notna().to_numpy()], n=1000)
            out.append({"period": per, "feature": f, "n_case": int(a.notna().sum()), "n_ctrl": int(b.notna().sum()),
                        "case_median": round(float(a.median()), 4), "ctrl_median": round(float(b.median()), 4),
                        "case_pct_in_ctrl": round(float(pr.mean()), 3), "se": round(se, 3),
                        "z": round((pr.mean() - 0.5) / se, 2) if se else None})
    out = pd.DataFrame(out)
    # precision estimate for 'OI up >= ctrl p80 & price flat' via Bayes with the panel base rate
    base = float(load_panel(["elig", "y7", "date"]).query("elig and date >= @START")["y7"].mean())
    q80 = x.loc[x["case"] == 0, "oi_minus_px7"].quantile(0.8)
    rule_case = (x.loc[x["case"] == 1, "oi_minus_px7"] >= q80).mean()
    rule_ctrl = (x.loc[x["case"] == 0, "oi_minus_px7"] >= q80).mean()
    prec = rule_case * base / (rule_case * base + rule_ctrl * (1 - base))
    out.to_csv(os.path.join(RES, "pump_anatomy_oi.csv"), index=False)
    print(out.to_string())
    print({"base_rate": base, "rule": "oi_minus_px7 >= ctrl p80", "recall": rule_case, "fpr": rule_ctrl,
           "precision_bayes": prec, "lift": prec / base})
    pd.DataFrame([{"base_rate": base, "rule": "oi_minus_px7 >= ctrl p80", "recall": rule_case, "fpr": rule_ctrl,
                   "precision_bayes": prec, "lift": prec / base}]).to_csv(os.path.join(RES, "pump_anatomy_oi_rule.csv"), index=False)


if __name__ == "__main__":
    {"pairs": make_pairs, "analyse": analyse}[sys.argv[1]]()
