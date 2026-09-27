"""Sanity tests for the engine on synthetic bars: python3 -m bt.test_engine"""
import numpy as np
import pandas as pd

from .engine import Costs, check_lookahead, simulate

Z = Costs(0, 0, 0)


def bars(rows):
    idx = pd.date_range("2024-01-01", periods=len(rows), freq="5min", tz="UTC")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)


def sig(n, at, d, stop, target=np.nan, limit=np.nan):
    s = pd.DataFrame({"signal": 0.0, "stop": np.nan, "target": np.nan, "entry_limit": np.nan},
                     index=range(n))
    s.loc[at, ["signal", "stop", "target", "entry_limit"]] = [d, stop, target, limit]
    return s


def test_market_target():
    df = bars([[100, 101, 99, 100], [100, 101, 99.5, 100.5], [100.5, 103, 100, 102.5], [102, 102, 101, 101]])
    tr = simulate(df, sig(4, 0, 1, 98, 102), Z)
    assert len(tr) == 1 and tr.reason[0] == "target" and abs(tr.R[0] - 1.0) < 1e-9, tr


def test_same_bar_stop_first():
    df = bars([[100, 100, 100, 100], [100, 100.5, 99.5, 100], [100, 103, 97, 100], [100, 100, 100, 100]])
    tr = simulate(df, sig(4, 0, 1, 98, 102), Z)
    assert tr.reason[0] == "stop" and abs(tr.R[0] + 1) < 1e-9, tr


def test_limit_needs_strict_touch_and_no_target_on_fill_bar():
    df = bars([[100, 100, 100, 100], [100, 100.5, 99.0, 100], [100, 100, 98.5, 99.5], [99.5, 104, 99.4, 103]])
    tr = simulate(df, sig(4, 0, 1, 97, 103, limit=99.0), Z, limit_ttl=3)
    # bar1 low == limit -> no fill; bar2 low 98.5 < 99 -> fill at 99; target 103 on bar3
    assert tr.t_entry[0] == df.index[2] and tr.entry[0] == 99 and tr.reason[0] == "target", tr


def test_stop_gap():
    df = bars([[100, 100, 100, 100], [100, 100.5, 99.5, 100], [95, 96, 94, 95], [95, 95, 95, 95]])
    tr = simulate(df, sig(4, 0, 1, 98), Z)
    assert tr.exit[0] == 95 and tr.reason[0] == "stop", tr


def test_lookahead_detector():
    idx = pd.date_range("2024-01-01", periods=800, freq="5min", tz="UTC")
    rng = np.random.default_rng(0)
    c = 100 + rng.standard_normal(800).cumsum()
    df = pd.DataFrame({"open": c, "high": c + 1, "low": c - 1, "close": c}, index=idx)

    def cheat(d):
        s = pd.DataFrame(index=d.index)
        s["signal"] = np.sign(d.close.shift(-1) - d.close).fillna(0)
        s["stop"] = d.close - 2
        return s

    def honest(d):
        s = pd.DataFrame(index=d.index)
        s["signal"] = np.sign(d.close - d.close.shift(1)).fillna(0)
        s["stop"] = d.close - 2
        return s

    check_lookahead(honest, df)
    try:
        check_lookahead(cheat, df)
    except AssertionError:
        return
    raise AssertionError("cheat strategy not detected")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
