"""Audit downloader: public data.binance.vision klines into trading/data/ext/audit/ (gitignored).

    python3 -m strategies.audit_dl klines BTCUSDT 1m 2023-01 2026-08
    python3 -m strategies.audit_dl klines BTCUSDT 1h 2023-01 2026-08
Stores one parquet per (symbol, tf) with the raw Binance columns (open_time ms, ...).
Uses at most 2 download threads (shared machine).
"""
import io
import os
import sys
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ext", "audit")
VISION = "https://data.binance.vision/data/futures/um"
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


def get(url, tries=5):
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 * (k + 1))
        except Exception:
            time.sleep(2 * (k + 1))
    raise RuntimeError(f"download failed: {url}")


def read_zip_csv(raw, **kw):
    z = zipfile.ZipFile(io.BytesIO(raw))
    return pd.read_csv(z.open(z.namelist()[0]), **kw)


def klines_month(symbol, tf, m):
    raw = get(f"{VISION}/monthly/klines/{symbol}/{tf}/{symbol}-{tf}-{m}.zip")
    if raw is None:
        return None
    df = read_zip_csv(raw, header=None)
    if not str(df.iloc[0, 0]).isdigit():
        df = df.iloc[1:]
    df.columns = KCOLS
    for c in KCOLS[:-1]:
        df[c] = pd.to_numeric(df[c])
    df["month_file"] = m
    return df.drop(columns=["ignore"])


def klines(symbol, tf, start, end, threads=2):
    path = os.path.join(ROOT, "klines", tf, f"{symbol}.parquet")
    if os.path.exists(path):
        return path
    with ThreadPoolExecutor(threads) as ex:
        parts = [p for p in ex.map(lambda m: klines_month(symbol, tf, m), months(start, end)) if p is not None]
    if not parts:
        return None
    df = pd.concat(parts, ignore_index=True)   # keep duplicates: the audit counts them
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_parquet(path, index=False)
    return path


def load_ext(symbol, tf):
    """Ext klines indexed by open time (UTC), deduplicated, same columns as bt.data.load (no resample)."""
    df = pd.read_parquet(os.path.join(ROOT, "klines", tf, f"{symbol}.parquet"))
    df = df.drop_duplicates("open_time").sort_values("open_time")
    df.index = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    return df


if __name__ == "__main__":
    cmd, sym, tf, s, e = sys.argv[1:6]
    assert cmd == "klines"
    print(sym, tf, klines(sym, tf, s, e), flush=True)
