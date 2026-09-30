#!/usr/bin/env python3
"""Backtest of strategy D (SMC): sweep -> CHoCH -> retrace into 0.5-0.786 zone with FVG.

Mirrors pine/smc_volume_gex.pine. Conservative fills: limit entry at zone price when
touched; if SL and TP are inside the same bar, SL is assumed first. Fees are charged
on every trade. Result in R (1R = risk to stop) and % of equity at fixed risk.

Usage:
    python3 smc_backtest.py BTCUSDT --tf 5m --months 2026-03 2026-04 2026-05 2026-06 2026-07 2026-08
"""
import argparse
import statistics

from volume_anomaly import enrich, fetch_vision, to_bars


def atr(bars, n=14):
    out, prev = [], None
    for b in bars:
        tr = b["h"] - b["l"] if prev is None else max(b["h"] - b["l"], abs(b["h"] - prev), abs(b["l"] - prev))
        out.append(tr if not out else out[-1] + (tr - out[-1]) / n)
        prev = b["c"]
    return out


def signals(bars, piv=5, z0=0.5, z1=0.786, ext=1.272, buf=0.3, fee=0.10, min_rr=2.0, need_fvg=True,
            vol_filter=False):
    A = atr(bars)
    swing_h = swing_l = None
    st = {+1: {"s": 0}, -1: {"s": 0}}
    out = []
    for i in range(2 * piv + 2, len(bars)):
        # confirmed pivots (piv bars ago)
        j = i - piv
        win = bars[j - piv:j + piv + 1]
        if bars[j]["h"] == max(x["h"] for x in win):
            swing_h = bars[j]["h"]
        if bars[j]["l"] == min(x["l"] for x in win):
            swing_l = bars[j]["l"]
        b = bars[i]
        vol_ok = (not vol_filter) or (b.get("rvol") or 0) >= 2.0
        # sweeps
        if swing_l is not None and b["l"] < swing_l < b["c"] and vol_ok:
            st[+1] = {"s": 1, "lo": b["l"], "choch": swing_h, "fvg": None}
        if swing_h is not None and b["h"] > swing_h > b["c"] and vol_ok:
            st[-1] = {"s": 1, "hi": b["h"], "choch": swing_l, "fvg": None}
        # long side
        L = st[+1]
        if L["s"] == 1:
            L["lo"] = min(L["lo"], b["l"])
            if L["choch"] is not None and b["c"] > L["choch"]:
                L.update(s=2, hi=b["h"])
        elif L["s"] == 2:
            # zone and FVG use only bars before i; bar i may only fill the limit order
            leg = L["hi"] - L["lo"]
            zhi, zlo = L["hi"] - leg * z0, L["hi"] - leg * z1
            fvg = L["fvg"]
            in_zone = fvg and fvg[0] <= zhi and fvg[1] >= zlo
            entry = (min(zhi, fvg[1]) if need_fvg and fvg else zhi)
            if (in_zone or not need_fvg) and b["l"] < entry:  # a resting limit fills on any trade through it
                sl = L["lo"] - buf * A[i]
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
        # short side
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
            entry = (max(zlo, fvg[0]) if need_fvg and fvg else zlo)
            if (in_zone or not need_fvg) and b["h"] > entry:
                sl = S["hi"] + buf * A[i]
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


def simulate(bars, sigs, fee=0.10, timeout=96):
    res = []
    busy_until = -1
    for i, d, e, sl, tp in sigs:
        if i <= busy_until:
            continue  # one position at a time
        risk = abs(e - sl)
        fee_r = e * fee / 100 / risk
        if (d > 0 and bars[i]["l"] <= sl) or (d < 0 and bars[i]["h"] >= sl):  # stopped on the fill bar
            res.append({"i": i, "dir": d, "r": -1.0 - fee_r, "stop_pct": 100 * risk / e})
            busy_until = i
            continue
        exit_r, k = None, i
        for k in range(i + 1, min(i + 1 + timeout, len(bars))):
            b = bars[k]
            hit_sl = b["l"] <= sl if d > 0 else b["h"] >= sl
            hit_tp = b["h"] >= tp if d > 0 else b["l"] <= tp
            if hit_sl:
                exit_r = -1.0
                break
            if hit_tp:
                exit_r = abs(tp - e) / risk
                break
        if exit_r is None:
            exit_r = d * (bars[k]["c"] - e) / risk
        res.append({"i": i, "dir": d, "r": exit_r - fee_r, "stop_pct": 100 * risk / e})
        busy_until = k
    return res


def report(name, res, risk_pct=0.5):
    if not res:
        print(f"{name}: no trades")
        return
    rs = [x["r"] for x in res]
    wins = sum(r > 0 for r in rs)
    eq, peak, dd = 1.0, 1.0, 0.0
    for r in rs:
        eq *= 1 + r * risk_pct / 100
        peak = max(peak, eq)
        dd = max(dd, 1 - eq / peak)
    print(f"{name:28s} trades {len(rs):4d}  win {100*wins/len(rs):4.0f}%  avg {statistics.mean(rs):+.3f}R  "
          f"sum {sum(rs):+7.1f}R  equity@{risk_pct}% {100*(eq-1):+6.1f}%  maxDD {100*dd:4.1f}%  "
          f"median stop {statistics.median(x['stop_pct'] for x in res):.2f}%")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol", nargs="?", default="BTCUSDT")
    ap.add_argument("--tf", default="5m")
    ap.add_argument("--months", nargs="+", default=["2026-08"])
    ap.add_argument("--fee", type=float, default=0.10)
    a = ap.parse_args()
    bars = enrich(to_bars(fetch_vision(a.symbol, a.tf, a.months)))
    print(f"{a.symbol} {a.tf} {a.months[0]}..{a.months[-1]}  bars={len(bars)}  fee={a.fee}% round trip")
    for label, kw in [("D: base (FVG, RR>=2)", {}),
                      ("D: + volume on sweep", {"vol_filter": True}),
                      ("D: RR>=3", {"min_rr": 3.0})]:
        report(label, simulate(bars, signals(bars, fee=a.fee, **kw), fee=a.fee))
    report("D: base, maker fees 0.04%", simulate(bars, signals(bars, fee=0.04), fee=0.04))


if __name__ == "__main__":
    main()
