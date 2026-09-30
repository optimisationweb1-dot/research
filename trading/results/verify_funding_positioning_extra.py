"""Extra verifier checks for C_level 4h (rcrowd src=level pct=0.9), no selection:
  - per-year (2024/2025/2026) base+harsh, per-symbol on the alternative OOS (2025-07..2026-08)
  - null test exactly as specified by the task: 200 permutations of entry times within each
    symbol-month (same count, same direction per trade, identical exit logic) + a common-shift
    variant; evaluated on the original OOS (2025-01..) and on the alternative OOS (2025-07..).
    cd /home/user/research/trading && python3 -m results.verify_funding_positioning_extra
"""
import json

import numpy as np
import pandas as pd

import strategies.funding_positioning as F
from bt.engine import simulate
from results.verify_funding_positioning import ALT_END, BASE, HARSH, IS_END, SYMS, blk, load, outcomes, run

OUT = "results/verify_funding_positioning_extra.json"


def main(n_perm=200, seed=2026):
    p = {"src": "level", "pct": 0.9}
    tb, th = run(F.rcrowd_4h, p), run(F.rcrowd_4h, p, costs=HARSH)
    out = {}
    yrs = {}
    for y in (2024, 2025, 2026):
        a, b = pd.Timestamp(f"{y}-01-01", tz="UTC"), pd.Timestamp(f"{y + 1}-01-01", tz="UTC")
        bb, hh = blk(tb, a, b), blk(th, a, b)
        yrs[str(y)] = {k: bb.get(k) for k in ("n", "win_pct", "avg_R", "t_stat", "t_cl_week", "ret_pct@0.5%",
                                              "max_dd_pct", "sym_pos")}
        yrs[str(y)]["harsh_avg_R"] = hh.get("avg_R")
    out["per_year"] = yrs
    ao = tb[tb["t_entry"] >= ALT_END]
    aoh = th[th["t_entry"] >= ALT_END]
    out["altOOS_per_symbol"] = {s: {"n": int(len(g)), "avg_R": round(float(g["R"].mean()), 3),
                                    "harsh_avg_R": round(float(aoh[aoh.symbol == s]["R"].mean()), 3)}
                                for s, g in ao.groupby("symbol")}
    out["altOOS_harsh"] = blk(th, lo=ALT_END)

    # ---- null test (task spec): 200 perms, random entry bars within the same symbol-month
    rng = np.random.default_rng(seed)
    recs, OUTC, VALID, MONTH = [], {}, {}, {}
    for s in SYMS:
        df = load(s, "4h")
        sig = F.rcrowd_4h(df, **p)
        tr = simulate(df, sig, BASE, 18, None, s)
        Ro = outcomes(df)
        pos = df.index.get_indexer(tr["t_signal"])
        dj = np.where(tr["dir"].to_numpy() > 0, 0, 1)
        assert np.allclose(Ro[pos, dj], tr["R"].to_numpy(), atol=1e-9)
        pctl = F.roll_pct(F.logpos(df["ls_accounts"]), F.bars(df, 24 * 30)).to_numpy()
        VALID[s] = np.isfinite(pctl) & np.isfinite(Ro).all(axis=1)
        OUTC[s] = Ro
        MONTH[s] = df.index.tz_convert(None).to_period("M").astype(str).to_numpy()
        for k in range(len(tr)):
            recs.append((s, int(pos[k]), int(dj[k]), MONTH[s][pos[k]], float(tr["R"].iloc[k]), tr["t_entry"].iloc[k]))
    T = pd.DataFrame(recs, columns=["sym", "pos", "dj", "month", "R", "t_entry"])
    masks = {"OOS_2025-01..": (T["t_entry"] >= IS_END).to_numpy(), "altOOS_2025-07..": (T["t_entry"] >= ALT_END).to_numpy(),
             "IS_2024": (T["t_entry"] < IS_END).to_numpy()}
    groups = [(key, g.index.to_numpy()) for key, g in T.groupby(["sym", "month"])]
    vpos = {key: np.flatnonzero(VALID[key[0]] & (MONTH[key[0]] == key[1])) for key, _ in groups}
    dj = T["dj"].to_numpy()
    null = {k: [] for k in masks}
    for _ in range(n_perm):
        Rn = np.full(len(T), np.nan)
        for key, ix in groups:
            vp = vpos[key]
            if len(vp):
                Rn[ix] = OUTC[key[0]][rng.choice(vp, size=len(ix), replace=len(vp) < len(ix)), dj[ix]]
        for k, m in masks.items():
            null[k].append(np.nanmean(Rn[m]))
    res = {}
    for k, m in masks.items():
        x = np.array(null[k])
        real = float(T.loc[m, "R"].mean())
        res[k] = {"n": int(m.sum()), "real_avg_R": round(real, 4), "null_mean": round(float(x.mean()), 4),
                  "null_sd": round(float(x.std(ddof=1)), 4), "null_p95": round(float(np.quantile(x, 0.95)), 4),
                  "p_value": round(float((1 + (x >= real).sum()) / (1 + len(x))), 4)}
    out["null_200perm_symbol_month"] = {"n_perm": n_perm, "seed": seed, **res}
    print(json.dumps(out, indent=1, default=str))
    json.dump(out, open(OUT, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
