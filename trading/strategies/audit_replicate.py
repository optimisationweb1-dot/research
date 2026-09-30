"""Audit step 1: replicate bt.engine trades with the independent audit_bt simulator.

    python3 -m strategies.audit_replicate      -> results/audit_replication.json
"""
import json
import os
import time

import numpy as np
import pandas as pd

from bt.data import load
from bt import engine as E
from strategies import audit_bt as A
from strategies import smc, audit_donchian as DC

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
KEYS = ["dir", "t_signal", "t_entry", "t_exit", "entry", "stop", "target", "exit", "reason", "R"]


def compare(te, ta):
    rep = {"n_engine": len(te), "n_audit": len(ta)}
    if len(te) == 0 and len(ta) == 0:
        return rep, None
    m = te.merge(ta, on=["t_signal"], how="outer", suffixes=("_e", "_a"), indicator=True)
    rep["only_engine"] = int((m["_merge"] == "left_only").sum())
    rep["only_audit"] = int((m["_merge"] == "right_only").sum())
    b = m[m["_merge"] == "both"]
    diffs = {}
    for k in ["dir", "t_entry", "t_exit", "reason"]:
        diffs[k] = int((b[k + "_e"] != b[k + "_a"]).sum())
    for k in ["entry", "exit", "R"]:
        x, y = b[k + "_e"].to_numpy(float), b[k + "_a"].to_numpy(float)
        diffs[k + "_maxabs"] = float(np.nanmax(np.abs(x - y))) if len(x) else 0.0
        diffs[k + "_n_gt_1e-9"] = int((np.abs(x - y) > 1e-9 * np.maximum(1, np.abs(x))).sum())
    rep["field_diffs"] = diffs
    rep["sumR_engine"] = round(float(te["R"].sum()), 4) if len(te) else 0
    rep["sumR_audit"] = round(float(ta["R"].sum()), 4) if len(ta) else 0
    bad = b[(b["reason_e"] != b["reason_a"]) | (np.abs(b["R_e"] - b["R_a"]) > 1e-9)]
    return rep, pd.concat([bad, m[m["_merge"] != "both"]]).head(20)


def main():
    res = {}
    cases = [("smc_5m", smc.strategy, "5m", {}), ("smc_15m", smc.strategy, "15m", {}),
             ("donchian_1h", DC.strategy, "1h", {})]
    for sym in ["BTCUSDT", "ETHUSDT"]:
        for name, fn, tf, params in cases:
            t0 = time.time()
            df = load(sym, tf)
            sig = fn(df, **params)
            mh, ttl = getattr(fn, "MAX_HOLD", None), getattr(fn, "LIMIT_TTL", None)
            te = E.simulate(df, sig, E.Costs(), mh, ttl, sym)
            ta, st = A.simulate(df, sig, A.BASE, mh, ttl, sym, return_stats=True)
            rep, bad = compare(te, ta)
            # harsh costs too
            teh = E.simulate(df, sig, E.Costs(0.0006, 0.0004, 0.0005), mh, ttl, sym)
            tah = A.simulate(df, sig, A.HARSH, mh, ttl, sym)
            reph, _ = compare(teh, tah)
            rep["harsh"] = {k: reph[k] for k in ("n_engine", "n_audit", "only_engine", "only_audit",
                                                   "field_diffs", "sumR_engine", "sumR_audit") if k in reph}
            rep["engine_split"] = E.split_summary(te, 0.5)
            rep["audit_stats"] = st
            rep["secs"] = round(time.time() - t0, 1)
            res[f"{sym}_{name}"] = rep
            print(sym, name, json.dumps({k: rep[k] for k in rep if k not in ("engine_split",)}, default=str), flush=True)
            if bad is not None and len(bad):
                print(bad[[c for c in bad.columns if c.startswith(("t_signal", "t_entry", "t_exit", "reason", "R_", "entry", "exit", "_merge"))]].to_string())
    with open(os.path.join(OUT, "audit_replication.json"), "w") as f:
        json.dump(res, f, indent=1, default=str)


if __name__ == "__main__":
    main()
