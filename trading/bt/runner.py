"""Grid runner with honest selection: choose parameters on in-sample only
(entries before 2025-01-01), then report the untouched out-of-sample result.

    python3 -m bt.runner strategies.smc --tf 5m --grid '{"piv": [3, 5, 8]}'
    python3 -m bt.runner strategies.smc --tf 15m --symbols BTCUSDT ETHUSDT --grid '{}' --out results/smc_15m.json

Outputs JSON: every config with IS/OOS summaries, the IS-selected config and its OOS,
and the OOS distribution across all configs (robustness: a real edge should not
depend on one lucky parameter set).
"""
import argparse
import importlib
import itertools
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from .data import SYMBOLS, load
from .engine import Costs, IS_END, check_lookahead, simulate, split_summary, summarize

COST_SCENARIOS = {
    "base": Costs(),                                   # taker 0.05%, maker 0.02%, slip 2bps
    "harsh": Costs(taker=0.0006, maker=0.0004, slippage=0.0005),
}


def _one(args):
    modname, fn, sym, tf, params, load_kw, cost_name = args
    mod = importlib.import_module(modname)
    strat = getattr(mod, fn)
    df = load(sym, tf, **load_kw)
    sig = strat(df, **params)
    return simulate(df, sig, COST_SCENARIOS[cost_name], getattr(strat, "MAX_HOLD", None),
                    getattr(strat, "LIMIT_TTL", None), sym)


def run_config(modname, fn, symbols, tf, params, load_kw, cost_name="base", workers=4):
    jobs = [(modname, fn, s, tf, params, load_kw, cost_name) for s in symbols]
    with ProcessPoolExecutor(workers) as ex:
        parts = list(ex.map(_one, jobs))
    parts = [p for p in parts if len(p)]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def grid_iter(grid):
    keys = list(grid)
    for vals in itertools.product(*(grid[k] for k in keys)):
        yield dict(zip(keys, vals))


def score(s):
    """IS selection score: t-stat of R, requires enough trades."""
    if not s or s.get("n", 0) < 30 or s.get("t_stat") is None:
        return -1e9
    return s["t_stat"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("module")
    ap.add_argument("--fn", default="strategy")
    ap.add_argument("--tf", default="5m")
    ap.add_argument("--symbols", nargs="+", default=SYMBOLS)
    ap.add_argument("--grid", default="{}")
    ap.add_argument("--load", default="{}", help='e.g. {"metrics": true, "funding": true, "dvol": true}')
    ap.add_argument("--out", default=None)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--risk", type=float, default=0.5)
    a = ap.parse_args()

    grid, load_kw = json.loads(a.grid), json.loads(a.load)
    mod = importlib.import_module(a.module)
    strat = getattr(mod, a.fn)
    # lookahead guard on the first symbol with the first config
    first = next(grid_iter(grid))
    df0 = load(a.symbols[0], a.tf, **load_kw)
    check_lookahead(strat, df0, first)
    print(f"lookahead check passed: {a.module}.{a.fn} {a.tf} {first}", flush=True)

    rows = []
    for params in grid_iter(grid):
        tr = run_config(a.module, a.fn, a.symbols, a.tf, params, load_kw, "base", a.workers)
        ss = split_summary(tr, a.risk, json.dumps(params))
        rows.append({"params": params, **ss})
        print(json.dumps(params), "IS", ss["IS"].get("n"), ss["IS"].get("avg_R"), ss["IS"].get("t_stat"),
              "| OOS", ss["OOS"].get("n"), ss["OOS"].get("avg_R"), ss["OOS"].get("t_stat"), flush=True)

    best = max(rows, key=lambda r: score(r["IS"]))
    tr_best = run_config(a.module, a.fn, a.symbols, a.tf, best["params"], load_kw, "base", a.workers)
    tr_harsh = run_config(a.module, a.fn, a.symbols, a.tf, best["params"], load_kw, "harsh", a.workers)
    oos = tr_best[tr_best["t_entry"] >= IS_END] if len(tr_best) else tr_best
    per_symbol = {s: summarize(g, a.risk, s) for s, g in oos.groupby("symbol")} if len(oos) else {}
    per_year = {str(y): summarize(g, a.risk, str(y)) for y, g in tr_best.groupby(tr_best["t_entry"].dt.year)} \
        if len(tr_best) else {}
    oos_avg = [r["OOS"].get("avg_R") for r in rows if r["OOS"].get("n", 0) >= 10]
    result = {
        "module": a.module, "fn": a.fn, "tf": a.tf, "symbols": a.symbols, "load": load_kw,
        "n_configs": len(rows), "selection": "max IS t-stat with IS n>=30",
        "selected_params": best["params"], "selected_IS": best["IS"], "selected_OOS": best["OOS"],
        "selected_OOS_harsh_costs": split_summary(tr_harsh, a.risk)["OOS"],
        "selected_OOS_per_symbol": per_symbol, "selected_per_year": per_year,
        "all_configs_OOS_avgR": {"median": float(np.median(oos_avg)) if oos_avg else None,
                                 "share_positive": float(np.mean([x > 0 for x in oos_avg])) if oos_avg else None,
                                 "n": len(oos_avg)},
        "configs": rows,
    }
    print("\nSELECTED", json.dumps(best["params"]))
    print("IS ", json.dumps(best["IS"]))
    print("OOS", json.dumps(best["OOS"]))
    print("OOS harsh", json.dumps(result["selected_OOS_harsh_costs"]))
    print("all-config OOS avgR", json.dumps(result["all_configs_OOS_avgR"]))
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        with open(a.out, "w") as f:
            json.dump(result, f, indent=1, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
