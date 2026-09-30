"""Audit: ex-ante universe (survivorship check).

    python3 -m strategies.audit_universe list      -> data/ext/audit/universe_2022-12.csv
    python3 -m strategies.audit_universe download  -> 1h klines for the ex-ante top-N (incl. delisted)

Ex-ante rule (decided before looking at any results): the 20 USDT-margined perpetuals with the
largest Binance USD-M quote volume in December 2022 (monthly 1d files on data.binance.vision),
excluding stablecoin-vs-stablecoin pairs. This is what an analyst could have chosen on 2023-01-01.
"""
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from strategies.audit_dl import ROOT, VISION, get, read_zip_csv, klines, KCOLS

S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?delimiter=/&prefix=data/futures/um/monthly/klines/"
STABLE = {"USDCUSDT", "BUSDUSDT", "TUSDUSDT", "USDPUSDT", "FDUSDUSDT"}


def all_symbols():
    out, marker = [], ""
    while True:
        url = S3 + (f"&marker={marker}" if marker else "")
        with urllib.request.urlopen(url, timeout=60) as r:
            x = r.read().decode()
        out += re.findall(r"<Prefix>data/futures/um/monthly/klines/([^/<]+)/</Prefix>", x)
        m = re.search(r"<NextMarker>([^<]+)</NextMarker>", x)
        if "<IsTruncated>true</IsTruncated>" in x and m:
            marker = m.group(1)
        else:
            break
    return sorted(set(out))


def dec22(sym):
    try:
        raw = get(f"{VISION}/monthly/klines/{sym}/1d/{sym}-1d-2022-12.zip", tries=2)
    except RuntimeError:
        return None
    if False:
        raw = get(f"{VISION}/monthly/klines/{sym}/1d/{sym}-1d-2022-12.zip")
    if raw is None:
        return None
    df = read_zip_csv(raw, header=None)
    if not str(df.iloc[0, 0]).isdigit():
        df = df.iloc[1:]
    df.columns = KCOLS
    return sym, float(pd.to_numeric(df["quote_vol"]).sum())


def truncate_delisted(df):
    """data.binance.vision keeps publishing flat zero-volume bars after a delisting: cut them."""
    live = df.index[df["volume"] > 0]
    return df[df.index <= live.max()] if len(live) else df.iloc[:0]


def compare(path):
    """Pre-registered: reference Donchian 1h (strategies.audit_donchian, default params) on the current
    10 large caps vs the ex-ante top-20 of Dec 2022 (delisted included, cut at delisting)."""
    import json
    import numpy as np
    from bt.data import load, SYMBOLS
    from strategies import audit_bt as A
    from strategies import audit_donchian as DC
    from strategies.audit_dl import load_ext
    cut = pd.Timestamp("2025-01-01", tz="UTC")
    top = pd.read_csv(path).head(20)["symbol"].tolist()
    out = {"ex_ante_top20": top, "current10": SYMBOLS}
    for name, syms, loader in (("current10", SYMBOLS, lambda s: load(s, "1h")),
                               ("ex_ante_top20", top, lambda s: truncate_delisted(load_ext(s, "1h")))):
        parts, bh, ends = [], {}, {}
        for s in syms:
            df = loader(s)
            ends[s] = str(df.index.max())
            bh[s] = float(df["close"].iloc[-1] / df["open"].iloc[0])
            parts.append(A.simulate(df, DC.strategy(df), A.BASE, DC.MAX_HOLD, None, s))
        tr = pd.concat(parts, ignore_index=True)
        row = {"buy_hold_multiple_equal_weight": round(float(np.mean(list(bh.values()))), 2),
               "buy_hold_multiple_median": round(float(np.median(list(bh.values()))), 2),
               "last_bar": {k: v for k, v in ends.items() if v < "2026-08-31"}}
        for lab, sub in (("ALL", tr), ("IS", tr[tr.t_entry < cut]), ("OOS", tr[tr.t_entry >= cut]),
                         ("LONG", tr[tr.dir > 0]), ("SHORT", tr[tr.dir < 0])):
            row[lab] = {**A.summary(sub, lab), "t_cluster_day": A.clustered_t(sub)}
        out[name] = row
        print(name, json.dumps(row), flush=True)
    res = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "audit_universe.json")
    with open(res, "w") as f:
        json.dump(out, f, indent=1)


def main():
    cmd = sys.argv[1]
    path = os.path.join(ROOT, "universe_2022-12.csv")
    if cmd == "list":
        syms = [s for s in all_symbols() if s.endswith("USDT") and s not in STABLE and s.isascii()]
        print("symbols listed:", len(syms), flush=True)
        with ThreadPoolExecutor(2) as ex:
            rows = [r for r in ex.map(dec22, syms) if r]
        df = pd.DataFrame(rows, columns=["symbol", "quote_vol_2022_12"]).sort_values("quote_vol_2022_12", ascending=False)
        df.to_csv(path, index=False)
        print(df.head(30).to_string())
    elif cmd == "compare":
        compare(path)
    elif cmd == "download":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        top = pd.read_csv(path).head(n)["symbol"].tolist()
        for s in top:
            print(s, klines(s, "1h", "2023-01", "2026-08"), flush=True)


if __name__ == "__main__":
    main()
