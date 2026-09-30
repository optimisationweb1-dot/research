"""macro_events: build the event calendar 2023-01..2026-08 with publication times (UTC).

Sources (raw copies saved under trading/data/ext/macro_events/raw/, downloaded 27.09.2026):
  FOMC      federalreserve.gov/monetarypolicy/fomccalendars.htm  (statement 2:00 p.m. ET, checked on
            statement pages 2023-02-01, 2025-03-19, 2025-12-10, 2026-09-16; press conference 2:30 p.m. ET)
  rates     FRED DFEDTARU (upper bound of the target range), DGS2 (2y UST, daily)
  CPI/NFP/PPI  bls.gov/bls/news-release/{cpi,empsit,ppi}.htm archive links (release date in URL),
            8:30 a.m. ET checked on 7 archived releases incl. the 2025 shutdown re-schedules
  PCE       ALFRED release dates rid=54 (alfred.stlouisfed.org/release/downloaddates?rid=54);
            8:30 a.m. ET except 2025-12-05 10:00 (BEA) and 2026-01-22 10:00 (BEA schedule)
  CPI nowcast  Cleveland Fed inflation nowcasting JSON (nowcast_month.json): last nowcast before
            the release and the "actual" series -> model-based surprise (NOT the press consensus)
  Political/regulatory: curated list below (each row: source URL + level + time precision)
  Truth Social: stiles/trump-truth-social-archive (S3 JSON, created_at from the Truth Social API;
            verified against the Mastodon snowflake id: id >> 16 = ms since epoch)

    python3 -m strategies.macro_events_calendar      (from trading/)
"""
import html
import json
import os
import re

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TRADING = os.path.dirname(HERE)
RAW = os.path.join(TRADING, "data", "ext", "macro_events", "raw")
OUT = os.path.join(TRADING, "research", "macro_events_events.csv")
OUT_TRUTH = os.path.join(TRADING, "research", "macro_events_truth_posts.csv")
ET = "America/New_York"
START, END = pd.Timestamp("2023-01-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC")
ACCESSED = "2026-09-27"


def et(date, hhmm):
    return pd.Timestamp(f"{date} {hhmm}").tz_localize(ET).tz_convert("UTC")


def fomc():
    t = open(os.path.join(RAW, "fomccal.html"), encoding="utf-8", errors="ignore").read()
    stm = sorted(set(re.findall(r"/newsevents/pressreleases/monetary(\d{8})a\.htm", t)))
    pres = set(re.findall(r"fomcpres+conf(\d{8})\.htm", t))
    mins = re.findall(r"fomcminutes(\d{8})\.htm\">HTML</a>\s*<br>\s*\(Released ([A-Za-z]+ \d+, \d{4})\)", t)
    rate = pd.read_csv(os.path.join(RAW, "fred_DFEDTARU.csv"))
    rate.columns = ["date", "upper"]
    rate["date"] = pd.to_datetime(rate["date"])
    rate = rate.set_index("date")["upper"]
    rows = []
    for s in stm:
        d = pd.Timestamp(s)
        if s < "20230101" or s not in pres:  # 2025-08-22 = notation vote on the longer-run goals statement, not a meeting
            continue
        before = rate[:d - pd.Timedelta(days=1)].iloc[-1]
        after = rate[d + pd.Timedelta(days=1):].iloc[0]
        bp = int(round((after - before) * 100))
        url = f"https://www.federalreserve.gov/newsevents/pressreleases/monetary{s}a.htm"
        base = dict(scheduled=1, time_precision="scheduled", direction_exante=0, value=bp,
                    value_name="rate_change_bp", source_url=url, source_level="[офиц.]")
        rows.append(dict(base, category="FOMC_STATEMENT", t_publish_utc=et(d.date(), "14:00"),
                         description=f"FOMC statement: {'hold' if bp == 0 else ('hike' if bp > 0 else 'cut')} {bp:+d} bp"))
        rows.append(dict(base, category="FOMC_PRESSER", t_publish_utc=et(d.date(), "14:30"),
                         source_url=f"https://www.federalreserve.gov/monetarypolicy/fomcpresconf{s}.htm",
                         description="FOMC press conference start (2:30 p.m. ET)"))
    for s, rel in mins:
        d = pd.Timestamp(rel)
        rows.append(dict(category="FOMC_MINUTES", t_publish_utc=et(d.date(), "14:00"), scheduled=1,
                         time_precision="scheduled", direction_exante=0, value=None, value_name=None,
                         description=f"FOMC minutes of {s[:4]}-{s[4:6]}-{s[6:]} meeting",
                         source_url=f"https://www.federalreserve.gov/monetarypolicy/fomcminutes{s}.htm",
                         source_level="[офиц.]"))
    return rows


def bls():
    rows = []
    for f, code in [("bls_cpi.html", "CPI"), ("bls_empsit.html", "NFP"), ("bls_ppi.html", "PPI")]:
        t = open(os.path.join(RAW, f), encoding="utf-8", errors="ignore").read()
        t = re.sub(r"<!--.*?-->", "", t, flags=re.S)  # future releases are commented out
        for href, d, txt in re.findall(r"<a href=\"(/news.release/archives/[a-z]+_(\d{8})\.htm)\">([^<]+)</a>", t):
            date = f"{d[4:]}-{d[:2]}-{d[2:4]}"
            rows.append(dict(category=code, t_publish_utc=et(date, "08:30"), scheduled=1,
                             time_precision="scheduled", direction_exante=0, value=None, value_name=None,
                             description=txt.strip(), ref_period=txt.strip().rsplit(" ", 3)[0] if code else None,
                             source_url="https://www.bls.gov" + href, source_level="[офиц.]"))
    return rows


def pce():
    txt = open(os.path.join(RAW, "alfred_rid54.txt")).read()
    dates = sorted(set(re.findall(r"^(20\d\d-\d\d-\d\d)\s*$", txt, flags=re.M)))
    rows = []
    for d in dates:
        hhmm, note = "08:30", ""
        if d in ("2025-12-05", "2026-01-22"):
            hhmm = "10:00"
            note = "BEA 10:00 a.m. ET (shutdown re-schedule)"
        if d == "2025-12-23":
            note = "data update with GDP Q3 initial (not a regular monthly PCE release)"
        rows.append(dict(category="PCE", t_publish_utc=et(d, hhmm), scheduled=1, time_precision="scheduled",
                         direction_exante=0, value=None, value_name=None,
                         description="Personal Income and Outlays (PCE) " + note,
                         source_url="https://alfred.stlouisfed.org/release/downloaddates?rid=54",
                         source_level="[офиц.]"))
    return rows


def cpi_nowcast():
    """Cleveland Fed: for each target month, last core-CPI nowcast before the release and the actual."""
    d = json.load(open(os.path.join(RAW, "cf_nowcast_month.json")))
    out = {}
    for e in d:
        sub = e["chart"]["subcaption"]  # target month, e.g. 2025-8
        cats = [c["label"] for c in e["categories"][0]["category"] if not c.get("vline")]
        ser = {ds["seriesname"]: [v.get("value", "") for v in ds["data"]] for ds in e["dataset"]}
        now, act = ser.get("Core CPI Inflation"), ser.get("Actual Core CPI Inflation")
        hnow, hact = ser.get("CPI Inflation"), ser.get("Actual CPI Inflation")
        if not now or not act:
            continue
        ia = [i for i, v in enumerate(act) if v != ""]
        if not ia:
            continue
        ia = ia[0]
        inow = [i for i, v in enumerate(now[:ia]) if v != ""]
        if not inow:
            continue
        y, m = map(int, sub.split("-"))
        out[(y, m)] = dict(core_actual=float(act[ia]), core_nowcast=float(now[inow[-1]]),
                           head_actual=float(hact[ia]) if hact and hact[ia] != "" else None,
                           head_nowcast=float(hnow[inow[-1]]) if hnow and hnow[inow[-1]] != "" else None,
                           cf_release_label=cats[ia] if ia < len(cats) else None)
    return out


MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                      "September", "October", "November", "December"], 1)}

# ----------------------------------------------------------------- curated political / regulatory events
# time_precision: exact = timestamp of the primary post/filing; approx = press time (+-15-60 min);
# date = only the date is reliable (used in daily analysis only).
# direction_exante: classified from the headline text only (pre-registered rule): +1 pro-crypto decision or
# tariff relief / risk-on; -1 tariff escalation, anti-crypto enforcement, hawkish surprise; 0 unclear.
TS = "https://truthsocial.com/@realDonaldTrump/"
CURATED = [
    # (t_utc, category, dir, description, precision, url, level)
    ("2023-06-05 15:00", "REGULATORY", -1, "SEC sues Binance and CZ (13 charges)", "date",
     "https://www.sec.gov/newsroom/press-releases/2023-101-sec-files-13-charges-against-binance-entities-founder-changpeng-zhao", "[офиц.] дата; время проверить"),
    ("2023-06-06 15:00", "REGULATORY", -1, "SEC sues Coinbase", "date",
     "https://www.sec.gov/newsroom/press-releases/2023-102", "[офиц.] дата; время проверить"),
    ("2023-06-15 20:43:42", "ETF", 1, "BlackRock iShares Bitcoin Trust S-1 accepted by EDGAR (16:43:42 ET)", "exact",
     "https://www.sec.gov/Archives/edgar/data/1980994/000143774923017574/0001437749-23-017574-index.htm", "[офиц.] EDGAR acceptance time"),
    ("2023-07-13 16:00", "REGULATORY", 1, "SEC v. Ripple: programmatic XRP sales not securities (Torres)", "date",
     "https://www.coindesk.com/policy/2023/07/13/sale-of-xrp-on-exchanges-not-investment-contracts-court-rules-in-sec-case-against-ripple", "[пресса] дата; время проверить"),
    ("2023-08-29 14:00", "ETF", 1, "DC Circuit: Grayscale wins vs SEC (GBTC conversion)", "date",
     "https://law.justia.com/cases/federal/appellate-courts/cadc/22-1142/22-1142-2023-08-29.html", "[офиц.] дата; время проверить"),
    ("2024-01-09 21:11", "ETF", 1, "Hacked @SECGov post: fake spot BTC ETF approval (4:11 p.m. ET)", "exact",
     "https://www.coindesk.com/business/2024/01/13/sec-statement-on-the-hack-of-its-x-account-and-the-resulting-fake-bitcoin-etf-approval-announcement", "[офиц.] SEC statement via [пресса]"),
    ("2024-01-10 21:00", "ETF", 1, "SEC approves 11 spot BTC ETFs (after 4 p.m. ET)", "approx",
     "https://www.sec.gov/newsroom/speeches-statements/gensler-statement-spot-bitcoin-011023", "[офиц.] дата; время ±30 мин проверить"),
    ("2024-05-20 19:20:27", "ETF", 1, "Bloomberg analysts raise spot ETH ETF approval odds 25%->75% (X post)", "exact",
     "https://x.com/EricBalchunas/status/1792636523050906102", "[пресса] время из snowflake ID"),
    ("2024-05-23 20:30", "ETF", 1, "SEC approves spot ETH ETF 19b-4 filings (afternoon ET)", "approx",
     "https://www.coindesk.com/markets/2024/05/23/sec-approves-spot-ether-etf-listing-still-needs-to-approve-products", "[пресса] время ±60 мин проверить"),
    ("2024-07-13 22:11", "POLITICAL", 1, "Assassination attempt on Trump in Butler, PA (6:11 p.m. ET), Trump odds up", "approx",
     "https://en.wikipedia.org/wiki/Attempted_assassination_of_Donald_Trump_in_Pennsylvania", "[пресса] проверить"),
    ("2024-07-27 21:00", "POLITICAL", 1, "Trump speech at Bitcoin 2024 Nashville (strategic stockpile promise)", "approx",
     TS + "112860519444352847", "[3P архив] RT 21:14 UTC"),
    ("2024-11-06 10:34", "POLITICAL", 1, "AP calls presidential race for Trump (5:34 a.m. EST)", "approx",
     "https://www.forbes.com/sites/saradorn/2024/11/06/election-2024-live-updates-donald-trump-wins-presidency-ap-projects/", "[пресса]; результат закладывался в цену всю ночь"),
    ("2025-01-18 02:00:51", "POLITICAL", 0, "Trump launches $TRUMP memecoin (Truth Social)", "exact",
     TS + "113846888132979151", "[3P архив Truth Social]"),
    ("2025-01-20 17:00", "POLITICAL", 0, "Inauguration oath (noon ET); no crypto in speech", "exact",
     "https://www.whitehouse.gov/", "[офиц.] расписание"),
    ("2025-01-23 21:00", "POLITICAL", 1, "EO 14178 Strengthening American Leadership in Digital Financial Technology", "date",
     "https://www.govinfo.gov/app/details/DCPD-202500169", "[офиц.] дата; время проверить"),
    ("2025-02-01 22:42:54", "TARIFF", -1, "Trump: 25% tariffs on Mexico/Canada, 10% on China implemented (IEEPA)", "exact",
     TS + "113931044424714413", "[3P архив Truth Social]; EO подписан раньше в тот же день"),
    ("2025-02-03 15:41:28", "TARIFF", 1, "Trump: Mexico tariffs paused one month after call with Sheinbaum", "exact",
     TS + "113940711907400754", "[3P архив Truth Social]"),
    ("2025-02-03 21:57:10", "TARIFF", 1, "Trump: Canada tariffs paused (border deal)", "exact",
     TS + "113942189236610107", "[3P архив Truth Social]"),
    ("2025-03-02 15:24:20", "POLITICAL", 1, "Trump: US Crypto Reserve incl. XRP, SOL, ADA (Sunday)", "exact",
     TS + "114093526901586124", "[3P архив Truth Social]"),
    ("2025-03-02 17:11:00", "POLITICAL", 1, "Trump: BTC and ETH will be the heart of the Reserve", "exact",
     TS + "114093946326587357", "[3P архив Truth Social]"),
    ("2025-03-07 00:11:37", "POLITICAL", 1, "Sacks: Trump signed EO on Strategic Bitcoin Reserve (forfeited BTC only, no purchases)", "exact",
     "https://x.com/davidsacks47/status/1897802280738734236", "[офиц. лицо] время из snowflake ID"),
    ("2025-04-02 20:00", "TARIFF", -1, "'Liberation Day' reciprocal tariffs, Rose Garden (4 p.m. ET)", "approx",
     "https://www.whitehouse.gov/presidential-actions/2025/04/regulating-imports-with-a-reciprocal-tariff-to-rectify-trade-practices-that-contribute-to-large-and-persistent-annual-united-states-goods-trade-deficits/", "[офиц.] дата; время [пресса] проверить"),
    ("2025-04-09 13:37:01", "TARIFF", 1, "Trump: 'THIS IS A GREAT TIME TO BUY!!!'", "exact",
     TS + "114308272725981913", "[3P архив Truth Social]"),
    ("2025-04-09 17:18:40", "TARIFF", 1, "Trump: 90-day pause of reciprocal tariffs (China raised to 125%)", "exact",
     TS + "114309144289505174", "[3P архив Truth Social]"),
    ("2025-05-12 07:00", "TARIFF", 1, "US-China Geneva joint statement: tariffs cut by 115 pp for 90 days (9:00 Geneva)", "approx",
     "https://www.whitehouse.gov/briefings-statements/2025/05/joint-statement-on-u-s-china-economic-and-trade-meeting-in-geneva/", "[офиц.] текст; время [пресса] проверить"),
    ("2025-07-18 20:00", "POLITICAL", 1, "GENIUS Act signed into law (expected)", "date",
     TS + "114876927258467384", "[3P архив Truth Social] пост 23:53 UTC"),
    ("2025-08-07 20:00", "POLITICAL", 1, "EO: alternative assets incl. crypto in 401(k) plans", "date",
     "https://www.ballardspahr.com/insights/alerts-and-articles/2025/08/eo-seeks-to-expand-access-to-crypto-and-private-investments-in-defined-contribution-plans", "[пресса] дата; время проверить"),
    ("2025-09-17 20:00", "ETF", 1, "SEC approves generic listing standards for commodity/crypto ETPs", "date",
     "https://www.dechert.com/knowledge/onpoint/2025/10/generic-listing-standards-for-crypto-and-commodity-etps--what-it.html", "[пресса] дата; время проверить"),
    ("2025-10-10 14:57:52", "TARIFF", -1, "Trump: China 'very hostile', threatens massive tariff increase", "exact",
     TS + "115350455734003647", "[3P архив Truth Social]"),
    ("2025-10-10 20:50:01", "TARIFF", -1, "Trump: additional 100% tariff on China from Nov 1 + software export controls", "exact",
     TS + "115351840469973590", "[3P архив Truth Social]"),
    ("2025-10-12 16:43:35", "TARIFF", 1, "Trump: 'Don't worry about China, it will all be fine!' (Sunday)", "exact",
     TS + "115362196088273474", "[3P архив Truth Social]"),
    ("2026-01-30 11:59", "POLITICAL", -1, "Trump nominates Kevin Warsh as Fed chair (Truth Social, 6:59 a.m. EST); seen as hawkish on balance sheet", "approx",
     "https://www.cnbc.com/2026/01/30/trump-nominates-kevin-warsh-for-federal-reserve-chair-to-succeed-jerome-powell.html", "[пресса] время проверить"),
    ("2026-02-20 15:00", "TARIFF", 1, "Supreme Court: IEEPA does not authorize tariffs (Learning Resources v. Trump), 10 a.m. ET opinion day", "approx",
     "https://www.congress.gov/crs-product/LSB11398", "[офиц.] дата; время проверить"),
]

# Fed chair speeches with market-moving potential (scheduled a few days ahead; 10:00 a.m. ET) - dates [офиц.]
FED_SPEECH = [
    ("2023-08-25 14:05", "Powell, Jackson Hole 2023", "https://www.federalreserve.gov/newsevents/speech/powell20230825a.htm"),
    ("2024-08-23 14:00", "Powell, Jackson Hole 2024 ('time has come')", "https://www.federalreserve.gov/newsevents/speech/powell20240823a.htm"),
    ("2025-08-22 14:00", "Powell, Jackson Hole 2025 (opens door to Sept cut)", "https://www.federalreserve.gov/newsevents/speech/powell20250822a.htm"),
]


def curated():
    rows = []
    for t, cat, d, desc, prec, url, lvl in CURATED:
        rows.append(dict(category=cat, t_publish_utc=pd.Timestamp(t, tz="UTC"), scheduled=0, time_precision=prec,
                         direction_exante=d, value=None, value_name=None, description=desc, source_url=url,
                         source_level=lvl))
    for t, desc, url in FED_SPEECH:
        rows.append(dict(category="FED_SPEECH", t_publish_utc=pd.Timestamp(t, tz="UTC"), scheduled=1,
                         time_precision="scheduled", direction_exante=0, value=None, value_name=None,
                         description=desc, source_url=url, source_level="[офиц.] дата; время по программе KC Fed проверить"))
    return rows


def truth_posts():
    d = pd.DataFrame(json.load(open(os.path.join(RAW, "truth_archive.json"))))
    d["ts"] = pd.to_datetime(d["created_at"], utc=True)
    d["id_ts"] = pd.to_datetime([int(x) >> 16 for x in d["id"]], unit="ms", utc=True)
    d["txt"] = d["content"].fillna("").map(lambda s: html.unescape(re.sub("<[^>]+>", " ", s)).strip())
    d["is_repost"] = d["txt"].str.startswith("RT ") | d["txt"].str.startswith("RT:")
    d["link_only"] = d["txt"].str.match(r"^https?://\S+$")
    kw = {"tariff": r"tariff", "china": r"\bchina\b|\bxi\b", "crypto": r"crypto|bitcoin|\bbtc\b|digital asset|stablecoin|genius act",
          "fed": r"\bfed\b|powell|interest rate|rate cut", "market": r"stock market|great time to buy|dow\b|nasdaq"}
    for k, p in kw.items():
        d["kw_" + k] = d["txt"].str.contains(p, case=False, regex=True)
    sel = d[(d["ts"] >= "2024-01-01") & ~d["is_repost"] & ~d["link_only"] &
            (d[[c for c in d if c.startswith("kw_")]].any(axis=1))].copy()
    sel = sel.sort_values("ts")
    # cluster: keep the first post of any 60-minute burst (later posts in a burst are not independent)
    first, last = [], None
    for t in sel["ts"]:
        first.append(last is None or (t - last) > pd.Timedelta(minutes=60))
        last = t if first[-1] else last
    sel["cluster_first"] = first
    sel["url"] = "https://truthsocial.com/@realDonaldTrump/" + sel["id"].astype(str)
    sel["id_minus_created_ms"] = (sel["id_ts"] - sel["ts"]).dt.total_seconds() * 1000
    cols = ["id", "ts", "url", "cluster_first", "id_minus_created_ms"] + [c for c in sel if c.startswith("kw_")] + ["txt"]
    sel["txt"] = sel["txt"].str.slice(0, 280)
    return sel[cols]


def main():
    rows = fomc() + bls() + pce() + curated()
    ev = pd.DataFrame(rows)
    ev["t_publish_utc"] = pd.to_datetime(ev["t_publish_utc"], utc=True)
    ev = ev[(ev["t_publish_utc"] >= START) & (ev["t_publish_utc"] < END)].copy()
    # CPI surprise vs Cleveland Fed nowcast (model expectation, not the consensus) + 2y yield change that day
    now = cpi_nowcast()
    dgs2 = pd.read_csv(os.path.join(RAW, "fred_DGS2.csv"))
    dgs2.columns = ["date", "dgs2"]
    dgs2["date"] = pd.to_datetime(dgs2["date"])
    dgs2["dgs2"] = pd.to_numeric(dgs2["dgs2"], errors="coerce")
    dgs2 = dgs2.dropna().set_index("date")["dgs2"]
    d2 = dgs2.diff() * 100  # bp
    for c in ["core_actual", "core_nowcast", "core_surprise_nowcast", "head_actual", "head_nowcast", "dgs2_change_bp"]:
        ev[c] = None
    for i, r in ev.iterrows():
        day = r["t_publish_utc"].tz_convert(ET).normalize().tz_localize(None)
        if day in d2.index:
            ev.at[i, "dgs2_change_bp"] = round(float(d2.loc[day]), 1)
        if r["category"] == "CPI":
            m = re.match(r"([A-Za-z]+) (\d{4})", r["description"])
            key = (int(m.group(2)), MONTHS[m.group(1)])
            if key in now:
                x = now[key]
                ev.at[i, "core_actual"] = round(x["core_actual"], 3)
                ev.at[i, "core_nowcast"] = round(x["core_nowcast"], 3)
                ev.at[i, "core_surprise_nowcast"] = round(x["core_actual"] - x["core_nowcast"], 3)
                ev.at[i, "head_actual"] = round(x["head_actual"], 3) if x["head_actual"] is not None else None
                ev.at[i, "head_nowcast"] = round(x["head_nowcast"], 3) if x["head_nowcast"] is not None else None
    ev["t_publish_et"] = ev["t_publish_utc"].dt.tz_convert(ET).dt.strftime("%Y-%m-%d %H:%M %Z")
    ev = ev.sort_values(["t_publish_utc", "category"]).reset_index(drop=True)
    ev.insert(0, "event_id", [f"E{i:04d}" for i in range(len(ev))])
    ev["accessed"] = ACCESSED
    ev["t_publish_utc"] = ev["t_publish_utc"].dt.strftime("%Y-%m-%d %H:%M:%S")
    cols = ["event_id", "category", "t_publish_utc", "t_publish_et", "scheduled", "time_precision",
            "direction_exante", "description", "value_name", "value", "core_actual", "core_nowcast",
            "core_surprise_nowcast", "head_actual", "head_nowcast", "dgs2_change_bp",
            "source_url", "source_level", "accessed"]
    ev[cols].to_csv(OUT, index=False)
    tp = truth_posts()
    tp.to_csv(OUT_TRUTH, index=False)
    print(ev.groupby("category").size().to_string())
    print("truth posts:", len(tp), "cluster-first:", int(tp["cluster_first"].sum()),
          "max |id-created| ms:", float(tp["id_minus_created_ms"].abs().max()))


if __name__ == "__main__":
    main()
