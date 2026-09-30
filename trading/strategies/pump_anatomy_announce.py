"""pump_anatomy: Binance announcement catalogs with publication timestamps (releaseDate, ms UTC).

    python3 -m strategies.pump_anatomy_announce
Source: https://www.binance.com/bapi/composite/v1/public/cms/article/list/query (public CMS API)
catalogId 48 = New Cryptocurrency Listing, 161 = Delisting.
"""
import json
import os
import time
import urllib.request

import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ext", "pump_anatomy")
URL = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId={c}&pageNo={p}&pageSize=50"


def fetch(cat):
    rows, p = [], 1
    while True:
        for k in range(5):
            try:
                with urllib.request.urlopen(URL.format(c=cat, p=p), timeout=30) as r:
                    x = json.loads(r.read())
                break
            except Exception:
                time.sleep(2 + k)
        arts = x["data"]["catalogs"][0]["articles"] if x["data"]["catalogs"] else []
        if not arts:
            break
        for a in arts:
            rows.append({"catalog": cat, "id": a["id"], "code": a["code"], "title": a["title"],
                         "release_ms": a["releaseDate"]})
        p += 1
        time.sleep(0.3)
    df = pd.DataFrame(rows)
    df["published_utc"] = pd.to_datetime(df["release_ms"], unit="ms", utc=True)
    df["url"] = "https://www.binance.com/en/support/announcement/detail/" + df["code"]
    return df


if __name__ == "__main__":
    os.makedirs(ROOT, exist_ok=True)
    out = pd.concat([fetch(48), fetch(161)], ignore_index=True)
    out.to_csv(os.path.join(ROOT, "binance_announcements.csv"), index=False)
    print(out.groupby("catalog").size(), out["published_utc"].min(), out["published_utc"].max())
