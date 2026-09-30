"""Adversarial verification of family trend_momentum (step 1: re-run every grid config).

Re-runs all 60 grid configs of the 12 variants (same functions, same grids as the
trend_momentum_*.json files) with the unmodified bt.engine at base and harsh costs and
stores every trade, so that any IS/OOS split can be re-evaluated offline.

    cd /home/user/research/trading && python3 -m results.verify_trend_momentum_run
Output: $VTM_CACHE/trades_all.parquet (default: /tmp scratch dir, see CACHE below).
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import strategies.trend_momentum as TM  # noqa: E402  (also patches bt.data._asof)
from bt.data import SYMBOLS, load  # noqa: E402
from bt.engine import simulate  # noqa: E402
from bt.runner import COST_SCENARIOS  # noqa: E402

RES = os.path.dirname(os.path.abspath(__file__))
CACHE = os.environ.get("VTM_CACHE", "/tmp/claude-0/-home-user-research/ea6ba1ab-fe99-5191-91e4-bb9455e40592/scratchpad/vtm")

VARIANTS = {}
for f in sorted(os.listdir(RES)):
    if f.startswith("trend_momentum_") and f[15:16] in "abcde" and f[16:17] == "_" and f.endswith(".json"):
        r = json.load(open(os.path.join(RES, f)))
        VARIANTS[f[15:-5]] = {"fn": r["fn"], "tf": r["tf"], "load": r["load"],
                              "grid": [c["params"] for c in r["configs"]],
                              "selected": r["selected_params"]}


def job(args):
    var, sym = args
    v = VARIANTS[var]
    df = load(sym, v["tf"], **v["load"])
    fn = getattr(TM, v["fn"])
    out = []
    for p in v["grid"]:
        sig = fn(df, **p)
        for cn in ("base", "harsh"):
            tr = simulate(df, sig, COST_SCENARIOS[cn], None, None, sym)
            if len(tr):
                tr["variant"], tr["params"], tr["costs"] = var, json.dumps(p, sort_keys=True), cn
                out.append(tr)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def main():
    os.makedirs(CACHE, exist_ok=True)
    jobs = [(v, s) for v in VARIANTS for s in SYMBOLS]
    with ProcessPoolExecutor(2) as ex:
        parts = list(ex.map(job, jobs))
    tr = pd.concat([p for p in parts if len(p)], ignore_index=True)
    tr.to_parquet(os.path.join(CACHE, "trades_all.parquet"))
    json.dump(VARIANTS, open(os.path.join(CACHE, "variants.json"), "w"), indent=1)
    print(len(tr), "trades;", tr.groupby(["variant", "costs"]).size().to_string())


if __name__ == "__main__":
    main()
