"""Causal features for the Coinbase-premium study (shared by analysis and strategies).

Input: hourly premium table (strategies.coinbase_premium_data.build), index = candle START ts (UTC);
the row at ts is known at ts + 1h (hour close). Every feature at row t uses rows <= t only.
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT = os.path.join(HERE, "data", "ext", "coinbase_premium")
Z_WIN = 720  # 30 days of hours


def zroll(x, n=Z_WIN):
    m = x.rolling(n, min_periods=n // 2).mean()
    s = x.rolling(n, min_periods=n // 2).std()
    return (x - m) / s


def features(p, a):
    """Signals for asset a in {'btc','eth','sol'} from the hourly premium table p."""
    f = pd.DataFrame(index=p.index)
    prem, raw = p[f"prem_{a}"], p[f"prem_raw_{a}"]
    usdt_dev = p["usdt"] - 1
    # rolling means tolerate a few missing hours (min_periods) - no forward fill of prices
    f["prem"] = prem
    f["P24"] = prem.rolling(24, min_periods=18).mean()
    f["P24raw"] = raw.rolling(24, min_periods=18).mean()
    f["L"] = zroll(f["P24"])
    f["R"] = zroll(f["P24raw"])
    f["D"] = zroll(f["P24"] - f["P24"].shift(24))
    f["P"] = (prem > 0).astype(float).where(prem.notna()).rolling(72, min_periods=54).mean() - 0.5
    f["U"] = zroll(usdt_dev.rolling(24, min_periods=18).mean())
    f["P168"] = prem.rolling(168, min_periods=120).mean()
    f["W"] = (f["P168"] - f["P168"].rolling(2160, min_periods=1080).mean()) / \
        f["P168"].rolling(2160, min_periods=1080).std()  # 7d mean vs 90d
    f["basis"] = p[f"basis_{a}"].rolling(24, min_periods=18).mean()
    return f


def load_table():
    return pd.read_parquet(os.path.join(EXT, "premium_1h.parquet"))


def merge_into(df, a, cols=("P24", "P24raw", "L", "R", "D", "P", "U"), lag_hours=0):
    """Attach hourly features to bars df (bt.data.load frame) as known at each bar's CLOSE.

    Feature row ts is known at ts + 1h (+ lag_hours). Uses merge_asof backward on close_time.
    """
    f = features(load_table(), a)
    f = f[list(cols)].copy()
    f["avail"] = f.index + pd.Timedelta(hours=1 + lag_hours)
    left = pd.DataFrame({"close_time": df["close_time"]})
    left["open_ts"] = df.index
    left = left.reset_index(drop=True)
    m = pd.merge_asof(left.sort_values("close_time"), f.sort_values("avail"), left_on="close_time",
                      right_on="avail", direction="backward")
    m.index = m["open_ts"]
    out = df.copy()
    for c in cols:
        out["cbp_" + c] = m[c].reindex(out.index).values
    # staleness guard: if the latest premium row is older than 3h at bar close, treat as unknown
    age = (pd.to_datetime(m["close_time"]) - m["avail"]).reindex(out.index)
    stale = (age > pd.Timedelta(hours=3)).to_numpy()
    for c in cols:
        out.loc[stale, "cbp_" + c] = np.nan
    return out


def etf_daily(asset):
    """Daily US spot ETF net flows (USD) from the treasury_flows agent's CSV (read-only)."""
    path = os.path.join(HERE, "research", f"treasury_flows_etf_{asset}.csv")
    e = pd.read_csv(path, parse_dates=["date"])
    e["date"] = pd.to_datetime(e["date"]).dt.tz_localize("UTC")
    return e.set_index("date")["total_usd"].astype(float)


def merge_etf(df, asset, known_days=2):
    """Last ETF flow known at bar close: flow of day D known from 00:00 UTC of D+known_days."""
    s = etf_daily(asset)
    e = pd.DataFrame({"flow": s.values, "flow_day": s.index, "avail": s.index + pd.Timedelta(days=known_days)})
    left = pd.DataFrame({"close_time": df["close_time"]})
    left["open_ts"] = df.index
    left = left.reset_index(drop=True)
    m = pd.merge_asof(left.sort_values("close_time"), e.sort_values("avail"), left_on="close_time",
                      right_on="avail", direction="backward")
    m.index = m["open_ts"]
    out = df.copy()
    out["etf_flow"] = m["flow"].reindex(out.index).values
    out["etf_flow_day"] = m["flow_day"].reindex(out.index).values
    return out
