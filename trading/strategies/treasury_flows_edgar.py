"""Download 8-K filings (2024-01..2026-09) for treasury companies from SEC EDGAR and cache text.

Publication timestamp = EDGAR acceptanceDateTime (converted from US/Eastern to UTC).
Cache: trading/data/ext/treasury_flows/edgar/<TICKER>/<accession>.txt (primary doc + EX-99.* text)
    python3 strategies/treasury_flows_edgar.py MSTR BMNR SBET
"""
import html
import json
import os
import re
import sys
import time
import urllib.request

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
EXT = os.path.join(os.path.dirname(HERE), "data", "ext", "treasury_flows", "edgar")
UA = {"User-Agent": "research-project iangojan@gmail.com"}
CIK = {"MSTR": 1050446, "BMNR": 1829311, "SBET": 1981535, "BTBT": 1710350, "BTCS": 1436229,
       "FGNX": 1591890, "GAME": 1714562, "XXI": 2070457, "NAKA": 1946573, "ASST": 1920406,
       "DJT": 1849635, "GME": 1326380, "MARA": 1507605, "UPXI": 1775194, "DFDV": 1805526,
       "FWDI": 38264, "HSDT": 1610853, "BNC": 1482541, "TSLA": 1318605, "COIN": 1679788}
START, END = "2024-01-01", "2026-09-27"
_last = [0.0]


def get(url, tries=4):
    for k in range(tries):
        wait = 0.22 - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 * (k + 1))
        except Exception:
            time.sleep(2 * (k + 1))
    return None


def html_to_text(raw):
    s = raw.decode("utf-8", errors="ignore")
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</h\d>", "\n", s)
    s = re.sub(r"(?i)</td>|</th>", " | ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s).replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s


def filings(ticker):
    cik = CIK[ticker]
    j = json.loads(get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json"))
    frames = [pd.DataFrame(j["filings"]["recent"])]
    for f in j["filings"].get("files", []):
        frames.append(pd.DataFrame(json.loads(get("https://data.sec.gov/submissions/" + f["name"]))))
    df = pd.concat(frames, ignore_index=True)
    df = df[df["form"].isin(["8-K", "8-K/A", "6-K"]) & (df["filingDate"] >= START) & (df["filingDate"] <= END)]
    return df.drop_duplicates("accessionNumber").sort_values("acceptanceDateTime")


def fetch(ticker):
    cik = CIK[ticker]
    d = os.path.join(EXT, ticker)
    os.makedirs(d, exist_ok=True)
    df = filings(ticker)
    df.to_csv(os.path.join(d, "_filings.csv"), index=False)
    n = 0
    for _, r in df.iterrows():
        acc = r["accessionNumber"]
        path = os.path.join(d, acc + ".txt")
        if os.path.exists(path):
            continue
        nod = acc.replace("-", "")
        idx = get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{nod}/index.json")
        if idx is None:
            continue
        items = json.loads(idx)["directory"]["item"]
        names = [it["name"] for it in items if it["name"].lower().endswith((".htm", ".html", ".txt"))
                 and not it["name"].endswith("-index.htm") and "index" not in it["name"].lower()]
        prim = r["primaryDocument"]
        docs = [prim] + [x for x in names if x != prim and re.search(r"(?i)ex(hibit)?[-_]?99|ex99|dex99|pr", x)]
        parts = []
        for nm in docs[:4]:
            raw = get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{nod}/{nm}")
            if raw:
                parts.append(f"=== {nm}\n" + html_to_text(raw))
        with open(path, "w") as fh:
            fh.write(f"ticker={ticker} acc={acc} accepted={r['acceptanceDateTime']} filed={r['filingDate']} "
                     f"form={r['form']} items={r.get('items', '')}\n" + "\n".join(parts))
        n += 1
    print(ticker, "filings", len(df), "new", n, flush=True)


if __name__ == "__main__":
    for t in sys.argv[1:] or ["MSTR", "BMNR", "SBET"]:
        fetch(t)
