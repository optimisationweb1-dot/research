"""Analysis of the verifier grid (see verify_smc_priceaction_run.py). Selection = bt.runner.score
(IS t-stat, IS n >= 30), always on the in-sample window of the split in question.

    cd trading && python3 -m results.verify_smc_priceaction_analysis
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bt.engine import summarize  # noqa: E402
from bt.runner import score  # noqa: E402

RES = os.path.dirname(os.path.abspath(__file__))
TR = os.environ.get("VERIFY_OUT", "/tmp/claude-0/-home-user-research/ea6ba1ab-fe99-5191-91e4-bb9455e40592/scratchpad/verify_smc_trades.parquet")
SPLIT_MAIN = pd.Timestamp("2025-01-01", tz="UTC")
SPLIT_ALT = pd.Timestamp("2025-07-01", tz="UTC")
KEYS = ["setup", "rr", "filt", "stop"]
SEL = dict(setup="fvg", rr="3", filt="kz_htf", stop="alt")


def wk_t(tr):
    if len(tr) < 3:
        return None
    w = tr.groupby(tr["t_entry"].dt.tz_localize(None).dt.to_period("W"))["R"].sum()
    return round(float(w.mean() / w.std(ddof=1) * math.sqrt(len(w))), 2) if len(w) > 2 and w.std(ddof=1) > 0 else None


def short(s):
    return {k: s.get(k) for k in ("n", "win_pct", "avg_R", "t_stat", "t_stat_day_cluster", "ret_pct@0.5%", "max_dd_pct",
                                  "median_stop_pct")}


def cfg(tr, tf, cost, **p):
    m = (tr["tf"] == tf) & (tr["cost"] == cost)
    for k, v in p.items():
        m &= tr[k] == str(v)
    return tr[m]


def split(tr, cut):
    return tr[tr["t_entry"] < cut], tr[tr["t_entry"] >= cut]


def evaluate(tr, tf, p, cut):
    b, h = cfg(tr, tf, "base", **p), cfg(tr, tf, "harsh", **p)
    bi, bo = split(b, cut)
    _, ho = split(h, cut)
    ps = {s: summarize(g).get("avg_R") for s, g in bo.groupby("symbol")}
    psi = {s: summarize(g).get("avg_R") for s, g in bi.groupby("symbol")}
    gross = bo.assign(G=bo["dir"] * (bo["exit"] - bo["entry"]) / (bo["risk_pct"] / 100 * bo["entry"]))  # "stop" col = config label
    return {"params": p, "tf": tf,
            "IS": short(summarize(bi)), "OOS": short(summarize(bo)), "OOS_harsh": short(summarize(ho)),
            "OOS_gross_avg_R_approx": round(float(gross["G"].mean()), 3) if len(gross) else None,
            "OOS_week_t": wk_t(bo), "OOS_symbols_positive": int(sum(v > 0 for v in ps.values() if v is not None)),
            "IS_symbols_positive": int(sum(v > 0 for v in psi.values() if v is not None)),
            "OOS_per_symbol": {s: (int(len(g)), round(float(g["R"].mean()), 3)) for s, g in bo.groupby("symbol")},
            "IS_per_symbol": {s: (int(len(g)), round(float(g["R"].mean()), 3)) for s, g in bi.groupby("symbol")},
            "per_year": {str(y): (int(len(g)), round(float(g["R"].mean()), 3))
                         for y, g in b.groupby(b["t_entry"].dt.year)}}


def half_table(tr, tf, p):
    b = cfg(tr, tf, "base", **p)
    hk = b["t_entry"].dt.year.astype(str) + "H" + np.where(b["t_entry"].dt.month <= 6, "1", "2")
    return {k: (int(len(g)), round(float(g["R"].mean()), 3)) for k, g in b.groupby(hk)}


def grid_rows(tr, tf, cut, setup=None, stops=("struct", "alt")):
    b = tr[(tr["tf"] == tf) & (tr["cost"] == "base") & tr["stop"].isin(stops)]
    if setup:
        b = b[b["setup"] == setup]
    rows = []
    for key, g in b.groupby(KEYS):
        gi, go = split(g, cut)
        rows.append({"params": dict(zip(KEYS, key)), "IS": short(summarize(gi)), "OOS": short(summarize(go))})
    return rows


def original_protocol(tr, tf, setup, cut):
    """Family protocol: 12 grid configs with stop=struct -> IS pick; + the pick with stop=alt; final = max IS score."""
    rows = grid_rows(tr, tf, cut, setup, ("struct",))
    pick = max(rows, key=lambda r: score(r["IS"]))
    alt = dict(pick["params"], stop="alt")
    rows13 = rows + [r for r in grid_rows(tr, tf, cut, setup, ("alt",)) if r["params"] == alt]
    final = max(rows13, key=lambda r: score(r["IS"]))
    oos = [r["OOS"]["avg_R"] for r in rows13 if (r["OOS"].get("n") or 0) >= 10]
    return final["params"], float(np.mean([x > 0 for x in oos])), rows13


def main():
    tr = pd.read_parquet(TR)
    for c in ("t_entry", "t_exit", "t_signal"):
        tr[c] = pd.to_datetime(tr[c], utc=True)
    out = {"n_configs_verifier": int(tr.groupby(["tf"] + KEYS).ngroups)}

    # (2) re-run of the claimed configuration and of its 15m origin
    out["rerun_selected_1h"] = evaluate(tr, "1h", SEL, SPLIT_MAIN)
    out["rerun_selected_1h"]["per_half"] = half_table(tr, "1h", SEL)
    out["rerun_origin_15m"] = evaluate(tr, "15m", SEL, SPLIT_MAIN)

    # original protocol replication at 15m (main split) -> does it pick fvg/3/kz_htf/alt?
    rep = {}
    for setup in ("choch", "ob", "fvg"):
        p, share, _ = original_protocol(tr, "15m", setup, SPLIT_MAIN)
        rep[setup] = {"final_pick_15m": p, "share_OOS_pos_13": share}
    out["replicate_main_protocol"] = rep

    # (5) parameter neighbours: full fvg 1h grid (24) and full 1h grid across setups (72), main split
    rows = grid_rows(tr, "1h", SPLIT_MAIN, "fvg")
    out["fvg_1h_grid_main_split"] = [{"p": "/".join(r["params"].values()),
                                      "IS": (r["IS"].get("n"), r["IS"].get("avg_R"), r["IS"].get("t_stat")),
                                      "OOS": (r["OOS"].get("n"), r["OOS"].get("avg_R"), r["OOS"].get("t_stat"))}
                                     for r in rows]
    fam = {}
    for tf in ("15m", "1h"):
        for setup in ("choch", "ob", "fvg"):
            rr_ = grid_rows(tr, tf, SPLIT_MAIN, setup)
            o = [r["OOS"]["avg_R"] for r in rr_ if (r["OOS"].get("n") or 0) >= 10]
            i = [r["IS"]["avg_R"] for r in rr_ if (r["IS"].get("n") or 0) >= 10]
            fam[f"{setup}_{tf}"] = {"n_cfg": len(rr_), "share_OOS_pos": round(float(np.mean([x > 0 for x in o])), 2),
                                    "median_OOS_avgR": round(float(np.median(o)), 3),
                                    "share_IS_pos": round(float(np.mean([x > 0 for x in i])), 2),
                                    "median_IS_avgR": round(float(np.median(i)), 3),
                                    "best_OOS_t": max(r["OOS"].get("t_stat") or -99 for r in rr_)}
    out["grid_share_main_split"] = fam
    nb = []
    for k, alts in (("rr", ("1.5", "2")), ("filt", ("none", "kz", "htf")), ("stop", ("struct",))):
        for v in alts:
            p = dict(SEL, **{k: v})
            e = evaluate(tr, "1h", p, SPLIT_MAIN)
            nb.append({"p": "/".join(p.values()), "IS": (e["IS"]["n"], e["IS"]["avg_R"]),
                       "OOS": (e["OOS"]["n"], e["OOS"]["avg_R"], e["OOS"]["t_stat"]),
                       "OOS_harsh": e["OOS_harsh"]["avg_R"], "sym_pos": e["OOS_symbols_positive"]})
    out["neighbours_1h"] = nb

    # (3) alternative split: IS < 2025-07-01, OOS 2025-07-01 .. 2026-08
    alt = {}
    for setup in ("choch", "ob", "fvg"):
        p15, share15, _ = original_protocol(tr, "15m", setup, SPLIT_ALT)
        e15 = evaluate(tr, "15m", p15, SPLIT_ALT)
        e1h = evaluate(tr, "1h", p15, SPLIT_ALT)          # port of the new 15m pick to 1h
        rows1h = grid_rows(tr, "1h", SPLIT_ALT, setup)     # direct 1h selection over 24 configs
        best1h = max(rows1h, key=lambda r: score(r["IS"]))
        e1h_sel = evaluate(tr, "1h", best1h["params"], SPLIT_ALT)
        o1h = [r["OOS"]["avg_R"] for r in rows1h if (r["OOS"].get("n") or 0) >= 10]
        alt[setup] = {"15m_pick": p15, "15m_share_OOS_pos_13": round(share15, 2),
                      "15m": {k: e15[k] for k in ("IS", "OOS", "OOS_harsh", "OOS_symbols_positive", "OOS_week_t")},
                      "1h_port": {k: e1h[k] for k in ("IS", "OOS", "OOS_harsh", "OOS_symbols_positive", "OOS_week_t")},
                      "1h_direct_pick": best1h["params"],
                      "1h_direct": {k: e1h_sel[k] for k in ("IS", "OOS", "OOS_harsh", "OOS_symbols_positive",
                                                            "OOS_week_t")},
                      "1h_grid_share_OOS_pos_24": round(float(np.mean([x > 0 for x in o1h])), 2)}
    # the claimed config itself under the alternative split (no reselection)
    alt["claimed_config_1h_fixed"] = {k: v for k, v in evaluate(tr, "1h", SEL, SPLIT_ALT).items()
                                      if k in ("IS", "OOS", "OOS_harsh", "OOS_symbols_positive", "OOS_week_t",
                                               "OOS_per_symbol")}
    out["alt_split_2025_07"] = alt

    with open(os.path.join(RES, "verify_smc_priceaction.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(json.dumps(out, default=str)[:20000])


if __name__ == "__main__":
    main()
