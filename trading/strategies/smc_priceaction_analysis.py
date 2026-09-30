"""Post-grid analysis for the smc_priceaction family (no new selection on OOS).

Steps (all selections use IN-SAMPLE only, score = bt.runner.score = IS t-stat with n>=30):
  1. read the runner grids results/smc_priceaction_<variant>_<tf>.json (12 configs each, stop=struct)
  2. stop-placement check (f): for each variant, the IS-selected (rr, filt) re-run with stop="alt"
  3. final pick per variant = max IS score over its 13 configs (grid + alt stop)
  4. for every final pick: base + harsh + zero-cost runs, OOS per symbol / per year,
     week-clustered t, share of the variant's configs with OOS avg_R > 0
  5. 1h portability: each setup's final 15m config applied unchanged to 1h
  6. descriptive filter table (d/e): IS and OOS avg_R by filter, averaged over rr (no selection)

    cd trading && python3 -m strategies.smc_priceaction_analysis
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd

from bt.data import SYMBOLS
from bt.engine import Costs, IS_END, split_summary, summarize
from bt import runner as R

R.COST_SCENARIOS["zero"] = Costs(taker=0.0, maker=0.0, slippage=0.0)

MOD = "strategies.smc_priceaction"
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
VARIANTS = [("a_choch", "choch"), ("b_ob", "ob"), ("c_fvg", "fvg")]
TFS = ["5m", "15m"]
WORKERS = 2
RISK = 0.5


def run(params, tf, cost="base", module=MOD):
    return R.run_config(module, "strategy", SYMBOLS, tf, params, {}, cost, WORKERS)


def cluster_t(tr, freq="W"):
    if tr is None or len(tr) < 3:
        return None
    wk = tr.groupby(tr["t_entry"].dt.tz_localize(None).dt.to_period(freq))["R"].sum()
    if len(wk) < 3 or wk.std(ddof=1) == 0:
        return None
    return round(float(wk.mean() / wk.std(ddof=1) * math.sqrt(len(wk))), 2)


def oos(tr):
    return tr[tr["t_entry"] >= IS_END] if len(tr) else tr


def iss(tr):
    return tr[tr["t_entry"] < IS_END] if len(tr) else tr


def evaluate(params, tf, module=MOD):
    base, harsh, zero = (run(params, tf, c, module) for c in ("base", "harsh", "zero"))
    ob, oh = oos(base), oos(harsh)
    per_sym = {s: summarize(g, RISK, s) for s, g in ob.groupby("symbol")} if len(ob) else {}
    per_year = {str(y): summarize(g, RISK, str(y)) for y, g in base.groupby(base["t_entry"].dt.year)}
    by_dir = {("long" if d > 0 else "short"): split_summary(g, RISK) for d, g in base.groupby("dir")}
    return {
        "params": params, "tf": tf,
        "base": split_summary(base, RISK), "harsh": split_summary(harsh, RISK),
        "zero_cost": split_summary(zero, RISK),
        "OOS_week_cluster_t": cluster_t(ob), "IS_week_cluster_t": cluster_t(iss(base)),
        "OOS_harsh_week_cluster_t": cluster_t(oh),
        "OOS_symbols_positive": int(sum(1 for v in per_sym.values() if v.get("avg_R", 0) > 0)),
        "OOS_per_symbol": per_sym, "per_year": per_year, "by_direction": by_dir,
        "OOS_exit_reasons": ob["reason"].value_counts().to_dict() if len(ob) else {},
        "OOS_median_risk_pct": float(ob["risk_pct"].median()) if len(ob) else None,
    }


def verdict(ev, share_pos):
    o, h = ev["base"]["OOS"], ev["harsh"]["OOS"]
    a, t = o.get("avg_R"), o.get("t_stat")
    if a is None or a <= 0:
        return "NO_EDGE"
    ok = (t is not None and t >= 2 and (h.get("avg_R") or -1) > 0 and ev["OOS_symbols_positive"] >= 6
          and share_pos is not None and share_pos >= 0.5)
    return "PROMISING" if ok else "WEAK"


def main():
    summary = {"variants": {}, "n_configs": {}, "controls": {}}
    total = 0
    # ---- controls: reference strategies/smc.py (limit in FVG), one config per tf
    for tf in TFS:
        p = os.path.join(RES, f"smc_priceaction_ref_{tf}.json")
        if os.path.exists(p):
            g = json.load(open(p))
            total += g["n_configs"]
            ev = evaluate({}, tf, module="strategies.smc")
            summary["controls"][f"ref_{tf}"] = ev
            print("ref", tf, ev["base"]["OOS"].get("avg_R"), flush=True)

    final_15m = {}
    for vname, setup in VARIANTS:
        for tf in TFS:
            p = os.path.join(RES, f"smc_priceaction_{vname}_{tf}.json")
            g = json.load(open(p))
            rows = [{"params": r["params"], "IS": r["IS"], "OOS": r["OOS"], "src": "grid"} for r in g["configs"]]
            sel = g["selected_params"]
            # (f) stop placement: IS-selected grid config with the alternative stop
            alt = dict(sel, stop="alt")
            tr = run(alt, tf)
            ss = split_summary(tr, RISK, json.dumps(alt))
            rows.append({"params": alt, "IS": ss["IS"], "OOS": ss["OOS"], "src": "stop_alt"})
            best = max(rows, key=lambda r: R.score(r["IS"]))
            oos_avg = [r["OOS"].get("avg_R") for r in rows if r["OOS"].get("n", 0) >= 10]
            share = float(np.mean([x > 0 for x in oos_avg])) if oos_avg else None
            ev = evaluate(best["params"], tf)
            key = f"{vname}_{tf}"
            total += len(rows)
            summary["n_configs"][key] = len(rows)
            summary["variants"][key] = {
                "selected_params": best["params"], "selected_from": best["src"],
                "share_configs_OOS_positive": share, "median_config_OOS_avgR": float(np.median(oos_avg)),
                "n_configs": len(rows), "eval": ev, "verdict": verdict(ev, share),
                "all_configs": [{"params": r["params"], "src": r["src"],
                                 "IS": {k: r["IS"].get(k) for k in ("n", "win_pct", "avg_R", "t_stat")},
                                 "OOS": {k: r["OOS"].get(k) for k in ("n", "win_pct", "avg_R", "t_stat")}}
                                for r in rows],
            }
            if tf == "15m":
                final_15m[vname] = best["params"]
            print(key, best["params"], "IS", ev["base"]["IS"].get("avg_R"), ev["base"]["IS"].get("t_stat"),
                  "OOS", ev["base"]["OOS"].get("avg_R"), ev["base"]["OOS"].get("t_stat"),
                  "harsh", ev["harsh"]["OOS"].get("avg_R"), "sym+", ev["OOS_symbols_positive"],
                  "share", share, summary["variants"][key]["verdict"], flush=True)

    # ---- 1h portability (optional tf): 15m IS-selected params, unchanged
    for vname, params in final_15m.items():
        ev = evaluate(params, "1h")
        total += 1
        key = f"{vname}_1h_port"
        summary["variants"][key] = {"selected_params": params, "selected_from": "15m IS pick, unchanged",
                                    "share_configs_OOS_positive": None, "n_configs": 1, "eval": ev,
                                    "verdict": verdict(ev, 1.0 if (ev["base"]["OOS"].get("avg_R") or -1) > 0 else 0.0)}
        print(key, ev["base"]["OOS"].get("avg_R"), ev["base"]["OOS"].get("t_stat"), flush=True)

    # ---- descriptive filter / rr tables from the grids (no selection)
    filt_tab = {}
    for vname, _ in VARIANTS:
        for tf in TFS:
            key = f"{vname}_{tf}"
            rows = [r for r in summary["variants"][key]["all_configs"] if r["src"] == "grid"]
            for dim in ("filt", "rr"):
                vals = sorted(set(str(r["params"][dim]) for r in rows))
                for v in vals:
                    sub = [r for r in rows if str(r["params"][dim]) == v]
                    filt_tab.setdefault(key, {}).setdefault(dim, {})[v] = {
                        "IS_avgR": round(float(np.mean([r["IS"]["avg_R"] for r in sub])), 3),
                        "OOS_avgR": round(float(np.mean([r["OOS"]["avg_R"] for r in sub])), 3),
                        "IS_n": int(np.mean([r["IS"]["n"] for r in sub])),
                        "OOS_n": int(np.mean([r["OOS"]["n"] for r in sub]))}
    summary["filter_rr_tables"] = filt_tab
    summary["n_configs_total"] = total
    print("TOTAL configs", total)
    with open(os.path.join(RES, "smc_priceaction_summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
