"""Re-run the claimed pre-registered holdouts for C_level 4h (fixed config, no selection) + null test B on them.
    cd trading && python3 -m results.verify_funding_positioning_holdout
Holdout data were downloaded by the original agent into the session scratchpad (not trading/data).
"""
import json, os
import numpy as np, pandas as pd
import strategies.funding_positioning as F
import bt.data as D
from bt.engine import simulate, Costs
from results.verify_funding_positioning import blk, IS_END, ALT_END, BASE, HARSH, outcomes

SP = "/tmp/claude-0/-home-user-research/ea6ba1ab-fe99-5191-91e4-bb9455e40592/scratchpad"
SETS = {"holdout1": (f"{SP}/fp_hdata", ["DOTUSDT", "NEARUSDT", "ATOMUSDT", "FILUSDT", "BCHUSDT", "ETCUSDT", "UNIUSDT", "APTUSDT", "ARBUSDT", "OPUSDT"]),
        "holdout2": (f"{SP}/fp_hdata2", ["TRXUSDT", "XLMUSDT", "HBARUSDT", "AAVEUSDT", "INJUSDT", "SUIUSDT", "LDOUSDT", "CRVUSDT", "ICPUSDT", "SEIUSDT"])}

def main(n_perm=1000, seed=5):
    rng = np.random.default_rng(seed)
    out = {}
    orig = D.ROOT
    for name, (root, syms) in SETS.items():
        D.ROOT = root
        trs, trh, recs, OUTC, VALID = [], [], [], {}, {}
        try:
            for s in syms:
                df = D.load(s, "4h", metrics=True, funding=True)
                sig = F.rcrowd_4h(df, src="level", pct=0.9)
                t = simulate(df, sig, BASE, 18, None, s); trs.append(t)
                trh.append(simulate(df, sig, HARSH, 18, None, s))
                Ro = outcomes(df); OUTC[s] = (Ro, df.index)
                p = F.roll_pct(F.logpos(df["ls_accounts"]), F.bars(df, 24 * 30)).to_numpy()
                VALID[s] = np.isfinite(p) & np.isfinite(Ro).all(axis=1)
        finally:
            D.ROOT = orig
        tb = pd.concat([t for t in trs if len(t)], ignore_index=True)
        th = pd.concat([t for t in trh if len(t)], ignore_index=True)
        r = {"2024": blk(tb, hi=IS_END), "2025-26": blk(tb, lo=IS_END), "2025-26_harsh": blk(th, lo=IS_END),
             "altOOS_2025H2-26": blk(tb, lo=ALT_END)}
        # null B on 2025-26: common monthly circular shift across symbols, on a common UTC 4h grid
        O = tb[tb["t_entry"] >= IS_END]
        real = O["R"].mean()
        mon = O["t_signal"].dt.tz_convert(None).dt.to_period("M")
        null = []
        for _ in range(n_perm):
            sh = {m: rng.integers(0, m.days_in_month * 6) for m in mon.unique()}
            vals = []
            for (s, ts, d, m) in zip(O["symbol"], O["t_signal"], O["dir"], mon):
                m0 = pd.Timestamp(m.start_time, tz="UTC")
                k = int((ts - m0) / pd.Timedelta(hours=4))
                q = m0 + pd.Timedelta(hours=4) * ((k + sh[m]) % (m.days_in_month * 6))
                Ro, idx = OUTC[s]
                j = idx.get_indexer([q])[0]
                if j >= 0 and VALID[s][j]:
                    vals.append(Ro[j, 0 if d > 0 else 1])
            null.append(np.mean(vals))
        null = np.array(null)
        r["null_B_2025-26"] = {"real": round(float(real), 4), "null_mean": round(float(null.mean()), 4),
                               "null_sd": round(float(null.std(ddof=1)), 4),
                               "p_value": round(float((1 + (null >= real).sum()) / (1 + len(null))), 4), "n_perm": n_perm}
        out[name] = r
        print(name, json.dumps({k: {kk: v.get(kk) for kk in ("n", "avg_R", "t_stat", "t_cl_week", "sym_pos")} if "null" not in k else v for k, v in r.items()}), flush=True)
    json.dump(out, open("results/verify_funding_positioning_holdout.json", "w"), indent=1, default=str)

if __name__ == "__main__":
    main()
