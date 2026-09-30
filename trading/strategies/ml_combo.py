"""Family ml_combo: walk-forward LightGBM over many causal factors (user thesis: the edge is only in the
COMBINATION of factors, not in any single one).

Design (all fixed a priori, before looking at any result):
  * Panel of 10 Binance USD-M symbols, one pooled symbol-agnostic model (features are ratios / z-scores /
    ATR distances, no symbol id). Optional per-symbol models.
  * Label = outcome of the exact trade the engine would take: market entry at open[t+1], symmetric bracket
    stop = close_t -/+ K*ATR14, target = close_t +/- K*ATR14, max hold H bars (same-bar stop+target -> stop,
    gap through stop -> open). y_L = 1 if the gross long R > 0, y_S likewise for the short.
        15m: K = 3.0, H = 48 bars (12h)    1h: K = 2.0, H = 24 bars (24h)
    (chosen so that the median stop is ~1-2% of price and round-trip costs are ~0.06-0.12R).
  * Walk-forward: monthly retrain, expanding window, PURGE of every row whose label window can reach the
    test month (t + H + 1 bars) plus an EMBARGO of 1 day. Predictions for month m use only rows < m.
  * Two augmentation modes:
        raw : two binary models (long label, short label) on raw features;
        sym : one model trained on [X, y_L] U [mirror(X), y_S] (mirror flips every directional feature), so the
              model cannot learn a pure long/short drift of the training period (IS 2023-24 = bull market,
              OOS 2025-26 = bear market).
  * Decision at close t: edge = 2p - 1 - costR, costR = 0.0012 * close / (K*ATR) (round trip, base costs).
    Trade the side with the larger edge if edge > thr; thr is frozen from the IS prediction distribution.

Data workarounds (bt/*.py is not edited):
  1) bt.data._asof fails under pandas 3 (tz-naive close_time vs tz-aware avail) -> patched below.
  2) Binance metrics stamped T describe the 5-min window [T, T+5): made available at T+6min (same as oi_flow
     and the audit patch), OI <= 0 -> NaN.
"""
import os
import time

import numpy as np
import pandas as pd

import bt.data as _D
from bt.features import atr, confirmed_swings, empty_signals, session_vwap, zscore

SCRATCH = os.environ.get("ML_COMBO_CACHE",
                         "/tmp/claude-0/-home-user-research/ea6ba1ab-fe99-5191-91e4-bb9455e40592/scratchpad/ml_combo")
METRICS_LAG = pd.Timedelta(minutes=6)


# ------------------------------------------------------------------ data patches

def _asof_fixed(df, ext, cols, avail_col="avail"):
    ct = pd.DatetimeIndex(pd.to_datetime(df["close_time"]))
    ct = (ct.tz_localize("UTC") if ct.tz is None else ct.tz_convert("UTC")).as_unit("ns")
    left = pd.DataFrame({"pos": np.arange(len(df)), "close_time": ct})
    right = ext[[avail_col] + cols].copy()
    av = pd.DatetimeIndex(pd.to_datetime(right[avail_col], utc=True)).as_unit("ns")
    right[avail_col] = av
    right = right.sort_values(avail_col)
    m = pd.merge_asof(left.sort_values("close_time"), right, left_on="close_time", right_on=avail_col,
                      direction="backward").sort_values("pos")
    out = df.copy()
    for c in cols:
        out[c] = m[c].to_numpy()
    return out


def _merge_metrics_conservative(df, symbol):
    mt = pd.read_parquet(os.path.join(_D.ROOT, "metrics", f"{symbol}.parquet"))
    mt["avail"] = mt["ts"] + METRICS_LAG
    mt.loc[mt["sum_open_interest"] <= 0, ["sum_open_interest", "sum_open_interest_value"]] = np.nan
    cols = ["sum_open_interest", "sum_open_interest_value", "count_toptrader_long_short_ratio",
            "sum_toptrader_long_short_ratio", "count_long_short_ratio", "sum_taker_long_short_vol_ratio"]
    out = _asof_fixed(df, mt, cols)
    return out.rename(columns={"sum_open_interest": "oi", "sum_open_interest_value": "oi_usd",
                               "count_toptrader_long_short_ratio": "top_ls_accounts",
                               "sum_toptrader_long_short_ratio": "top_ls_positions",
                               "count_long_short_ratio": "ls_accounts",
                               "sum_taker_long_short_vol_ratio": "taker_ls_ratio"})


_D._asof = _asof_fixed
_D.merge_metrics = _merge_metrics_conservative

SYMBOLS = list(_D.SYMBOLS)
TF_CFG = {"15m": dict(bph=4, K=3.0, H=48), "1h": dict(bph=1, K=2.0, H=24)}
COST_RT = 0.0012  # round trip used only inside the decision rule (engine applies the real costs)


def load_raw(symbol, tf, metrics):
    return _D.load(symbol, tf, metrics=metrics, funding=True, dvol=True)


# ------------------------------------------------------------------ features

def _safe_log(x):
    return np.log(x.where(x > 0))


def own_features(df, tf, metrics):
    """Per-symbol causal features. Row t uses rows <= t only (rolling windows, shifts >= 0)."""
    bph = TF_CFG[tf]["bph"]
    B = lambda hours: max(1, int(round(hours * bph)))
    D = B(24)
    o, h, l, c, v = (df[k] for k in ("open", "high", "low", "close", "volume"))
    lr = np.log(c).diff()
    vol30 = lr.rolling(30 * D, min_periods=7 * D).std()
    A = atr(df, 14)
    f = {}
    hs = ([0.25] if tf == "15m" else []) + [1, 4, 12, 24, 72, 168]
    names = {0.25: "15m", 1: "1h", 4: "4h", 12: "12h", 24: "1d", 72: "3d", 168: "7d"}
    for hh in hs:
        b = B(hh)
        f[f"r_{names[hh]}"] = np.log(c / c.shift(b)) / (vol30 * np.sqrt(b))
    f["rvr_4h"] = np.log(lr.rolling(max(B(4), 4)).std() / lr.rolling(D).std())
    f["rvr_1d"] = np.log(lr.rolling(D).std() / vol30)
    f["rvr_7d"] = np.log(lr.rolling(7 * D).std() / vol30)
    f["vol_ann"] = np.log(vol30 * np.sqrt(365 * D))
    f["atr_pct"] = np.log(A / c)
    rng = (h - l)
    f["range_atr"] = rng / A
    f["body"] = (c - o) / A
    f["clv"] = ((c - l) / rng.where(rng > 0) - 0.5).fillna(0)
    f["wick_up"] = (h - np.maximum(o, c)) / A
    f["wick_dn"] = (np.minimum(o, c) - l) / A
    f["rvol"] = _safe_log(v / v.shift(1).rolling(D, min_periods=D // 2).median())
    f["rvol_4h"] = _safe_log(v.rolling(B(4)).mean() / v.shift(1).rolling(7 * D, min_periods=D).mean())
    f["vol_trend"] = _safe_log(v.rolling(D).mean() / v.rolling(30 * D, min_periods=7 * D).mean())
    f["tsize_z"] = zscore(_safe_log(v / df["trades"].where(df["trades"] > 0)), 7 * D)
    dl = df["delta"]
    f["ds"] = (dl / v.where(v > 0)).fillna(0)
    for hh in ([1] if tf == "15m" else []) + [4, 24]:
        b = B(hh)
        f[f"ds_{names[hh]}"] = dl.rolling(b).sum() / v.rolling(b).sum().where(lambda x: x > 0)
    f["ds_1d_z"] = zscore(f["ds_1d"], 30 * D)
    for nm, hh in (("1d", 24), ("7d", 168), ("30d", 720)):
        b = B(hh)
        hi, lo = h.rolling(b, min_periods=b // 2).max(), l.rolling(b, min_periods=b // 2).min()
        f[f"dhi_{nm}"] = (c - hi) / A
        f[f"dlo_{nm}"] = (c - lo) / A
        f[f"pos_{nm}"] = (c - lo) / (hi - lo).where(hi > lo) - 0.5
    f["dvwap"] = (c - session_vwap(df, "1D")) / A
    sh, sl = confirmed_swings(df, 5)
    f["dsh"] = (c - sh) / A
    f["dsl"] = (c - sl) / A
    f["tod"] = pd.Series((df.index.hour * 60 + df.index.minute) / 60.0, index=df.index)
    f["dow"] = pd.Series(df.index.dayofweek.astype(float), index=df.index)
    fu = df["funding"] * 1e4
    f["fund"] = fu
    f["fund_z"] = zscore(fu, 30 * D)
    f["fund_chg"] = fu - fu.shift(D)
    dv = df["dvol"]
    f["dvol_lvl"] = dv / 100
    f["dvol_z"] = zscore(dv, 90 * D)
    f["dvol_chg"] = np.log(dv / dv.shift(D))
    f["vrp"] = np.log((dv / 100) / (lr.rolling(7 * D, min_periods=D).std() * np.sqrt(365 * D)))
    if metrics:
        oi = df["oi"].where(df["oi"] > 0)
        loi = np.log(oi)
        for nm, hh in (("1h", 1), ("4h", 4), ("1d", 24)):
            f[f"oi_chg_{nm}"] = zscore(loi.diff(B(hh)), 30 * D)
        f["oi_lvl"] = np.log(oi / oi.rolling(30 * D, min_periods=7 * D).mean())
        f["oi_turn"] = zscore(np.log(df["oi_usd"].where(df["oi_usd"] > 0) /
                                     df["quote_vol"].rolling(D).sum().where(lambda x: x > 0)), 30 * D)
        tp, ta, ga = (_safe_log(df[k]) for k in ("top_ls_positions", "top_ls_accounts", "ls_accounts"))
        f["top_pos_lvl"] = tp
        f["glob_acc_lvl"] = ga
        f["top_pos_z"] = zscore(tp, 30 * D)
        f["top_acc_z"] = zscore(ta, 30 * D)
        f["glob_acc_z"] = zscore(ga, 30 * D)
        f["top_pos_chg"] = tp - tp.shift(D)
        f["glob_acc_chg"] = ga - ga.shift(D)
        f["smart_div"] = zscore(tp - ga, 30 * D)
        f["oip_4h"] = f["oi_chg_4h"] * f["r_4h"]
        f["oip_1d"] = f["oi_chg_1d"] * f["r_1d"]
    out = pd.DataFrame(f, index=df.index).replace([np.inf, -np.inf], np.nan)
    return out.astype("float32")


BTC_COLS = ["r_1h", "r_4h", "r_1d", "r_3d", "rvr_1d", "ds_4h", "ds_1d", "dhi_1d", "dlo_1d", "vrp", "fund"]
XS_COLS = ["r_4h", "r_1d", "r_7d", "ds_1d", "fund"]

# mirror spec: odd -> -x ; pairs (a, b, flip) -> a' = +/-b, b' = +/-a ; everything else even
ODD_BASE = ["r_15m", "r_1h", "r_4h", "r_12h", "r_1d", "r_3d", "r_7d", "body", "clv", "ds", "ds_1h", "ds_4h",
            "ds_1d", "ds_1d_z", "pos_1d", "pos_7d", "pos_30d", "dvwap", "fund", "fund_z", "fund_chg",
            "top_pos_lvl", "glob_acc_lvl", "top_pos_z", "top_acc_z", "glob_acc_z", "top_pos_chg", "glob_acc_chg",
            "smart_div", "oip_4h", "oip_1d", "rel_r_1d", "rel_r_7d"]
PAIRS_BASE = [("wick_up", "wick_dn", False), ("dhi_1d", "dlo_1d", True), ("dhi_7d", "dlo_7d", True),
              ("dhi_30d", "dlo_30d", True), ("dsh", "dsl", True)]


def mirror_spec(cols):
    odd = [c for c in cols if c in ODD_BASE or (c.startswith("btc_") and c[4:] in ODD_BASE)
           or c.startswith("xs_")]
    pairs = [(a, b, fl) for a, b, fl in PAIRS_BASE if a in cols]
    pairs += [("btc_" + a, "btc_" + b, fl) for a, b, fl in PAIRS_BASE if "btc_" + a in cols]
    return odd, pairs


def mirror(X, cols):
    """X: 2-D float array with columns `cols`. Returns the long<->short mirrored copy."""
    odd, pairs = mirror_spec(cols)
    idx = {c: i for i, c in enumerate(cols)}
    M = X.copy()
    for c in odd:
        M[:, idx[c]] = -X[:, idx[c]]
    for a, b, fl in pairs:
        s = -1.0 if fl else 1.0
        M[:, idx[a]] = s * X[:, idx[b]]
        M[:, idx[b]] = s * X[:, idx[a]]
    return M


def panel_features(raw, tf, metrics, truncate_at=None):
    """raw: {symbol: df}. Returns {symbol: features df} incl. BTC context and cross-sectional ranks."""
    if truncate_at is not None:
        raw = {s: d[d.index <= truncate_at] for s, d in raw.items()}
    own = {s: own_features(d, tf, metrics) for s, d in raw.items()}
    btc = own["BTCUSDT"]
    xs = {}
    for col in XS_COLS:
        wide = pd.DataFrame({s: own[s][col] for s in own})
        cnt = wide.notna().sum(axis=1)
        # centred rank in [-0.5, 0.5], exactly antisymmetric under order reversal (needed by mirror())
        xs[col] = wide.rank(axis=1).sub((cnt + 1) / 2, axis=0).div(cnt.where(cnt > 1), axis=0)
    out = {}
    for s, fe in own.items():
        b = btc[BTC_COLS].reindex(fe.index)
        b.columns = ["btc_" + c for c in BTC_COLS]
        extra = pd.DataFrame({"rel_r_1d": fe["r_1d"] - b["btc_r_1d"],
                              "rel_r_7d": fe["r_7d"] - btc["r_7d"].reindex(fe.index)}, index=fe.index)
        x = pd.DataFrame({f"xs_{c}": xs[c][s].reindex(fe.index) for c in XS_COLS}, index=fe.index)
        out[s] = pd.concat([fe, b, extra, x], axis=1).astype("float32")
    return out


# ------------------------------------------------------------------ labels

def bracket_labels(df, K, H):
    """Gross R of the long and short bracket trade entered at open[t+1] (engine fill rules, no costs)."""
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    A = atr(df, 14).to_numpy(float)
    n = len(c)
    up, dn = c + K * A, c - K * A
    ent = np.full(n, np.nan)
    ent[:-1] = o[1:]
    RL, RS = np.full(n, np.nan), np.full(n, np.nan)
    doneL = ~(ent > dn)  # engine skips the trade if entry already beyond the stop
    doneS = ~(ent < up)
    riskL, riskS = ent - dn, up - ent
    t = np.arange(n)
    for j in range(1, H + 1):
        k = t + j
        ok = k < n
        kk = np.where(ok, k, n - 1)
        oj, hj, lj = o[kk], h[kk], l[kk]
        # long
        m = ~doneL & ok
        stop_hit = m & (lj <= dn)
        px = np.where((j > 1) & (oj < dn), oj, dn)
        RL = np.where(stop_hit, (px - ent) / riskL, RL)
        doneL |= stop_hit
        m = ~doneL & ok
        tgt = m & (hj >= up)
        RL = np.where(tgt, (up - ent) / riskL, RL)
        doneL |= tgt
        # short
        m = ~doneS & ok
        stop_hit = m & (hj >= up)
        px = np.where((j > 1) & (oj > up), oj, up)
        RS = np.where(stop_hit, (ent - px) / riskS, RS)
        doneS |= stop_hit
        m = ~doneS & ok
        tgt = m & (lj <= dn)
        RS = np.where(tgt, (ent - dn) / riskS, RS)
        doneS |= tgt
    ke = t + H + 1
    ok = ke < n
    ex = np.where(ok, o[np.where(ok, ke, n - 1)], np.nan)
    RL = np.where(~doneL & ok, (ex - ent) / riskL, RL)
    RS = np.where(~doneS & ok, (ent - ex) / riskS, RS)
    return pd.DataFrame({"RL": RL, "RS": RS, "atr": A}, index=df.index)


# ------------------------------------------------------------------ panel

def build_panel(tf, track, symbols=SYMBOLS, use_cache=True, truncate_at=None):
    """Long panel: symbol, ts, features..., RL, RS, costR. track 1 = no metrics, track 2 = with metrics.
    truncate_at: rebuild everything from raw data cut at that bar (causality verification)."""
    metrics = track == 2
    path = os.path.join(SCRATCH, f"panel_{tf}_t{track}.parquet")
    if use_cache and truncate_at is None and os.path.exists(path):
        p = pd.read_parquet(path)
        return p, [c for c in p.columns if c not in META_COLS]
    raw = {s: load_raw(s, tf, metrics) for s in symbols}
    if truncate_at is not None:
        raw = {s: d[d.index <= truncate_at] for s, d in raw.items()}
    feats = panel_features(raw, tf, metrics)
    K, H = TF_CFG[tf]["K"], TF_CFG[tf]["H"]
    parts = []
    for s in symbols:
        lab = bracket_labels(raw[s], K, H)
        fe = feats[s]
        p = fe.copy()
        p["RL"] = lab["RL"].astype("float32")
        p["RS"] = lab["RS"].astype("float32")
        p["costR"] = (COST_RT * raw[s]["close"] / (K * lab["atr"])).astype("float32")
        p["symbol"] = s
        p["ts"] = fe.index
        p["i"] = np.arange(len(p), dtype=np.int32)
        # deterministic pseudo-random subsample key: depends only on (symbol, row number from data start),
        # so it is identical when the panel is rebuilt on truncated history
        key = (np.arange(len(p), dtype=np.uint64) * np.uint64(2654435761) + np.uint64(SYMBOLS.index(s) * 97 + 13))
        p["u"] = ((key % np.uint64(1000003)).astype(np.float64) / 1000003.0).astype("float32")
        parts.append(p.reset_index(drop=True))
    P = pd.concat(parts, ignore_index=True)
    if metrics:
        P = P[P["ts"] >= pd.Timestamp("2024-01-01", tz="UTC")].reset_index(drop=True)
    if truncate_at is None:
        os.makedirs(SCRATCH, exist_ok=True)
        P.to_parquet(path, index=False)
    return P, [c for c in P.columns if c not in META_COLS]


META_COLS = {"RL", "RS", "costR", "symbol", "ts", "i", "u"}

MODEL_CFGS = {
    "small": dict(num_leaves=15, min_data_in_leaf=2000, n_estimators=300),
    "large": dict(num_leaves=63, min_data_in_leaf=500, n_estimators=500),
    # per-symbol models (~8.7k 1h rows per symbol-year): shallower trees, same learning rate
    "ps": dict(num_leaves=7, min_data_in_leaf=300, n_estimators=300),
}
TRAIN_START = {1: "2023-02-01", 2: "2024-01-15"}
FIRST_TEST = {1: "2023-07-01", 2: "2024-04-01"}
LAST_TEST = "2026-08-01"


def lgb_params(cfg, seed=42):
    return dict(objective="binary", learning_rate=0.03, num_leaves=cfg["num_leaves"],
                min_data_in_leaf=cfg["min_data_in_leaf"], feature_fraction=0.6, bagging_fraction=0.7,
                bagging_freq=1, lambda_l2=10.0, max_bin=127, verbose=-1, num_threads=2, seed=seed,
                deterministic=True, force_col_wise=True)


def _fit(X, y, cfg, cols):
    import lightgbm as lgb
    ds = lgb.Dataset(X, label=y, feature_name=cols, free_raw_data=True)
    return lgb.train(lgb_params(cfg), ds, num_boost_round=cfg["n_estimators"])


def month_starts(first, last):
    return list(pd.date_range(pd.Timestamp(first, tz="UTC"), pd.Timestamp(last, tz="UTC"), freq="MS"))


def train_mask(P, tf, track, m0, stride):
    """Rows usable for a model that predicts month m0: label window ends before m0 minus an embargo."""
    H = TF_CFG[tf]["H"]
    bar = pd.Timedelta(minutes=_D.TF_MIN[tf])
    embargo = pd.Timedelta(days=1)
    cutoff = m0 - (H + 1) * bar - embargo  # row t allowed iff t <= cutoff  => label window < m0 - embargo
    m = (P["ts"] >= pd.Timestamp(TRAIN_START[track], tz="UTC")) & (P["ts"] <= cutoff)
    m &= P["RL"].notna() & P["RS"].notna()
    if stride > 1:
        m &= P["u"] < 1.0 / stride
    return m.to_numpy()


def walk_forward(P, cols, tf, track, aug, model, stride=1, months=None, log=True, keep_models=False,
                 symbols=None, min_rows=5000):
    """Monthly retrain. Returns (preds DataFrame[symbol, ts, pL, pS], gain importances DataFrame, models)."""
    cfg = MODEL_CFGS[model]
    months = months or month_starts(FIRST_TEST[track], LAST_TEST)
    if symbols is not None:
        P = P[P["symbol"].isin(symbols)].reset_index(drop=True)
    X_all = P[cols].to_numpy(np.float32)
    yL = (P["RL"].to_numpy() > 0).astype(np.float32)
    yS = (P["RS"].to_numpy() > 0).astype(np.float32)
    ts = P["ts"]
    out, imps, models = [], [], {}
    for m0 in months:
        t0 = time.time()
        m1 = m0 + pd.offsets.MonthBegin(1)
        tm = train_mask(P, tf, track, m0, stride)
        te = ((ts >= m0) & (ts < m1)).to_numpy()
        if te.sum() == 0 or tm.sum() < min_rows:
            continue
        Xtr = X_all[tm]
        Xte = X_all[te]
        if aug == "sym":
            bst = _fit(np.vstack([Xtr, mirror(Xtr, cols)]), np.concatenate([yL[tm], yS[tm]]), cfg, cols)
            pL, pS = bst.predict(Xte), bst.predict(mirror(Xte, cols))
            gains = bst.feature_importance("gain")
            bsts = (bst,)
        else:
            bL = _fit(Xtr, yL[tm], cfg, cols)
            bS = _fit(Xtr, yS[tm], cfg, cols)
            pL, pS = bL.predict(Xte), bS.predict(Xte)
            gains = bL.feature_importance("gain") + bS.feature_importance("gain")
            bsts = (bL, bS)
        if keep_models:
            models[m0] = bsts
        imps.append(pd.Series(gains / max(gains.sum(), 1e-12), index=cols, name=m0))
        out.append(pd.DataFrame({"symbol": P["symbol"].to_numpy()[te], "ts": ts.to_numpy()[te],
                                 "pL": pL.astype(np.float32), "pS": pS.astype(np.float32)}))
        if log:
            print(f"  {tf} t{track} {aug} {model} {m0:%Y-%m} train={tm.sum()} test={te.sum()} "
                  f"{time.time() - t0:.1f}s", flush=True)
    preds = pd.concat(out, ignore_index=True)
    return preds, pd.DataFrame(imps), models


# ------------------------------------------------------------------ signals

def edges(preds, P):
    """Attach costR and edges to predictions."""
    m = preds.merge(P[["symbol", "ts", "costR", "RL", "RS"]], on=["symbol", "ts"], how="left")
    m["eL"] = 2 * m["pL"] - 1 - m["costR"]
    m["eS"] = 2 * m["pS"] - 1 - m["costR"]
    return m


def signals_for_symbol(df, E_sym, thr, K):
    """df: raw bars of one symbol; E_sym: edges rows for that symbol (ts-indexed)."""
    out = empty_signals(df)
    e = E_sym.set_index("ts").reindex(df.index)
    eL, eS = e["eL"].to_numpy(float), e["eS"].to_numpy(float)
    A = atr(df, 14).to_numpy(float)
    c = df["close"].to_numpy(float)
    long_ = (eL > thr) & (eL >= eS)
    short = (eS > thr) & (eS > eL) & ~long_
    sig = np.where(long_, 1.0, np.where(short, -1.0, 0.0))
    sig[np.isnan(A)] = 0.0
    out["signal"] = sig
    out["stop"] = np.where(sig > 0, c - K * A, np.where(sig < 0, c + K * A, np.nan))
    out["target"] = np.where(sig > 0, c + K * A, np.where(sig < 0, c - K * A, np.nan))
    return out


# ------------------------------------------------------------------ strategy wrapper (for check_lookahead)

_RAW_CACHE = {}
_FROZEN = {}


def _raw_cached(sym, tf, metrics):
    key = (sym, tf, metrics)
    if key not in _RAW_CACHE:
        _RAW_CACHE[key] = load_raw(sym, tf, metrics)
    return _RAW_CACHE[key]


def strategy(df, tf="1h", track=1, aug="sym", model_path=None, thr=0.0, symbol="BTCUSDT"):
    """End-to-end causal decision for ONE symbol with a frozen booster (used for bt.engine.check_lookahead).
    Other symbols (BTC context, cross-sectional ranks) are truncated at df's last bar."""
    import lightgbm as lgb
    metrics = track == 2
    if model_path not in _FROZEN:
        _FROZEN[model_path] = lgb.Booster(model_file=model_path)
    bst = _FROZEN[model_path]
    cols = bst.feature_name()
    raw = {s: (df if s == symbol else _raw_cached(s, tf, metrics)) for s in SYMBOLS}
    feats = panel_features(raw, tf, metrics, truncate_at=df.index[-1])[symbol]
    X = feats[cols].to_numpy(np.float32)
    K = TF_CFG[tf]["K"]
    A = atr(df, 14)
    costR = (COST_RT * df["close"] / (K * A)).to_numpy(float)
    pL = bst.predict(X)
    pS = bst.predict(mirror(X, cols)) if aug == "sym" else 1 - pL
    E = pd.DataFrame({"ts": df.index, "eL": 2 * pL - 1 - costR, "eS": 2 * pS - 1 - costR})
    return signals_for_symbol(df, E, thr, K)


strategy.MAX_HOLD = 24
