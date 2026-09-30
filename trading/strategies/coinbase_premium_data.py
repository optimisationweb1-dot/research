"""Data for the Coinbase-premium study (key: coinbase_premium).

Downloads (public, no keys) into trading/data/ext/coinbase_premium/:
  cb_<PRODUCT>_1h.parquet   Coinbase Exchange candles, granularity 3600
                            https://api.exchange.coinbase.com/products/<P>/candles  (max 300 rows/request)
                            row = [time(start, s), low, high, open, close, volume]
  bn_spot_<SYM>_1h.parquet  Binance SPOT klines from https://data.binance.vision/data/spot/monthly/klines/
                            (timestamps are microseconds from 2025-01 on - normalised to ms here)

Then builds premium_1h.parquet: one row per hour (candle START time `ts`, known at ts+1h):
  cb_<a>, bns_<a>, bnf_<a>   closes: Coinbase <A>-USD, Binance spot <A>USDT, Binance USD-M perp <A>USDT
  usdt                       Coinbase USDT-USD close (USD per 1 USDT)
  prem_raw_<a>   = cb / bns - 1                        (classic "Coinbase premium", CryptoQuant-style)
  prem_<a>       = cb / (bns * usdt) - 1               (tether-adjusted: both legs in USD)
  prem_typ_<a>   = same with (O+H+L+C)/4 of each hour  (hour-average, less last-trade noise)
  basis_<a>      = bnf / bns - 1                       (perp vs spot on Binance)
  prem_fut_<a>   = cb / (bnf * usdt) - 1               (premium vs the perp; mixes in basis)

    python3 -m strategies.coinbase_premium_data download
    python3 -m strategies.coinbase_premium_data build
"""
import io
import json
import os
import sys
import time
import urllib.request
import zipfile

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT = os.path.join(HERE, "data", "ext", "coinbase_premium")
CB = "https://api.exchange.coinbase.com/products/{p}/candles?granularity=3600&start={s}&end={e}"
BV = "https://data.binance.vision/data/spot/monthly/klines/{s}/1h/{s}-1h-{m}.zip"
START, END = "2023-01-01", "2026-09-01"   # END exclusive
ASSETS = {"btc": ("BTC-USD", "BTCUSDT"), "eth": ("ETH-USD", "ETHUSDT"), "sol": ("SOL-USD", "SOLUSDT")}


def _get(url, tries=6):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "research-script/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(1.5 * (k + 1))
        except Exception:
            time.sleep(1.5 * (k + 1))
    raise RuntimeError(f"failed: {url}")


def download_coinbase(product):
    path = os.path.join(EXT, f"cb_{product}_1h.parquet")
    if os.path.exists(path):
        return path
    t0, t1 = pd.Timestamp(START, tz="UTC"), pd.Timestamp(END, tz="UTC")
    rows, cur = [], t0
    step = pd.Timedelta(hours=300)
    while cur < t1:
        nxt = min(cur + step, t1)
        # Coinbase 'end' is inclusive; ask up to nxt - 1h so windows do not overlap
        url = CB.format(p=product, s=cur.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        e=(nxt - pd.Timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"))
        data = json.loads(_get(url))
        if isinstance(data, dict):
            raise RuntimeError(f"{url}: {data}")
        rows += data
        cur = nxt
        time.sleep(0.2)
    df = pd.DataFrame(rows, columns=["t", "low", "high", "open", "close", "volume"])
    df["ts"] = pd.to_datetime(df["t"], unit="s", utc=True)
    df = df.drop(columns="t").drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    os.makedirs(EXT, exist_ok=True)
    df.to_parquet(path, index=False)
    return path


def _months(a, b):
    out, p = [], pd.Period(a[:7], "M")
    while p < pd.Period(b[:7], "M"):
        out.append(str(p))
        p += 1
    return out


def download_binance_spot(sym):
    path = os.path.join(EXT, f"bn_spot_{sym}_1h.parquet")
    if os.path.exists(path):
        return path
    parts = []
    for m in _months(START, END):
        raw = _get(BV.format(s=sym, m=m))
        if raw is None:
            print("missing", sym, m, flush=True)
            continue
        z = zipfile.ZipFile(io.BytesIO(raw))
        d = pd.read_csv(z.open(z.namelist()[0]), header=None)
        if not str(d.iloc[0, 0]).isdigit():
            d = d.iloc[1:]
        d = d.iloc[:, :11]
        d.columns = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_vol",
                     "trades", "buy_vol", "buy_quote_vol"]
        parts.append(d)
    df = pd.concat(parts)
    for c in df.columns:
        df[c] = pd.to_numeric(df[c])
    ot = df["open_time"].to_numpy(dtype=np.int64)
    ot = np.where(ot > 10 ** 14, ot // 1000, ot)  # microseconds (2025+) -> ms
    df["ts"] = pd.to_datetime(ot, unit="ms", utc=True)
    df = df.drop(columns=["open_time", "close_time"]).drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    os.makedirs(EXT, exist_ok=True)
    df.to_parquet(path, index=False)
    return path


def _fut_1h(sym):
    sys.path.insert(0, HERE)
    from bt.data import load
    f = load(sym, "1h")
    return f


def build():
    """Assemble the hourly premium table. Missing hours stay NaN (no forward fill of prices)."""
    idx = pd.date_range(START, END, freq="1h", tz="UTC", inclusive="left")
    out = pd.DataFrame(index=idx)
    usdt = pd.read_parquet(os.path.join(EXT, "cb_USDT-USD_1h.parquet")).set_index("ts")
    out["usdt"] = usdt["close"].reindex(idx)
    out["usdt_typ"] = ((usdt["open"] + usdt["high"] + usdt["low"] + usdt["close"]) / 4).reindex(idx)
    # USDT-USD trades nearly every hour; a stale-by-one-hour value is harmless for a ~1e-4 level series
    out["usdt"] = out["usdt"].ffill(limit=3)
    out["usdt_typ"] = out["usdt_typ"].ffill(limit=3)
    for a, (prod, sym) in ASSETS.items():
        cb = pd.read_parquet(os.path.join(EXT, f"cb_{prod}_1h.parquet")).set_index("ts")
        bs = pd.read_parquet(os.path.join(EXT, f"bn_spot_{sym}_1h.parquet")).set_index("ts")
        bf = _fut_1h(sym)
        out[f"cb_{a}"] = cb["close"].reindex(idx)
        out[f"cbvol_{a}"] = cb["volume"].reindex(idx)
        out[f"bns_{a}"] = bs["close"].reindex(idx)
        out[f"bnsvol_{a}"] = bs["quote_vol"].reindex(idx)
        out[f"bnf_{a}"] = bf["close"].reindex(idx)
        cbt = ((cb["open"] + cb["high"] + cb["low"] + cb["close"]) / 4).reindex(idx)
        bst = ((bs["open"] + bs["high"] + bs["low"] + bs["close"]) / 4).reindex(idx)
        out[f"prem_raw_{a}"] = out[f"cb_{a}"] / out[f"bns_{a}"] - 1
        out[f"prem_{a}"] = out[f"cb_{a}"] / (out[f"bns_{a}"] * out["usdt"]) - 1
        out[f"prem_typ_{a}"] = cbt / (bst * out["usdt_typ"]) - 1
        out[f"basis_{a}"] = out[f"bnf_{a}"] / out[f"bns_{a}"] - 1
        out[f"prem_fut_{a}"] = out[f"cb_{a}"] / (out[f"bnf_{a}"] * out["usdt"]) - 1
    out.index.name = "ts"
    path = os.path.join(EXT, "premium_1h.parquet")
    out.to_parquet(path)
    return path, out


def load_premium():
    return pd.read_parquet(os.path.join(EXT, "premium_1h.parquet"))


def recent(start="2026-09-01", end="2026-09-27"):
    """Current regime snapshot (after the backtest window): Coinbase candles + Binance SPOT daily archives."""
    t0, t1 = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")
    res = {}
    for prod in ["USDT-USD", "BTC-USD", "ETH-USD"]:
        rows, cur = [], t0
        while cur < t1:
            nxt = min(cur + pd.Timedelta(hours=300), t1)
            rows += json.loads(_get(CB.format(p=prod, s=cur.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                              e=(nxt - pd.Timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"))))
            cur = nxt
            time.sleep(0.2)
        d = pd.DataFrame(rows, columns=["t", "low", "high", "open", "close", "volume"])
        d["ts"] = pd.to_datetime(d["t"], unit="s", utc=True)
        res[prod] = d.drop_duplicates("ts").set_index("ts").sort_index()["close"]
    for sym in ["BTCUSDT", "ETHUSDT"]:
        parts = []
        for day in pd.date_range(t0, t1 - pd.Timedelta(days=1), freq="D"):
            raw = _get(f"https://data.binance.vision/data/spot/daily/klines/{sym}/1h/{sym}-1h-{day:%Y-%m-%d}.zip")
            if raw is None:
                continue
            z = zipfile.ZipFile(io.BytesIO(raw))
            parts.append(pd.read_csv(z.open(z.namelist()[0]), header=None).iloc[:, :5])
        d = pd.concat(parts)
        ot = pd.to_numeric(d[0]).to_numpy(dtype=np.int64)
        ot = np.where(ot > 10 ** 14, ot // 1000, ot)
        res[sym] = pd.Series(pd.to_numeric(d[4]).to_numpy(), index=pd.to_datetime(ot, unit="ms", utc=True)).sort_index()
    t = pd.DataFrame({"usdt": res["USDT-USD"], "cb_btc": res["BTC-USD"], "cb_eth": res["ETH-USD"],
                      "bns_btc": res["BTCUSDT"], "bns_eth": res["ETHUSDT"]})
    for a in ["btc", "eth"]:
        t[f"prem_{a}"] = t[f"cb_{a}"] / (t[f"bns_{a}"] * t["usdt"]) - 1
        t[f"prem_raw_{a}"] = t[f"cb_{a}"] / t[f"bns_{a}"] - 1
    t.to_parquet(os.path.join(EXT, "recent_2026-09.parquet"))
    return t


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "download"
    if cmd == "download":
        for p in ["USDT-USD", "BTC-USD", "ETH-USD", "SOL-USD"]:
            print(p, download_coinbase(p), flush=True)
        for s in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
            print(s, download_binance_spot(s), flush=True)
    elif cmd == "build":
        path, out = build()
        print(path, out.shape)
        print(out.describe().T.to_string())
    elif cmd == "recent":
        t = recent()
        w = t.resample("W-SUN").mean()
        cols = ["prem_btc", "prem_raw_btc", "prem_eth", "prem_raw_eth"]
        print((w[cols] * 1e4).round(2).assign(usdt_dev_bps=((w["usdt"] - 1) * 1e4).round(2),
                                               btc_close=t["bns_btc"].resample("W-SUN").last()).to_string())
        print("last ts", t.dropna().index.max(), "rows", len(t.dropna()))
