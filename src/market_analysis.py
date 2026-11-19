"""Bond math, issuance/concentration statistics, new-issue spread comparisons
and macro credit-condition statistics. Conventional methods only."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- bond math
def bond_price(coupon_pct: float, ytm_pct: float, years: float, freq: int = 2) -> float:
    """Price per 100 face of a fixed-rate bullet bond on a coupon date."""
    n = int(round(years * freq))
    if n <= 0:
        return 100.0
    c = coupon_pct / freq
    y = ytm_pct / 100 / freq
    if y == 0:
        return c * n + 100.0
    disc = (1 + y) ** -np.arange(1, n + 1)
    return float(c * disc.sum() + 100 * disc[-1])


def macaulay_duration(coupon_pct: float, ytm_pct: float, years: float, freq: int = 2) -> float:
    n = int(round(years * freq))
    if n <= 0:
        return 0.0
    c = coupon_pct / freq
    y = ytm_pct / 100 / freq
    t = np.arange(1, n + 1)
    cf = np.full(n, c, dtype=float)
    cf[-1] += 100
    pv = cf * (1 + y) ** -t
    return float((t * pv).sum() / pv.sum() / freq)


def modified_duration(coupon_pct: float, ytm_pct: float, years: float, freq: int = 2) -> float:
    return macaulay_duration(coupon_pct, ytm_pct, years, freq) / (1 + ytm_pct / 100 / freq)


def first_order_price_change(duration: float, shock_bp: float) -> float:
    """dP/P ≈ -D × Δy (Δy in decimal). Excludes convexity."""
    return -duration * shock_bp / 10_000


# ----------------------------------------------------------------- issuance
RATING_TO_ICE = {"AAA": "BAMLC0A2CAA", "AA+": "BAMLC0A2CAA", "AA": "BAMLC0A2CAA", "AA-": "BAMLC0A2CAA",
                 "A+": "BAMLC0A3CA", "A": "BAMLC0A3CA", "A-": "BAMLC0A3CA",
                 "BBB+": "BAMLC0A4CBBB", "BBB": "BAMLC0A4CBBB", "BBB-": "BAMLC0A4CBBB"}
# ICE AA index (BAMLC0A2CAA) includes AAA-rated paper only via the separate AAA index; AAA-rated MSFT is
# mapped to AA as the nearest available bucket and flagged.


def add_bond_analytics(tr: pd.DataFrame) -> pd.DataFrame:
    """At-issue modified duration and duration-times-spread for USD fixed-rate tranches,
    computed from disclosed coupon, re-offer yield and approximate tenor (maturity year −
    issue year). Make-whole and par calls are ignored (bullet assumption)."""
    tr = tr.copy()
    ok = (tr.currency == "USD") & (tr.rate_type == "fixed") & tr.reoffer_yield_pct.notna()
    tr["mod_duration_at_issue"] = np.nan
    tr.loc[ok, "mod_duration_at_issue"] = [
        modified_duration(c, y, max(t, 0.5)) for c, y, t in
        zip(tr.loc[ok, "coupon_pct"], tr.loc[ok, "reoffer_yield_pct"], tr.loc[ok, "tenor_years_approx"])]
    tr["dts_at_issue"] = tr["mod_duration_at_issue"] * tr["spread_to_ust_bp"]  # years × bp
    tr["tenor_bucket"] = pd.cut(tr["tenor_years_approx"], [0, 3.5, 7.5, 12.5, 25, 35, 120],
                                labels=["≤3y", "4-7y", "8-12y", "13-25y", "26-35y", ">35y"])
    return tr


def annual_issuance(tr: pd.DataFrame) -> pd.DataFrame:
    g = tr.groupby(["issue_year", "ticker", "currency"])["principal_usd"].sum().unstack(["ticker", "currency"])
    return g


def issuance_summary(tr: pd.DataFrame) -> pd.DataFrame:
    """Per issuer-year: gross USD-equivalent, USD-only, n tranches, principal-weighted tenor, median tenor."""
    def agg(g):
        w = g["principal_usd"]
        return pd.Series({
            "gross_all_ccy_usd_bn": w.sum() / 1e9,
            "gross_usd_denominated_bn": g.loc[g.currency == "USD", "principal_usd"].sum() / 1e9,
            "n_tranches": len(g),
            "n_deals": g["accession"].nunique(),
            "pw_avg_tenor_y": np.average(g["tenor_years_approx"], weights=w),
            "median_tenor_y": g["tenor_years_approx"].median(),
            "share_principal_tenor_over_25y": w[g.tenor_years_approx > 25].sum() / w.sum(),
        })
    return tr.groupby(["ticker", "issue_year"]).apply(agg, include_groups=False).reset_index()


def concentration_vs_sifma(tr: pd.DataFrame, ext: pd.DataFrame) -> pd.DataFrame:
    """Five-issuer USD-denominated SEC-registered issuance vs SIFMA total US corporate issuance.

    SIFMA's denominator is all US corporate bonds (IG+HY+private placement+convertible);
    the IG-only share cannot be computed for full years from openly published SIFMA data."""
    usd = tr[tr.currency == "USD"].copy()
    usd["q"] = usd["filing_date"].dt.to_period("Q")
    rows = []
    spec = [("FY2023", 2023, None, "sifma_corp_iss_2023"), ("FY2024", 2024, None, "sifma_corp_iss_2024"),
            ("FY2025", 2025, None, "sifma_corp_iss_2025"),
            ("2026 Jan-Sep", 2026, pd.Timestamp("2026-09-30"), "sifma_corp_iss_2026q1q3"),
            ("2026 Jan-Oct", 2026, pd.Timestamp("2026-10-31"), "sifma_corp_iss_2026ytd_oct")]
    for label, yr, end, sid in spec:
        sel = usd[usd.filing_date.dt.year == yr]
        if end is not None:
            sel = sel[sel.filing_date <= end]
        denom = float(ext.loc[ext.stat_id == sid, "value"].iloc[0])
        num = sel.principal_usd.sum() / 1e9
        rows.append({"period": label, "five_issuer_usd_registered_bn": num, "denominator_bn": denom,
                     "denominator": "SIFMA total US corporate issuance (all types)",
                     "share_of_denominator": num / denom, "sifma_stat_id": sid})
    q = usd[(usd.filing_date >= "2026-07-01") & (usd.filing_date <= "2026-09-30")].principal_usd.sum() / 1e9
    ig_share = float(ext.loc[ext.stat_id == "sifma_corp_ig_share_3q26", "value"].iloc[0]) / 100
    q3_total = float(ext.loc[ext.stat_id == "sifma_corp_iss_3q26", "value"].iloc[0])
    rows.append({"period": "3Q26 (IG-only denominator)", "five_issuer_usd_registered_bn": q,
                 "denominator_bn": q3_total * ig_share, "denominator": "SIFMA 3Q26 total × SIFMA 3Q26 IG share",
                 "share_of_denominator": q / (q3_total * ig_share),
                 "sifma_stat_id": "sifma_corp_iss_3q26 × sifma_corp_ig_share_3q26"})
    return pd.DataFrame(rows)


def new_issue_vs_index(tr: pd.DataFrame, fred: pd.DataFrame) -> pd.DataFrame:
    """New-issue spread to benchmark Treasury vs same-day ICE OAS for the tranche's rating bucket
    (S&P rating printed in the term sheet). Only for pricing dates inside FRED's ICE window."""
    f = fred.set_index("date").sort_index()
    x = tr[(tr.currency == "USD") & (tr.rate_type == "fixed") & tr.spread_to_ust_bp.notna()].copy()
    x["ice_series"] = x["sp_at_pricing"].map(RATING_TO_ICE)
    out = []
    for i, r in x.iterrows():
        sid = r["ice_series"]
        if not isinstance(sid, str):
            continue
        s = f[sid].dropna()
        s = s.loc[:r["filing_date"] - pd.Timedelta(days=1)]  # last close before the final prospectus date
        if s.empty or s.index[-1] < r["filing_date"] - pd.Timedelta(days=7):
            continue
        out.append({"idx": i, "index_oas_bp": s.iloc[-1] * 100, "index_date": s.index[-1],
                    "ig_oas_bp": f["BAMLC0A0CM"].dropna().loc[:s.index[-1]].iloc[-1] * 100})
    o = pd.DataFrame(out).set_index("idx")
    x = x.join(o, how="inner")
    x["spread_minus_rating_index_oas_bp"] = x["spread_to_ust_bp"] - x["index_oas_bp"]
    return x


# -------------------------------------------------------------------- macro
def rolling_corr(fred: pd.DataFrame, a: str, b: str, window: int = 126) -> pd.Series:
    d = fred.set_index("date")[[a, b]].dropna().diff().dropna()
    return d[a].rolling(window).corr(d[b])


def full_period_corr(fred: pd.DataFrame, a: str, b: str, start=None, end=None, freq="D") -> dict:
    d = fred.set_index("date")[[a, b]].dropna()
    if start:
        d = d.loc[start:]
    if end:
        d = d.loc[:end]
    if freq != "D":
        d = d.resample(freq).last()
    ch = d.diff().dropna()
    return {"pair": f"Δ{a} vs Δ{b}", "start": str(d.index.min().date()), "end": str(d.index.max().date()),
            "freq": freq, "n": len(ch), "corr_changes": ch[a].corr(ch[b]), "corr_levels": d[a].corr(d[b])}


def rate_shock_episodes(fred: pd.DataFrame, horizon: int = 63, threshold_bp: float = 50) -> pd.DataFrame:
    """Non-overlapping windows of `horizon` business days in which the 10Y CMT yield rose by at
    least `threshold_bp`. Reports concurrent changes in credit spreads (bp)."""
    d = fred.set_index("date")[["DGS10", "BAA10Y", "BAMLC0A0CM", "BAMLC0A4CBBB", "BAMLC0A2CAA"]].copy()
    d = d[d["DGS10"].notna()]
    ch = (d.shift(-horizon) - d) * 100
    rows, i = [], 0
    idx = d.index
    while i < len(idx) - horizon:
        if ch["DGS10"].iloc[i] >= threshold_bp:
            r = {"start": idx[i].date(), "end": idx[i + horizon].date()}
            for c in d.columns:
                r[f"d_{c}_bp"] = ch[c].iloc[i]
            rows.append(r)
            i += horizon
        else:
            i += 1
    return pd.DataFrame(rows)


def regime_table(fred: pd.DataFrame) -> pd.DataFrame:
    """Descriptive statistics of spread levels by named macro regime."""
    regimes = [("Pre-hiking 2018-2019", "2018-01-01", "2019-12-31"),
               ("COVID shock Mar-Apr 2020", "2020-03-01", "2020-04-30"),
               ("Zero-rate 2020H2-2021", "2020-07-01", "2021-12-31"),
               ("Fed hiking 2022", "2022-01-01", "2022-12-31"),
               ("Restrictive plateau 2023-mid 2024", "2023-01-01", "2024-08-31"),
               ("Easing / pre-AI-supply 2024Q4-2025", "2024-09-01", "2025-09-30"),
               ("Hyperscaler supply wave Oct-2025 to cutoff", "2025-10-01", "2026-11-13")]
    d = fred.set_index("date")
    rows = []
    for name, s, e in regimes:
        x = d.loc[s:e]
        r = {"regime": name, "start": s, "end": e}
        for c in ["DGS10", "DGS30", "BAA10Y", "BAMLC0A0CM", "BAMLC0A2CAA", "BAMLC0A3CA", "BAMLC0A4CBBB"]:
            v = x[c].dropna()
            r[f"{c}_mean"] = v.mean() * 100 if len(v) else np.nan
        rows.append(r)
    return pd.DataFrame(rows)
