"""Audit: SMC numbers - legacy trading/smc_backtest.py (README table) vs the bt port strategies/smc.py.

    python3 -m strategies.audit_smc       -> results/audit_smc.json

1. Reproduce the README table (legacy code, 5m, 2025-09..2026-08, BTC ETH SOL XRP DOGE, fee 0.10% round trip).
2. Same legacy code with ONE fix: a resting buy limit at `entry` fills whenever low < entry (legacy fills only
   when zlo < low < entry, i.e. it silently drops the bars that fall through the whole zone - the bars most
   likely to hit the stop), and a stop touched on the fill bar counts.
3. bt port (strategies.smc via the independent simulator, base and harsh costs) for the same window and for
   2023-01..2026-08 on all 10 symbols, with IS/OOS split.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

from bt.data import load, SYMBOLS
from strategies import audit_bt as A
from strategies import smc

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import smc_backtest as LEG  # noqa: E402  (legacy, read-only use)

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
W0, W1 = pd.Timestamp("2025-09-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC")
README5 = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]


def bars_of(df):
    return [{"t": int(t.value // 10 ** 6), "o": o, "h": h, "l": l, "c": c, "v": v}
            for t, o, h, l, c, v in zip(df.index, df.open, df.high, df.low, df.close, df.volume)]


def legacy_signals_fixed(bars, piv=5, z0=0.5, z1=0.786, ext=1.272, buf=0.3, fee=0.10, min_rr=2.0):
    """Copy of smc_backtest.signals with the fill rule changed to `low < entry` (any touch through)."""
    A_ = LEG.atr(bars)
    swing_h = swing_l = None
    st = {+1: {"s": 0}, -1: {"s": 0}}
    out = []
    for i in range(2 * piv + 2, len(bars)):
        j = i - piv
        win = bars[j - piv:j + piv + 1]
        if bars[j]["h"] == max(x["h"] for x in win):
            swing_h = bars[j]["h"]
        if bars[j]["l"] == min(x["l"] for x in win):
            swing_l = bars[j]["l"]
        b = bars[i]
        if swing_l is not None and b["l"] < swing_l < b["c"]:
            st[+1] = {"s": 1, "lo": b["l"], "choch": swing_h, "fvg": None}
        if swing_h is not None and b["h"] > swing_h > b["c"]:
            st[-1] = {"s": 1, "hi": b["h"], "choch": swing_l, "fvg": None}
        L = st[+1]
        if L["s"] == 1:
            L["lo"] = min(L["lo"], b["l"])
            if L["choch"] is not None and b["c"] > L["choch"]:
                L.update(s=2, hi=b["h"])
        elif L["s"] == 2:
            leg = L["hi"] - L["lo"]
            zhi, zlo = L["hi"] - leg * z0, L["hi"] - leg * z1
            fvg = L["fvg"]
            in_zone = fvg and fvg[0] <= zhi and fvg[1] >= zlo
            entry = min(zhi, fvg[1]) if fvg else zhi
            if in_zone and b["l"] < entry:                       # FIX: was zlo < b["l"] < entry
                sl = L["lo"] - buf * A_[i]
                tp = L["lo"] + leg * ext
                f = entry * fee / 100
                if entry > sl and (tp - entry - f) / (entry - sl + f) >= min_rr:
                    out.append((i, +1, entry, sl, tp))
                L["s"] = 0
            elif b["l"] < L["lo"]:
                L["s"] = 0
            else:
                L["hi"] = max(L["hi"], b["h"])
                if b["l"] > bars[i - 2]["h"]:
                    L["fvg"] = (bars[i - 2]["h"], b["l"])
        S = st[-1]
        if S["s"] == 1:
            S["hi"] = max(S["hi"], b["h"])
            if S["choch"] is not None and b["c"] < S["choch"]:
                S.update(s=2, lo=b["l"])
        elif S["s"] == 2:
            leg = S["hi"] - S["lo"]
            zlo, zhi = S["lo"] + leg * z0, S["lo"] + leg * z1
            fvg = S["fvg"]
            in_zone = fvg and fvg[1] >= zlo and fvg[0] <= zhi
            entry = max(zlo, fvg[0]) if fvg else zlo
            if in_zone and b["h"] > entry:                       # FIX: was entry < b["h"] < zhi
                sl = S["hi"] + buf * A_[i]
                tp = S["hi"] - leg * ext
                f = entry * fee / 100
                if sl > entry and (entry - tp - f) / (sl - entry + f) >= min_rr:
                    out.append((i, -1, entry, sl, tp))
                S["s"] = 0
            elif b["h"] > S["hi"]:
                S["s"] = 0
            else:
                S["lo"] = min(S["lo"], b["l"])
                if b["h"] < bars[i - 2]["l"]:
                    S["fvg"] = (b["h"], bars[i - 2]["l"])
    return out


def legacy_simulate_fixed(bars, sigs, fee=0.10, timeout=96):
    """smc_backtest.simulate + the stop can be hit on the fill bar itself."""
    res, busy = [], -1
    for i, d, e, sl, tp in sigs:
        if i <= busy:
            continue
        risk = abs(e - sl)
        fee_r = e * fee / 100 / risk
        b = bars[i]
        if (d > 0 and b["l"] <= sl) or (d < 0 and b["h"] >= sl):
            res.append({"i": i, "dir": d, "r": -1.0 - fee_r, "stop_pct": 100 * risk / e})
            busy = i
            continue
        exit_r, k = None, i
        for k in range(i + 1, min(i + 1 + timeout, len(bars))):
            x = bars[k]
            if (d > 0 and x["l"] <= sl) or (d < 0 and x["h"] >= sl):
                exit_r = -1.0
                break
            if (d > 0 and x["h"] >= tp) or (d < 0 and x["l"] <= tp):
                exit_r = abs(tp - e) / risk
                break
        if exit_r is None:
            exit_r = d * (bars[k]["c"] - e) / risk
        res.append({"i": i, "dir": d, "r": exit_r - fee_r, "stop_pct": 100 * risk / e})
        busy = k
    return res


def s_(rs):
    rs = np.asarray(rs, float)
    if len(rs) == 0:
        return {"n": 0}
    sd = rs.std(ddof=1) if len(rs) > 1 else np.nan
    return {"n": int(len(rs)), "win_pct": round(float((rs > 0).mean() * 100), 1), "avg_R": round(float(rs.mean()), 3),
            "sum_R": round(float(rs.sum()), 1), "t": round(float(rs.mean() / sd * np.sqrt(len(rs))), 2) if sd > 0 else None}


def main():
    res = {"readme_window": {}, "full_period_bt_port": {}}
    tot = {"legacy_as_is": [], "legacy_fill_fixed": [], "bt_port_base": [], "bt_port_harsh": []}
    for sym in README5:
        df = load(sym, "5m")
        w = df[(df.index >= W0) & (df.index < W1)]
        bars = bars_of(w)
        leg = LEG.simulate(bars, LEG.signals(bars, fee=0.10), fee=0.10)
        fix = legacy_simulate_fixed(bars, legacy_signals_fixed(bars, fee=0.10), fee=0.10)
        sig = smc.strategy(df)
        tb = A.simulate(df, sig, A.BASE, smc.MAX_HOLD, smc.LIMIT_TTL, sym)
        th = A.simulate(df, sig, A.HARSH, smc.MAX_HOLD, smc.LIMIT_TTL, sym)
        tb = tb[(tb.t_entry >= W0) & (tb.t_entry < W1)]
        th = th[(th.t_entry >= W0) & (th.t_entry < W1)]
        row = {"legacy_as_is": s_([x["r"] for x in leg]), "legacy_fill_fixed": s_([x["r"] for x in fix]),
               "bt_port_base": s_(tb["R"]), "bt_port_harsh": s_(th["R"])}
        tot["legacy_as_is"] += [x["r"] for x in leg]
        tot["legacy_fill_fixed"] += [x["r"] for x in fix]
        tot["bt_port_base"] += list(tb["R"])
        tot["bt_port_harsh"] += list(th["R"])
        res["readme_window"][sym] = row
        print(sym, json.dumps(row), flush=True)
    res["readme_window"]["TOTAL"] = {k: s_(v) for k, v in tot.items()}
    print("TOTAL", json.dumps(res["readme_window"]["TOTAL"]), flush=True)
    for tf in ("5m", "15m"):
        parts = []
        for sym in SYMBOLS:
            df = load(sym, tf)
            parts.append(A.simulate(df, smc.strategy(df), A.BASE, smc.MAX_HOLD, smc.LIMIT_TTL, sym))
        tr = pd.concat(parts, ignore_index=True)
        r = A.is_oos(tr, f"smc {tf}")
        r["per_symbol_OOS_avgR"] = {s: round(float(g[g.t_entry >= pd.Timestamp('2025-01-01', tz='UTC')]["R"].mean()), 3)
                                    for s, g in tr.groupby("symbol")}
        r["t_cluster_day_OOS"] = A.clustered_t(tr[tr.t_entry >= pd.Timestamp("2025-01-01", tz="UTC")])
        res["full_period_bt_port"][tf] = r
        print(tf, json.dumps(r), flush=True)
    with open(os.path.join(OUT, "audit_smc.json"), "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
