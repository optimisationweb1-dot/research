"""Parse cached EDGAR 8-K texts into a dated purchase table.

Publication timestamp: EDGAR acceptanceDateTime (UTC, verified against the -index.htm 'Accepted' field,
which is US/Eastern). If the text says 'On <date>, ... announced' with a date EARLIER than acceptance
(e.g. SEC holiday), ann_ts = that date 12:00 UTC [estimate] and ts_source='text_date_est'.
"""
import glob
import os
import re

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
EXT = os.path.join(os.path.dirname(HERE), "data", "ext", "treasury_flows", "edgar")

NUM = r"(\d[\d,]*(?:\.\d+)?)"
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"


def num(s):
    return float(s.replace(",", ""))


def header(txt):
    m = re.match(r"ticker=(\S+) acc=(\S+) accepted=(\S+) filed=(\S+) form=(\S+) items=(.*)", txt.split("\n", 1)[0])
    return dict(zip(["ticker", "acc", "accepted", "filed", "form", "items"], m.groups()))


VAL = re.compile(r"^\$?\s*\(?\$?\s*[-\u2014\u2013]?[\d,]*\.?\d*\s*(billion|million)?\)?\s*(\(\d\))?\*?$")


def _isval(c):
    c = c.strip()
    return bool(c) and bool(VAL.match(c)) and c not in ("(1)", "(2)", "(3)", "(4)")


def _v(c, unit=1.0):
    neg = "(" in re.sub(r"\(\d\)", "", c)
    mult = 1e9 / unit if "billion" in c else (1e6 / unit if "million" in c else 1.0)
    c = re.sub(r"\(\d\)|billion|million|[\$\s\(\)\*]", "", c)
    if c in ("", "-", "\u2014", "\u2013"):
        return 0.0
    x = float(c.replace(",", "")) * mult
    return -x if neg else x


def parse_table_cells(t, asset_word="BTC"):
    """Cell walk over '|'-separated text. Returns (net_coins, net_usd, holdings, n_tables) or None."""
    cells = [c.strip() for c in t.split("|")]
    cells = [c for c in cells if c not in ("", "$")]
    net_c = net_u = 0.0
    hold, ntab, i = None, 0, 0
    lab_trade = re.compile(rf"^{asset_word} (Acquired|Purchased|Sold)")
    while i < len(cells):
        c = cells[i]
        if lab_trade.match(c) or c.startswith(f"Aggregate {asset_word} Holdings"):
            labels = []
            j = i
            while j < len(cells) and not _isval(cells[j]) and len(labels) < 8:
                labels.append(cells[j]); j += 1
            vals = []
            while j < len(cells) and _isval(cells[j]) and len(vals) < 6:
                vals.append(cells[j]); j += 1
            has_trade = any(lab_trade.match(x) for x in labels)
            has_hold = any(x.startswith(f"Aggregate {asset_word} Holdings") for x in labels)
            k = 0
            if has_trade and len(vals) >= 3:
                sold = any(x.startswith(f"{asset_word} Sold") for x in labels)
                q, u = _v(vals[0]), _v(vals[1], unit=1e6)
                if q and u and abs(u * 1e6 / q) < 1000:  # table said "(in billions)"
                    u *= 1000
                if sold:
                    q, u = -abs(q), -abs(u)
                elif "(" in vals[0].replace("(1)", "").replace("(2)", ""):
                    q, u = -abs(q), -abs(u)
                net_c += q; net_u += u * 1e6; ntab += 1; k = 3
            if has_hold and len(vals) >= k + 1:
                hold = _v(vals[k])
            i = j
        else:
            i += 1
    if ntab == 0 and hold is None:
        return None
    return net_c, net_u, hold, ntab


def _parse_doc(t):
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"(\| )+", "| ", t)
    bought = usd = hold = None
    kind = ""
    m = re.search(r"acquired (?:an aggregate of )?approximately " + NUM +
                  r" bitcoins? for (?:an aggregate purchase price of )?(?:approximately )?\$" + NUM +
                  r" ?(million|billion)", t)
    if m:
        bought = num(m.group(1)); usd = num(m.group(2)) * (1e9 if m.group(3) == "billion" else 1e6); kind = "prose"
    m2 = re.search(r"(?:held|holds|Holds) (?:an aggregate of )?approximately " + NUM + r" (?:bitcoins?|BTC)", t)
    if m2:
        hold = num(m2.group(1))
    no_trade = re.search(r"did not purchase (?:or sell )?any (?:additional )?bitcoin", t, re.I)
    sec = re.search(r"(BTC Updates?\b.{0,6000})", t)
    if bought is None and sec:
        p = parse_table_cells(sec.group(1)[:6000])
        if p and (p[3] > 0 or p[2] is not None):
            bought, usd, h2, ntab = p; kind = "table"
            hold = h2 if h2 is not None else hold
            if ntab == 0:
                bought = usd = None
    if bought is None and no_trade:
        bought, usd, kind = 0.0, 0.0, "no_trade"
    if bought is None and hold is None:
        return None
    return bought, usd, hold, kind


def parse_mstr(txt):
    """Returns (net_btc, net_usd, holdings, kind) or None. net<0 = sale. Primary doc first, then exhibits."""
    docs = txt.split("\n=== ")[1:]
    best = None
    for d in docs:
        p = _parse_doc(d)
        if p and p[0] is not None:
            return p
        if p and best is None:
            best = p
    return best


def announced_date(txt, accepted):
    t = re.sub(r"\s+", " ", txt)
    m = re.search(rf"On ((?:{MONTHS}) \d{{1,2}}, 20\d\d), (?:the Company|Strategy|MicroStrategy|Bitmine|BitMine|SharpLink|Sharplink)[^.]{{0,80}}(?:announced (?:that|updates|the following)|issued a press release)", t)
    if not m:
        m = re.search(rf"\b((?:{MONTHS}) \d{{1,2}}, 20\d\d) ?(?:/PRNewswire/)? ?[\u2013\u2014-]{{1,2}} ", t)
    if not m:
        return None
    d = pd.Timestamp(m.group(1)).tz_localize("UTC")
    lag = (accepted.normalize() - d).days
    return d if 1 <= lag <= 4 else None


def run_mstr():
    rows = []
    for f in sorted(glob.glob(os.path.join(EXT, "MSTR", "*.txt"))):
        txt = open(f).read()
        h = header(txt)
        p = parse_mstr(txt)
        if p is None:
            continue
        acc_ts = pd.Timestamp(h["accepted"]).tz_convert("UTC") if pd.Timestamp(h["accepted"]).tzinfo else pd.Timestamp(h["accepted"], tz="UTC")
        ad = announced_date(txt, acc_ts)
        rows.append({"company": "Strategy (MSTR)", "ticker": "MSTR", "asset": "BTC", "accession": h["acc"],
                     "edgar_accepted_utc": acc_ts, "ann_ts_utc": (ad + pd.Timedelta(hours=12)) if ad is not None else acc_ts,
                     "ts_source": "text_date_est" if ad is not None else "edgar_accepted",
                     "coins_net": p[0], "usd_net": p[1], "holdings_after": p[2], "parse": p[3], "form": h["form"], "items": h["items"]})
    df = pd.DataFrame(rows).sort_values("edgar_accepted_utc").reset_index(drop=True)
    return df


if __name__ == "__main__":
    d = run_mstr()
    pd.set_option("display.width", 250)
    d["dh"] = d["holdings_after"].diff()
    d["px"] = d["usd_net"] / d["coins_net"]
    print(d[["edgar_accepted_utc", "ann_ts_utc", "ts_source", "coins_net", "usd_net", "px", "holdings_after", "dh", "parse", "items"]].to_string())


# ---------------------------------------------------------------- ETH treasuries (BMNR, SBET, others)
HOLD_PATTERNS = [
    (r"comprised of ([\d,][\d,\s]{4,}\d) ETH", 1),
    (r"(?:ETH|Aggregate ETH) [Hh]oldings (?:were|of|rose to|increased to|totaled approximately|totaled) ([\d,]{6,})", 1),
    (r"total (?:holdings of ETH|ETH holdings) to ([\d,]{6,}) ETH", 1),
    (r"holdings of approximately ([\d,]{6,}) ETH", 1),
    (r"(?:Now Holds|now holds|holds|with) ([\d,]{6,}) ETH", 1),
    (r"total ETH of ([\d,]{6,}) tokens", 1),
    (r"ETH holdings exceed ([\d,]{6,})", 1),
    (r"Holdings Exceed ([\d,]{6,}) Tokens", 1),
    (r"from [\d,.]+ (?:million )?to ([\d.]+) million tokens", 1e6),
    (r"([\d.]+) million ETH [Tt]okens", 1e6),
]
BUY_PATTERN = r"acquired ([\d,]{3,}) ETH for an aggregate purchase price of (?:approximately )?\$([\d,.]+)(?: (million|billion))?"


def parse_eth(txt):
    t = re.sub(r"\s+", " ", txt)
    t = re.sub(r"(\| )+", "| ", t)
    hold = bought = usd = px = None
    for pat, mult in HOLD_PATTERNS:
        m = re.search(pat, t)
        if m:
            hold = float(m.group(1).replace(",", "").replace(" ", "")) * mult
            break
    m = re.search(BUY_PATTERN, t)
    if m:
        bought = num(m.group(1))
        usd = num(m.group(2)) * {"million": 1e6, "billion": 1e9, None: 1.0}[m.group(3)]
    m = re.search(r"ETH at \$([\d,]+) per ETH", t)
    if m:
        px = num(m.group(1))
    return hold, bought, usd, px


def run_eth(ticker, company):
    rows = []
    for f in sorted(glob.glob(os.path.join(EXT, ticker, "*.txt"))):
        txt = open(f).read()
        h = header(txt)
        hold, bought, usd, px = parse_eth(txt)
        if hold is None and bought is None:
            continue
        acc_ts = pd.Timestamp(h["accepted"])
        acc_ts = acc_ts.tz_convert("UTC") if acc_ts.tzinfo else acc_ts.tz_localize("UTC")
        ad = announced_date(txt, acc_ts)
        rows.append({"company": company, "ticker": ticker, "asset": "ETH", "accession": h["acc"],
                     "edgar_accepted_utc": acc_ts,
                     "ann_ts_utc": (ad + pd.Timedelta(hours=12)) if ad is not None else acc_ts,
                     "ts_source": "text_date_est" if ad is not None else "edgar_accepted",
                     "holdings_after": hold, "coins_reported_bought": bought, "usd_reported": usd, "px_reported": px,
                     "form": h["form"], "items": h["items"]})
    return pd.DataFrame(rows).sort_values("edgar_accepted_utc").reset_index(drop=True) if rows else pd.DataFrame()
