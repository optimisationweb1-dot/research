"""pump_anatomy: top-30 pumps (by 7d peak gain, L1 events) with Binance announcements naming the asset
published in [onset-14d, peak] (timestamps from the Binance CMS feed). Web-sourced narrative labels are
added by hand in trading/research/pump_anatomy_top30_labels.csv (source, date, level).

    python3 -m strategies.pump_anatomy_catalysts
"""
import os

import pandas as pd

from strategies.pump_anatomy_analysis import RES, load_events
from strategies.pump_anatomy_features import title_assets
from strategies.pump_anatomy_panel import ROOT


def main(n=30):
    e = load_events().sort_values("peak_gain", ascending=False).head(n).copy()
    a = pd.read_csv(os.path.join(ROOT, "binance_announcements.csv"))
    a["pub"] = pd.to_datetime(a["published_utc"], utc=True, format="ISO8601")
    syms = pd.read_csv(os.path.join(ROOT, "symbols_use.csv"))["symbol"]
    known = set(syms.str.replace("USDT$", "", regex=True).str.replace(r"^1000000|^1000|^1M", "", regex=True))
    a["assets"] = a["title"].map(lambda t: title_assets(t, known))
    rows = []
    for _, r in e.iterrows():
        asset = r["symbol"][:-4]
        for pre in ("1000000", "1000", "1M"):
            if asset.startswith(pre):
                asset = asset[len(pre):]
        m = a[a["assets"].map(lambda s: asset in s) & (a["pub"] >= r["date"] - pd.Timedelta(days=14))
              & (a["pub"] <= r["peak_date"] + pd.Timedelta(days=1))]
        rows.append({"onset": r["date"].date(), "symbol": r["symbol"], "peak_gain_pct": round(100 * r["peak_gain"]),
                     "peak_date": r["peak_date"].date(), "med30_qv_musd": round(r["med30qv"] / 1e6, 1),
                     "age_days": int(r["age"]),
                     "ret_peak_to_30d_pct": round(100 * r["ret_peak_to_30d"]) if pd.notna(r["ret_peak_to_30d"]) else None,
                     "binance_ann": " | ".join(f"{x.pub:%Y-%m-%d %H:%M} UTC: {x.title} ({x.url})" for x in m.itertuples())})
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(RES, "pump_anatomy_top30.csv"), index=False)
    return out


if __name__ == "__main__":
    with pd.option_context("display.width", 300, "display.max_colwidth", 200):
        print(main().to_string())
