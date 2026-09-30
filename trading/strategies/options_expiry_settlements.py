"""Download Deribit delivery settlements (per-option `position` at expiry = OI at expiry) and daily
official delivery prices. Public API, no keys.

    cd trading && python3 -m strategies.options_expiry_settlements
      -> data/ext/options_expiry/settlements/{BTC,ETH}.parquet, delivery_{btc,eth}_usd.parquet
"""
import json
import os
import time
import urllib.parse
import urllib.request

import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT = os.path.join(HERE, "data", "ext", "options_expiry", "settlements")
API = "https://www.deribit.com/api/v2/public/"
STOP_MS = int(pd.Timestamp("2022-12-20", tz="UTC").timestamp() * 1000)


def get(method, **kw):
    url = API + method + "?" + urllib.parse.urlencode(kw)
    for k in range(5):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)["result"]
        except Exception:
            time.sleep(2 * (k + 1))
    raise RuntimeError(url)


def settlements(cur):
    path = os.path.join(EXT, f"{cur}.parquet")
    if os.path.exists(path):
        return pd.read_parquet(path)
    rows, cont = [], None
    while True:
        kw = {"currency": cur, "type": "delivery", "count": 1000}
        if cont:
            kw["continuation"] = cont
        r = get("get_last_settlements_by_currency", **kw)
        s = r["settlements"]
        rows += s
        cont = r.get("continuation")
        oldest = min(x["timestamp"] for x in s) if s else 0
        print(cur, len(rows), pd.Timestamp(oldest, unit="ms"), flush=True)
        if not s or not cont or oldest < STOP_MS:
            break
        time.sleep(0.2)
    d = pd.DataFrame(rows)
    d["ts"] = pd.to_datetime(d["timestamp"], unit="ms", utc=True)
    d = d[d["instrument_name"].str.count("-") == 3].copy()  # options only
    p = d["instrument_name"].str.split("-", expand=True)
    d["strike"] = p[2].astype(float)
    d["cp"] = p[3]
    d["expiry"] = d["ts"].dt.floor("h")
    d = d.drop_duplicates("instrument_name")
    os.makedirs(EXT, exist_ok=True)
    d.to_parquet(path, index=False)
    return d


def delivery_prices(index):
    path = os.path.join(EXT, f"delivery_{index}.parquet")
    if os.path.exists(path):
        return pd.read_parquet(path)
    rows, off = [], 0
    while True:
        r = get("get_delivery_prices", index_name=index, offset=off, count=1000)
        rows += r["data"]
        off += 1000
        if off >= r["records_total"] or not r["data"]:
            break
    d = pd.DataFrame(rows)
    d["date"] = pd.to_datetime(d["date"], utc=True)
    d.to_parquet(path, index=False)
    return d


if __name__ == "__main__":
    for c in ("BTC", "ETH"):
        s = settlements(c)
        print(c, len(s), s["ts"].min(), s["ts"].max(), s["expiry"].nunique())
    for i in ("btc_usd", "eth_usd"):
        d = delivery_prices(i)
        print(i, len(d), d["date"].min(), d["date"].max())
