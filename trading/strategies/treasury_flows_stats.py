"""Statistics helpers for treasury_flows: event study with placebo, Newey-West OLS (numpy only)."""
import numpy as np
import pandas as pd


def nw_ols(y, X, lags):
    """OLS with Newey-West (Bartlett) HAC standard errors. X without constant -> constant added.
    Returns dict(coef, se, t, n, r2)."""
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    if X.ndim == 1:
        X = X[:, None]
    ok = np.isfinite(y) & np.isfinite(X).all(axis=1)
    y, X = y[ok], X[ok]
    X = np.column_stack([np.ones(len(y)), X])
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ y
    e = y - X @ b
    u = X * e[:, None]
    S = u.T @ u
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1)
        G = u[L:].T @ u[:-L]
        S += w * (G + G.T)
    V = XtX_inv @ S @ XtX_inv * n / max(n - k, 1)
    se = np.sqrt(np.diag(V))
    r2 = 1 - (e @ e) / ((y - y.mean()) @ (y - y.mean())) if n > 1 else np.nan
    return {"coef": b, "se": se, "t": b / se, "n": n, "r2": r2}


def nw_mean_t(x, lags):
    r = nw_ols(np.asarray(x, float), np.zeros((len(x), 0)), lags)
    return float(r["coef"][0]), float(r["t"][0])


class EventStudy:
    """Hourly log-price event study. lp: pd.Series of log OPEN prices indexed by hourly bar open time."""

    def __init__(self, lp, horizons_h):
        self.lp = lp.dropna()
        self.t = self.lp.index
        self.v = self.lp.to_numpy()
        self.H = list(horizons_h)
        n = len(self.v)
        self.R = {}
        for h in self.H:
            r = np.full(n, np.nan)
            r[:n - h] = self.v[h:] - self.v[:n - h]
            self.R[h] = r
        self.Rpre = {}
        for h in self.H:
            r = np.full(n, np.nan)
            r[h:] = self.v[h:] - self.v[:n - h]
            self.Rpre[h] = r

    def idx(self, times):
        """Entry bar = first bar whose open >= event time (i.e. next full hour)."""
        ts = pd.DatetimeIndex(pd.to_datetime(times, utc=True)).ceil("h")
        i = self.t.searchsorted(ts)
        return np.where(i < len(self.t), i, -1)

    def run(self, times, weights=None, n_placebo=2000, seed=11, window=None, pre=False):
        rng = np.random.default_rng(seed)
        ix = self.idx(times)
        ok = ix >= 0
        ix = ix[ok]
        w = None if weights is None else np.asarray(weights, float)[ok]
        lo = int(ix.min()) - 24 * 30 if window is None else int(self.t.searchsorted(window[0]))
        lo = max(lo, 0)
        hi_all = len(self.v) - 1 if window is None else int(self.t.searchsorted(window[1]))
        dow = self.t.dayofweek.to_numpy()
        hod = self.t.hour.to_numpy()
        out = []
        src = self.Rpre if pre else self.R
        for h in self.H:
            R = src[h]
            hi = hi_all - (0 if pre else h)
            sel = ix[(ix <= hi) & np.isfinite(R[ix])]
            if len(sel) < 5:
                continue
            ww = None if w is None else w[(ix <= hi) & np.isfinite(R[ix])]
            x = R[sel]
            pool = R[lo:hi + 1]
            drift = np.nanmean(pool)
            mean = float(np.average(x, weights=ww)) if ww is not None else float(x.mean())
            # circular-shift placebo: shift the whole event set, preserve spacing/overlap
            L = hi - lo + 1
            pm = np.empty(n_placebo)
            for k in range(n_placebo):
                d = rng.integers(24 * 7, L - 24 * 7)
                j = lo + (sel - lo + d) % L
                xx = R[j]
                m = np.isfinite(xx)
                pm[k] = np.average(xx[m], weights=ww[m]) if ww is not None else xx[m].mean()
            # weekday+hour matched random placebo
            cand = {}
            pdw = np.empty(n_placebo)
            keys = list(zip(dow[sel], hod[sel]))
            for kk in set(keys):
                c = np.arange(lo, hi + 1)
                c = c[(dow[c] == kk[0]) & (hod[c] == kk[1]) & np.isfinite(R[c])]
                cand[kk] = c
            draws = np.column_stack([rng.choice(cand[kk], n_placebo) for kk in keys])
            xx = R[draws]
            pdw = (xx * ww).sum(1) / ww.sum() if ww is not None else xx.mean(1)
            spacing_h = np.median(np.diff(np.sort(sel))) if len(sel) > 2 else h
            lags = int(np.ceil(h / max(spacing_h, 1)))
            _, t_nw = nw_mean_t(x - drift, lags)
            out.append({"h": h, "n": int(len(sel)), "mean_pct": 100 * mean, "drift_pct": 100 * drift,
                        "abn_pct": 100 * (mean - drift), "median_pct": 100 * float(np.median(x)),
                        "hit_vs_drift": float((x > drift).mean()),
                        "p_circ": float((pm >= mean).mean()), "p_dow": float((pdw >= mean).mean()),
                        "placebo_circ_mean_pct": 100 * float(pm.mean()), "t_nw": t_nw, "nw_lags": lags})
        return pd.DataFrame(out)
