"""Null test for smc_priceaction market-entry configs (fvg / choch).

Keep: exit logic (engine market-entry rules: next-open entry + slippage, stop/target, stop wins ties,
gap-through stops at the open, MAX_HOLD time exit, taker in / maker at target), each real trade's
direction and stop distance (as a fraction of the decision close), RR, and the number of trades per
symbol-month. Randomize: the decision bar, uniformly within the same symbol-month.
  null A: any bar of the month
  null B: only bars that pass the variant's own filter for that direction (killzone & 4h bias),
          i.e. does the SMC pattern add anything beyond the filter?
p = (1 + #{null avg_R >= real avg_R}) / (1 + N)

    cd trading && python3 -m results.verify_smc_priceaction_null
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bt.data import SYMBOLS, load  # noqa: E402
from bt.engine import Costs, simulate  # noqa: E402
import strategies.smc_priceaction as S  # noqa: E402

RES = os.path.dirname(os.path.abspath(__file__))
N_PERM = 200
COSTS = {"base": Costs(), "harsh": Costs(taker=0.0006, maker=0.0004, slippage=0.0005)}
CONFIGS = [
    ("c_fvg_1h_port", "1h", dict(setup="fvg", rr=3, filt="kz_htf", stop="alt")),
    ("a_choch_1h_port", "1h", dict(setup="choch", rr=2, filt="none", stop="struct")),
    ("c_fvg_15m", "15m", dict(setup="fvg", rr=3, filt="kz_htf", stop="alt")),
]
SPLITS = {"IS": ("2000-01-01", "2025-01-01"), "OOS": ("2025-01-01", "2100-01-01")}
OUT_NAME = "verify_smc_priceaction_null.json"
if len(sys.argv) > 1 and sys.argv[1] == "alt":   # alternative split: OOS = 2025-07-01 .. 2026-08
    SPLITS = {"IS": ("2000-01-01", "2025-07-01"), "OOS": ("2025-07-01", "2100-01-01")}
    CONFIGS = [
        ("c_fvg_1h_port_altsplit", "1h", dict(setup="fvg", rr=3, filt="kz_htf", stop="alt")),
        ("c_fvg_1h_direct_altsplit", "1h", dict(setup="fvg", rr=3, filt="htf", stop="alt")),
        ("a_choch_1h_port_altsplit", "1h", dict(setup="choch", rr=3, filt="none", stop="struct")),
    ]
    OUT_NAME = "verify_smc_priceaction_null_altsplit.json"


def exit_R(o, h, l, c, t, d, stop, target, cost, max_hold=S.MAX_HOLD):
    """Vectorized engine market-entry trade outcome. t, d, stop, target: arrays (decision bar t)."""
    n = len(c)
    k0 = t + 1
    entry = o[k0] * (1 + d * cost.slippage)
    valid = d * (entry - stop) > 0
    W = max_hold
    idx = k0[:, None] + np.arange(W)[None, :]
    inside = idx <= n - 1
    idxc = np.minimum(idx, n - 1)
    H, L, O = h[idxc], l[idxc], o[idxc]
    dd = d[:, None]
    hit_s = np.where(dd > 0, L <= stop[:, None], H >= stop[:, None]) & inside
    hit_t = np.where(dd > 0, H >= target[:, None], L <= target[:, None]) & inside
    big = W + 10
    fs = np.where(hit_s.any(1), hit_s.argmax(1), big)
    ft = np.where(hit_t.any(1), hit_t.argmax(1), big)
    last = np.minimum(n - 1 - k0, W - 1)   # last bar index checked (end of data or max-hold bar)
    R = np.full(len(t), np.nan)
    reason = np.empty(len(t), object)
    for i in range(len(t)):
        if not valid[i]:
            continue
        di, e, sp, tp = d[i], entry[i], stop[i], target[i]
        if fs[i] <= last[i] and fs[i] <= ft[i]:
            k = k0[i] + fs[i]
            gap = fs[i] > 0 and ((di > 0 and o[k] < sp) or (di < 0 and o[k] > sp))
            x, fo, rs = (o[k] if gap else sp) * (1 - di * cost.slippage), cost.taker, "stop"
        elif ft[i] <= last[i]:
            x, fo, rs = tp, cost.maker, "target"
        elif k0[i] + last[i] >= n - 1:
            x, fo, rs = c[n - 1], cost.taker, "end"
        else:
            x, fo, rs = o[k0[i] + W] * (1 - di * cost.slippage), cost.taker, "time"
        risk = abs(e - sp)
        R[i] = (di * (x - e) - (e * cost.taker + x * fo)) / risk
        reason[i] = rs
    return R, reason


def sym_data(sym, tf, p):
    df = load(sym, tf)
    sig = S.strategy(df, **p)
    real = simulate(df, sig, COSTS["base"], S.MAX_HOLD, S.LIMIT_TTL, sym)
    real_h = simulate(df, sig, COSTS["harsh"], S.MAX_HOLD, S.LIMIT_TTL, sym)
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    pos = {ts: i for i, ts in enumerate(df.index)}
    t = np.array([pos[x] for x in real["t_signal"]], int)
    d = real["dir"].to_numpy(int)
    rf = np.abs(c[t] - real["stop"].to_numpy()) / c[t]
    # sanity: re-implementation must reproduce the engine
    R, _ = exit_R(o, h, l, c, t, d, real["stop"].to_numpy(), real["target"].to_numpy(), COSTS["base"])
    err = float(np.nanmax(np.abs(R - real["R"].to_numpy()))) if len(R) else 0.0
    month = df.index.tz_localize(None).to_period("M")
    kz = S.killzone_mask(df) if "kz" in p["filt"] else np.ones(len(df), bool)
    bias = S.htf_bias(df) if "htf" in p["filt"] else None
    ok_l = kz & (bias > 0) if bias is not None else kz
    ok_s = kz & (bias < 0) if bias is not None else kz
    ok_l, ok_s = ok_l.copy(), ok_s.copy()
    last_ok = len(df) - 2
    ok_l[last_ok:] = ok_s[last_ok:] = False
    return dict(df=df, o=o, h=h, l=l, c=c, t=t, d=d, rf=rf, real=real, real_h=real_h, err=err,
                month=np.asarray(month.astype(str)), ok_l=ok_l, ok_s=ok_s)


def perm_trades(D, rng, mode, rr):
    t_real, d, rf, month = D["t"], D["d"], D["rf"], D["month"]
    n = len(D["c"])
    ts_all = np.arange(n - 2)
    new_t = np.empty(len(t_real), int)
    new_d = np.empty(len(t_real), int)
    new_rf = np.empty(len(t_real))
    mths = month[t_real]
    for m in np.unique(mths):
        sel = np.flatnonzero(mths == m)
        perm = rng.permutation(sel)            # direction + stop distance travel together, shuffled
        bars_m = ts_all[month[:n - 2] == m]
        for j, src in zip(sel, perm):
            dj = d[src]
            if mode == "A":
                pool = bars_m
            else:
                okm = D["ok_l"] if dj > 0 else D["ok_s"]
                pool = bars_m[okm[bars_m]]
                if len(pool) == 0:
                    pool = bars_m
            new_t[j] = rng.choice(pool)
            new_d[j] = dj
            new_rf[j] = rf[src]
    c = D["c"]
    stop = c[new_t] * (1 - new_d * new_rf)
    target = c[new_t] * (1 + new_d * rr * new_rf)
    return new_t, new_d, stop, target


def main():
    rng = np.random.default_rng(20260930)
    out = {}
    for name, tf, p in CONFIGS:
        Ds = {s: sym_data(s, tf, p) for s in SYMBOLS}
        real = pd.concat([D["real"] for D in Ds.values()], ignore_index=True)
        res = {"params": p, "tf": tf, "max_abs_R_diff_vs_engine": max(D["err"] for D in Ds.values())}
        real_h = pd.concat([D["real_h"] for D in Ds.values()], ignore_index=True)
        real_stats = {}
        for cn, rr_ in (("base", real), ("harsh", real_h)):
            for sp, (a, b) in SPLITS.items():
                m = (rr_["t_entry"] >= pd.Timestamp(a, tz="UTC")) & (rr_["t_entry"] < pd.Timestamp(b, tz="UTC"))
                real_stats[f"{cn}_{sp}"] = {"n": int(m.sum()), "avg_R": float(rr_.loc[m, "R"].mean())}
        res["real"] = real_stats
        for mode in ("A", "B"):
            null = {cn: {sp: [] for sp in SPLITS} for cn in COSTS}
            for it in range(N_PERM):
                Rs = {cn: [] for cn in COSTS}
                ents = []
                for s, D in Ds.items():
                    if len(D["t"]) == 0:
                        continue
                    t, d, st, tg = perm_trades(D, rng, mode, p["rr"])
                    for cn, cst in COSTS.items():
                        R, _ = exit_R(D["o"], D["h"], D["l"], D["c"], t, d, st, tg, cst)
                        Rs[cn].append(R)
                    ents.append(D["df"].index[t + 1].tz_localize(None).values)
                ent = np.concatenate([np.asarray(e) for e in ents])
                for cn in COSTS:
                    R = np.concatenate(Rs[cn])
                    for sp, (a, b) in SPLITS.items():
                        m = (ent >= np.datetime64(a)) & (ent < np.datetime64(b)) & ~np.isnan(R)
                        null[cn][sp].append(float(R[m].mean()))
            blk = {}
            for cn in COSTS:
                for sp in SPLITS:
                    arr = np.array(null[cn][sp])
                    rv = real_stats[f"{cn}_{sp}"]["avg_R"]
                    blk[f"{cn}_{sp}"] = {"null_mean": round(float(arr.mean()), 4),
                                         "null_sd": round(float(arr.std(ddof=1)), 4),
                                         "null_p05": round(float(np.quantile(arr, .05)), 4),
                                         "null_p95": round(float(np.quantile(arr, .95)), 4)}
                    if rv is not None:
                        blk[f"{cn}_{sp}"].update(real_avg_R=round(rv, 4),
                                                 p_value=round((1 + int((arr >= rv).sum())) / (1 + len(arr)), 4))
            res[f"null_{mode}"] = blk
            print(name, mode, json.dumps(blk), flush=True)
        out[name] = res
    with open(os.path.join(RES, OUT_NAME), "w") as f:
        json.dump(out, f, indent=1, default=str)


if __name__ == "__main__":
    main()
