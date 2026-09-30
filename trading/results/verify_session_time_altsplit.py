"""Adversarial verification of session_time: ALTERNATIVE SPLIT for every grid of the family.

    cd /home/user/research/trading && python3 results/verify_session_time_altsplit.py

For each results/session_time_<variant>_<tf>.json (the 16 runner grids, 72 configs) every config
is re-run unchanged (base costs). Then:
  * original split  (IS < 2025-01-01): selection by max IS t (n >= 30) must reproduce the JSON;
  * alternative split (IS < 2025-07-01): parameters re-selected by the same rule on the longer IS,
    OOS = 2025-07-01 .. 2026-08; harsh costs for the re-selected config; per-symbol OOS;
    share of configs with positive alt-OOS.
No config outside the stored grids is evaluated. Output: results/verify_session_time_altsplit.json
"""
import glob
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/user/research/trading")
os.chdir("/home/user/research/trading")

import strategies.session_time as st  # noqa: E402  (applies the loader patch)
from bt.data import SYMBOLS, load  # noqa: E402
from bt.engine import IS_END, simulate, summarize  # noqa: E402
from bt.runner import COST_SCENARIOS  # noqa: E402

ALT_END = pd.Timestamp("2025-07-01", tz="UTC")
_CACHE = {}


def _df(sym, tf, lk):
    key = (sym, tf, json.dumps(lk, sort_keys=True))
    if key not in _CACHE:
        _CACHE.clear() if len(_CACHE) > 12 else None
        _CACHE[key] = load(sym, tf, **lk)
    return _CACHE[key]


def _job(a):
    fnname, tf, lk, sym, plist, cost = a
    df = _df(sym, tf, lk)
    fn = getattr(st, fnname)
    out = []
    for p in plist:
        sig = fn(df, **p)
        out.append(simulate(df, sig, COST_SCENARIOS[cost], fn.MAX_HOLD, fn.LIMIT_TTL, sym))
    return out


def score(s):
    if not s or s.get("n", 0) < 30 or s.get("t_stat") is None:
        return -1e9
    return s["t_stat"]


def small(s):
    return {k: s.get(k) for k in ("n", "win_pct", "avg_R", "t_stat", "t_stat_day_cluster", "ret_pct@0.5%",
                                  "max_dd_pct")}


def main():
    res = {}
    paths = sorted(p for p in glob.glob("results/session_time_*_*.json")
                   if not os.path.basename(p)[13:].startswith(("explore", "summary", "holdout", "decay", "control")))
    with ProcessPoolExecutor(2) as ex:
        for path in paths:
            name = os.path.basename(path)[len("session_time_"):-5]
            r = json.load(open(path))
            fnname, tf, lk = r["fn"], r["tf"], r["load"]
            plist = [c["params"] for c in r["configs"]]
            parts = list(ex.map(_job, [(fnname, tf, lk, s, plist, "base") for s in SYMBOLS]))
            trs = [pd.concat([parts[i][j] for i in range(len(SYMBOLS)) if len(parts[i][j])], ignore_index=True)
                   for j in range(len(plist))]
            rows = []
            for p, tr in zip(plist, trs):
                rows.append({"params": p,
                             "IS": summarize(tr[tr.t_entry < IS_END]), "OOS": summarize(tr[tr.t_entry >= IS_END]),
                             "altIS": summarize(tr[tr.t_entry < ALT_END]),
                             "altOOS": summarize(tr[tr.t_entry >= ALT_END])})
            j0 = int(np.argmax([score(x["IS"]) for x in rows]))
            j1 = int(np.argmax([score(x["altIS"]) for x in rows]))
            # harsh for the alt-selected config
            hp = list(ex.map(_job, [(fnname, tf, lk, s, [plist[j1]], "harsh") for s in SYMBOLS]))
            th = pd.concat([h[0] for h in hp if len(h[0])], ignore_index=True)
            tb = trs[j1]
            ao = tb[tb.t_entry >= ALT_END]
            persym = ao.groupby("symbol")["R"].mean()
            share = [x["altOOS"].get("avg_R", 0) > 0 for x in rows if x["altOOS"].get("n", 0) >= 10]
            rep = {
                "fn": fnname, "tf": tf, "n_configs": len(plist),
                "orig_selected": plist[j0], "orig_selected_matches_json": plist[j0] == r["selected_params"],
                "orig_IS": small(rows[j0]["IS"]), "orig_OOS": small(rows[j0]["OOS"]),
                "json_OOS_avgR": r["selected_OOS"].get("avg_R"), "json_OOS_n": r["selected_OOS"].get("n"),
                "alt_selected": plist[j1], "alt_IS": small(rows[j1]["altIS"]), "alt_OOS": small(rows[j1]["altOOS"]),
                "alt_OOS_harsh_avgR": round(float(th[th.t_entry >= ALT_END]["R"].mean()), 3),
                "alt_OOS_symbols_positive": int((persym > 0).sum()),
                "alt_OOS_per_symbol": persym.round(3).to_dict(),
                "alt_share_configs_OOS_positive": float(np.mean(share)) if share else None,
                "all_configs": [{"params": x["params"], "IS": x["IS"].get("avg_R"), "OOS": x["OOS"].get("avg_R"),
                                 "altIS_avgR": x["altIS"].get("avg_R"), "altIS_t": x["altIS"].get("t_stat"),
                                 "altOOS_avgR": x["altOOS"].get("avg_R"), "altOOS_t": x["altOOS"].get("t_stat"),
                                 "altOOS_n": x["altOOS"].get("n")} for x in rows],
            }
            res[name] = rep
            print(name, "orig match", rep["orig_selected_matches_json"], "OOS", rep["orig_OOS"]["avg_R"],
                  "(json", rep["json_OOS_avgR"], ") | ALT sel", plist[j1], "altIS", rep["alt_IS"]["avg_R"],
                  rep["alt_IS"]["t_stat"], "altOOS", rep["alt_OOS"]["n"], rep["alt_OOS"]["avg_R"],
                  rep["alt_OOS"]["t_stat"], "harsh", rep["alt_OOS_harsh_avgR"], "sym+",
                  rep["alt_OOS_symbols_positive"], "share", rep["alt_share_configs_OOS_positive"], flush=True)
            json.dump(res, open("results/verify_session_time_altsplit.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
