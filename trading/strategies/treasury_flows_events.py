"""Build trading/research/treasury_flows_events.csv from parsed EDGAR 8-Ks (Strategy, BitMine, SharpLink).

event_type: purchase / no_purchase / sale. coins = net coins in the reported period.
usd: as reported (Strategy, SharpLink); BitMine: holdings delta x ETH price quoted in the same release;
     if no price given -> Binance close at publication [estimate].
Publication time = EDGAR acceptance (UTC). ts_source='text_date_est': release dated earlier than the
EDGAR acceptance (SEC holiday) -> date 12:00 UTC [estimate].
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TR = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from treasury_flows_parse import run_eth, run_mstr  # noqa: E402
from treasury_flows_prices import load_ext  # noqa: E402

CIK = {"MSTR": 1050446, "BMNR": 1829311, "SBET": 1981535}
OUT = os.path.join(TR, "research", "treasury_flows_events.csv")
# SharpLink filings that restate PAST quarter-end holdings (not new purchase news) - excluded
SBET_EXCLUDE = {"0001981535-25-000012", "0001981535-25-000065"}


BT = "https://bitcointreasuries.net/public-companies/metaplanet"
SECONDARY = [
    # company, ticker, asset, publication ts (UTC), ts_source, coins, url, level, note
    ("GameStop (GME)", "GME", "BTC", "2025-05-28T10:53:00Z", "edgar_accepted", 4710,
     "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1326380&type=8-K", "[офиц.] SEC 8-K",
     "8-K: 'purchased 4,710 Bitcoin'"),
    ("FG Nexus (FGNX)", "FGNX", "ETH", "2025-08-12T00:14:00Z", "edgar_accepted", 47331,
     "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1591890&type=8-K", "[офиц.] SEC 8-K",
     "PR 11.08.2025 '47,331 ETH purchase'; 8-K accepted 12.08 00:14 UTC; PR time earlier - проверить"),
    ("BTCS (BTCS)", "BTCS", "ETH", "2025-07-28T11:00:00Z", "edgar_accepted", 14240,
     "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1436229&type=8-K", "[офиц.] SEC 8-K",
     "increased ETH by 14,240 to 70,028"),
    ("GameSquare (GAME)", "GAME", "ETH", "2025-08-04T12:00:00Z", "edgar_accepted", 2717,
     "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1714562&type=8-K", "[офиц.] SEC 8-K",
     "acquired 2,717 ETH for $10 million"),
    ("Strive (ASST)", "ASST", "BTC", "2025-09-22T13:18:00Z", "edgar_accepted", 5816,
     "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1920406&type=8-K", "[офиц.] SEC 8-K",
     "purchase of 5,816 bitcoin"),
    ("Strive (ASST)", "ASST", "BTC", "2025-11-10T14:28:00Z", "edgar_accepted", 1567,
     "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1920406&type=8-K", "[офиц.] SEC 8-K",
     "acquired 1,567 BTC 28.10-09.11.2025"),
] + [("Metaplanet (3350.T)", "MTPLF", "BTC", ts, "tracker_occurred_at [3P]", c, BT, "[3P] bitcointreasuries.net",
      f"balance_date {bd}; время = запись трекера, не TDnet - проверить")
     for ts, c, bd in (("2025-08-18T07:52:00Z", 775, "2025-08-18"), ("2025-08-25T06:34:00Z", 103, "2025-08-25"),
                       ("2025-09-01T06:42:00Z", 1009, "2025-09-01"), ("2025-09-08T06:40:00Z", 136, "2025-09-08"),
                       ("2025-09-22T04:28:00Z", 5419, "2025-09-22"), ("2025-10-01T06:59:00Z", 5268, "2025-10-01"),
                       ("2025-12-30T06:52:00Z", 4279, "2025-12-30"), ("2026-04-02T07:18:00Z", 5075, "2026-04-02"),
                       ("2026-07-02T07:03:00Z", 2823, "2026-07-02"))]


def url(tk, acc):
    return f"https://www.sec.gov/Archives/edgar/data/{CIK[tk]}/{acc.replace('-', '')}/{acc}-index.htm"


def px_at(closes, ts):
    i = closes.index.searchsorted(ts.floor("h"))
    return float(closes.iloc[max(0, i - 1)])


def build():
    btc = load_ext("BTCUSDT", "1h")["close"]
    eth = load_ext("ETHUSDT", "1h")["close"]
    ev = []
    # ---- Strategy
    m = run_mstr()
    m = m[m["coins_net"].notna()].copy()
    for _, r in m.iterrows():
        typ = "purchase" if r.coins_net > 0 else ("sale" if r.coins_net < 0 else "no_purchase")
        ev.append(dict(company="Strategy (MSTR)", ticker="MSTR", asset="BTC", event_type=typ,
                       ann_ts_utc=r.ann_ts_utc, ts_source=r.ts_source, edgar_accepted_utc=r.edgar_accepted_utc,
                       coins=r.coins_net, usd=r.usd_net, usd_source="reported", holdings_after=r.holdings_after,
                       accession=r.accession, source_url=url("MSTR", r.accession), source_level="[офиц.] SEC 8-K"))
    # ---- BitMine: holdings delta
    b = run_eth("BMNR", "BitMine (BMNR)")
    b = b[b["holdings_after"].notna()].sort_values("edgar_accepted_utc")
    prev = 0.0
    for _, r in b.iterrows():
        d = r.holdings_after - prev
        if d <= 1000 and prev > 0:        # duplicate / rounded restatement (e.g. 8-K/A, 4.803 million)
            continue
        px = r.px_reported if pd.notna(r.px_reported) else px_at(eth, r.ann_ts_utc)
        ev.append(dict(company="BitMine (BMNR)", ticker="BMNR", asset="ETH", event_type="purchase",
                       ann_ts_utc=r.ann_ts_utc, ts_source=r.ts_source, edgar_accepted_utc=r.edgar_accepted_utc,
                       coins=d, usd=d * px, usd_source="holdings_delta x px_in_release" if pd.notna(r.px_reported)
                       else "holdings_delta x Binance close [оценка]", holdings_after=r.holdings_after,
                       accession=r.accession, source_url=url("BMNR", r.accession), source_level="[офиц.] SEC 8-K EX-99.1"))
        prev = r.holdings_after
    # ---- SharpLink
    s = run_eth("SBET", "SharpLink (SBET)")
    s = s[~s["accession"].isin(SBET_EXCLUDE)].sort_values("edgar_accepted_utc")
    prev = 0.0
    for _, r in s.iterrows():
        dh = (r.holdings_after or 0) - prev
        if pd.notna(r.coins_reported_bought):
            d, usd, src = r.coins_reported_bought, r.usd_reported, "reported"
            if prev > 0 and 1000 < dh < d:   # part of the period's buying was already announced earlier
                usd, d, src = usd * dh / d, dh, "reported, scaled to new-info part (holdings delta)"
        else:
            d = dh
            usd, src = d * px_at(eth, r.ann_ts_utc), "holdings_delta x Binance close [оценка]"
            if d <= 5000:   # small deltas after Sep 2025 are mostly staking rewards, not purchases
                prev = max(prev, r.holdings_after or prev)
                continue
        if d <= 1000:
            prev = max(prev, r.holdings_after or prev)
            continue
        ev.append(dict(company="SharpLink (SBET)", ticker="SBET", asset="ETH", event_type="purchase",
                       ann_ts_utc=r.ann_ts_utc, ts_source=r.ts_source, edgar_accepted_utc=r.edgar_accepted_utc,
                       coins=d, usd=usd, usd_source=src, holdings_after=r.holdings_after,
                       accession=r.accession, source_url=url("SBET", r.accession), source_level="[офиц.] SEC 8-K"))
        prev = max(prev, r.holdings_after or prev)
    for e in ev:
        e["set"] = "primary"
    # ---- secondary (timeline only; NOT used in the primary tests). Curated from 8-K texts / tracker.
    for co, tk, asset, ts, src, coins, url_, lvl, note in SECONDARY:
        t = pd.Timestamp(ts)
        px = px_at(btc if asset == "BTC" else eth, t)
        ev.append(dict(company=co, ticker=tk, asset=asset, event_type="purchase", ann_ts_utc=t, ts_source=src,
                       edgar_accepted_utc=t if src == "edgar_accepted" else pd.NaT, coins=coins, usd=coins * px,
                       usd_source="coins x Binance close [оценка]", holdings_after=np.nan, accession="",
                       source_url=url_, source_level=lvl, set="secondary", note=note))
    df = pd.DataFrame(ev).sort_values("ann_ts_utc").reset_index(drop=True)
    # price at publication (for context)
    df["px_at_pub"] = [px_at(btc if a == "BTC" else eth, t) for a, t in zip(df.asset, df.ann_ts_utc)]
    for c in ("ann_ts_utc", "edgar_accepted_utc"):
        df[c] = pd.to_datetime(df[c], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    df.to_csv(OUT, index=False, float_format="%.2f")
    return df


if __name__ == "__main__":
    d = build()
    pd.set_option("display.width", 250)
    print(d.groupby(["ticker", "event_type"]).agg(n=("coins", "size"), coins=("coins", "sum"),
                                                  usd_bn=("usd", lambda x: x.sum() / 1e9)))
    print(d[d.ticker == "SBET"][["ann_ts_utc", "coins", "usd", "usd_source", "holdings_after"]].to_string())
