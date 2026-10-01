"""Replication test: crowd_bot.signals == strategies.funding_positioning.rcrowd_4h on history,
and the paper fill logic == bt.engine.simulate.   python3 -m live.test_crowd_bot"""
import numpy as np
import pandas as pd

import strategies.funding_positioning as fp
from bt.data import load
from bt.engine import Costs, simulate
from live import crowd_bot as cb


def ms(t):
    t = pd.DatetimeIndex(t)
    return np.asarray((t - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(milliseconds=1), dtype=np.int64)


def main(symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT")):
    for s in symbols:
        df = load(s, "4h", start="2024-01-01", metrics=True, funding=True)
        ref = fp.rcrowd_4h(df, src="level", pct=0.9)
        mt = pd.read_parquet(f"data/metrics/{s}.parquet")
        ts = ms(pd.to_datetime(mt["ts"], utc=True))
        vals = mt["count_long_short_ratio"].to_numpy(float)
        o = np.argsort(ts)
        ts, vals = ts[o], vals[o]
        t_open = ms(df.index)
        x = np.array([cb.ratio_at(ts, vals, t + cb.BAR_MS) for t in t_open])
        sig, stop, tgt = cb.signals(*(df[k].to_numpy(float) for k in ("open", "high", "low", "close")), x)
        a, b = ref["signal"].to_numpy(), sig
        mism = int((a != b).sum())
        both = (a != 0) & (b != 0)
        dstop = float(np.nanmax(np.abs(ref["stop"].to_numpy()[both] - stop[both]) / stop[both])) if both.any() else 0
        print(f"{s}: ref signals {int((a != 0).sum())}, bot {int((b != 0).sum())}, mismatches {mism}, max stop diff {dstop:.2e}")
        # fills: engine on bot signals
        sg = pd.DataFrame({"signal": sig, "stop": stop, "target": tgt}, index=df.index)
        tr_e = simulate(df, sg, Costs(), max_hold=18, symbol=s)
        tr_r = simulate(df, ref, Costs(), max_hold=18, symbol=s)
        st = {"equity": 1000.0, "positions": {}, "pending": {}, "last_bar": {}}
        trades = []
        cb.process_symbol(st, s, t_open, *(df[k].to_numpy(float) for k in ("open", "high", "low", "close")),
                          sig, stop, tgt, 0, None, 0.25, [], trades)
        rb = np.array([x["R"] for x in trades])
        n = min(len(rb), len(tr_e))
        print(f"   paper book trades {len(rb)} avgR {rb.mean():+.3f}; max |dR| vs engine on first {n}: "
              f"{np.max(np.abs(rb[:n] - tr_e.R.to_numpy()[:n])):.2e}")
        print(f"   engine trades on bot signals {len(tr_e)} avgR {tr_e.R.mean():+.3f} | on ref {len(tr_r)} avgR {tr_r.R.mean():+.3f}")


if __name__ == "__main__":
    main()
