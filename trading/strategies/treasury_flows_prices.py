"""Prices for the treasury_flows study: cached Binance USD-M 5m (bt.data) + September 2026 daily 5m files
from data.binance.vision (stored in trading/data/ext/treasury_flows/klines_5m_<SYM>_2026-09.parquet)."""
import io
import os
import sys
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TR = os.path.dirname(HERE)
sys.path.insert(0, TR)
from bt.data import KCOLS, load  # noqa: E402

EXT = os.path.join(TR, "data", "ext", "treasury_flows")
VISION = "https://data.binance.vision/data/futures/um/daily/klines"


def _day(sym, d):
    url = f"{VISION}/{sym}/5m/{sym}-5m-{d}.zip"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            raw = r.read()
    except Exception:
        return None
    df = pd.read_csv(zipfile.ZipFile(io.BytesIO(raw)).open(zipfile.ZipFile(io.BytesIO(raw)).namelist()[0]), header=None)
    if not str(df.iloc[0, 0]).isdigit():
        df = df.iloc[1:]
    df.columns = KCOLS
    return df


def download_sept(sym, last_day="2026-09-26"):
    path = os.path.join(EXT, f"klines_5m_{sym}_2026-09.parquet")
    if os.path.exists(path):
        return path
    days = pd.date_range("2026-09-01", last_day, freq="D").strftime("%Y-%m-%d")
    with ThreadPoolExecutor(4) as ex:
        parts = [p for p in ex.map(lambda d: _day(sym, d), days) if p is not None]
    df = pd.concat(parts)
    for c in KCOLS[:-1]:
        df[c] = pd.to_numeric(df[c])
    df = df.drop(columns=["ignore", "buy_quote_vol"]).drop_duplicates("open_time").sort_values("open_time")
    df.to_parquet(path, index=False)
    return path


def load_ext(sym, tf="1h"):
    """bt.data.load(sym, tf) extended with September 2026 (same resampling rules)."""
    base = load(sym, "5m")
    p = os.path.join(EXT, f"klines_5m_{sym}_2026-09.parquet")
    if os.path.exists(p):
        s = pd.read_parquet(p)
        s.index = pd.to_datetime(s["open_time"], unit="ms", utc=True)
        s = s.drop(columns=["open_time", "close_time"])
        s["sell_vol"] = s["volume"] - s["buy_vol"]
        s["delta"] = s["buy_vol"] - s["sell_vol"]
        base = pd.concat([base[base.columns.intersection(s.columns)], s[s.index > base.index[-1]]])
    if tf == "5m":
        return base
    rule = {"15m": "15min", "1h": "1h", "4h": "4h", "1d": "1D"}[tf]
    df = base.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum",
         "quote_vol": "sum", "trades": "sum", "buy_vol": "sum"}).dropna(subset=["open"])
    df["sell_vol"] = df["volume"] - df["buy_vol"]
    df["delta"] = df["buy_vol"] - df["sell_vol"]
    df["close_time"] = df.index + pd.Timedelta({"15m": "15min", "1h": "1h", "4h": "4h", "1d": "1D"}[tf])
    return df


if __name__ == "__main__":
    for s in sys.argv[1:] or ["BTCUSDT", "ETHUSDT"]:
        print(s, download_sept(s))
        d = load_ext(s, "1h")
        print(d.index[0], d.index[-1], len(d))
