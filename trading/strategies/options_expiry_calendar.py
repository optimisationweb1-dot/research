"""Deribit option expiry calendar built from the real instrument list (history.deribit.com).

    python3 -m strategies.options_expiry_calendar      # writes data/ext/options_expiry/calendar.parquet

Class per UTC date (08:00 expiry): Q (quarterly month expiry), M (monthly), W (weekly), D (daily only), N (none).
Also records the list of listed strikes per expiry (the strike grid Deribit actually offered).
"""
import json
import os
import urllib.request

import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT = os.path.join(HERE, "data", "ext", "options_expiry")
URL = "https://history.deribit.com/api/v2/public/get_instruments?currency={c}&kind=option&expired=true"


def fetch(c):
    p = os.path.join(EXT, f"instr_{c}.json")
    if not os.path.exists(p):
        os.makedirs(EXT, exist_ok=True)
        with urllib.request.urlopen(URL.format(c=c), timeout=600) as r, open(p, "wb") as f:
            f.write(r.read())
    d = pd.DataFrame(json.load(open(p))["result"])
    d["exp"] = pd.to_datetime(d["expiration_timestamp"], unit="ms", utc=True)
    return d


def calendar(c):
    d = fetch(c)
    d = d[(d["exp"] >= "2022-12-01") & (d["exp"].dt.hour == 8) & (d["exp"].dt.minute == 0)]
    rank = {"day": 0, "week": 1, "month": 2}
    g = d.groupby("exp").agg(period=("settlement_period", lambda s: max(s, key=lambda x: rank.get(x, -1))),
                             n_instr=("instrument_name", "size"),
                             strikes=("strike", lambda s: sorted(set(s))))
    g = g.reset_index()
    g["cls"] = g["period"].map({"day": "D", "week": "W", "month": "M"})
    g.loc[(g["cls"] == "M") & g["exp"].dt.month.isin([3, 6, 9, 12]), "cls"] = "Q"
    g["date"] = g["exp"].dt.normalize()
    g["currency"] = c
    return g


def build():
    out = pd.concat([calendar(c) for c in ("BTC", "ETH")], ignore_index=True)
    out["strikes"] = out["strikes"].map(json.dumps)
    out.to_parquet(os.path.join(EXT, "calendar.parquet"), index=False)
    return out


def load_calendar(c):
    p = os.path.join(EXT, "calendar.parquet")
    if not os.path.exists(p):
        build()
    g = pd.read_parquet(p)
    g = g[g["currency"] == c].copy()
    g["strikes"] = g["strikes"].map(json.loads)
    return g


if __name__ == "__main__":
    o = build()
    for c, g in o.groupby("currency"):
        g = g[(g["exp"] >= "2023-01-01") & (g["exp"] < "2026-09-01")]
        print(c, g["cls"].value_counts().to_dict(), "weekday of W/M/Q:",
              g[g.cls != "D"]["exp"].dt.dayofweek.value_counts().to_dict())
        print(g[g.cls.isin(["M", "Q"])][["exp", "cls", "n_instr"]].to_string())
