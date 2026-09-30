"""Collect results/ml_combo_*.json into markdown tables (used to write results/ml_combo.md)."""
import glob
import json
import os

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")


def verdict(r):
    o, h = r["selected_OOS"], r["selected_OOS_harsh_costs"]
    share = r["all_configs_OOS_avgR"]["share_positive"] or 0
    if not o.get("n") or o.get("avg_R", 0) <= 0:
        return "NO_EDGE"
    ok = ((o.get("t_stat") or 0) >= 2 and h.get("avg_R", 0) > 0 and r["oos_symbols_positive"] >= 6 and share >= 0.5)
    return "PROMISING" if ok else "WEAK"


def row(s):
    return (f"{s.get('n', 0)} | {s.get('win_pct', '-')} | {s.get('avg_R', '-')} | {s.get('t_stat', '-')} | "
            f"{s.get('t_day_cluster', s.get('t_stat_day_cluster', '-'))} | {s.get('ret_pct@0.5%', '-')} | "
            f"{s.get('max_dd_pct', '-')}")


def main():
    files = sorted(f for f in glob.glob(os.path.join(RES, "ml_combo_t*.json")))
    total = 0
    print("| variant | tf | selected | sample | n | win% | avg_R | t | t_day | ret@0.5% | maxDD% |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    summary = []
    for f in files:
        r = json.load(open(f))
        total += r["n_configs"]
        sp = r["selected_params"]
        sel = f"{sp['model']} q={sp['q']}"
        v = r["variant"]
        print(f"| {v} | {r['tf']} | {sel} | IS | {row(r['selected_IS'])} |")
        print(f"| {v} | {r['tf']} | {sel} | OOS | {row(r['selected_OOS'])} |")
        print(f"| {v} | {r['tf']} | {sel} | OOS harsh | {row(r['selected_OOS_harsh_costs'])} |")
        summary.append({"variant": v, "tf": r["tf"], "verdict": verdict(r),
                        "oos_symbols_positive": r["oos_symbols_positive"],
                        "share_cfg_pos": r["all_configs_OOS_avgR"]["share_positive"],
                        "long_share_IS": r["selected_IS"].get("long_share"),
                        "long_share_OOS": r["selected_OOS"].get("long_share"),
                        "per_symbol": {k: (v2["n"], v2["avg_R"]) for k, v2 in r["selected_OOS_per_symbol"].items()},
                        "IC": {m: {k: d[k] for k in d if k.startswith(("IC", "AUC"))} for m, d in r["diagnostics"].items()},
                        "top_dec_net": {m: d["OOS_deciles_best_side"][-1]["net_R_approx"] for m, d in r["diagnostics"].items()},
                        "imp": {m: (d["max_share"], d["top5_share"], list(d["top15_gain_share"])[:6])
                                for m, d in r["feature_importance_gain"].items()}})
    print("\nTOTAL configs", total)
    for s in summary:
        print(json.dumps(s))
    print("\nALL CONFIGS")
    for f in files:
        r = json.load(open(f))
        for c in r["configs"]:
            print(r["variant"], json.dumps(c["params"]), "IS", c["IS"].get("n"), c["IS"].get("avg_R"), c["IS"].get("t_stat"),
                  "| OOS", c["OOS"].get("n"), c["OOS"].get("avg_R"), c["OOS"].get("t_stat"))


if __name__ == "__main__":
    main()
