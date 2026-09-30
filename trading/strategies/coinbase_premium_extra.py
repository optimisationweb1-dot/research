"""Supplementary (post-hoc, descriptive) numbers for the report: per-trade % returns and exposure of the
selected A/B configs, A+B two-sleeve combination, pooled BTC+ETH Donchian split by premium sign.

    OMP_NUM_THREADS=2 python3 -m strategies.coinbase_premium_extra
"""
import json
import math
import os

import numpy as np
import pandas as pd

from bt.engine import IS_END, split_summary
from strategies import coinbase_premium as S
from strategies.coinbase_premium_backtest import RES, SYM, frames, run_one

RNG = np.random.default_rng(11)


def pct_stats(tr, df):
    out = {}
    for per, m in [("IS", tr.t_entry < IS_END), ("OOS", tr.t_entry >= IS_END)]:
        t = tr[m]
        span = df.index[(df.index < IS_END)] if per == "IS" else df.index[df.index >= IS_END]
        r = t.ret_pct.to_numpy()
        out[per] = {"n": len(t), "mean_ret_pct": round(r.mean(), 3) if len(r) else None,
                    "t": round(r.mean() / r.std(ddof=1) * math.sqrt(len(r)), 2) if len(r) > 2 else None,
                    "sum_ret_pct": round(r.sum(), 1), "exposure_share": round(t.bars.sum() / len(span), 3)}
    return out


def main():
    bt = json.load(open(os.path.join(RES, "coinbase_premium_backtest.json")))
    fr = frames()
    out = {"pct": {}, "AB": {}, "C_pooled_split": {}}
    for a in SYM:
        df = fr[a]["1h"]
        pa = bt["families"]["A_long_L"]["assets"][a]["selected"]
        pb = bt["families"]["B_short_L"]["assets"][a]["selected"]
        ta = run_one(S.premium_long, df, {"asset": a, **pa}, pa["hold"], "harsh", SYM[a])
        tb = run_one(S.premium_short, df, {"asset": a, **pb}, pb["hold"], "harsh", SYM[a])
        # buy & hold of the perp over each period (no funding) for scale
        bh = {}
        for per, m in [("IS", df.index < IS_END), ("OOS", df.index >= IS_END)]:
            c = df.loc[m, "close"]
            bh[per] = round(100 * (c.iloc[-1] / c.iloc[0] - 1), 1)
        out["pct"][a] = {"A": pct_stats(ta, df), "B": pct_stats(tb, df), "buy_hold_pct": bh}
        ab = pd.concat([ta, tb], ignore_index=True)
        out["AB"][a] = split_summary(ab, 0.5, f"A+B {a} harsh")
        print(a, json.dumps(out["pct"][a]), flush=True)
        print(a, "A+B", json.dumps(out["AB"][a]), flush=True)
    # pooled Donchian split (base trades), premium sign at the signal bar
    rows = []
    for a in SYM:
        df = fr[a]["4h"]
        tr = run_one(S.donchian_filter, df, {"asset": a, "filt": "none"}, None, "base", SYM[a])
        tr["pos"] = df["cbp_P24"].reindex(tr["t_signal"]).to_numpy() > 0
        rows.append(tr)
    tr = pd.concat(rows, ignore_index=True)
    for per, m in [("IS", tr.t_entry < IS_END), ("OOS", tr.t_entry >= IS_END), ("ALL", tr.t_entry == tr.t_entry)]:
        t = tr[m]
        g1, g0 = t[t.pos].R, t[~t.pos].R
        diff = g1.mean() - g0.mean()
        se = math.sqrt(g1.var(ddof=1) / len(g1) + g0.var(ddof=1) / len(g0))
        # permutation of labels (trade-level; ignores time clustering)
        R, pos = t.R.to_numpy(), t.pos.to_numpy()
        perm = [R[p].mean() - R[~p].mean() for p in (RNG.permutation(pos) for _ in range(5000))]
        out["C_pooled_split"][per] = {"n_pos": int(len(g1)), "n_neg": int(len(g0)), "avgR_pos": round(g1.mean(), 3),
                                      "avgR_neg": round(g0.mean(), 3), "diff": round(diff, 3),
                                      "t_welch": round(diff / se, 2), "perm_p_one_sided": float(np.mean(np.array(perm) >= diff))}
    print(json.dumps(out["C_pooled_split"], indent=1))
    with open(os.path.join(RES, "coinbase_premium_extra.json"), "w") as fh:
        json.dump(out, fh, indent=1, default=str)


if __name__ == "__main__":
    main()
