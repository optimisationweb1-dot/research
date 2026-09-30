"""H4 backtest through bt.engine: daily bars, base and harsh costs, IS (<2025) / OOS (2025-01..2026-08).
Grid (pre-registered): hold N in {7,14,30} x pct in {0.7,0.8,0.9}; controls: momentum, always-long."""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TR = os.path.dirname(HERE)
sys.path.insert(0, TR)
sys.path.insert(0, HERE)
from bt.data import load  # noqa: E402
from bt.engine import check_lookahead, simulate, split_summary  # noqa: E402
from bt.runner import COST_SCENARIOS  # noqa: E402
import treasury_flows as S  # noqa: E402

SYM = {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}


def run_one(asset, fn, params, hold, cost):
    df = load(SYM[asset], "1d")
    sig = fn(df, **params)
    return simulate(df, sig, COST_SCENARIOS[cost], max_hold=hold, symbol=SYM[asset])


def extra(tr):
    """Per-trade % return stats (R depends on stop width)."""
    if tr is None or len(tr) == 0:
        return {}
    out = {}
    for lab, m in (("IS", tr.t_entry < pd.Timestamp("2025-01-01", tz="UTC")),
                   ("OOS", tr.t_entry >= pd.Timestamp("2025-01-01", tz="UTC"))):
        x = tr.loc[m, "ret_pct"]
        out[lab] = {"n": int(len(x)), "avg_ret_pct": round(float(x.mean()), 3) if len(x) else None,
                    "t_ret": round(float(x.mean() / x.std(ddof=1) * np.sqrt(len(x))), 2) if len(x) > 2 else None,
                    "sum_ret_pct": round(float(x.sum()), 1) if len(x) else None,
                    "days_in_market": int(tr.loc[m, "bars"].sum())}
    return out


def main():
    res = {}
    for asset in ("BTC", "ETH"):
        df = load(SYM[asset], "1d")
        check_lookahead(S.flow_long, df, {"asset": asset}, n_checks=30)
        check_lookahead(S.mom_long, df, {}, n_checks=10)
        for cost in ("base", "harsh"):
            for hold in (7, 14, 30):
                for pct in (0.7, 0.8, 0.9):
                    key = f"{asset}|flow_all|N{hold}|p{int(pct * 100)}|{cost}"
                    tr = run_one(asset, S.flow_long, {"asset": asset, "pct": pct}, hold, cost)
                    res[key] = {"summary": split_summary(tr, label=key), "ret": extra(tr)}
                for src in ("etf", "treasury"):
                    key = f"{asset}|flow_{src}|N{hold}|p80|{cost}"
                    tr = run_one(asset, S.flow_long, {"asset": asset, "pct": 0.8, "source": src}, hold, cost)
                    res[key] = {"summary": split_summary(tr, label=key), "ret": extra(tr)}
                key = f"{asset}|ctl_mom14|N{hold}|{cost}"
                tr = run_one(asset, S.mom_long, {}, hold, cost)
                res[key] = {"summary": split_summary(tr, label=key), "ret": extra(tr)}
                start = "2024-03-15" if asset == "BTC" else "2024-09-25"
                key = f"{asset}|ctl_always|N{hold}|{cost}"
                tr = run_one(asset, S.always_long, {"start": start}, hold, cost)
                res[key] = {"summary": split_summary(tr, label=key), "ret": extra(tr)}
    with open(os.path.join(TR, "results", "treasury_flows_backtest.json"), "w") as f:
        json.dump(res, f, indent=1, default=str)
    rows = []
    for k, v in res.items():
        a, strat, *rest = k.split("|")
        for per in ("IS", "OOS"):
            s = v["summary"][per]
            r = v["ret"].get(per, {})
            rows.append({"key": k, "per": per, "n": s.get("n", 0), "avg_R": s.get("avg_R"), "t": s.get("t_stat"),
                         "win%": s.get("win_pct"), "avg_ret%": r.get("avg_ret_pct"), "t_ret": r.get("t_ret"),
                         "sum_ret%": r.get("sum_ret_pct"), "days": r.get("days_in_market")})
    t = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    print(t.to_string(index=False))
    t.to_csv(os.path.join(TR, "results", "treasury_flows_backtest_table.csv"), index=False)


if __name__ == "__main__":
    main()
