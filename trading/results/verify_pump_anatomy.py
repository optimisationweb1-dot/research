"""Adversarial verification of pump_anatomy (scanner A long/short decile portfolio and related claims).

    cd trading && OMP_NUM_THREADS=2 python3 results/verify_pump_anatomy.py [step]

Reads only the pump_anatomy cached panel/scores/funding (data/ext/pump_anatomy/, read-only).
Writes trading/results/verify_pump_anatomy_*.csv|json. Does not modify other agents' files.

Engine here is an independent matrix re-implementation:
  - decision at close of day d (features <= d), entry at px_exec[d] (01:00 UTC d+1), r[d] = px_exec[d+1]/px_exec[d]-1
  - mode "fixed": their convention (tranche weights constant, i.e. implicit daily rebalancing, cost on weight diffs)
  - mode "bh": buy-and-hold tranches (weights drift with price, short exposure grows when a coin pumps),
    cost on entry and on exit notional
  - funding "day": their calendar-day sum (fund_next); "exact": prints with ts in (01:00 d+1, 01:00 d+2]
"""
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
TR = os.path.dirname(HERE)
sys.path.insert(0, TR)
ROOT = os.path.join(TR, "data", "ext", "pump_anatomy")
OUT = HERE
IS_END = pd.Timestamp("2025-01-01", tz="UTC")
ALT_END = pd.Timestamp("2025-07-01", tz="UTC")
OOS_END = pd.Timestamp("2026-09-01", tz="UTC")
HARSH, EXTREME, BASE = 0.0011, 0.0025, 0.0007


def nw_t(x, lags):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 20:
        return np.nan
    u = x - x.mean()
    s = (u @ u) / n
    for L in range(1, lags + 1):
        s += 2 * (1 - L / (lags + 1)) * (u[L:] @ u[:-L]) / n
    return float(x.mean() / np.sqrt(s / n)) if s > 0 else np.nan


def block_boot_p(x, block=14, n=2000, seed=1):
    """One-sided p of mean<=0 by circular block bootstrap of the de-meaned series."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    rng = np.random.default_rng(seed)
    T = len(x)
    u = x - x.mean()
    nb = int(np.ceil(T / block))
    starts = rng.integers(0, T, size=(n, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n, -1)[:, :T] % T
    bm = u[idx].mean(1)
    return float((np.sum(bm >= x.mean()) + 1) / (n + 1))


# ------------------------------------------------------------------ data
def load():
    cols = ["date", "symbol", "elig", "elig2", "px_exec", "r_next", "fund_next", "close", "lr", "med30qv", "age",
            "ann14", "fund_last", "y7"]
    from strategies.pump_anatomy_features import FEATS
    prc = [f"pr_{f}" for f in FEATS]
    p = pd.read_parquet(os.path.join(ROOT, "panel.parquet"), columns=cols + prc)
    sc = pd.read_parquet(os.path.join(ROOT, "scores.parquet"))
    p = p.merge(sc, on=["date", "symbol"], how="left")
    p = p.sort_values(["symbol", "date"])
    p["vol30"] = p.groupby("symbol")["lr"].transform(lambda x: x.rolling(30, min_periods=20).std())
    return p


def mats(p):
    dates = pd.date_range(p["date"].min(), p["date"].max(), freq="1D", tz="UTC")
    syms = sorted(p["symbol"].unique())

    def M(col):
        return p.pivot_table(index="date", columns="symbol", values=col, aggfunc="first").reindex(
            index=dates, columns=syms)
    E = (M("elig").fillna(0).astype(bool) & M("px_exec").notna()).to_numpy()
    E2 = (M("elig2").fillna(0).astype(bool) & M("px_exec").notna()).to_numpy()
    R = M("r_next").to_numpy()
    F = M("fund_next").to_numpy()
    Q = M("med30qv").to_numpy()
    return dates, syms, E, E2, R, F, Q


def exact_funding(dates, syms):
    """Fx[d, s] = sum of funding prints with ts in (d+1 01:00, d+2 01:00]."""
    Fx = np.zeros((len(dates), len(syms)))
    d0 = dates[0]
    for j, s in enumerate(syms):
        fp = os.path.join(ROOT, "funding", f"{s}.parquet")
        if not os.path.exists(fp):
            continue
        f = pd.read_parquet(fp)
        if not len(f):
            continue
        ts = pd.to_datetime(f["ts"], utc=True)
        # print at time t belongs to holding day d with (d+1 01:00, d+2 01:00]  => d = floor(t - 1h - 1ns) - 1 day
        dd = (ts - pd.Timedelta(hours=1) - pd.Timedelta(microseconds=1)).dt.floor("1D") - pd.Timedelta(days=1)
        k = ((dd - d0).dt.days).to_numpy()
        ok = (k >= 0) & (k < len(dates))
        np.add.at(Fx[:, j], k[ok], f["funding"].to_numpy()[ok])
    return Fx


def select(S, E, frac, side, min_names=10):
    """Equal weights (sum 1) on top (side=+1) or bottom (side=-1) frac of eligible names per day."""
    W = np.zeros_like(S, dtype=float)
    Sm = np.where(E & np.isfinite(S), S, np.nan)
    for i in range(S.shape[0]):
        row = Sm[i]
        ok = np.flatnonzero(np.isfinite(row))
        n = len(ok)
        if n < min_names:
            continue
        # rank(pct, method='first') > 1-frac  <=> position among ascending order
        order = ok[np.argsort(row[ok], kind="stable")]
        rk = (np.arange(1, n + 1)) / n
        pick = order[rk > 1 - frac] if side > 0 else order[rk <= frac]
        if len(pick):
            W[i, pick] = 1.0 / len(pick)
    return W


def leg(W, R, F, hold, cost, mode="fixed", sign=1.0, cost_mat=None):
    """Daily leg returns (per unit of leg capital). Returns DataFrame-like dict of arrays."""
    T = W.shape[0]
    R0 = np.nan_to_num(R, nan=0.0)
    F0 = np.nan_to_num(F, nan=0.0)
    C = cost if cost_mat is None else cost_mat
    if mode == "fixed":
        Wt = np.zeros_like(W)
        cs = np.cumsum(W, axis=0)
        Wt = cs.copy()
        Wt[hold:] -= cs[:-hold]
        Wt /= hold
        gross = sign * (Wt * R0).sum(1)
        fund = -sign * (Wt * F0).sum(1)
        dW = np.abs(np.diff(Wt, axis=0, prepend=0.0))
        costv = -(dW * C).sum(1)
        active = Wt.sum(1) > 0
        return gross, fund, costv, active
    # buy and hold tranches: tranche started at d (weights W[d]) earns on days d..d+hold-1
    gross = np.zeros(T)
    fund = np.zeros(T)
    costv = np.zeros(T)
    V = W.copy()  # current value (relative) of each name in tranche started at row i
    active = np.zeros(T, bool)
    entry_cost = (W * C).sum(1)
    for k in range(hold):
        # contribution on day i+k from tranche i : V_k[i] * R[i+k]
        Rk = np.zeros_like(R0)
        Fk = np.zeros_like(F0)
        Rk[:T - k] = R0[k:]
        Fk[:T - k] = F0[k:]
        pnl = sign * (V * Rk).sum(1)
        fu = -sign * (V * Fk).sum(1)
        gross[k:] += pnl[:T - k] / hold
        fund[k:] += fu[:T - k] / hold
        active[k:] |= (W.sum(1) > 0)[:T - k]
        V = V * (1 + Rk)
    # V now = value after `hold` days; exit cost charged on the last holding day
    exit_cost = (V * C).sum(1)
    costv -= entry_cost / hold
    ec = np.zeros(T)
    ec[hold - 1:] = exit_cost[:T - hold + 1]
    costv -= ec / hold
    return gross, fund, costv, active


def ls_portfolio(S, E, R, F, frac=0.1, hold=7, cost=HARSH, mode="fixed", cost_mat=None, legs="ls"):
    WL = select(S, E, frac, +1)
    WS = select(S, E, frac, -1)
    gL, fL, cL, aL = leg(WL, R, F, hold, cost, mode, +1.0, cost_mat)
    gS, fS, cS, aS = leg(WS, R, F, hold, cost, mode, -1.0, cost_mat)
    if legs == "long":
        g, f, c, a = gL, fL, cL, aL
    elif legs == "short":
        g, f, c, a = gS, fS, cS, aS
    else:
        g, f, c, a = (gL + gS) / 2, (fL + fS) / 2, (cL + cS) / 2, aL | aS
    return g, f, c, a


def summarize(dates, g, f, c, a, hold, start=None, end=None, with_funding=True):
    net = g + (f if with_funding else 0) + c
    m = a.copy()
    if start is not None:
        m &= dates >= start
    if end is not None:
        m &= dates < end
    x = net[m]
    return {"n": int(m.sum()), "net_pct_day": round(100 * x.mean(), 4), "t_nw": round(nw_t(x, hold + 2), 2),
            "gross_pct_day": round(100 * g[m].mean(), 4), "fund_pct_day": round(100 * f[m].mean(), 4),
            "cost_pct_day": round(100 * c[m].mean(), 4)}


PERIODS = {"IS": (None, IS_END), "OOS": (IS_END, OOS_END), "altIS<2025-07": (None, ALT_END),
           "altOOS>=2025-07": (ALT_END, OOS_END)}


def score_mat(p, col, dates, syms):
    return p.pivot_table(index="date", columns="symbol", values=col, aggfunc="first").reindex(
        index=dates, columns=syms).to_numpy()


# ------------------------------------------------------------------ steps
def main():
    p = load()
    dates, syms, E, E2, R, F, Q = mats(p)
    Fx = exact_funding(dates, syms)
    SA = score_mat(p, "score_A", dates, syms)
    SC = score_mat(p, "score_C", dates, syms)
    SV = score_mat(p, "vol30", dates, syms)
    res = {}
    rows = []

    def run(tag, S, **kw):
        g, f, c, a = ls_portfolio(S, kw.pop("E", E), R, kw.pop("F", F), **kw)
        for per, (s0, s1) in PERIODS.items():
            rows.append({"variant": tag, "period": per, **summarize(dates, g, f, c, a, kw.get("hold", 7), s0, s1)})
        return g, f, c, a

    # 1) reproduction of their numbers (fixed weights, calendar-day funding)
    run("A_repro_fixed_dayfund", SA)
    # 2) exact funding timing
    run("A_fixed_exactfund", SA, F=Fx)
    # 3) buy-and-hold tranches + exact funding (primary verification variant)
    gA, fA, cA, aA = run("A_bh_exactfund", SA, F=Fx, mode="bh")
    run("A_bh_exactfund_extreme", SA, F=Fx, mode="bh", cost=EXTREME)
    # liquidity-tiered cost: 0.11% if med30qv>=10M, 0.25% if 2-10M, plus 0.5% for names with med30qv<5M
    cm = np.where(np.nan_to_num(Q) >= 10e6, HARSH, np.where(np.nan_to_num(Q) >= 5e6, EXTREME, 0.0075))
    run("A_bh_exactfund_liqtiered", SA, F=Fx, mode="bh", cost_mat=cm)
    run("A_bh_exactfund_L2", SA, F=Fx, mode="bh", E=E2)
    run("A_bh_long_only", SA, F=Fx, mode="bh", legs="long")
    run("A_bh_short_only", SA, F=Fx, mode="bh", legs="short")
    run("C_bh_exactfund", SC, F=Fx, mode="bh")
    run("vol30_bh_exactfund", SV, F=Fx, mode="bh")
    # neighbours
    for fr in (0.05, 0.2, 0.3):
        run(f"A_bh_frac{fr}", SA, F=Fx, mode="bh", frac=fr)
    for h in (1, 3, 5, 10, 14):
        run(f"A_bh_hold{h}", SA, F=Fx, mode="bh", hold=h)
    # one extra day of delay (decide d, trade at d+1 01:00)
    SA_d = np.vstack([np.full((1, SA.shape[1]), np.nan), SA[:-1]])
    E_d = np.vstack([np.zeros((1, E.shape[1]), bool), E[:-1]]) & E
    run("A_bh_delay1d", SA_d, F=Fx, mode="bh", E=E_d)
    # clipping
    Rc = np.clip(R, -0.5, 0.5)
    g, f, c, a = ls_portfolio(SA, E, Rc, Fx, mode="bh")
    for per, (s0, s1) in PERIODS.items():
        rows.append({"variant": "A_bh_clip50", "period": per, **summarize(dates, g, f, c, a, 7, s0, s1)})
    tab = pd.DataFrame(rows)
    tab.to_csv(os.path.join(OUT, "verify_pump_anatomy_variants.csv"), index=False)
    with pd.option_context("display.width", 250, "display.max_rows", 500):
        print(tab.to_string())

    # ---- regressions: beta to EW market, spanning vs vol30 L/S
    mkt = np.array([np.nanmean(np.where(E[i], R[i], np.nan)) if E[i].any() else np.nan for i in range(len(dates))])
    netA = gA + fA + cA
    gV, fV, cV, aV = ls_portfolio(SV, E, R, Fx, mode="bh")
    netV = gV + fV + cV
    reg = {}
    for per, (s0, s1) in (("IS", (None, IS_END)), ("OOS", (IS_END, OOS_END))):
        m = aA & np.isfinite(mkt)
        if s0 is not None:
            m &= dates >= s0
        m &= dates < s1
        y = netA[m]
        X = np.column_stack([np.ones(m.sum()), mkt[m]])
        b = np.linalg.lstsq(X, y, rcond=None)[0]
        resid = y - X @ b
        X2 = np.column_stack([np.ones(m.sum()), mkt[m], netV[m]])
        b2 = np.linalg.lstsq(X2, y, rcond=None)[0]
        resid2 = y - X2 @ b2
        reg[per] = {"beta_EW": round(float(b[1]), 3), "alpha_pct_day": round(100 * float(b[0]), 4),
                    "alpha_t_nw": round(nw_t(resid + b[0], 9), 2),
                    "span_vol30_beta": round(float(b2[2]), 3), "span_alpha_pct_day": round(100 * float(b2[0]), 4),
                    "span_alpha_t_nw": round(nw_t(resid2 + b2[0], 9), 2),
                    "block_boot_p_net": round(block_boot_p(y), 4)}
    res["regressions_A_bh_exactfund"] = reg
    print(json.dumps(reg, indent=1))

    # ---- by year / half-year
    s = pd.Series(netA, index=dates)[aA]
    res["A_bh_by_halfyear_pct_day"] = {f"{y}H{h}": round(100 * v, 4) for (y, h), v in
                                       s.groupby([s.index.year, (s.index.month > 6) + 1]).mean().items()}
    res["A_bh_by_halfyear_t"] = {f"{y}H{h}": round(nw_t(v.to_numpy(), 9), 2) for (y, h), v in
                                 s.groupby([s.index.year, (s.index.month > 6) + 1])}

    # ---- concentration & excluding top events (OOS, bh, exact funding)
    WL = select(SA, E, 0.1, +1)
    WS = select(SA, E, 0.1, -1)
    contrib = np.zeros_like(R)
    R0 = np.nan_to_num(R)
    for W, sg in ((WL, 1.0), (WS, -1.0)):
        V = W.copy()
        T = W.shape[0]
        for k in range(7):
            Rk = np.zeros_like(R0)
            Rk[:T - k] = R0[k:]
            c_ = sg * V * Rk / 7 / 2
            contrib[k:] += c_[:T - k]
            V = V * (1 + Rk)
    oos = (dates >= IS_END) & (dates < OOS_END)
    C = pd.DataFrame(contrib[oos], index=dates[oos], columns=syms)
    st = C.stack()
    st = st[st != 0].sort_values(ascending=False)
    bysym = C.sum().sort_values(ascending=False)
    tot = float(st.sum())
    res["concentration_OOS_gross"] = {"total": round(tot, 4), "top3_symdays": round(float(st.head(3).sum()), 4),
                                      "top10_symdays": round(float(st.head(10).sum()), 4),
                                      "top50_symdays": round(float(st.head(50).sum()), 4),
                                      "top3_symbols": {k: round(float(v), 4) for k, v in bysym.head(3).items()},
                                      "top10_symbols": {k: round(float(v), 4) for k, v in bysym.head(10).items()},
                                      "top_symdays": [(str(a.date()), b, round(float(v), 4)) for (a, b), v in st.head(10).items()]}
    extra = []
    # exclude top-3 / top-10 symbols entirely (from both legs; universe re-ranked)
    for n in (3, 10):
        drop = [syms.index(sy) for sy in bysym.head(n).index]
        Ex = E.copy()
        Ex[:, drop] = False
        g, f, c, a = ls_portfolio(SA, Ex, R, Fx, mode="bh")
        for per, (s0, s1) in PERIODS.items():
            extra.append({"variant": f"A_bh_excl_top{n}_symbols", "period": per, **summarize(dates, g, f, c, a, 7, s0, s1)})
    # exclude the top-3 pump events: zero the returns of the top-3 symbols over +-7 days around their best OOS day
    Rz = R.copy()
    for (d, sy), _ in st.head(3).items():
        i = dates.get_loc(d)
        Rz[max(0, i - 7):i + 8, syms.index(sy)] = 0.0
    g, f, c, a = ls_portfolio(SA, E, Rz, Fx, mode="bh")
    for per, (s0, s1) in PERIODS.items():
        extra.append({"variant": "A_bh_excl_top3_events(+-7d)", "period": per, **summarize(dates, g, f, c, a, 7, s0, s1)})
    ex = pd.DataFrame(extra)
    ex.to_csv(os.path.join(OUT, "verify_pump_anatomy_exclusions.csv"), index=False)
    print(ex.to_string())
    json.dump(res, open(os.path.join(OUT, "verify_pump_anatomy_main.json"), "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))


def placebo(nrep=200, kinds=("iid", "circshift", "persist30"), tag=""):
    """Null distributions for the OOS L/S net (bh, exact funding, harsh):
    (a) iid random scores each day (the original placebo; high turnover -> cost-biased null)
    (b) circular time-shift of score_A within each symbol by a random offset >= 90 days (keeps persistence,
        cross-sectional dispersion and turnover; breaks alignment with future returns)
    (c) random per-symbol scores held fixed for 30 days (persistent random ranks)
    Reported for net and gross."""
    p = load()
    dates, syms, E, E2, R, F, Q = mats(p)
    Fx = exact_funding(dates, syms)
    SA = score_mat(p, "score_A", dates, syms)
    oos = (dates >= IS_END) & (dates < OOS_END)
    alt = (dates >= ALT_END) & (dates < OOS_END)

    def stat(S):
        g, f, c, a = ls_portfolio(S, E, R, Fx, mode="bh")
        net = g + f + c
        return (float(net[oos & a].mean()), float(g[oos & a].mean()), float(net[alt & a].mean()))
    obs = stat(SA)
    rng = np.random.default_rng(7)
    out = {"obs": {"OOS_net": obs[0], "OOS_gross": obs[1], "altOOS_net": obs[2]}}
    T, N = SA.shape
    for kind in kinds:
        null = []
        for r in range(nrep):
            if kind == "iid":
                S = np.where(np.isfinite(SA), rng.random(SA.shape), np.nan)
            elif kind == "circshift":
                S = np.full_like(SA, np.nan)
                for j in range(N):
                    col = SA[:, j]
                    ok = np.flatnonzero(np.isfinite(col))
                    if len(ok) < 2:
                        continue
                    v = col[ok]
                    # offset in [90, len-90]: neither near-past nor near-future scores (the 30d features of a
                    # score from t+5 would contain the future returns of t..t+5 -> leakage)
                    if len(v) < 200:
                        S[ok, j] = rng.permutation(v)  # short histories: full permutation
                        continue
                    k = rng.integers(90, len(v) - 90)
                    S[ok, j] = np.roll(v, k)
            else:
                blocks = np.arange(T) // 30
                draws = rng.random((blocks.max() + 1, N))
                S = np.where(np.isfinite(SA), draws[blocks], np.nan)
            null.append(stat(S))
        null = np.array(null)
        out[kind] = {
            "null_mean_OOS_net": round(100 * null[:, 0].mean(), 4), "null_sd_OOS_net": round(100 * null[:, 0].std(), 4),
            "p_OOS_net": float((np.sum(null[:, 0] >= obs[0]) + 1) / (nrep + 1)),
            "null_mean_OOS_gross": round(100 * null[:, 1].mean(), 4), "null_sd_OOS_gross": round(100 * null[:, 1].std(), 4),
            "p_OOS_gross": float((np.sum(null[:, 1] >= obs[1]) + 1) / (nrep + 1)),
            "null_mean_altOOS_net": round(100 * null[:, 2].mean(), 4),
            "p_altOOS_net": float((np.sum(null[:, 2] >= obs[2]) + 1) / (nrep + 1)), "nrep": nrep}
        print(kind, out[kind], flush=True)
    out["obs"] = {k: round(100 * v, 4) for k, v in out["obs"].items()}
    json.dump(out, open(os.path.join(OUT, f"verify_pump_anatomy_placebo{tag}.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


def altsplit():
    """Refit scanner A (same spec) on labels realised before 2025-07-01, test 2025-07..2026-08."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from strategies.pump_anatomy_analysis import scanner_X
    p = load()
    dates, syms, E, E2, R, F, Q = mats(p)
    Fx = exact_funding(dates, syms)
    q = p[p["elig"]].copy()
    tr = q[(q["date"] <= pd.Timestamp("2025-06-23", tz="UTC")) & q["y7"].notna()]
    m = LogisticRegression(C=1.0, max_iter=2000).fit(scanner_X(tr), tr["y7"].astype(int))
    q["score_A2"] = m.predict_proba(scanner_X(q))[:, 1]
    te = q[(q["date"] >= ALT_END) & q["y7"].notna()]
    auc = {"A2_altOOS_AUC": round(float(roc_auc_score(te["y7"].astype(int), te["score_A2"])), 4),
           "A_orig_altOOS_AUC": round(float(roc_auc_score(te["y7"].astype(int), te["score_A"])), 4),
           "vol30_altOOS_AUC": round(float(roc_auc_score(te.dropna(subset=["vol30"])["y7"].astype(int),
                                                          te.dropna(subset=["vol30"])["vol30"])), 4)}
    p = p.merge(q[["date", "symbol", "score_A2"]], on=["date", "symbol"], how="left")
    S2 = score_mat(p, "score_A2", dates, syms)
    rows = []
    for tag, kw in (("A2_fixed_dayfund", {}), ("A2_bh_exactfund", {"mode": "bh", "F": Fx}),
                    ("A2_bh_exactfund_extreme", {"mode": "bh", "F": Fx, "cost": EXTREME})):
        FF = kw.pop("F", F)
        g, f, c, a = ls_portfolio(S2, E, R, FF, **kw)
        for per, (s0, s1) in (("altIS<2025-07(in-sample)", (None, ALT_END)), ("altOOS>=2025-07", (ALT_END, OOS_END))):
            rows.append({"variant": tag, "period": per, **summarize(dates, g, f, c, a, 7, s0, s1)})
            rows.append({"variant": tag + "_nofunding", "period": per,
                         **summarize(dates, g, f, c, a, 7, s0, s1, with_funding=False)})
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(OUT, "verify_pump_anatomy_altsplit.csv"), index=False)
    json.dump({"auc": auc, "coef": dict(zip(scanner_X(tr).columns, np.round(m.coef_[0], 3).tolist()))},
              open(os.path.join(OUT, "verify_pump_anatomy_altsplit.json"), "w"), indent=1)
    print(auc)
    print(t.to_string())


def announce_placebo(nrep=500):
    """Sell-the-news after Binance announcements: compare the 7d BTC-adjusted log return from entry with a
    random-date null for the same symbols (unconditional drift of alts vs BTC is strongly negative)."""
    ev = pd.read_csv(os.path.join(TR, "results", "pump_anatomy_announce_events.csv"))
    ev["pub"] = pd.to_datetime(ev["pub"], utc=True, format="ISO8601")
    from strategies.pump_anatomy_panel import load_1h
    btc = load_1h("BTCUSDT")["open"]
    rng = np.random.default_rng(3)
    rows = []
    cache = {}
    for cat in ("spot_list", "hodler", "add_margin_earn", "delist"):
        g = ev[(ev["cat"] == cat) & (ev["pub"] >= IS_END) & ev["abn168h"].notna()]
        if not len(g):
            continue
        obs = g["abn168h"].mean()
        nulls = []
        per_ev = []
        for _, r in g.iterrows():
            s = r["symbol"]
            if s not in cache:
                cache[s] = load_1h(s)["open"]
            h = cache[s]
            idx = h.index[(h.index >= IS_END) & (h.index < OOS_END - pd.Timedelta(days=8))]
            idx = idx[idx.hour == r["pub"].hour]
            vals = []
            for t in rng.choice(idx, size=min(nrep, len(idx)), replace=True) if len(idx) else []:
                t = pd.Timestamp(t)
                t2 = t + pd.Timedelta(hours=168)
                if t2 in h.index and t in btc.index and t2 in btc.index:
                    vals.append(np.log(h[t2] / h[t]) - np.log(btc[t2] / btc[t]))
            per_ev.append(np.array(vals))
        # null of the cross-event mean: draw one random date per event, nrep times
        L = min(len(v) for v in per_ev if len(v)) if per_ev else 0
        for k in range(nrep):
            nulls.append(np.mean([v[rng.integers(0, len(v))] for v in per_ev if len(v)]))
        nulls = np.array(nulls)
        rows.append({"cat": cat, "n": len(g), "obs_abn7d_pct": round(100 * obs, 2),
                     "null_mean_pct": round(100 * nulls.mean(), 2), "null_sd_pct": round(100 * nulls.std(), 2),
                     "excess_vs_null_pct": round(100 * (obs - nulls.mean()), 2),
                     "p_lower": float((np.sum(nulls <= obs) + 1) / (nrep + 1)),
                     "obs_excl_worst3_pct": round(100 * g["abn168h"].sort_values().iloc[3:].mean(), 2)})
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(OUT, "verify_pump_anatomy_announce_placebo.csv"), index=False)
    print(t.to_string())


def fundconc():
    """Which symbols supply the OOS funding income of the L/S (bh, exact funding)?"""
    p = load()
    dates, syms, E, E2, R, F, Q = mats(p)
    Fx = exact_funding(dates, syms)
    SA = score_mat(p, "score_A", dates, syms)
    oos = (dates >= IS_END) & (dates < OOS_END)
    contrib = np.zeros_like(R)
    R0 = np.nan_to_num(R)
    for W, sg in ((select(SA, E, 0.1, +1), 1.0), (select(SA, E, 0.1, -1), -1.0)):
        V = W.copy()
        T = W.shape[0]
        for k in range(7):
            Rk = np.zeros_like(R0)
            Fk = np.zeros_like(Fx)
            Rk[:T - k] = R0[k:]
            Fk[:T - k] = Fx[k:]
            c_ = -sg * V * Fk / 7 / 2
            contrib[k:] += c_[:T - k]
            V = V * (1 + Rk)
    C = pd.DataFrame(contrib[oos], index=dates[oos], columns=syms)
    bys = C.sum().sort_values(ascending=False)
    tot = float(bys.sum())
    out = {"OOS_funding_total": round(tot, 4), "top3_symbols_share": round(float(bys.head(3).sum() / tot), 3),
           "top10_symbols_share": round(float(bys.head(10).sum() / tot), 3),
           "top10": {k: round(float(v), 4) for k, v in bys.head(10).items()},
           "funding_ex_top10_pct_day": round(100 * float(bys.iloc[10:].sum()) / int(oos.sum()), 4)}
    json.dump(out, open(os.path.join(OUT, "verify_pump_anatomy_fundconc.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"placebo_circ": lambda: placebo(200, ("circshift",), "_circ_noleak"), "fundconc": fundconc, "main": main, "placebo": placebo, "altsplit": altsplit, "announce": announce_placebo}[
        sys.argv[1] if len(sys.argv) > 1 else "main"]()
