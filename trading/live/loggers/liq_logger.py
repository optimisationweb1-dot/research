#!/usr/bin/env python3
"""Liquidations logger: long-running process (systemd), writes live/state/liq/liq_YYYY-MM-DD.csv.

Streams (public, no keys):
  OKX     wss://ws.okx.com/ws/v5/public   channel liquidation-orders, instType SWAP (all symbols)
  Bybit   wss://stream.bybit.com/v5/public/linear  allLiquidation.<SYMBOL> (every liquidation)
  Binance wss://fstream.binance.com/ws/!forceOrder@arr  (only the largest per symbol per second)
Columns: recv_ts, exchange, symbol, side_liquidated (long/short), price, qty, usd.
Reconnects with backoff. Bybit and Binance block US IPs; run on the EU server.
"""
import asyncio
import csv
import json
import os
import time
from datetime import datetime, timezone

import websockets

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "liq")
BYBIT_SYMBOLS = os.environ.get("LIQ_BYBIT_SYMBOLS", "BTCUSDT ETHUSDT SOLUSDT XRPUSDT DOGEUSDT BNBUSDT ADAUSDT "
                                "AVAXUSDT LINKUSDT LTCUSDT HYPEUSDT SUIUSDT").split()


def write(row):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"liq_{datetime.now(timezone.utc):%Y-%m-%d}.csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["recv_ts", "exchange", "symbol", "side_liquidated", "price", "qty", "usd"])
        w.writerow(row)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


async def okx():
    async with websockets.connect("wss://ws.okx.com/ws/v5/public", ping_interval=20) as ws:
        await ws.send(json.dumps({"op": "subscribe", "args": [{"channel": "liquidation-orders", "instType": "SWAP"}]}))
        async for msg in ws:
            d = json.loads(msg)
            for item in d.get("data", []):
                for x in item.get("details", []):
                    # posSide = side of the liquidated position; sz in contracts (USD value approximated as sz*px
                    # only for USDT-margined linear contracts with ctVal=1 unit; keep raw qty)
                    px, sz = float(x["bkPx"]), float(x["sz"])
                    write([now(), "okx", item["instId"], x.get("posSide"), px, sz, ""])


async def bybit():
    async with websockets.connect("wss://stream.bybit.com/v5/public/linear", ping_interval=None) as ws:
        await ws.send(json.dumps({"op": "subscribe", "args": [f"allLiquidation.{s}" for s in BYBIT_SYMBOLS]}))

        async def pinger():
            while True:
                await asyncio.sleep(20)
                await ws.send(json.dumps({"op": "ping"}))
        task = asyncio.create_task(pinger())
        try:
            async for msg in ws:
                d = json.loads(msg)
                for x in d.get("data", []) if isinstance(d.get("data"), list) else []:
                    # S = side of the liquidation ORDER: Buy -> a short was liquidated
                    side = "short" if x.get("S") == "Buy" else "long"
                    px, qty = float(x["p"]), float(x["v"])
                    write([now(), "bybit", x["s"], side, px, qty, round(px * qty, 2)])
        finally:
            task.cancel()


async def binance():
    async with websockets.connect("wss://fstream.binance.com/ws/!forceOrder@arr", ping_interval=20) as ws:
        async for msg in ws:
            o = json.loads(msg).get("o", {})
            if not o:
                continue
            side = "short" if o.get("S") == "BUY" else "long"
            px, qty = float(o.get("ap") or o.get("p")), float(o.get("z") or o.get("q"))
            write([now(), "binance", o["s"], side, px, qty, round(px * qty, 2)])


async def forever(name, fn):
    delay = 2
    while True:
        try:
            t0 = time.time()
            await fn()
        except Exception as e:
            print(now(), name, "error:", repr(e)[:200], flush=True)
        delay = 2 if time.time() - t0 > 300 else min(delay * 2, 300)
        await asyncio.sleep(delay)


async def main():
    enabled = os.environ.get("LIQ_EXCHANGES", "okx bybit binance").split()
    tasks = [forever(n, f) for n, f in (("okx", okx), ("bybit", bybit), ("binance", binance)) if n in enabled]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
