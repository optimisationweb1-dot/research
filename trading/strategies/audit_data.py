"""Audit step 2: data integrity of the bt cache.

    python3 -m strategies.audit_data     -> results/audit_data.json (+ prints)

Checks: gaps/duplicates/time unit of 5m klines, OHLC and taker-volume sanity, 1m->5m consistency,
5m->15m/1h/4h/1d resample vs native Binance klines, partial resample bins, metrics/funding/DVOL
cadence and stamp semantics, the pandas-3 as-of merge failure and a leak scan of merged columns.
"""
import json
import os
import urllib.request

import numpy as np
import pandas as pd

import bt.data as D
from strategies.audit_dl import ROOT as EXT, load_ext

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
SYMS = D.SYMBOLS


def raw5(sym):
    return pd.read_parquet(os.path.join(D.ROOT, "klines", "5m", f"{sym}.parquet"))


def check_klines(k, step_ms, label):
    r = {"label": label, "rows": int(len(k))}
    ot = k["open_time"].to_numpy()
    r["open_time_min"] = str(pd.to_datetime(ot.min(), unit="ms", utc=True))
    r["open_time_max"] = str(pd.to_datetime(ot.max(), unit="ms", utc=True))
    r["time_unit_ok_ms"] = bool(1.5e12 < ot.min() and ot.max() < 2.0e12)
    r["duplicates_open_time"] = int(pd.Series(ot).duplicated().sum())
    r["monotonic"] = bool(np.all(np.diff(ot) > 0))
    r["close_time_minus_open_ok"] = float(np.mean(k["close_time"].to_numpy() - ot == step_ms - 1))
    dt = np.diff(np.sort(np.unique(ot)))
    gaps = dt[dt != step_ms]
    r["gaps"] = int(len(gaps))
    r["missing_bars"] = int(((gaps // step_ms) - 1).sum()) if len(gaps) else 0
    expected = int((ot.max() - ot.min()) // step_ms + 1)
    r["expected_rows"] = expected
    if len(gaps):
        idx = np.flatnonzero(dt != step_ms)
        su = np.sort(np.unique(ot))
        big = sorted(((int(dt[i] // step_ms) - 1, str(pd.to_datetime(su[i], unit="ms", utc=True))) for i in idx),
                     reverse=True)[:8]
        r["largest_gaps(bars_missing, after)"] = big
    o, h, l, c = (k[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    r["ohlc_violations"] = int(((h < np.maximum(o, c) - 1e-12) | (l > np.minimum(o, c) + 1e-12) | (h < l)).sum())
    v, bv = k["volume"].to_numpy(float), k["buy_vol"].to_numpy(float)
    r["buy_vol_gt_volume"] = int((bv > v * (1 + 1e-9) + 1e-12).sum())
    r["buy_vol_negative"] = int((bv < 0).sum())
    r["zero_volume_bars"] = int((v == 0).sum())
    r["zero_range_bars"] = int((h == l).sum())
    lr = np.abs(np.diff(np.log(c)))
    r["abs_ret_gt_5pct"] = int((lr > 0.05).sum())
    r["max_abs_ret_pct"] = round(float(lr.max() * 100), 2)
    oc = np.abs(o[1:] / c[:-1] - 1)
    r["open_vs_prev_close_gt_0.5pct"] = int((oc > 0.005).sum())
    return r


def compare_ohlcv(a, b, cols=("open", "high", "low", "close", "volume", "buy_vol", "quote_vol", "trades")):
    j = a.join(b, how="outer", lsuffix="_res", rsuffix="_nat")
    out = {"rows_resampled": int(a.shape[0]), "rows_native": int(b.shape[0]),
           "only_resampled": int(j[f"open_nat"].isna().sum()), "only_native": int(j[f"open_res"].isna().sum())}
    both = j.dropna(subset=["open_res", "open_nat"])
    for c in cols:
        x, y = both[c + "_res"].to_numpy(float), both[c + "_nat"].to_numpy(float)
        rel = np.abs(x - y) / np.maximum(np.abs(y), 1e-12)
        out[c + "_mismatch(rel>1e-6)"] = int((rel > 1e-6).sum())
        out[c + "_max_rel"] = float(rel.max()) if len(rel) else 0.0
    return out, both


def resample_checks():
    res = {}
    for sym, tfs in [("BTCUSDT", ["1h", "4h", "1d"]), ("ETHUSDT", ["1h"])]:
        for tf in tfs:
            p = os.path.join(EXT, "klines", tf, f"{sym}.parquet")
            if not os.path.exists(p):
                continue
            nat = load_ext(sym, tf)[["open", "high", "low", "close", "volume", "buy_vol", "quote_vol", "trades"]]
            ours = D.load(sym, tf)[["open", "high", "low", "close", "volume", "buy_vol", "quote_vol", "trades"]]
            out, both = compare_ohlcv(ours, nat)
            # partial bins: resampled bars built from fewer than the full number of 5m bars
            raw = raw5(sym)
            ix = pd.to_datetime(raw["open_time"], unit="ms", utc=True)
            cnt = pd.Series(1, index=ix).resample({"1h": "1h", "4h": "4h", "1d": "1D"}[tf]).sum()
            full = {"1h": 12, "4h": 48, "1d": 288}[tf]
            out["partial_bins"] = int(((cnt > 0) & (cnt < full)).sum())
            out["partial_bin_examples"] = [str(x) for x in cnt[(cnt > 0) & (cnt < full)].index[:5]]
            out["label_check_first_bar_open"] = [str(ours.index[0]), str(nat.index[0])]
            res[f"{sym}_{tf}"] = out
            print(sym, tf, out, flush=True)
    # 1m -> 5m consistency (BTC, ETH)
    for sym in ["BTCUSDT", "ETHUSDT"]:
        p = os.path.join(EXT, "klines", "1m", f"{sym}.parquet")
        if not os.path.exists(p):
            continue
        m1 = load_ext(sym, "1m")
        res[f"{sym}_1m_raw"] = check_klines(pd.read_parquet(p), 60_000, f"{sym} 1m")
        agg = m1.resample("5min", label="left", closed="left").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum", "buy_vol": "sum",
             "quote_vol": "sum", "trades": "sum"}).dropna(subset=["open"])
        ours = D.load(sym, "5m")[["open", "high", "low", "close", "volume", "buy_vol", "quote_vol", "trades"]]
        out, both = compare_ohlcv(agg, ours)
        # where high/low disagree, the 1m path cannot fully resolve that 5m bar
        hl_bad = both[(np.abs(both.high_res - both.high_nat) > 1e-9) | (np.abs(both.low_res - both.low_nat) > 1e-9)]
        out["hl_mismatch_examples"] = [str(x) for x in hl_bad.index[:5]]
        res[f"{sym}_1m_to_5m"] = out
        print(sym, "1m->5m", out, flush=True)
    return res


def metrics_checks():
    res = {}
    for sym in SYMS:
        m = pd.read_parquet(os.path.join(D.ROOT, "metrics", f"{sym}.parquet"))
        ts = m["ts"]
        dt = ts.diff().dropna()
        r = {"rows": int(len(m)), "first": str(ts.min()), "last": str(ts.max()),
             "gaps(!=5min)": int((dt != pd.Timedelta(minutes=5)).sum()),
             "missing_5m_slots": int(((dt / pd.Timedelta(minutes=5)).round() - 1).clip(lower=0).sum()),
             "largest_gap": str(dt.max()), "nan_cells": int(m.drop(columns="ts").isna().sum().sum()),
             "stamps_on_5m_grid": float(((ts.dt.minute % 5 == 0) & (ts.dt.second == 0)).mean())}
        # stamp semantics: taker ratio stamped T vs taker buy/sell of the 5m bar opening at T-5 / T
        k = raw5(sym)
        kr = pd.Series((k.buy_vol / (k.volume - k.buy_vol)).to_numpy(),
                       index=pd.to_datetime(k.open_time, unit="ms", utc=True))
        x = m.set_index("ts")["sum_taker_long_short_vol_ratio"]
        for lag in (-1, 0, 1):
            y = kr.reindex(x.index + pd.Timedelta(minutes=5 * lag))
            ok = np.isfinite(y.values) & np.isfinite(x.values)
            r[f"corr_taker_ratio_vs_bar_open_T{5 * lag:+d}m"] = round(float(np.corrcoef(x.values[ok], y.values[ok])[0, 1]), 3)
        lo = np.log(m.set_index("ts")["sum_open_interest"]).diff().abs()
        kret = pd.Series(np.abs(np.log(k.close.to_numpy()) - np.log(k.open.to_numpy())),
                         index=pd.to_datetime(k.open_time, unit="ms", utc=True))
        for lag in (-1, 0, 1):
            y = kret.reindex(lo.index + pd.Timedelta(minutes=5 * lag))
            ok = np.isfinite(y.values) & np.isfinite(lo.values)
            r[f"spearman_absdOI_vs_absret_bar_open_T{5 * lag:+d}m"] = round(
                float(pd.Series(lo.values[ok]).corr(pd.Series(y.values[ok]), method="spearman")), 3)
        res[sym] = r
        print("metrics", sym, r, flush=True)
    return res


def funding_checks():
    res = {}
    for sym in SYMS:
        f = pd.read_parquet(os.path.join(D.ROOT, "funding", f"{sym}.parquet"))
        ts = f["ts"]
        off = (ts - ts.dt.floor("h"))
        dt = ts.diff().dropna().dt.round("h")
        r = {"rows": int(len(f)), "first": str(ts.min()), "last": str(ts.max()),
             "interval_hours_counts": {str(k): int(v) for k, v in (dt / pd.Timedelta(hours=1)).value_counts().items()},
             "max_stamp_offset_ms": float(off.max() / pd.Timedelta(milliseconds=1)),
             "mean_rate": float(f.funding.mean()), "mean_abs_rate": float(f.funding.abs().mean()),
             "share_positive": float((f.funding > 0).mean()),
             "annualized_mean_pct": float(f.funding.sum() / ((ts.max() - ts.min()).days / 365.25) * 100)}
        res[sym] = r
        print("funding", sym, r, flush=True)
    return res


def dvol_checks():
    res = {}
    for cur in ("BTC", "ETH"):
        d = pd.read_parquet(os.path.join(D.ROOT, "dvol", f"{cur}.parquet"))
        dt = d.ts.diff().dropna()
        res[cur] = {"rows": int(len(d)), "first": str(d.ts.min()), "last": str(d.ts.max()),
                    "gaps(!=1h)": int((dt != pd.Timedelta(hours=1)).sum()), "largest_gap": str(dt.max())}
    # stamp semantics: hourly candle stamped T vs 1-minute candles (public API, one sample day)
    try:
        t0, t1 = 1754006400000, 1754006400000 + 6 * 3600 * 1000     # 2025-08-01 00:00..06:00 UTC
        def get(res_):
            u = (f"https://www.deribit.com/api/v2/public/get_volatility_index_data?currency=BTC"
                 f"&start_timestamp={t0}&end_timestamp={t1}&resolution={res_}")
            with urllib.request.urlopen(u, timeout=60) as r:
                return pd.DataFrame(json.loads(r.read())["result"]["data"], columns=["t", "o", "h", "l", "c"])
        hh, mm = get(3600), get(60)
        mt_ = mm["t"].astype("int64").to_numpy()
        rows = []
        for _, x in hh.iterrows():
            t = int(x.t)
            w_open = mm[(mt_ >= t) & (mt_ < t + 3600_000)]          # minutes [T, T+60)
            w_prev = mm[(mt_ >= t - 3600_000) & (mt_ < t)]          # minutes [T-60, T)
            rows.append({"T": str(pd.to_datetime(t, unit="ms", utc=True)), "hour_close": x.c,
                         "last_min_close_in_[T,T+60)": float(w_open.c.iloc[-1]) if len(w_open) else None,
                         "last_min_close_in_[T-60,T)": float(w_prev.c.iloc[-1]) if len(w_prev) else None,
                         "hour_open": x.o, "first_min_open_in_[T,T+60)": float(w_open.o.iloc[0]) if len(w_open) else None})
        res["stamp_semantics_sample"] = rows
    except Exception as e:  # network may be blocked
        res["stamp_semantics_sample"] = f"failed: {e}"
    print("dvol", json.dumps(res, default=str)[:2000], flush=True)
    return res


def asof_fixed(df, ext, cols, avail_col="avail"):
    """Same semantics as bt.data._asof, with both keys cast to datetime64[ns, UTC]."""
    left = pd.DataFrame({"open_ts": df.index,
                         "close_time": pd.DatetimeIndex(df["close_time"]).tz_convert("UTC").as_unit("ns")})
    right = ext[[avail_col] + cols].copy()
    right[avail_col] = pd.DatetimeIndex(right[avail_col]).tz_convert("UTC").as_unit("ns")
    right = right.sort_values(avail_col)
    m = pd.merge_asof(left.sort_values("close_time"), right, left_on="close_time", right_on=avail_col,
                      direction="backward")
    m.index = m["open_ts"]
    out = df.copy()
    for c in cols:
        out[c] = m[c].reindex(out.index).values
    out["_avail"] = pd.DatetimeIndex(m[avail_col].reindex(out.index)).tz_localize(None).tz_localize("UTC") \
        if pd.DatetimeIndex(m[avail_col]).tz is not None else pd.DatetimeIndex(m[avail_col].reindex(out.index)).tz_localize("UTC")
    return out


def merge_checks():
    res = {}
    df = D.load("BTCUSDT", "1h")
    for name, fn in (("metrics", lambda: D.load("BTCUSDT", "1h", metrics=True)),
                     ("funding", lambda: D.load("BTCUSDT", "1h", funding=True)),
                     ("dvol", lambda: D.load("BTCUSDT", "1h", dvol=True))):
        try:
            fn()
            res[f"bt.data.load({name}=True)"] = "ok"
        except Exception as e:
            res[f"bt.data.load({name}=True)"] = f"{type(e).__name__}: {str(e)[:160]}"
    # alignment of the fixed merge: stamp of the attached value vs bar close
    fr = pd.read_parquet(os.path.join(D.ROOT, "funding", "BTCUSDT.parquet"))
    fr["avail"] = fr["ts"]
    x = asof_fixed(df, fr, ["funding"])
    lag = (pd.DatetimeIndex(x["close_time"]).as_unit("ns") - pd.DatetimeIndex(x["_avail"]).as_unit("ns"))
    res["funding_merge_lag_hours(min,median,max)"] = [float(lag.min() / pd.Timedelta(hours=1)),
                                                      float(lag.median() / pd.Timedelta(hours=1)),
                                                      float(lag.max() / pd.Timedelta(hours=1))]
    res["funding_merge_any_future(avail>close)"] = int((lag < pd.Timedelta(0)).sum())
    dv = pd.read_parquet(os.path.join(D.ROOT, "dvol", "BTC.parquet"))
    dv["avail"] = dv["ts"] + pd.Timedelta(hours=1)
    y = asof_fixed(df, dv, ["dvol"])
    lag = (pd.DatetimeIndex(y["close_time"]).as_unit("ns") - pd.DatetimeIndex(y["_avail"]).as_unit("ns"))
    res["dvol_merge_any_future"] = int((lag < pd.Timedelta(0)).sum())
    res["dvol_merge_lag_hours(min,median,max)"] = [float(lag.min() / pd.Timedelta(hours=1)),
                                                   float(lag.median() / pd.Timedelta(hours=1)),
                                                   float(lag.max() / pd.Timedelta(hours=1))]
    # leak scan: corr of each merged column (level and change) with the NEXT bar return vs the CURRENT bar
    mt = pd.read_parquet(os.path.join(D.ROOT, "metrics", "BTCUSDT.parquet"))
    mt["avail"] = mt["ts"] + pd.Timedelta(minutes=1)
    for tf in ("5m", "1h"):
        d = D.load("BTCUSDT", tf)
        d = asof_fixed(d, mt, ["sum_open_interest", "sum_taker_long_short_vol_ratio", "count_long_short_ratio"])
        d = asof_fixed(d.drop(columns="_avail"), fr, ["funding"])
        d = asof_fixed(d.drop(columns="_avail"), dv, ["dvol"])
        d = d[d.index >= pd.Timestamp("2024-01-02", tz="UTC")]
        r = np.log(d.close).diff()
        scan = {}
        for c in ["sum_open_interest", "sum_taker_long_short_vol_ratio", "count_long_short_ratio", "funding", "dvol",
                  "delta", "buy_vol"]:
            z = np.log(d[c].where(d[c] > 0)) if c in ("sum_open_interest", "dvol") else d[c]
            dz = z.diff()
            scan[c] = {"corr(d{x}_t, r_t)": round(float(dz.corr(r)), 3),
                       "corr(d{x}_t, r_t+1)": round(float(dz.corr(r.shift(-1))), 3),
                       "corr(d{x}_t, r_t-1)": round(float(dz.corr(r.shift(1))), 3)}
        res[f"leak_scan_BTC_{tf}"] = scan
        print("leak scan", tf, scan, flush=True)
    return res


def klines_checks():
    out = {}
    for s in SYMS:
        r = check_klines(raw5(s), 300_000, s)
        out[s] = r
        print(r, flush=True)
    return out


def main():
    import sys
    path = os.path.join(OUT, "audit_data.json")
    out = json.load(open(path)) if os.path.exists(path) else {}
    secs = {"klines_5m": klines_checks, "resample": resample_checks, "metrics": metrics_checks,
            "funding": funding_checks, "dvol": dvol_checks, "merges": merge_checks}
    for name in (sys.argv[1:] or list(secs)):
        out[name] = secs[name]()
        with open(path, "w") as f:
            json.dump(out, f, indent=1, default=str)


if __name__ == "__main__":
    main()
