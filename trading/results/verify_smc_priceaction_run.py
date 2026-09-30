"""Verifier for smc_priceaction: re-run the grid (all setups, rr, filt, both stops) on 15m and 1h,
base + harsh costs, and cache every trade for the analysis step.

    cd trading && python3 -m results.verify_smc_priceaction_run
Output: <scratch>/verify_smc_trades.parquet (path from env VERIFY_OUT or default below)
"""
import itertools
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bt.data import SYMBOLS, load  # noqa: E402
from bt.engine import Costs, check_lookahead, simulate  # noqa: E402
import strategies.smc_priceaction as S  # noqa: E402

OUT = os.environ.get("VERIFY_OUT", "/tmp/claude-0/-home-user-research/ea6ba1ab-fe99-5191-91e4-bb9455e40592/scratchpad/verify_smc_trades.parquet")
COSTS = {"base": Costs(), "harsh": Costs(taker=0.0006, maker=0.0004, slippage=0.0005)}
GRID = [dict(setup=s, rr=r, filt=f, stop=st) for s, r, f, st in itertools.product(
    ("choch", "ob", "fvg"), (1.5, 2, 3), ("none", "kz", "htf", "kz_htf"), ("struct", "alt"))]
TFS = ("15m", "1h")


def _one(args):
    sym, tf = args
    df = load(sym, tf)
    out = []
    for p in GRID:
        sig = S.strategy(df, **p)
        for cn, c in COSTS.items():
            tr = simulate(df, sig, c, S.MAX_HOLD, S.LIMIT_TTL, sym)
            if len(tr):
                tr = tr.assign(tf=tf, cost=cn, **{k: str(v) for k, v in p.items()})
                out.append(tr)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def main():
    t0 = time.time()
    # extra lookahead checks on the configuration under review (+ its 15m origin), several symbols
    for sym, tf in (("BTCUSDT", "1h"), ("SOLUSDT", "1h"), ("ADAUSDT", "15m"), ("DOGEUSDT", "1h")):
        df = load(sym, tf)
        for p in (dict(setup="fvg", rr=3, filt="kz_htf", stop="alt"), dict(setup="ob", rr=3, filt="kz_htf", stop="alt"),
                  dict(setup="choch", rr=2, filt="none", stop="struct")):
            check_lookahead(S.strategy, df, p, n_checks=20)
    print("lookahead checks passed", round(time.time() - t0), "s", flush=True)
    jobs = [(s, tf) for tf in TFS for s in SYMBOLS]
    with ProcessPoolExecutor(2) as ex:
        parts = list(ex.map(_one, jobs))
    tr = pd.concat([p for p in parts if len(p)], ignore_index=True)
    tr.to_parquet(OUT, index=False)
    print("saved", OUT, len(tr), round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
