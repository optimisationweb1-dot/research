"""pump_anatomy: data download for the full Binance USD-M perpetual universe (incl. delisted).

    python3 -m strategies.pump_anatomy_data list       -> data/ext/pump_anatomy/symbols_all.csv
    python3 -m strategies.pump_anatomy_data klines     -> 1h klines 2023-01..2026-08 (monthly zips)
    python3 -m strategies.pump_anatomy_data funding    -> fundingRate monthly
    python3 -m strategies.pump_anatomy_data metrics FILE -> daily metrics for (symbol, date) pairs in FILE

Source: https://data.binance.vision (public, no keys). Stored as parquet under
trading/data/ext/pump_anatomy/ (gitignored).
"""
import io
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
import zipfile
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ext", "pump_anatomy")
VISION = "https://data.binance.vision/data/futures/um"
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?delimiter=/&prefix="
KCOLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_vol",
         "trades", "buy_vol", "buy_quote_vol", "ignore"]
START, END = "2023-01", "2026-08"


def months(start=START, end=END):
    y, m = map(int, start.split("-"))
    ye, me = map(int, end.split("-"))
    out = []
    while (y, m) <= (ye, me):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def get(url, tries=5):
    url = urllib.parse.quote(url, safe=":/?&=%")   # non-ASCII symbols (e.g. 2025 Chinese-name memecoins)
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(1 + k)
        except Exception:
            time.sleep(1 + k)
    return None


def s3_list(prefix, key="Prefix"):
    out, marker = [], ""
    while True:
        url = S3 + prefix + (f"&marker={marker}" if marker else "")
        x = get(url).decode()
        if key == "Prefix":
            out += re.findall(r"<Prefix>" + re.escape(prefix) + r"([^/<]+)/</Prefix>", x)
        else:
            out += re.findall(r"<Key>([^<]+)</Key>", x)
        m = re.search(r"<NextMarker>([^<]+)</NextMarker>", x)
        if "<IsTruncated>true</IsTruncated>" in x and m:
            marker = m.group(1)
        else:
            break
    return out


def read_zip_csv(raw, **kw):
    z = zipfile.ZipFile(io.BytesIO(raw))
    return pd.read_csv(z.open(z.namelist()[0]), **kw)


def list_symbols():
    syms = sorted(set(s3_list("data/futures/um/monthly/klines/")))
    df = pd.DataFrame({"symbol": syms})
    os.makedirs(ROOT, exist_ok=True)
    df.to_csv(os.path.join(ROOT, "symbols_all.csv"), index=False)
    return df


def klines_month(symbol, tf, m):
    raw = get(f"{VISION}/monthly/klines/{symbol}/{tf}/{symbol}-{tf}-{m}.zip")
    if raw is None:
        return None
    df = read_zip_csv(raw, header=None)
    if not str(df.iloc[0, 0]).isdigit():
        df = df.iloc[1:]
    df.columns = KCOLS
    return df


def download_klines(symbol, tf="1h"):
    path = os.path.join(ROOT, "klines", tf, f"{symbol}.parquet")
    if os.path.exists(path):
        return path
    keys = s3_list(f"data/futures/um/monthly/klines/{symbol}/{tf}/", key="Key")
    have = sorted(set(re.findall(rf"{symbol}-{tf}-(\d{{4}}-\d{{2}})\.zip$", "\n".join(keys), re.M)))
    ms = [m for m in months() if m in have]
    parts = [klines_month(symbol, tf, m) for m in ms]
    parts = [p for p in parts if p is not None and len(p)]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not parts:
        pd.DataFrame(columns=KCOLS[:-1]).to_parquet(path, index=False)
        return path
    df = pd.concat(parts)
    for c in KCOLS[:-1]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.drop(columns=["ignore"]).drop_duplicates("open_time").sort_values("open_time")
    df.to_parquet(path, index=False)
    return path


def download_funding(symbol):
    path = os.path.join(ROOT, "funding", f"{symbol}.parquet")
    if os.path.exists(path):
        return path
    parts = []
    keys = s3_list(f"data/futures/um/monthly/fundingRate/{symbol}/", key="Key")
    have = set(re.findall(rf"{symbol}-fundingRate-(\d{{4}}-\d{{2}})\.zip$", "\n".join(keys), re.M))
    for m in [m for m in months() if m in have]:
        raw = get(f"{VISION}/monthly/fundingRate/{symbol}/{symbol}-fundingRate-{m}.zip")
        if raw is not None:
            try:
                parts.append(read_zip_csv(raw))
            except Exception:
                pass
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not parts:
        pd.DataFrame(columns=["ts", "funding"]).to_parquet(path, index=False)
        return path
    df = pd.concat(parts)
    df["ts"] = pd.to_datetime(pd.to_numeric(df["calc_time"]), unit="ms", utc=True)
    df = df[["ts", "last_funding_rate"]].rename(columns={"last_funding_rate": "funding"})
    df["funding"] = pd.to_numeric(df["funding"], errors="coerce")
    df = df.drop_duplicates("ts").sort_values("ts")
    df.to_parquet(path, index=False)
    return path


def metrics_day(symbol, d):
    raw = get(f"{VISION}/daily/metrics/{symbol}/{symbol}-metrics-{d}.zip")
    if raw is None:
        return None
    try:
        df = read_zip_csv(raw)
    except Exception:
        return None
    return df


def download_metrics_pairs(pairs_csv, threads=12):
    """pairs_csv: columns symbol,date (YYYY-MM-DD). Stores one parquet per symbol (appends)."""
    pairs = pd.read_csv(pairs_csv).drop_duplicates()
    out_dir = os.path.join(ROOT, "metrics")
    os.makedirs(out_dir, exist_ok=True)
    for sym, g in pairs.groupby("symbol"):
        path = os.path.join(out_dir, f"{sym}.parquet")
        have = set()
        old = None
        if os.path.exists(path):
            old = pd.read_parquet(path)
            have = set(old["date"].unique())
        need = sorted(set(g["date"]) - have)
        if not need:
            continue
        with ThreadPoolExecutor(threads) as ex:
            parts = list(ex.map(lambda d: (d, metrics_day(sym, d)), need))
        rows = []
        for d, p in parts:
            if p is None or not len(p):
                rows.append(pd.DataFrame({"date": [d]}))  # mark as tried
                continue
            p = p.copy()
            p["date"] = d
            rows.append(p)
        new = pd.concat(rows, ignore_index=True)
        if "symbol" in new:
            new = new.drop(columns=["symbol"])
        allm = pd.concat([old, new], ignore_index=True) if old is not None else new
        allm.to_parquet(path, index=False)
        print(sym, len(need), flush=True)


def _pool(fn, syms, threads):
    t0 = time.time()
    with ThreadPoolExecutor(threads) as ex:
        for i, _ in enumerate(ex.map(fn, syms)):
            if i % 25 == 0:
                print(i, len(syms), round(time.time() - t0), flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "list":
        print(len(list_symbols()))
    elif cmd in ("klines", "funding"):
        syms = pd.read_csv(os.path.join(ROOT, "symbols_use.csv"))["symbol"].tolist()
        fn = download_klines if cmd == "klines" else download_funding
        _pool(fn, syms, int(sys.argv[2]) if len(sys.argv) > 2 else 12)
    elif cmd == "metrics":
        download_metrics_pairs(sys.argv[2])
