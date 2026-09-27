"""Extended IS-only event studies for the mean_reversion family (design stage).

Every function loads the full history but keeps ONLY rows before 2025-01-01 (IS) before computing
statistics. Forward returns are measured from open[t+1] to close[t+h], normalized by ATR(14)[t],
and signed in the FADE direction unless stated otherwise. Overlapping events inflate t-stats:
read them as descriptive, not as significance tests.

    python3 -m strategies.mean_reversion_events_ext   -> results/mean_reversion_events_ext_IS.json
"""
import io
import json
import sys
from contextlib import redirect_stdout

def ev2(tf=None):
    # IS-only: event study in ATR units with session / weekend / vol-regime conditioning
    import sys, numpy as np, pandas as pd
    import strategies.mean_reversion as M
    from strategies.mean_reversion_analysis import events_frame
    from bt.data import SYMBOLS, load
    from bt.engine import IS_END
    fr = []
    for s in SYMBOLS:
        df = load(s, tf, dvol=True)
        f = events_frame(df); f['sym'] = s
        f['hour'] = df.index.hour; f['wd'] = df.index.dayofweek
        fr.append(f[f.index < IS_END])
    F = pd.concat(fr)
    for h in (1, 4, 12, 24):
        F[f'a{h}'] = F[f'fwd{h}'] / F['atr_bps']
    def show(name, ms, ml):
        a = F[ms].assign(sg=-1.0); b = F[ml].assign(sg=1.0); ab = pd.concat([a, b])
        row = []
        for h in (1, 4, 12, 24):
            x = (ab['sg'] * ab[f'a{h}']).dropna()
            row.append(f"a{h} {x.mean():+.3f} (t{x.mean()/x.std()*np.sqrt(len(x)):+.1f})")
        print(name[:44].ljust(44), f"n{len(ab):6d}", ' | '.join(row))
    z = F['z']; sess = pd.cut(F['hour'], [-1, 7, 12, 20, 23], labels=['asia', 'eu', 'us', 'late'])
    show('z>=2.5', z >= 2.5, z <= -2.5)
    for s_ in ['asia', 'eu', 'us', 'late']:
        show(f'z>=2.5 {s_}', (z >= 2.5) & (sess == s_), (z <= -2.5) & (sess == s_))
    show('z>=2.5 weekend', (z >= 2.5) & (F.wd >= 5), (z <= -2.5) & (F.wd >= 5))
    show('z>=2.5 weekday', (z >= 2.5) & (F.wd < 5), (z <= -2.5) & (F.wd < 5))
    show('bb reenter', F.reenter_s, F.reenter_l)
    for nm, reg in [('adx<20', F.adx < 20), ('adx>=30', F.adx >= 30), ('dvr<0.3', F.dvr < 0.3), ('dvr>=0.7', F.dvr >= 0.7), ('er<0.2', F.er < 0.2)]:
        show(f'bb reenter & {nm}', F.reenter_s & reg, F.reenter_l & reg)
    for s_ in ['asia', 'eu', 'us', 'late']:
        show(f'bb reenter {s_}', F.reenter_s & (sess == s_), F.reenter_l & (sess == s_))
    show('1bar>=2.5ATR', F.m1 >= 2.5, F.m1 <= -2.5)
    show('1bar>=2ATR', F.m1 >= 2, F.m1 <= -2)
    show('1bar>=3ATR', F.m1 >= 3, F.m1 <= -3)
    show('rsi2 WITH 4h trend', (F.tr4h < 0) & (F.r2 > 90) & (F.m3 >= 1.5), (F.tr4h > 0) & (F.r2 < 10) & (F.m3 <= -1.5))
    show('rsi2 WITH 4h, m3>=2.5', (F.tr4h < 0) & (F.r2 > 90) & (F.m3 >= 2.5), (F.tr4h > 0) & (F.r2 < 10) & (F.m3 <= -2.5))
    show('CONTROL follow 4h', F.tr4h < 0, F.tr4h > 0)
    show('CONTROL long', pd.Series(False, index=F.index), pd.Series(True, index=F.index))
    show('vwap dev>=3', F.dev >= 3, F.dev <= -3)
    show('vwap dev>=3 asia', (F.dev >= 3) & (sess == 'asia'), (F.dev <= -3) & (sess == 'asia'))



def ev3(tf=None):
    # IS-only robustness of the "quiet-hours fade" observation (15m)
    import sys, numpy as np, pandas as pd
    from strategies.mean_reversion_analysis import events_frame
    from bt.data import SYMBOLS, load
    from bt.engine import IS_END
    fr = []
    for s in SYMBOLS:
        df = load(s, tf, dvol=True)
        f = events_frame(df); f['sym'] = s
        f['hour'] = df.index.hour; f['wd'] = df.index.dayofweek; f['yr'] = df.index.year
        fr.append(f[f.index < IS_END])
    F = pd.concat(fr)
    for h in (1, 4, 12, 24):
        F[f'a{h}'] = F[f'fwd{h}'] / F['atr_bps']
    F['quiet'] = (F.hour < 8) | (F.wd >= 5)
    def stats(ab, h):
        x = (ab['sg'] * ab[f'a{h}']).dropna()
        return f"{x.mean():+.3f}(t{x.mean()/x.std()*np.sqrt(len(x)):+.1f},n{len(x)})"
    def show(name, ms, ml, by=None):
        ab = pd.concat([F[ms].assign(sg=-1.0), F[ml].assign(sg=1.0)])
        print(name.ljust(40), ' '.join(f"a{h} {stats(ab,h)}" for h in (4, 12, 24)))
        if by:
            for k, g in ab.groupby(by):
                print('   ', str(k).ljust(10), ' '.join(f"a{h} {stats(g,h)}" for h in (4, 12, 24)))
    z = F.z
    show('z>=2.5 quiet(asia|weekend)', (z >= 2.5) & F.quiet, (z <= -2.5) & F.quiet, 'yr')
    ab = pd.concat([F[(z >= 2.5) & F.quiet].assign(sg=-1.0), F[(z <= -2.5) & F.quiet].assign(sg=1.0)])
    print('  per symbol a12:', {s: round(float((g.sg*g.a12).mean()),3) for s, g in ab.groupby('sym')})
    print('  long a12', stats(ab[ab.sg>0],12), ' short a12', stats(ab[ab.sg<0],12))
    show('z>=2.5 active(weekday 8-24)', (z >= 2.5) & ~F.quiet, (z <= -2.5) & ~F.quiet, 'yr')
    show('bb reenter quiet', F.reenter_s & F.quiet, F.reenter_l & F.quiet, 'yr')
    show('bb reenter active', F.reenter_s & ~F.quiet, F.reenter_l & ~F.quiet, 'yr')
    show('z>=2 quiet', (z >= 2) & F.quiet, (z <= -2) & F.quiet)
    show('z>=3 quiet', (z >= 3) & F.quiet, (z <= -3) & F.quiet)



def ev4(tf=None):
    # IS-only: does the realized/implied vol ratio condition the fade? (rank of RV24h/DVOL over 60d)
    import sys, numpy as np, pandas as pd
    import strategies.mean_reversion as M
    from strategies.mean_reversion_analysis import events_frame
    from bt.data import SYMBOLS, load
    from bt.engine import IS_END
    fr = []
    for s in SYMBOLS:
        df = load(s, tf, dvol=True)
        f = events_frame(df); f['sym'] = s; f['yr'] = df.index.year
        k = M.bars(df, 24)
        rv = np.sqrt((np.log(df.close).diff() ** 2).rolling(k).sum() * 365) * 100
        ratio = rv / df['dvol']
        ct = df.index + pd.Timedelta(minutes=M.bar_minutes(df))
        f['vrr'] = M.roll_rank(ratio[ct.minute == 0], 24 * 60).reindex(df.index).ffill()
        fr.append(f[f.index < IS_END])
    F = pd.concat(fr)
    for h in (1, 4, 12, 24):
        F[f'a{h}'] = F[f'fwd{h}'] / F['atr_bps']
    def stats(ab, h):
        x = (ab['sg'] * ab[f'a{h}']).dropna()
        return f"{x.mean():+.3f}(t{x.mean()/x.std()*np.sqrt(len(x)):+.1f},n{len(x)})"
    def show(name, ms, ml):
        ab = pd.concat([F[ms].assign(sg=-1.0), F[ml].assign(sg=1.0)])
        print(name.ljust(34), ' '.join(f"a{h} {stats(ab,h)}" for h in (1, 4, 12, 24)))
        for k, g in ab.groupby('yr'):
            print('   ', k, ' '.join(f"a{h} {stats(g,h)}" for h in (4, 12)))
    z = F.z
    for nm, reg in [('vrr<0.3', F.vrr < 0.3), ('vrr>0.7', F.vrr > 0.7), ('vrr>0.9', F.vrr > 0.9)]:
        show(f'z>=2.5 & {nm}', (z >= 2.5) & reg, (z <= -2.5) & reg)
        show(f'bb reenter & {nm}', F.reenter_s & reg, F.reenter_l & reg)



def ev5(tf=None):
    # IS-only: (i) volume-conditioned reversal (Campbell-Grossman-Wang), (ii) alt residual vs BTC reversal
    import sys, numpy as np, pandas as pd
    import strategies.mean_reversion as M
    from bt.data import SYMBOLS, load
    from bt.engine import IS_END
    from bt.features import atr
    btc = load('BTCUSDT', tf)
    rb = np.log(btc.close).diff()
    rows = []
    for s in SYMBOLS:
        df = load(s, tf)
        A = atr(df); c, o = df.close, df.open
        k = M.bars(df, 1) if tf == '15m' else 1   # 1 hour move
        mv = (c - c.shift(k)) / (A.shift(k) * np.sqrt(k))
        v = df.volume.rolling(k).sum()
        # seasonal volume ratio: same hour over previous 20 days
        hr = df.index.hour * 60 + df.index.minute
        base = v.groupby(hr).transform(lambda x: x.shift(1).rolling(20, min_periods=10).median())
        vr = v / base
        f = pd.DataFrame({'mv': mv, 'vr': vr, 'atr_bps': 1e4 * A / c, 'sym': s, 'yr': df.index.year}, index=df.index)
        for h in (1, 4, 12, 24):
            f[f'a{h}'] = (c.shift(-h) - o.shift(-1)) / o.shift(-1) * 1e4 / f['atr_bps']
        if s != 'BTCUSDT':
            r = np.log(c).diff()
            n = M.bars(df, 24 * 7)
            cov = r.rolling(n).cov(rb.reindex(r.index)); var = rb.reindex(r.index).rolling(n).var()
            beta = cov / var
            kk = M.bars(df, 4)
            res = r.rolling(kk).sum() - beta * rb.reindex(r.index).rolling(kk).sum()
            f['rz'] = res / (r - beta * rb.reindex(r.index)).rolling(n).std() / np.sqrt(kk)
        else:
            f['rz'] = np.nan
        rows.append(f[f.index < IS_END])
    F = pd.concat(rows)
    def stats(ab, h):
        x = (ab['sg'] * ab[f'a{h}']).dropna()
        return f"{x.mean():+.3f}(t{x.mean()/x.std()*np.sqrt(len(x)):+.1f},n{len(x)})"
    def show(name, ms, ml, by='yr'):
        ab = pd.concat([F[ms].assign(sg=-1.0), F[ml].assign(sg=1.0)])
        print(name.ljust(36), ' '.join(f"a{h} {stats(ab,h)}" for h in (1, 4, 12, 24)))
        if by:
            for kk, g in ab.groupby(by):
                print('    ', kk, ' '.join(f"a{h} {stats(g,h)}" for h in (4, 12)))
    m = F.mv
    show('1h move>=2 fade, all', m >= 2, m <= -2)
    show('1h move>=2 fade, LOW vol (vr<1)', (m >= 2) & (F.vr < 1.0), (m <= -2) & (F.vr < 1.0))
    show('1h move>=2 fade, HIGH vol (vr>3)', (m >= 2) & (F.vr > 3), (m <= -2) & (F.vr > 3))
    show('1h move>=1.5 fade, LOW vol (vr<0.8)', (m >= 1.5) & (F.vr < 0.8), (m <= -1.5) & (F.vr < 0.8))
    show('alt 4h residual z>=2.5 fade', F.rz >= 2.5, F.rz <= -2.5)
    show('alt 4h residual z>=3.5 fade', F.rz >= 3.5, F.rz <= -3.5)



def ev6(tf=None):
    # IS-only: slower z-score reversion on 1h bars (window 2-5 days, hold 1-3 days)
    import sys, numpy as np, pandas as pd
    import strategies.mean_reversion as M
    from bt.data import SYMBOLS, load
    from bt.engine import IS_END
    from bt.features import atr
    rows = []
    for s in SYMBOLS:
        df = load(s, '1h', dvol=True)
        c, o = df.close, df.open
        A = atr(df)
        f = pd.DataFrame({'atr_bps': 1e4 * A / c, 'yr': df.index.year, 'sym': s}, index=df.index)
        for n in (48, 120):
            m, sd = c.rolling(n).mean(), c.rolling(n).std()
            f[f'z{n}'] = (c - m) / sd
        f['adx'] = M.adx(df); f['dvr'] = M.dvol_rank(df)
        for h in (12, 24, 72):
            f[f'a{h}'] = (c.shift(-h) - o.shift(-1)) / o.shift(-1) * 1e4 / f['atr_bps']
        rows.append(f[f.index < IS_END])
    F = pd.concat(rows)
    def stats(ab, h):
        x = (ab['sg'] * ab[f'a{h}']).dropna()
        return f"{x.mean():+.3f}(t{x.mean()/x.std()*np.sqrt(len(x)):+.1f},n{len(x)})"
    def show(name, ms, ml):
        ab = pd.concat([F[ms].assign(sg=-1.0), F[ml].assign(sg=1.0)])
        print(name.ljust(30), ' '.join(f"a{h} {stats(ab,h)}" for h in (12, 24, 72)))
        for k, g in ab.groupby('yr'):
            print('    ', k, ' '.join(f"a{h} {stats(g,h)}" for h in (24, 72)))
    for n in (48, 120):
        z = F[f'z{n}']
        first_s = (z >= 2.5) & ~(z.shift(1) >= 2.5); first_l = (z <= -2.5) & ~(z.shift(1) <= -2.5)
        show(f'z{n}>=2.5 first cross', first_s, first_l)
        show(f'z{n}>=2.5 & adx<20', first_s & (F.adx < 20), first_l & (F.adx < 20))
        show(f'z{n}>=2.5 & dvr<0.5', first_s & (F.dvr < 0.5), first_l & (F.dvr < 0.5))
    print('--- follow-signed long/short split, z120 first cross (IS)')
    z = F['z120']
    fs = (z >= 2.5) & ~(z.shift(1) >= 2.5); fl = (z <= -2.5) & ~(z.shift(1) <= -2.5)
    for nm, m, sg in [('up-break long', fs, 1.0), ('down-break short', fl, -1.0)]:
        for reg_nm, reg in [('all', F.dvr > -1), ('dvr<0.5', F.dvr < 0.5), ('dvr>=0.5', F.dvr >= 0.5)]:
            ab = F[m & reg].assign(sg=sg)
            print(nm, reg_nm, ' '.join(f"a{h} {stats(ab,h)}" for h in (24, 72)))



RUNS = [("ev2", "15m"), ("ev2", "1h"), ("ev3", "15m"), ("ev3", "1h"), ("ev4", "15m"), ("ev4", "1h"),
        ("ev5", "15m"), ("ev5", "1h"), ("ev6", None)]
DOC = {'ev2': 'session / weekend / regime splits (ATR units)', 'ev3': 'robustness of quiet-hours fade by year, symbol, side', 'ev4': 'realized/implied vol ratio conditioning', 'ev5': 'volume-conditioned reversal and alt residual vs BTC', 'ev6': 'slow z-score (2-5 day) reversion on 1h, with follow-signed long/short split'}


def main():
    out = {"note": "IS only (< 2025-01-01). Fade-signed forward returns in ATR units: a<h> = mean, t, n.", "runs": []}
    for fn, tf in RUNS:
        buf = io.StringIO()
        with redirect_stdout(buf):
            globals()[fn](tf)
        txt = buf.getvalue()
        print(f"== {fn} {tf}: {DOC[fn]}\n{txt}", flush=True)
        out["runs"].append({"study": fn, "tf": tf, "what": DOC[fn], "lines": txt.splitlines()})
    with open("results/mean_reversion_events_ext_IS.json", "w") as f:
        json.dump(out, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
