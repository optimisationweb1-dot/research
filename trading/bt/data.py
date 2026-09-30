"""Historical data cache for backtests (Binance USD-M futures + Deribit DVOL).

All public, no keys. Stored as parquet under trading/data/ (gitignored).

    python3 -m bt.data download              # default universe and period
    python3 -m bt.data download --symbols BTCUSDT ETHUSDT --start 2023-01 --end 2026-08

Loaded frames are indexed by bar OPEN time (UTC). Columns:
    open high low close volume quote_vol trades buy_vol sell_vol delta close_time
Every derived/external column is aligned so that its value is known at the bar's
CLOSE time (see merge_* helpers) - strategies may use row t only after bar t closes.
"""
import argparse
import io
import os
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import numpy as np
import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
VISION = "https://data.binance.vision/data/futures/um"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
           "BNBUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "LTCUSDT"]
START, END = "2023-01", "2026-08"
METRICS_START = "2024-01"
TF_MIN = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}
KCOLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_vol",
         "trades", "buy_vol", "buy_quote_vol", "ignore"]


def months(start, end):
    y, m = map(int, start.split("-"))
    ye, me = map(int, end.split("-"))
    out = []
    while (y, m) <= (ye, me):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except Exception:
            pass
    return None


def _read_zip_csv(raw, **kw):
    z = zipfile.ZipFile(io.BytesIO(raw))
    return pd.read_csv(z.open(z.namelist()[0]), **kw)


def _klines_month(symbol, tf, m):
    raw = _get(f"{VISION}/monthly/klines/{symbol}/{tf}/{symbol}-{tf}-{m}.zip")
    if raw is None:
        return None
    df = _read_zip_csv(raw, header=None)
    if not str(df.iloc[0, 0]).isdigit():  # header row present in newer files
        df = df.iloc[1:]
    df.columns = KCOLS
    return df


def download_klines(symbol, tf, start=START, end=END):
    path = os.path.join(ROOT, "klines", tf, f"{symbol}.parquet")
    if os.path.exists(path):
        return path
    with ThreadPoolExecutor(8) as ex:
        parts = [p for p in ex.map(lambda m: _klines_month(symbol, tf, m), months(start, end)) if p is not None]
    if not parts:
        return None
    df = pd.concat(parts)
    for c in KCOLS[:-1]:
        df[c] = pd.to_numeric(df[c])
    df = df.drop(columns=["ignore", "buy_quote_vol"]).drop_duplicates("open_time").sort_values("open_time")
    live = df.loc[df["volume"] > 0, "open_time"]
    if len(live):  # data.binance.vision keeps writing flat zero-volume bars after a delisting
        df = df[df["open_time"] <= live.max()]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_parquet(path, index=False)
    return path


def _metrics_day(symbol, d):
    raw = _get(f"{VISION}/daily/metrics/{symbol}/{symbol}-metrics-{d}.zip")
    return None if raw is None else _read_zip_csv(raw)


def download_metrics(symbol, start=METRICS_START, end=END):
    path = os.path.join(ROOT, "metrics", f"{symbol}.parquet")
    if os.path.exists(path):
        return path
    y, m = map(int, start.split("-"))
    ye, me = map(int, end.split("-"))
    d0 = date(y, m, 1)
    d1 = (date(ye + (me == 12), me % 12 + 1, 1) - timedelta(days=1))
    days = [(d0 + timedelta(days=i)).isoformat() for i in range((d1 - d0).days + 1)]
    with ThreadPoolExecutor(16) as ex:
        parts = [p for p in ex.map(lambda d: _metrics_day(symbol, d), days) if p is not None]
    if not parts:
        return None
    df = pd.concat(parts)
    df["ts"] = pd.to_datetime(df["create_time"], utc=True)
    df = df.drop(columns=["create_time", "symbol"]).drop_duplicates("ts").sort_values("ts")
    for c in df.columns:
        if c != "ts":
            df[c] = pd.to_numeric(df[c], errors="coerce")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_parquet(path, index=False)
    return path


def download_funding(symbol, start=START, end=END):
    path = os.path.join(ROOT, "funding", f"{symbol}.parquet")
    if os.path.exists(path):
        return path
    parts = []
    for m in months(start, end):
        raw = _get(f"{VISION}/monthly/fundingRate/{symbol}/{symbol}-fundingRate-{m}.zip")
        if raw is not None:
            parts.append(_read_zip_csv(raw))
    if not parts:
        return None
    df = pd.concat(parts)
    df["ts"] = pd.to_datetime(pd.to_numeric(df["calc_time"]), unit="ms", utc=True)
    df = df[["ts", "last_funding_rate"]].rename(columns={"last_funding_rate": "funding"})
    df["funding"] = pd.to_numeric(df["funding"])
    df = df.drop_duplicates("ts").sort_values("ts")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_parquet(path, index=False)
    return path


def download_dvol(currency, start=START, end=END):
    """Deribit DVOL (30d implied vol index), hourly candles."""
    import json
    path = os.path.join(ROOT, "dvol", f"{currency}.parquet")
    if os.path.exists(path):
        return path
    t0 = int(pd.Timestamp(start + "-01", tz="UTC").timestamp() * 1000)
    t1 = int((pd.Timestamp(end + "-01", tz="UTC") + pd.offsets.MonthEnd(1) + pd.Timedelta(days=1)).timestamp() * 1000)
    rows, cur = [], t0
    while cur < t1:
        nxt = min(cur + 1000 * 3600 * 1000, t1)
        url = (f"https://www.deribit.com/api/v2/public/get_volatility_index_data?currency={currency}"
               f"&start_timestamp={cur}&end_timestamp={nxt}&resolution=3600")
        raw = _get(url)
        if raw:
            rows += json.loads(raw)["result"]["data"]
        cur = nxt
    df = pd.DataFrame(rows, columns=["t", "dvol_open", "dvol_high", "dvol_low", "dvol"])
    df["ts"] = pd.to_datetime(df["t"], unit="ms", utc=True)
    df = df.drop(columns=["t"]).drop_duplicates("ts").sort_values("ts")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_parquet(path, index=False)
    return path


# ---------------------------------------------------------------- loading

def load(symbol, tf="5m", start=None, end=None, metrics=False, funding=False, dvol=False):
    """Bars indexed by open time (UTC). tf in 1m/5m/15m/1h/4h/1d.

    1m and 5m are stored; larger timeframes are resampled from 5m so taker volume
    aggregates exactly. External series are merged as-of the bar CLOSE time.
    """
    base = "1m" if tf == "1m" else "5m"
    path = os.path.join(ROOT, "klines", base, f"{symbol}.parquet")
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} - run: python3 -m bt.data download --symbols {symbol} --tfs {base}")
    df = pd.read_parquet(path)
    df.index = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.drop(columns=["open_time", "close_time"])
    if tf not in ("1m", "5m"):
        rule = {"15m": "15min", "1h": "1h", "4h": "4h", "1d": "1D"}[tf]
        df = df.resample(rule, label="left", closed="left").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum",
             "quote_vol": "sum", "trades": "sum", "buy_vol": "sum"}).dropna(subset=["open"])
    df["sell_vol"] = df["volume"] - df["buy_vol"]
    df["delta"] = df["buy_vol"] - df["sell_vol"]
    df["close_time"] = df.index + pd.Timedelta(minutes=TF_MIN[tf])
    if start:
        df = df[df.index >= pd.Timestamp(start, tz="UTC")]
    if end:
        df = df[df.index < pd.Timestamp(end, tz="UTC")]
    if metrics:
        df = merge_metrics(df, symbol)
    if funding:
        df = merge_funding(df, symbol)
    if dvol:
        cur = "ETH" if symbol.startswith("ETH") else "BTC"
        df = merge_dvol(df, cur)
    return df


def _asof(df, ext, cols, avail_col="avail"):
    """Attach ext[cols] known at df.close_time (ext[avail_col] <= close_time)."""
    ns_utc = lambda x: pd.DatetimeIndex(x).tz_convert("UTC").as_unit("ns")
    left = pd.DataFrame({"open_ts": df.index, "close_time": ns_utc(df["close_time"])})
    right = ext[[avail_col] + cols].copy()
    right[avail_col] = ns_utc(right[avail_col])
    right = right.sort_values(avail_col)
    m = pd.merge_asof(left.sort_values("close_time"), right, left_on="close_time", right_on=avail_col,
                      direction="backward")
    m.index = m["open_ts"]
    out = df.copy()
    for c in cols:
        out[c] = m[c].reindex(out.index).values
    return out


def merge_metrics(df, symbol):
    path = os.path.join(ROOT, "metrics", f"{symbol}.parquet")
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    mt = pd.read_parquet(path)
    # the row stamped T describes the window [T, T+5) (its taker ratio matches the 5m kline opening at T,
    # corr 0.93-0.97), so it is not known before T+5; +1 minute publication latency [estimate]
    mt["avail"] = mt["ts"] + pd.Timedelta(minutes=6)
    mt.loc[mt["sum_open_interest"] <= 0, ["sum_open_interest", "sum_open_interest_value"]] = np.nan
    cols = ["sum_open_interest", "sum_open_interest_value", "count_toptrader_long_short_ratio",
            "sum_toptrader_long_short_ratio", "count_long_short_ratio", "sum_taker_long_short_vol_ratio"]
    out = _asof(df, mt, cols)
    return out.rename(columns={"sum_open_interest": "oi", "sum_open_interest_value": "oi_usd",
                               "count_toptrader_long_short_ratio": "top_ls_accounts",
                               "sum_toptrader_long_short_ratio": "top_ls_positions",
                               "count_long_short_ratio": "ls_accounts",
                               "sum_taker_long_short_vol_ratio": "taker_ls_ratio"})


def merge_funding(df, symbol):
    path = os.path.join(ROOT, "funding", f"{symbol}.parquet")
    fr = pd.read_parquet(path)
    fr["avail"] = fr["ts"]
    return _asof(df, fr, ["funding"])


def merge_dvol(df, currency):
    path = os.path.join(ROOT, "dvol", f"{currency}.parquet")
    dv = pd.read_parquet(path)
    dv["avail"] = dv["ts"] + pd.Timedelta(hours=1)  # hourly candle closes 1h after its stamp
    return _asof(df, dv, ["dvol"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["download"])
    ap.add_argument("--symbols", nargs="+", default=SYMBOLS)
    ap.add_argument("--tfs", nargs="+", default=["5m"])
    ap.add_argument("--start", default=START)
    ap.add_argument("--end", default=END)
    ap.add_argument("--no-metrics", action="store_true")
    a = ap.parse_args()
    for s in a.symbols:
        for tf in a.tfs:
            print(s, tf, download_klines(s, tf, a.start, a.end), flush=True)
        print(s, "funding", download_funding(s, a.start, a.end), flush=True)
        if not a.no_metrics:
            print(s, "metrics", download_metrics(s, max(METRICS_START, a.start), a.end), flush=True)
    for c in ("BTC", "ETH"):
        print(c, "dvol", download_dvol(c, a.start, a.end), flush=True)


if __name__ == "__main__":
    main()
