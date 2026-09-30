"""Build daily US spot ETF net-flow CSVs (BTC, ETH) from The Block chart API, cross-check with TFTC.

Raw files (gitignored) in trading/data/ext/treasury_flows/:
  theblock_btc_etf_flows.json  <- https://www.theblock.co/api/charts/chart/etfs/bitcoin-etf/spot-bitcoin-etf-flows
  theblock_eth_etf_flows.json  <- https://www.theblock.co/api/charts/chart/etfs/ethereum-etf/spot-ethereum-etf-flows
  tftc_btc_etf_flows.json      <- https://www.tftc.io/bitcoin-etf-flows/data.json (CC BY 4.0)
Output: trading/research/treasury_flows_etf_btc.csv, treasury_flows_etf_eth.csv
"""
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TR = os.path.dirname(HERE)
EXT = os.path.join(TR, "data", "ext", "treasury_flows")
OUT = os.path.join(TR, "research")


def theblock(asset):
    d = json.loads(json.load(open(os.path.join(EXT, f"theblock_{asset}_etf_flows.json")))["jsonFile"]["data"])
    cols = {}
    for tk, s in d["Series"].items():
        ser = pd.Series({pd.Timestamp(x["Timestamp"], unit="s", tz="UTC").normalize(): x["Result"] for x in s["Data"]})
        cols[tk] = ser
    df = pd.DataFrame(cols).sort_index()
    df.index.name = "date"
    df = df.fillna(0.0)
    df["total_usd"] = df.sum(axis=1)
    return df


def main():
    rep = {}
    for a in ("btc", "eth"):
        df = theblock(a)
        df.index = df.index.strftime("%Y-%m-%d")
        df.to_csv(os.path.join(OUT, f"treasury_flows_etf_{a}.csv"), float_format="%.0f")
        rep[a] = (df.index[0], df.index[-1], len(df), df["total_usd"].sum() / 1e9)
    print(rep)
    # cross-check BTC totals vs TFTC
    tb = theblock("btc")["total_usd"]
    tb.index = tb.index.tz_localize(None)
    tf = pd.DataFrame(json.load(open(os.path.join(EXT, "tftc_btc_etf_flows.json")))["days"])
    tf = tf.set_index(pd.to_datetime(tf["date"]))["netFlowUsd"].astype(float)
    j = pd.concat([tb.rename("theblock"), tf.rename("tftc")], axis=1).dropna()
    diff = (j["theblock"] - j["tftc"]).abs()
    print("common days", len(j), "corr", round(j.corr().iloc[0, 1], 4),
          "median |diff| $m", round(diff.median() / 1e6, 2), "days |diff|>50m", int((diff > 50e6).sum()),
          "sum theblock $bn", round(j.theblock.sum() / 1e9, 2), "sum tftc $bn", round(j.tftc.sum() / 1e9, 2))
    miss = sorted(set(tf.index) - set(tb.index))
    print("days in TFTC not in TheBlock:", len(miss), [d.date().isoformat() for d in miss[:10]])
    big = j[diff > 50e6]
    print(big.head(15) / 1e6)


if __name__ == "__main__":
    main()
