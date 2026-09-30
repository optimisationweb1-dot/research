"""Extra checks for c_tsmom_1d {K:72, z0:0.5}: open-at-end trades, truncated data end, clustered t.
    cd /home/user/research/trading && python3 -m results.verify_trend_momentum_extra
"""
import json, math, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import strategies.trend_momentum as TM  # noqa
from bt.data import SYMBOLS, load
from bt.engine import simulate
from bt.runner import COST_SCENARIOS

def t(R):
    R = np.asarray(R, float); return round(float(R.mean() / R.std(ddof=1) * math.sqrt(len(R))), 2)

def cl_t(tr, f):
    k = tr.t_entry.dt.tz_localize(None).dt.to_period(f)
    e = (tr.R - tr.R.mean()).groupby(k).sum().to_numpy()
    se = math.sqrt((e ** 2).sum() * len(e) / (len(e) - 1)) / len(tr)
    return round(float(tr.R.mean() / se), 2)

def run(end=None, cost="base"):
    parts = []
    for s in SYMBOLS:
        df = load(s, "1d", end=end)
        parts.append(simulate(df, TM.tsmom(df, K=72, z0=0.5), COST_SCENARIOS[cost], None, None, s))
    return pd.concat(parts, ignore_index=True)

out = {}
for lab, end in (("full_to_2026-08-31", None), ("data_end_2026-07-31", "2026-08-01"), ("data_end_2026-06-30", "2026-07-01")):
    tr = run(end); O = tr[tr.t_entry >= "2025-01-01"]
    closed = O[O.reason != "end"]
    out[lab] = {"OOS_n": len(O), "avg_R": round(float(O.R.mean()), 3), "t": t(O.R),
                "t_week_cluster": cl_t(O, "W"), "t_month_cluster": cl_t(O, "M"),
                "n_open_at_end": int((O.reason == "end").sum()), "sumR_open_at_end": round(float(O[O.reason == "end"].R.sum()), 1),
                "closed_only_avg_R": round(float(closed.R.mean()), 3), "closed_only_t": t(closed.R),
                "sym_pos": int((O.groupby("symbol").R.mean() > 0).sum())}
    print(lab, out[lab], flush=True)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_trend_momentum_extra.json"), "w"), indent=1)
