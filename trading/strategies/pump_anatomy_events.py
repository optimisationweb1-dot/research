"""pump_anatomy: event studies H12 (narrative contagion via correlation peers), H12b (after a +20% day),
H13 (Binance announcements, entry 1h+ after publication).

    python3 -m strategies.pump_anatomy_events contagion
    python3 -m strategies.pump_anatomy_events announce
"""
import json
import os
import sys

import numpy as np
import pandas as pd

from strategies.pump_anatomy_analysis import IS_END, RES, RNG, load_panel, week_block_boot
from strategies.pump_anatomy_panel import ROOT, load_1h

IGN_TH = 0.20
HS = (1, 3, 7)


def cum_abn(p):
    """Wide matrices: cumulative log return of exec-to-exec and EW-market-adjusted version."""
    r = p.pivot_table(index="date", columns="symbol", values="r_next", aggfunc="first").sort_index()
    el = p.pivot_table(index="date", columns="symbol", values="elig", aggfunc="first").reindex(r.index).fillna(False).astype(bool)
    lr = np.log1p(r)
    mkt = lr.where(el).mean(1)
    abn = lr.sub(mkt, axis=0)
    return lr, abn, el


def fwd_sum(mat, h):
    """sum of rows d..d+h-1 (returns earned from exec(d) to exec(d+h)), aligned at d."""
    return mat[::-1].rolling(h, min_periods=h).sum()[::-1]


def run_contagion():
    p = load_panel(["date", "symbol", "elig", "r_next", "ret1", "lr", "close"])
    lr, abn, el = cum_abn(p)
    dl = p.pivot_table(index="date", columns="symbol", values="lr", aggfunc="first").reindex(lr.index)
    F = {h: fwd_sum(abn, h) for h in HS}
    q = p[p["elig"] & (p["ret1"] >= IGN_TH)].sort_values(["symbol", "date"])
    # first ignition in 7 days
    q = q[q.groupby("symbol")["date"].diff().dt.days.fillna(999) > 7]
    rows = []
    dates = lr.index
    pos = {d: i for i, d in enumerate(dates)}
    for _, ev in q.iterrows():
        d, x = ev["date"], ev["symbol"]
        i = pos[d]
        if i < 60:
            continue
        win = dl.iloc[i - 60:i]
        elig_today = el.iloc[i]
        cands = [c for c in win.columns if c != x and elig_today.get(c, False)]
        if len(cands) < 20 or x not in win:
            continue
        W = win[cands]
        ok = W.notna().sum() >= 40
        W = W.loc[:, ok]
        if W.shape[1] < 20 or win[x].notna().sum() < 40:
            continue
        corr = W.corrwith(win[x]).dropna().sort_values(ascending=False)
        peers = list(corr.index[:5])
        low = list(corr.index[-5:])
        rnd = list(RNG.choice(corr.index, size=5, replace=False))
        rec = {"date": d, "symbol": x, "ret1": ev["ret1"], "peer_corr_mean": float(corr.iloc[:5].mean())}
        for h in HS:
            fh = F[h].iloc[i]
            rec[f"self_abn{h}"] = fh.get(x, np.nan)
            rec[f"peer_abn{h}"] = float(np.nanmean(fh[peers]))
            rec[f"low_abn{h}"] = float(np.nanmean(fh[low]))
            rec[f"rnd_abn{h}"] = float(np.nanmean(fh[rnd]))
        # peers' same-day return (already realised when we trade) - co-movement check
        rec["peer_ret_day0"] = float(np.nanmean(dl.iloc[i][peers]))
        rows.append(rec)
    ev = pd.DataFrame(rows)
    ev.to_csv(os.path.join(RES, "pump_anatomy_contagion_events.csv"), index=False)
    wk = ev["date"].dt.tz_localize(None).dt.to_period("W").astype(str).to_numpy()
    out = []
    for per, m in (("IS", ev["date"] < IS_END), ("OOS", ev["date"] >= IS_END), ("all", ev["date"].notna())):
        for h in HS:
            for grp in ("self", "peer", "low", "rnd"):
                v = ev.loc[m, f"{grp}_abn{h}"].to_numpy()
                se = week_block_boot(v, wk[m.to_numpy()], n=1000)
                mu = float(np.nanmean(v))
                out.append({"period": per, "h": h, "group": grp, "n": int(np.isfinite(v).sum()),
                            "mean_abn_log_pct": round(100 * mu, 3), "median_pct": round(100 * float(np.nanmedian(v)), 3),
                            "se_pct": round(100 * se, 3), "t_block": round(mu / se, 2) if se else None,
                            "hit_pct": round(100 * float(np.nanmean(v > 0)), 1)})
            d = (ev.loc[m, f"peer_abn{h}"] - ev.loc[m, f"rnd_abn{h}"]).to_numpy()
            se = week_block_boot(d, wk[m.to_numpy()], n=1000)
            out.append({"period": per, "h": h, "group": "peer_minus_rnd", "n": int(np.isfinite(d).sum()),
                        "mean_abn_log_pct": round(100 * float(np.nanmean(d)), 3), "se_pct": round(100 * se, 3),
                        "t_block": round(float(np.nanmean(d)) / se, 2) if se else None})
    out = pd.DataFrame(out)
    out.to_csv(os.path.join(RES, "pump_anatomy_contagion.csv"), index=False)
    print(len(ev), "ignitions")
    with pd.option_context("display.width", 200, "display.max_rows", 200):
        print(out.to_string())


# ------------------------------------------------------------------ H13 announcements
def categorize(t):
    tl = t.lower()
    if "monitoring tag" in tl:
        return "monitoring_tag"
    if "delist" in tl or "cease" in tl:
        return "delist"
    if "futures will launch" in tl or "perpetual" in tl or "delivery contract" in tl:
        return "futures_launch"
    if "hodler" in tl:
        return "hodler"
    if "launchpool" in tl or "megadrop" in tl or "launchpad" in tl:
        return "launchpool"
    if "alpha" in tl:
        return "alpha"
    if "will list" in tl:
        return "spot_list"
    if "will add" in tl and ("margin" in tl or "earn" in tl or "convert" in tl):
        return "add_margin_earn"
    return "other"


def run_announce():
    a = pd.read_csv(os.path.join(ROOT, "binance_announcements.csv"))
    a["pub"] = pd.to_datetime(a["published_utc"], utc=True)
    a = a[(a["pub"] >= "2023-01-01") & (a["pub"] < "2026-08-25")]
    a["cat"] = a["title"].map(categorize)
    rows = []
    for _, r in a.iterrows():
        for tok in set(pd.Series(r["title"]).str.findall(r"\(([A-Z0-9]{2,15})\)").iloc[0]):
            rows.append({**r.to_dict(), "asset": tok})
    an = pd.DataFrame(rows)
    syms = pd.read_csv(os.path.join(ROOT, "symbols_use.csv"))["symbol"]
    m = {}
    for s in syms:
        b = s[:-4]
        for pre in ("1000000", "1000", "1M"):
            if b.startswith(pre) and len(b) > len(pre) + 1:
                b = b[len(pre):]
        m.setdefault(b, s)
    an["symbol"] = an["asset"].map(m)
    an = an.dropna(subset=["symbol"])
    btc = load_1h("BTCUSDT")["close"]
    btc_o = load_1h("BTCUSDT")["open"]
    cache = {}
    out = []
    for _, r in an.iterrows():
        s = r["symbol"]
        if s not in cache:
            cache[s] = load_1h(s)
        h = cache[s]
        if h is None:
            continue
        pub = r["pub"]
        t_in = pub.ceil("1h") + pd.Timedelta(hours=1)       # entry bar open: 1-2h after publication
        t_pre = pub.floor("1h")
        if h.index.min() > pub - pd.Timedelta(days=3) or t_in not in h.index or t_pre not in h.index:
            continue   # perp must already trade >= 3 days before the announcement
        e_px = h.at[t_in, "open"]
        pre_px = h.at[t_pre, "open"]
        rec = {"pub": pub, "cat": r["cat"], "symbol": s, "title": r["title"], "url": r["url"],
               "react_pub_to_entry": e_px / pre_px - 1}
        t7 = t_pre - pd.Timedelta(days=7)
        if t7 in h.index:
            rec["pre7d"] = pre_px / h.at[t7, "open"] - 1
            if t7 in btc_o.index and t_pre in btc_o.index:
                rec["pre7d_abn"] = np.log(rec["pre7d"] + 1) - np.log(btc_o[t_pre] / btc_o[t7])
        for hh in (24, 72, 168):
            t_out = t_in + pd.Timedelta(hours=hh)
            if t_out in h.index and t_out in btc_o.index and t_in in btc_o.index:
                x = h.at[t_out, "open"] / e_px
                b = btc_o[t_out] / btc_o[t_in]
                rec[f"ret{hh}h"] = x - 1
                rec[f"abn{hh}h"] = np.log(x) - np.log(b)
        out.append(rec)
    ev = pd.DataFrame(out)
    ev.to_csv(os.path.join(RES, "pump_anatomy_announce_events.csv"), index=False)
    ev["day"] = ev["pub"].dt.floor("1D")
    res = []
    for cat, g in ev.groupby("cat"):
        for per, m in (("IS", g["pub"] < IS_END), ("OOS", g["pub"] >= IS_END), ("all", g["pub"].notna())):
            gg = g[m]
            if len(gg) < 3:
                continue
            rec = {"cat": cat, "period": per, "n": len(gg),
                   "react_pub_to_entry_mean_pct": round(100 * gg["react_pub_to_entry"].mean(), 2),
                   "pre7d_abn_mean_pct": round(100 * gg.get("pre7d_abn", pd.Series(dtype=float)).mean(), 2)}
            for hh in (24, 72, 168):
                v = gg[f"abn{hh}h"]
                # cluster by day: average per day first
                dd = gg.groupby("day")[f"abn{hh}h"].mean().dropna()
                t = dd.mean() / dd.std(ddof=1) * np.sqrt(len(dd)) if len(dd) > 2 and dd.std() > 0 else np.nan
                rec[f"abn{hh}h_mean_pct"] = round(100 * v.mean(), 2)
                rec[f"abn{hh}h_median_pct"] = round(100 * v.median(), 2)
                rec[f"abn{hh}h_t_dayclust"] = round(t, 2) if np.isfinite(t) else None
                rec[f"abn{hh}h_hit_pct"] = round(100 * (v > 0).mean(), 1)
            res.append(rec)
    res = pd.DataFrame(res)
    res.to_csv(os.path.join(RES, "pump_anatomy_announce.csv"), index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(res.to_string())


if __name__ == "__main__":
    {"contagion": run_contagion, "announce": run_announce}[sys.argv[1]]()
