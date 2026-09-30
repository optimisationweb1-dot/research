"""Audit: Binance USD-M 1m bars (the backtest data) vs the execution venues BingX and Bitunix.

    python3 -m strategies.audit_venue        -> results/audit_venue.json

Public market-data endpoints only (no keys, no accounts):
  BingX   https://open-api.bingx.com/openApi/swap/v3/quote/klines  (symbol BTC-USDT, startTime, limit<=1440)
  Bitunix https://fapi.bitunix.com/api/v1/futures/market/kline     (symbol BTCUSDT, endTime, limit)
Period: 2026-08-01 .. 2026-08-31 (last month of the cached Binance data).
"""
import json
import os
import time
import urllib.request

import numpy as np
import pandas as pd

from strategies.audit_dl import ROOT as EXT, load_ext

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
T0, T1 = pd.Timestamp("2026-08-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC")


def _get(url):
    for k in range(5):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(1 + k)
    raise RuntimeError(url)


def bingx(sym):
    rows, cur = [], int(T0.timestamp() * 1000)
    end = int(T1.timestamp() * 1000)
    while cur < end:
        d = _get(f"https://open-api.bingx.com/openApi/swap/v3/quote/klines?symbol={sym[:-4]}-USDT&interval=1m"
                 f"&startTime={cur}&endTime={min(cur + 1440 * 60000, end) - 1}&limit=1440")["data"]
        if not d:
            cur += 1440 * 60000
            continue
        rows += d
        cur = max(int(x["time"]) for x in d) + 60000
        time.sleep(0.15)
    df = pd.DataFrame(rows)
    df["t"] = pd.to_datetime(df["time"].astype("int64"), unit="ms", utc=True)
    return df.drop_duplicates("t").set_index("t")[["open", "high", "low", "close", "volume"]].astype(float).sort_index()


def bitunix(sym):
    rows, cur = [], int(T1.timestamp() * 1000) - 60000
    start = int(T0.timestamp() * 1000)
    while cur >= start:
        d = _get(f"https://fapi.bitunix.com/api/v1/futures/market/kline?symbol={sym}&interval=1m"
                 f"&endTime={cur}&limit=200")["data"]
        if not d:
            break
        rows += d
        mn = min(int(x["time"]) for x in d)
        if mn >= cur:
            break
        cur = mn - 60000
        time.sleep(0.12)
    df = pd.DataFrame(rows)
    df["t"] = pd.to_datetime(df["time"].astype("int64"), unit="ms", utc=True)
    df = df.rename(columns={"baseVol": "volume"})
    df = df.drop_duplicates("t").set_index("t")[["open", "high", "low", "close", "volume"]].astype(float).sort_index()
    return df[(df.index >= T0) & (df.index < T1)]


def compare(bn, vx, label):
    j = bn.join(vx, how="inner", lsuffix="_bn", rsuffix="_vx")
    p = j["close_bn"]
    out = {"label": label, "minutes_binance": int(len(bn)), "minutes_venue": int(len(vx)), "minutes_joined": int(len(j))}
    for c in ("close", "high", "low"):
        d = (j[c + "_vx"] - j[c + "_bn"]) / p * 1e4
        out[c + "_diff_bps"] = {"mean": round(float(d.mean()), 2), "median_abs": round(float(d.abs().median()), 2),
                                "p95_abs": round(float(d.abs().quantile(0.95)), 2),
                                "p99_abs": round(float(d.abs().quantile(0.99)), 2),
                                "share_abs_gt_5bps": round(float((d.abs() > 5).mean()), 4)}
    r_bn, r_vx = np.log(j.close_bn).diff(), np.log(j.close_vx).diff()
    out["corr_1m_returns"] = round(float(r_bn.corr(r_vx)), 4)
    # 5m bars: range differences in bps (what a stop/limit sees)
    agg = {"high_bn": "max", "low_bn": "min", "close_bn": "last", "high_vx": "max", "low_vx": "min", "close_vx": "last"}
    f = j[list(agg)].resample("5min").agg(agg).dropna()
    for c in ("high", "low"):
        d = (f[c + "_vx"] - f[c + "_bn"]) / f["close_bn"] * 1e4
        out[f"5m_{c}_diff_bps"] = {"mean": round(float(d.mean()), 2), "median_abs": round(float(d.abs().median()), 2),
                                   "p95_abs": round(float(d.abs().quantile(0.95)), 2)}
    # deeper wick on Binance than on the venue (a Binance-based stop/limit may trigger when the venue's would not)
    out["5m_share_binance_low_below_venue_low_by_gt_3bps"] = round(float(((f.low_vx - f.low_bn) / f.close_bn * 1e4 > 3).mean()), 4)
    out["5m_share_binance_high_above_venue_high_by_gt_3bps"] = round(float(((f.high_bn - f.high_vx) / f.close_bn * 1e4 > 3).mean()), 4)
    return out


def main():
    res = {}
    os.makedirs(os.path.join(EXT, "venue"), exist_ok=True)
    for sym in ("BTCUSDT", "ETHUSDT"):
        bn = load_ext(sym, "1m")
        bn = bn[(bn.index >= T0) & (bn.index < T1)][["open", "high", "low", "close", "volume"]]
        for name, fn in (("bingx", bingx), ("bitunix", bitunix)):
            p = os.path.join(EXT, "venue", f"{name}_{sym}_2026-08.parquet")
            if os.path.exists(p):
                vx = pd.read_parquet(p)
            else:
                vx = fn(sym)
                vx.to_parquet(p)
            r = compare(bn, vx, f"{sym} binance vs {name}")
            res[f"{sym}_{name}"] = r
            print(json.dumps(r), flush=True)
    with open(os.path.join(OUT, "audit_venue.json"), "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
