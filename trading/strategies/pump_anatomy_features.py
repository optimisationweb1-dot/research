"""pump_anatomy: causal daily features, eligibility, labels, cross-sectional ranks, pump events.

    python3 -m strategies.pump_anatomy_features     -> data/ext/pump_anatomy/panel.parquet, events.csv

Every feature in row (d, sym) uses data up to the close of day d only. fwd_* and y* are future labels.
"""
import os

import numpy as np
import pandas as pd

from strategies.pump_anatomy_panel import INDEX_LIKE, ROOT, TRADFI

MIN_QV_L1, MIN_QV_L2, MIN_AGE = 2e6, 10e6, 30
PUMP_TH, PUMP_H, COOLDOWN = 0.40, 7, 30

FEATS = ["rvol1", "rvol3", "rvol7", "tshare1", "tshare7", "tshare_z", "fund1", "fund7", "vcomp", "rcomp",
         "rs1", "rs3", "rs7", "rs14", "rs30", "age", "size", "dist_hi90", "dist_lo90", "h_rvol_max",
         "h_tshare_max", "ret1", "ret7", "ann14"]


def per_symbol(d):
    d = d.sort_values("date").copy()
    c = d["close"]
    lr = np.log(c).diff()
    for k in (1, 3, 7, 14, 30):
        d[f"ret{k}"] = c / c.shift(k) - 1
    qv = d["quote_vol"]
    d["med30qv"] = qv.shift(1).rolling(30, min_periods=20).median()
    d["rvol1"] = qv / d["med30qv"]
    d["rvol3"] = qv.rolling(3).mean() / qv.shift(3).rolling(30, min_periods=20).median()
    d["rvol7"] = qv.rolling(7).mean() / qv.shift(7).rolling(30, min_periods=20).median()
    ts = (d["buy_quote_vol"] / qv).where(qv > 0)
    d["tshare1"] = ts
    d["tshare7"] = d["buy_quote_vol"].rolling(7).sum() / qv.rolling(7).sum()
    m, s = ts.shift(1).rolling(30, min_periods=20).mean(), ts.shift(1).rolling(30, min_periods=20).std()
    d["tshare_z"] = (ts - m) / s
    d["fund1"] = d["fund_sum"]
    d["fund7"] = d["fund_sum"].rolling(7, min_periods=4).mean()
    v7, v60 = lr.rolling(7).std(), lr.rolling(60, min_periods=30).std()
    d["vcomp"] = v7 / v60
    r7 = (d["high"].rolling(7).max() - d["low"].rolling(7).min()) / c
    r60 = (d["high"].rolling(60, min_periods=30).max() - d["low"].rolling(60, min_periods=30).min()) / c
    d["rcomp"] = r7 / r60
    first = d.loc[c.notna(), "date"].min()
    d["age"] = (d["date"] - first).dt.days
    d["size"] = np.log(d["med30qv"])
    d["dist_hi90"] = c / d["high"].rolling(90, min_periods=1).max() - 1
    d["dist_lo90"] = c / d["low"].rolling(90, min_periods=1).min() - 1
    # execution prices: px_exec[d] = close of first hour of d+1; at the series end use the last close
    px = d["px_exec"].copy()
    last = c.last_valid_index()
    if last is not None and pd.isna(px.loc[last]):
        px.loc[last] = c.loc[last]
    d["px_exec"] = px
    d["r_next"] = px.shift(-1) / px - 1          # return from exec(d) to exec(d+1)   [future]
    d["fund_next"] = d["fund_sum"].shift(-1)     # funding paid during that holding day [future]
    fut = pd.concat([c.shift(-k) for k in range(1, PUMP_H + 1)], axis=1)
    d["fwd_max7"] = fut.max(axis=1, skipna=True) / c - 1
    d.loc[fut.isna().all(axis=1), "fwd_max7"] = np.nan
    d["fwd_ret7_exec"] = px.shift(-7) / px - 1
    d["fwd_ret1_exec"] = d["r_next"]
    d["lr"] = lr
    return d


def add_btc_and_ranks(p):
    btc = p.loc[p["symbol"] == "BTCUSDT", ["date"] + [f"ret{k}" for k in (1, 3, 7, 14, 30)]]
    btc = btc.rename(columns={f"ret{k}": f"btc{k}" for k in (1, 3, 7, 14, 30)})
    p = p.merge(btc, on="date", how="left")
    for k in (1, 3, 7, 14, 30):
        p[f"rs{k}"] = np.log1p(p[f"ret{k}"]) - np.log1p(p[f"btc{k}"])
    return p


def add_announcements(p):
    """ann14: any Binance announcement (listing/delisting catalogs) naming the base asset, published within
    the 14 days up to the close of day d. Base asset match on title tokens '(ASSET)'."""
    a = pd.read_csv(os.path.join(ROOT, "binance_announcements.csv"))
    a["published_utc"] = pd.to_datetime(a["published_utc"], utc=True)
    rows = []
    for _, r in a.iterrows():
        for tok in set(pd.Series(r["title"]).str.findall(r"\(([A-Z0-9]{2,15})\)").iloc[0]):
            rows.append((tok, r["published_utc"], r["catalog"], r["title"]))
    an = pd.DataFrame(rows, columns=["asset", "pub", "catalog", "title"])
    base = p["symbol"].str.replace("USDT$", "", regex=True).str.replace(r"^1000000|^1000|^1M", "", regex=True)
    p["asset"] = base
    # day of publication (a publication at 13:00 on day d is known at the close of day d)
    an["date"] = an["pub"].dt.floor("1D")
    hit = an.groupby(["asset", "date"]).size().rename("ann_n").reset_index()
    p = p.merge(hit, on=["asset", "date"], how="left")
    p["ann_n"] = p["ann_n"].fillna(0)
    p = p.sort_values(["symbol", "date"])
    p["ann14"] = p.groupby("symbol")["ann_n"].transform(lambda x: x.rolling(14, min_periods=1).sum())
    return p


def rank_xs(p, cols, elig="elig"):
    q = p[p[elig]]
    r = q.groupby("date")[cols].rank(pct=True)
    for c in cols:
        p[f"pr_{c}"] = np.nan
        p.loc[r.index, f"pr_{c}"] = r[c]
    return p


def find_events(p, th=PUMP_TH, elig="elig", cooldown=COOLDOWN):
    ev = []
    lab = p["fwd_max7"] >= th
    p = p.assign(_y=lab & p[elig])
    for sym, g in p.groupby("symbol"):
        g = g.sort_values("date")
        y = g["_y"].to_numpy()
        prev_y = np.r_[False, y[:-1]]
        starts = g.loc[y & ~prev_y]
        last = None
        for idx, r in starts.iterrows():
            if last is not None and (r["date"] - last).days < cooldown:
                continue
            last = r["date"]
            ev.append(idx)
    e = p.loc[ev, ["date", "symbol", "close", "fwd_max7", "med30qv", "age"]].copy()
    return e.sort_values("date")


def event_details(p, e):
    """Peak day/magnitude, ignition day (first close >= +20% above base), post-peak drawdown."""
    out = []
    by = {s: g.set_index("date").sort_index() for s, g in p.groupby("symbol")}
    for _, r in e.iterrows():
        g = by[r["symbol"]]
        c0 = r["close"]
        w = g.loc[r["date"]:r["date"] + pd.Timedelta(days=PUMP_H), "close"].iloc[1:]
        peak_d = w.idxmax()
        ign = w[w / c0 >= 1.2]
        after = g.loc[peak_d:peak_d + pd.Timedelta(days=30), "close"]
        c14 = g["close"].get(peak_d + pd.Timedelta(days=14), np.nan)
        c30 = g["close"].get(peak_d + pd.Timedelta(days=30), np.nan)
        out.append({"peak_date": peak_d, "peak_gain": w.max() / c0 - 1,
                    "ign_date": ign.index[0] if len(ign) else pd.NaT,
                    "days_to_peak": (peak_d - r["date"]).days,
                    "ret_peak_to_14d": c14 / w.max() - 1, "ret_peak_to_30d": c30 / w.max() - 1,
                    "base_to_30d_after_peak": c30 / c0 - 1,
                    "min_after_peak_30d": after.min() / w.max() - 1})
    return pd.concat([e.reset_index(drop=True), pd.DataFrame(out)], axis=1)


def build():
    raw = pd.read_parquet(os.path.join(ROOT, "panel_raw.parquet"))
    cls = pd.read_csv(os.path.join(ROOT, "symbol_class.csv"), index_col=0)
    excl = set(INDEX_LIKE) | set(TRADFI)
    raw = raw[~raw["symbol"].isin(excl)]
    raw["date"] = pd.to_datetime(raw["date"], utc=True)
    p = pd.concat([per_symbol(g) for _, g in raw.groupby("symbol")], ignore_index=True)
    p = add_btc_and_ranks(p)
    p = add_announcements(p)
    p["elig"] = (p["age"] >= MIN_AGE) & (p["med30qv"] >= MIN_QV_L1) & p["close"].notna() & (p["n_hours"] >= 20)
    p["elig2"] = p["elig"] & (p["med30qv"] >= MIN_QV_L2)
    p["y7"] = (p["fwd_max7"] >= PUMP_TH).astype(float).where(p["fwd_max7"].notna())
    p = rank_xs(p, FEATS)
    p.to_parquet(os.path.join(ROOT, "panel.parquet"), index=False)
    for th, tag in ((0.40, ""), (0.30, "_30"), (1.00, "_100")):
        e = find_events(p, th)
        e = event_details(p, e)
        e.to_csv(os.path.join(ROOT, f"events{tag}.csv"), index=False)
        print(tag or "_40", len(e))
    e2 = event_details(p, find_events(p, 0.40, elig="elig2"))
    e2.to_csv(os.path.join(ROOT, "events_L2.csv"), index=False)
    print("L2", len(e2))
    return p


if __name__ == "__main__":
    p = build()
    print(p.shape, p["elig"].sum(), p.loc[p["elig"], "symbol"].nunique())
