"""Follow-up to verify_ml_combo.py: why is the random-timing null so negative (-0.13R), and does the model's
advantage over random timing survive a finer volatility (cost-in-R) match?

    cd /home/user/research/trading && python3 results/verify_ml_combo_extra.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import verify_ml_combo as V  # noqa: E402
from bt.engine import Costs  # noqa: E402
from bt.runner import COST_SCENARIOS  # noqa: E402

M = V.M
IS1, END = V.IS1, pd.Timestamp("2026-09-01", tz="UTC")
T0 = pd.Timestamp("2023-07-01", tz="UTC")


def main():
    tf, K, H = "1h", 2.0, 24
    raw = V.raw_all(tf)
    E = V.edges_for(tf, 1, "raw", "large", "")
    tr = V.sim_all(tf, E, 0.62377, "base")
    tabs_net = {s: V.bracket_net_R(df, K, H, COST_SCENARIOS["base"]) for s, df in raw.items()}
    tabs_gross = {s: V.bracket_net_R(df, K, H, Costs(0.0, 0.0, 0.0)) for s, df in raw.items()}
    out = {}
    # ---- decomposition of random-entry R: gross vs costs, by stop% decile
    rows = []
    for s in raw:
        a = tabs_net[s].join(tabs_gross[s][["RL", "RS"]], rsuffix="_g")
        a["symbol"] = s
        rows.append(a[(a.index >= T0) & (a.index < END)])
    A = pd.concat(rows)
    A["oos"] = A.index >= IS1
    A["dec"] = pd.qcut(A["stop_pct"].rank(method="first"), 10, labels=False)
    dec = A.groupby(["oos", "dec"]).agg(stop_pct=("stop_pct", "median"), RL_net=("RL", "mean"), RS_net=("RS", "mean"),
                                        RL_gross=("RL_g", "mean"), RS_gross=("RS_g", "mean")).round(4)
    out["random_entry_R_by_stop_decile"] = {f"{'OOS' if k[0] else 'IS'}_d{k[1]}": v for k, v in
                                            dec.to_dict(orient="index").items()}
    for nm, part in (("IS", A[~A["oos"]]), ("OOS", A[A["oos"]])):
        out[f"random_entry_{nm}"] = {"RL_net": round(float(part["RL"].mean()), 4),
                                     "RS_net": round(float(part["RS"].mean()), 4),
                                     "RL_gross": round(float(part["RL_g"].mean()), 4),
                                     "RS_gross": round(float(part["RS_g"].mean()), 4),
                                     "median_stop_pct": round(float(part["stop_pct"].median() * 100), 3)}
    # ---- real trades: gross vs net, stop% percentile vs same symbol-month
    for nm, lo, hi in (("IS", T0, IS1), ("OOS", IS1, END)):
        p = tr[(tr["t_entry"] >= lo) & (tr["t_entry"] < hi)].copy()
        g = np.array([tabs_gross[s].at[t, "RL" if d > 0 else "RS"] for s, t, d in
                      zip(p["symbol"], p["t_signal"], p["dir"])])
        # percentile of the trade's stop% within the same symbol-month
        prc = []
        for s, grp in p.groupby("symbol"):
            tb = tabs_net[s]
            mon = tb.index.tz_convert(None).to_period("M")
            rk = tb.groupby(mon)["stop_pct"].rank(pct=True)
            prc += list(rk.reindex(grp["t_signal"]).to_numpy())
        out[f"real_trades_{nm}"] = {"n": int(len(p)), "net_avg_R": round(float(p["R"].mean()), 4),
                                    "gross_avg_R": round(float(np.nanmean(g)), 4),
                                    "median_stop_pct": round(float(p["risk_pct"].median()), 3),
                                    "median_stop_pct_rank_in_symbol_month": round(float(np.nanmedian(prc)), 3),
                                    "exit_reasons": p["reason"].value_counts(normalize=True).round(3).to_dict()}
    # ---- finer null: nearest-neighbour stop% match (same symbol, same month, same direction, 20 closest bars)
    rng = np.random.default_rng(5)
    for nm, lo, hi in (("IS", T0, IS1), ("OOS", IS1, END)):
        p = tr[(tr["t_entry"] >= lo) & (tr["t_entry"] < hi)]
        draws = []
        for s, t, d in zip(p["symbol"], p["t_signal"], p["dir"]):
            tb = tabs_net[s]
            mon = tb.index.tz_convert(None).to_period("M")
            pool = tb[mon == t.tz_convert(None).to_period("M")]
            col = "RL" if d > 0 else "RS"
            pool = pool[pool[col].notna() & (pool.index != t)]
            idx = np.argsort(np.abs(pool["stop_pct"].to_numpy() - tb.at[t, "stop_pct"]))[:20]
            vals = pool[col].to_numpy()[idx]
            draws.append(vals[rng.integers(0, len(vals), 2000)])
        null = np.vstack(draws).mean(axis=0)
        real = float(p["R"].mean())
        out[f"null_nn20_stop_matched_{nm}"] = {"real": round(real, 4), "null_mean": round(float(null.mean()), 4),
                                               "null_sd": round(float(null.std()), 4),
                                               "p_value": float((1 + (null >= real).sum()) / 2001)}
    # ---- block bootstrap (weekly blocks) of the claimed OOS trades: P(avg_R <= 0)
    p = tr[tr["t_entry"] >= IS1].copy()
    wk = pd.DatetimeIndex(p["t_entry"]).tz_convert(None).to_period("W")
    groups = [g["R"].to_numpy() for _, g in p.groupby(wk)]
    bs = []
    for _ in range(5000):
        pick = rng.integers(0, len(groups), len(groups))
        arr = np.concatenate([groups[i] for i in pick])
        bs.append(arr.mean())
    bs = np.array(bs)
    out["oos_weekly_block_bootstrap"] = {"n_weeks": len(groups), "mean": round(float(bs.mean()), 4),
                                         "ci95": [round(float(np.quantile(bs, 0.025)), 4),
                                                  round(float(np.quantile(bs, 0.975)), 4)],
                                         "p_avgR_le_0": round(float((bs <= 0).mean()), 4)}
    with open(os.path.join(V.RES, "verify_ml_combo_extra.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
