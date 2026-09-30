"""pump_anatomy: robustness of scanner portfolios (decomposition, outliers, liquidity L2, by half-year).

    python3 -m strategies.pump_anatomy_robust
"""
import json
import os
import warnings

import numpy as np
import pandas as pd

from strategies.pump_anatomy_analysis import (COSTS, IS_END, OOS_END, RES, ROOT, add_vol, ew_market, load_panel,
                                              portfolio, split_perf, nw_t)

warnings.filterwarnings("ignore")


def ls(p, score, hold, cost, elig="elig", clip=None):
    q = p
    if clip is not None:
        q = p.assign(r_next=p["r_next"].clip(-clip, clip))
    L = portfolio(q, score, hold=hold, side="long", cost=cost, elig=elig)
    S = portfolio(q, score, hold=hold, side="short", cost=cost, elig=elig)
    idx = L.index.union(S.index)
    out = pd.DataFrame({c: (L[c].reindex(idx).fillna(0) + S[c].reindex(idx).fillna(0)) / 2
                        for c in ("gross", "fund", "cost", "net")})
    return out, L, S


def main():
    p = add_vol(load_panel())
    sc = pd.read_parquet(os.path.join(ROOT, "scores.parquet"))
    p = p.merge(sc, on=["date", "symbol"], how="left")
    res = {}
    rows = []
    for score in ("score_A", "score_C", "pr_vol30"):
        for hold in (7,):
            for tag, kw in (("L1", {}), ("L2_min10M", {"elig": "elig2"}), ("L1_clip50%", {"clip": 0.5}),
                            ("L1_extreme_cost", {"cost_name": "extreme"})):
                cost = COSTS[kw.pop("cost_name", "harsh")]
                x, L, S = ls(p, score, hold, cost, **kw)
                for per, m in (("IS", x.index < IS_END), ("OOS", (x.index >= IS_END) & (x.index < OOS_END))):
                    xx = x[m]
                    rows.append({"score": score, "hold": hold, "variant": tag, "period": per,
                                 "gross_pct_day": round(100 * xx["gross"].mean(), 4),
                                 "funding_pct_day": round(100 * xx["fund"].mean(), 4),
                                 "cost_pct_day": round(100 * xx["cost"].mean(), 4),
                                 "net_pct_day": round(100 * xx["net"].mean(), 4),
                                 "net_ex_funding_t": round(nw_t((xx["gross"] + xx["cost"]).to_numpy(), hold + 2), 2),
                                 "net_t_nw": round(nw_t(xx["net"].to_numpy(), hold + 2), 2),
                                 "sharpe": round(xx["net"].mean() / xx["net"].std() * np.sqrt(365), 2)})
            # half-year breakdown of the base variant
            x, L, S = ls(p, score, 7, COSTS["harsh"])
            hy = x["net"].groupby([x.index.year, (x.index.month > 6).astype(int) + 1]).agg(["mean", "count"])
            res[f"{score}_halfyear_net_pct_day"] = {f"{a}H{b}": round(100 * v, 4) for (a, b), v in hy["mean"].items()}
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(RES, "pump_anatomy_robust.csv"), index=False)
    # beta of L/S (score_C, 7d) to EW market and to BTC, OOS
    mkt = ew_market(p)
    x, L, S = ls(p, "score_C", 7, COSTS["harsh"])
    o = x.index >= IS_END
    b = np.polyfit(mkt.reindex(x.index[o]).fillna(0), x.loc[o, "net"], 1)
    res["scoreC_LS7_OOS_beta_to_EWmkt"] = round(float(b[0]), 3)
    res["scoreC_LS7_OOS_alpha_pct_day"] = round(100 * float(b[1]), 4)
    res["EW_market"] = split_perf(mkt)
    # symbol concentration: contribution of top-5 symbols to OOS long gross
    q = p.assign(r=p["r_next"])
    json.dump(res, open(os.path.join(RES, "pump_anatomy_robust.json"), "w"), indent=1)
    with pd.option_context("display.width", 250):
        print(t.to_string())
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()


def concentration(score="score_C", hold=7):
    """Top symbol-day contributions to the OOS long-short gross P&L (weights x returns)."""
    p = load_panel(["date", "symbol", "elig", "r_next", "px_exec", "fund_next"])
    sc = pd.read_parquet(os.path.join(ROOT, "scores.parquet"))
    p = p.merge(sc, on=["date", "symbol"], how="left")
    q = p.loc[p["elig"] & p[score].notna() & p["px_exec"].notna(), ["date", "symbol", score]]
    rk = q.groupby("date")[score].rank(pct=True, method="first")
    q = q.assign(w=np.where(rk > 0.9, 1.0, np.where(rk <= 0.1, -1.0, 0.0)))
    q = q[q["w"] != 0]
    w = q.pivot_table(index="date", columns="symbol", values="w", aggfunc="first")
    w = w.div(w.abs().sum(1), axis=0)  # each leg 0.5 gross
    dates = pd.date_range(p["date"].min(), p["date"].max(), freq="1D", tz="UTC")
    w = (w.reindex(dates).fillna(0).rolling(hold, min_periods=1).sum() / hold)
    r = p.pivot_table(index="date", columns="symbol", values="r_next", aggfunc="first").reindex(dates)[w.columns]
    c = (w * r.fillna(0)).stack()
    c = c[c.index.get_level_values(0) >= IS_END]
    tot = c.sum()
    s = c.sort_values(ascending=False)
    by_sym = c.groupby(level=1).sum().sort_values(ascending=False)
    out = {"OOS_total_gross_sum": round(float(tot), 4), "top10_symbol_days_sum": round(float(s.head(10).sum()), 4),
           "top50_symbol_days_sum": round(float(s.head(50).sum()), 4),
           "bottom10_symbol_days_sum": round(float(s.tail(10).sum()), 4),
           "top10_symbols": {k: round(float(v), 4) for k, v in by_sym.head(10).items()},
           "worst10_symbols": {k: round(float(v), 4) for k, v in by_sym.tail(10).items()},
           "top10_symbol_days": [(str(a.date()), b, round(float(v), 4)) for (a, b), v in s.head(10).items()]}
    json.dump(out, open(os.path.join(RES, f"pump_anatomy_concentration_{score}.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


def symmetry():
    """POST-HOC: are 'pump detectors' just volatility detectors? P(max7>=+40%) vs P(min7<=-30%) by signal."""
    from strategies.pump_anatomy_analysis import RULES
    p = add_vol(load_panel())
    sc = pd.read_parquet(os.path.join(ROOT, "scores.parquet"))
    p = p.merge(sc, on=["date", "symbol"], how="left").sort_values(["symbol", "date"])
    fut = pd.concat([p.groupby("symbol")["close"].shift(-k) for k in range(1, 8)], axis=1)
    p["fwd_min7"] = fut.min(axis=1) / p["close"] - 1
    q = p[p["elig"] & p["y7"].notna() & p["fwd_min7"].notna()].copy()
    for s in ("score_A", "score_C"):
        q[f"top_{s}"] = q.groupby("date")[s].rank(pct=True) > 0.9
    sigs = {r: RULES[r](q).fillna(False).astype(bool) for r in
            ("rvol7>=p90", "rs7>=p90", "age<90", "ret1>=+15%", "rvol1>=p90&tshare1>=p80", "POSTHOC_vol30>=p90")}
    sigs["score_A_top10%"] = q["top_score_A"]
    sigs["score_C_top10%"] = q["top_score_C"]
    sigs["ALL"] = pd.Series(True, index=q.index)
    rows = []
    for per, m in (("IS", q["date"] < IS_END), ("OOS", q["date"] >= IS_END)):
        for k, s in sigs.items():
            x = q[m & s]
            rows.append({"period": per, "signal": k, "n": len(x), "P_pump40": round(float(x["y7"].mean()), 4),
                         "P_dump30": round(float((x["fwd_min7"] <= -0.30).mean()), 4),
                         "mean_fwd7_exec": round(float(x["fwd_ret7_exec"].mean()), 4),
                         "median_fwd7_exec": round(float(x["fwd_ret7_exec"].median()), 4)})
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(RES, "pump_anatomy_symmetry.csv"), index=False)
    print(t.to_string())


def placebo_portfolio(n=100, score="score_A", hold=7):
    """Random cross-sectional scores (same eligible universe, same dates): null distribution of the OOS
    long-short net mean (harsh costs). Also a 'shuffled-within-date' version of the real score is identical
    in distribution to random ranks, so one null suffices."""
    rng = np.random.default_rng(42)
    p = load_panel(["date", "symbol", "elig", "r_next", "px_exec", "fund_next"])
    sc = pd.read_parquet(os.path.join(ROOT, "scores.parquet"))
    p = p.merge(sc[["date", "symbol", score]], on=["date", "symbol"], how="left")
    obs_x, _, _ = ls(p, score, hold, COSTS["harsh"])
    obs = float(obs_x.loc[obs_x.index >= IS_END, "net"].mean())
    null = []
    for i in range(n):
        p["rnd"] = np.where(p[score].notna(), rng.random(len(p)), np.nan)
        x, _, _ = ls(p, "rnd", hold, COSTS["harsh"])
        null.append(float(x.loc[x.index >= IS_END, "net"].mean()))
    null = np.array(null)
    out = {"score": score, "hold": hold, "obs_OOS_net_pct_day": round(100 * obs, 4),
           "null_mean_pct_day": round(100 * null.mean(), 4), "null_sd_pct_day": round(100 * null.std(), 4),
           "p_value": float((np.sum(null >= obs) + 1) / (n + 1)), "n_perm": n}
    json.dump(out, open(os.path.join(RES, f"pump_anatomy_placebo_portfolio_{score}.json"), "w"), indent=1)
    print(out)
