"""pump_anatomy: build the daily symbol panel from 1h klines + funding (all features causal).

    python3 -m strategies.pump_anatomy_panel        -> data/ext/pump_anatomy/panel.parquet

Row (date d, symbol): the daily bar d = [d 00:00, d+1 00:00) UTC. Every feature in the row is known at
the CLOSE of day d (d+1 00:00 UTC). Execution prices for strategies:
    px_exec[d] = close of the first hour of day d+1 (01:00 UTC) -> one hour after the decision.
Forward labels (fwd_*) are explicitly future and are only used as targets.
"""
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ext", "pump_anatomy")

INDEX_LIKE = {"BTCDOMUSDT", "DEFIUSDT", "BLUEBIRDUSDT", "FOOTBALLUSDT", "USDCUSDT", "PAXGUSDT", "XAUTUSDT"}
# TradFi underlyings (stocks, ETFs, commodities, pre-IPO) listed on Binance USD-M in 2025-2026.
# Checked additionally by the weekend-activity test in classify(); list reviewed by hand.
TRADFI = set("""AAOIUSDT AAPLUSDT ADBEUSDT AMATUSDT AMDUSDT AMZNUSDT ANTHROPICUSDT ASMLUSDT ASTSUSDT AVGOUSDT
AXTIUSDT BABAUSDT BITOUSDT BMNRUSDT BRKBUSDT CBRSUSDT CIENUSDT COHRUSDT COINUSDT COPPERUSDT COSTUSDT CRCLUSDT
CRDOUSDT CRMUSDT CRWDUSDT CRWVUSDT CSCOUSDT CSOPSAMSUNG2LUSDT CSOPSKHYNIX2LUSDT CXMTUSDT DELLUSDT DISUSDT DJTUSDT
DKNGUSDT DRAMUSDT EBAYUSDT EWJUSDT EWYUSDT EWZUSDT FLNCUSDT GDXUSDT GEVUSDT GLWUSDT GMEUSDT GOOGLUSDT HANMIUSDT
HIMSUSDT HK0700USDT HK1810USDT HOODUSDT HPEUSDT HYUNDAIUSDT IBMUSDT INTCUSDT INTWUSDT IONQUSDT IRENUSDT IWMUSDT
JPMUSDT KLACUSDT KODEX200USDT KUAISHOUUSDT LGELECTRONICSUSDT LLYUSDT LRCXUSDT MARAUSDT MEITUANUSDT METAUSDT
MRKUSDT MRNAUSDT MRVLUSDT MSFTUSDT MSTRUSDT MUUSDT NATGASUSDT NAVERUSDT NBISUSDT NFLXUSDT NOKUSDT NVDAUSDT NVOUSDT
ONDSUSDT OPENAIUSDT ORCLUSDT PANWUSDT PDDUSDT PLTRUSDT POPMARTUSDT PYPLUSDT QCOMUSDT QQQUSDT RDDTUSDT RIVNUSDT
RKLBUSDT SAMSUNGEMUSDT SAMSUNGUSDT SHOPUSDT SKHYNIXUSDT SKHYUSDT SLXUSDT SMCIUSDT SMHUSDT SNDKUSDT SNOWUSDT
SOFIUSDT SONYUSDT SOXLUSDT SOXSUSDT SPCXUSDT SPYUSDT SQQQUSDT TENCENTUSDT TMFUSDT TQQQUSDT TSLAUSDT TSMUSDT
TTWOUSDT TXNUSDT TZAUSDT UBERUSDT URNMUSDT UVXYUSDT WDCUSDT WMTUSDT XAGUSDT XAUUSDT XBIUSDT XLEUSDT XPDUSDT
XPTUSDT ZHIPUUSDT ZHONGJIUSDT MINIMAXUSDT UNITREEUSDT GIGADEVUSDT PAYPUSDT USARUSDT STRCUSDT""".split())


def load_1h(sym):
    p = os.path.join(ROOT, "klines", "1h", f"{sym}.parquet")
    if not os.path.exists(p):
        return None
    df = pd.read_parquet(p)
    if not len(df):
        return None
    df.index = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df[~df.index.duplicated()].sort_index()
    return df


def load_funding(sym):
    p = os.path.join(ROOT, "funding", f"{sym}.parquet")
    if not os.path.exists(p):
        return None
    f = pd.read_parquet(p)
    if not len(f):
        return None
    f["ts"] = pd.to_datetime(f["ts"], utc=True)
    return f.dropna()


def daily_for_symbol(sym):
    h = load_1h(sym)
    if h is None or len(h) < 24 * 10:
        return None
    # hourly derived: RVOL vs median of previous 720 hours; taker share per hour
    qv = h["quote_vol"].astype(float)
    base = qv.shift(1).rolling(720, min_periods=240).median()
    h["h_rvol"] = qv / base
    h["h_tshare"] = (h["buy_quote_vol"] / qv).where(qv > 0)
    day = h.index.floor("1D")
    g = h.groupby(day)
    d = pd.DataFrame({
        "open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(), "close": g["close"].last(),
        "quote_vol": g["quote_vol"].sum(), "buy_quote_vol": g["buy_quote_vol"].sum(), "trades": g["trades"].sum(),
        "n_hours": g["close"].count(), "h_rvol_max": g["h_rvol"].max(),
        "h_tshare_max": g["h_tshare"].max(),
        "first_hour_close": g["close"].first(),  # close of the 00:00 bar (known at 01:00)
    })
    d.index.name = "date"
    # regular daily calendar; mark gaps
    full = pd.date_range(d.index.min(), d.index.max(), freq="1D", tz="UTC")
    d = d.reindex(full)
    d.index.name = "date"
    d["symbol"] = sym
    # execution price for a decision at the close of day d: close of first hour of day d+1
    d["px_exec"] = d["first_hour_close"].shift(-1)
    # funding: sum of prints within the day; last print known at day close
    f = load_funding(sym)
    if f is not None:
        fd = f.groupby(f["ts"].dt.floor("1D"))["funding"].agg(["sum", "last", "count"])
        fd.index.name = "date"
        d["fund_sum"] = fd["sum"].reindex(d.index)
        d["fund_last"] = fd["last"].reindex(d.index)
        d["fund_n"] = fd["count"].reindex(d.index)
    else:
        d["fund_sum"] = np.nan
        d["fund_last"] = np.nan
        d["fund_n"] = np.nan
    return d.reset_index()


def classify(panel):
    """Weekend activity ratio: mean |ret| Sat+Sun / weekdays (TradFi underlyings ~ closed on weekends)."""
    p = panel[["date", "symbol", "close"]].copy()
    p["r"] = p.groupby("symbol")["close"].transform(lambda x: np.log(x).diff().abs())
    p["we"] = p["date"].dt.dayofweek >= 5
    s = p.groupby(["symbol", "we"])["r"].mean().unstack()
    s.columns = ["wd", "we"]
    s["we_ratio"] = s["we"] / s["wd"]
    return s


def build(workers=2):
    syms = pd.read_csv(os.path.join(ROOT, "symbols_use.csv"))["symbol"].tolist()
    with ProcessPoolExecutor(workers) as ex:
        parts = [p for p in ex.map(daily_for_symbol, syms, chunksize=8) if p is not None]
    panel = pd.concat(parts, ignore_index=True)
    cls = classify(panel)
    cls["tradfi_list"] = cls.index.isin(TRADFI)
    cls["index_like"] = cls.index.isin(INDEX_LIKE)
    cls.to_csv(os.path.join(ROOT, "symbol_class.csv"))
    panel.to_parquet(os.path.join(ROOT, "panel_raw.parquet"), index=False)
    return panel, cls


if __name__ == "__main__":
    panel, cls = build(int(sys.argv[1]) if len(sys.argv) > 1 else 2)
    print(panel.shape, panel["symbol"].nunique())
    print(cls.sort_values("we_ratio").head(40))
