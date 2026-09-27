"""Thin wrapper around bt.runner for the volume_absorption family.

Works around a bug in bt/data._asof (not edited here: another agent owns bt/*.py):
with pandas >= 2 `df["close_time"].values` drops the UTC timezone, so pd.merge_asof fails
("incompatible merge keys ... dtype('<M8[us]') and datetime64[..., UTC]") for
load(metrics=True / funding=True / dvol=True). The patch below keeps both keys as
datetime64[ns, UTC]; the as-of logic (value known at bar CLOSE) is unchanged.

    python3 -m strategies.volume_absorption_runner strategies.volume_absorption --fn absorb ...
"""
import sys

import pandas as pd

import bt.data as _data


def _asof_fixed(df, ext, cols, avail_col="avail"):
    left = pd.DataFrame({"open_ts": df.index,
                         "close_time": pd.DatetimeIndex(df["close_time"]).as_unit("ns")})
    right = ext[[avail_col] + cols].copy()
    right[avail_col] = pd.DatetimeIndex(right[avail_col]).as_unit("ns")
    right = right.sort_values(avail_col)
    m = pd.merge_asof(left.sort_values("close_time"), right, left_on="close_time", right_on=avail_col,
                      direction="backward")
    m.index = m["open_ts"]
    out = df.copy()
    for c in cols:
        out[c] = m[c].reindex(out.index).values
    return out


_data._asof = _asof_fixed

if __name__ == "__main__":
    from bt import runner
    sys.exit(runner.main())
