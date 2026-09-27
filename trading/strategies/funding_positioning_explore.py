"""IN-SAMPLE-ONLY exploration for the funding_positioning family (no OOS data is touched).

Computes causal features on 4h/1h bars and their rank IC with forward vol-normalized returns,
restricted to bars whose forward window ends before 2025-01-01. Used only to fix signal
directions a priori; disclosed in results/funding_positioning.md as part of multiple testing.

    cd trading && python3 -m strategies.funding_positioning_explore
"""
import json

import numpy as np
import pandas as pd

import strategies.funding_positioning as F
from bt.data import SYMBOLS, load

IS_END = pd.Timestamp("2025-01-01", tz="UTC")


def feats(df):
    lc = np.log(df["close"])
    b24, b72 = F.bars(df, 24), F.bars(df, 72)
    r1 = lc.diff()
    vol = r1.rolling(F.bars(df, 24 * 30), min_periods=50).std()
    X = pd.DataFrame(index=df.index)
    X["past24"] = (lc - lc.shift(b24)) / (vol * np.sqrt(b24))
    X["past72"] = (lc - lc.shift(b72)) / (vol * np.sqrt(b72))
    X["fz"] = F.funding_z(df)
    X["flev"] = df["funding"].rolling(b24, min_periods=1).mean()
    X["div"] = F.top_crowd_div(df)
    n30 = F.bars(df, 24 * 30)
    X["crowd_lvl"] = F.roll_z(F.logpos(df["ls_accounts"]), n30)
    X["top_lvl"] = F.roll_z(F.logpos(df["top_ls_positions"]), n30)
    X["dcrowd24"] = F.roll_z(F.logpos(df["ls_accounts"]).diff(b24), n30)
    X["dtop24"] = F.roll_z(F.logpos(df["top_ls_positions"]).diff(b24), n30)
    X["cres"] = F.roll_z(F.crowd_residual(df), n30)
    X["oiz72"] = F.oi_chg_z(df)
    X["fwd24"] = (lc.shift(-b24) - lc) / (vol * np.sqrt(b24))
    X["fwd72"] = (lc.shift(-b72) - lc) / (vol * np.sqrt(b72))
    X["fwd_end"] = df.index + pd.Timedelta(hours=72) + pd.Timedelta(minutes=F.bar_minutes(df))
    return X


def main():
    out = {}
    for tf in ("4h", "1h"):
        parts = []
        for s in SYMBOLS:
            df = load(s, tf, metrics=True, funding=True)
            X = feats(df)
            X = X[X["fwd_end"] < IS_END].drop(columns="fwd_end")   # IS only, forward window inside IS
            X["symbol"], X["year"] = s, X.index.year
            parts.append(X)
        P = pd.concat(parts)
        fcols = ["past24", "past72", "fz", "flev", "div", "crowd_lvl", "top_lvl", "dcrowd24", "dtop24",
                 "cres", "oiz72"]
        res = {}
        for y in (2023, 2024):
            Q = P[P["year"] == y]
            r = {}
            for fcol in fcols:
                q = Q[list(dict.fromkeys([fcol, "fwd24", "fwd72", "past24", "past72", "symbol"]))].dropna()
                if len(q) < 500:
                    continue
                ic24 = q[fcol].rank().corr(q["fwd24"].rank())
                ic72 = q[fcol].rank().corr(q["fwd72"].rank())
                # sign consistency per symbol (fwd72)
                pos = sum(g[fcol].rank().corr(g["fwd72"].rank()) > 0 for _, g in q.groupby("symbol"))
                # correlation with the past move (how mechanical is the feature)
                cp = q[fcol].rank().corr(q["past72"].rank())
                # tails: mean fwd72 when feature in top/bottom 5% (per-symbol pooled quantiles)
                hi = q[fcol] >= q.groupby("symbol")[fcol].transform(lambda x: x.quantile(0.95))
                lo = q[fcol] <= q.groupby("symbol")[fcol].transform(lambda x: x.quantile(0.05))
                r[fcol] = {"n": int(len(q)), "ic24": round(ic24, 4), "ic72": round(ic72, 4),
                           "sym_pos_ic72": int(pos), "corr_past72": round(cp, 3),
                           "fwd72_top5": round(float(q.loc[hi, "fwd72"].mean()), 3),
                           "fwd72_bot5": round(float(q.loc[lo, "fwd72"].mean()), 3),
                           "fwd72_all": round(float(q["fwd72"].mean()), 3)}
            res[str(y)] = r
        out[tf] = res
        print(tf, json.dumps(res, indent=1))
    with open("results/funding_positioning_is_explore.json", "w") as f:
        json.dump({"note": "IN-SAMPLE ONLY (forward window ends before 2025-01-01). Rank IC of feature "
                           "vs forward vol-normalized log return; fwd72_top5/bot5 = mean forward 72h "
                           "normalized return when the feature is in its per-symbol top/bottom 5%.",
                   "results": out}, f, indent=1)


if __name__ == "__main__":
    main()
