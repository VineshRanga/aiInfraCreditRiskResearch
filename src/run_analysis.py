"""Run all analyses on the curated datasets and write tables, figures and diagnostics.

Usage: python src/run_analysis.py   (after src/build_datasets.py)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import market_analysis as ma  # noqa: E402
import scenarios as sc  # noqa: E402
import visualization as viz  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC, CUR = ROOT / "data" / "processed", ROOT / "data" / "curated"
TAB, DIAG = ROOT / "outputs" / "tables", ROOT / "outputs" / "diagnostics"
CUTOFF = pd.Timestamp("2026-11-13")
ORDER = ["AMZN", "GOOGL", "MSFT", "META", "ORCL"]


def load():
    annual = pd.read_csv(PROC / "issuer_annual_10k.csv", parse_dates=["fiscal_period_end", "filed_10k"])
    snap = pd.read_csv(PROC / "issuer_latest_10q_snapshot.csv")
    mat = pd.read_csv(CUR / "debt_maturity_schedule_latest_10k.csv", parse_dates=["fiscal_period_end"])
    orcl = pd.read_csv(CUR / "oracle_note_level_debt_fy2026.csv", parse_dates=["issue_date", "maturity_date"])
    tr = pd.read_csv(CUR / "bond_issuance_tranches.csv", parse_dates=["filing_date"])
    ext = pd.read_csv(CUR / "external_published_statistics.csv")
    fred = pd.read_csv(PROC / "fred_daily.csv", parse_dates=["date"])
    nfci = pd.read_csv(PROC / "fred_nfci_weekly.csv", parse_dates=["date"])
    return annual, snap, mat, orcl, tr, ext, fred, nfci


def to_md(df: pd.DataFrame, path: Path, title: str, notes: str) -> None:
    def fmt(v):
        if isinstance(v, (float, np.floating)):
            if np.isnan(v):
                return ""
            return f"{v:,.1f}" if abs(v) >= 100 else (f"{v:,.2f}" if abs(v) >= 1 else f"{v:.3f}")
        return str(v)
    cols = list(df.columns)
    lines = [f"**{title}**", "", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(fmt(v) for v in r) + " |" for r in df.itertuples(index=False)]
    lines += ["", notes, ""]
    path.write_text("\n".join(lines))


def save(df: pd.DataFrame, name: str, title: str, notes: str) -> None:
    TAB.mkdir(parents=True, exist_ok=True)
    df.to_csv(TAB / f"{name}.csv", index=False)
    to_md(df, TAB / f"{name}.md", title, notes)


def table1(annual, snap, tr):
    last = annual.sort_values("fiscal_period_end").groupby("ticker").tail(1).set_index("ticker")
    s = snap.set_index("ticker")
    rows = []
    for t in ORDER:
        a = annual[annual.ticker == t].set_index("fiscal_year")
        fy = int(last.loc[t, "fiscal_year"])
        base = fy - 3
        rate = tr[(tr.ticker == t) & tr.sp_at_pricing.notna()].sort_values("filing_date").tail(1)
        rows.append({
            "ticker": t, "latest_fy": f"FY{fy}", "fy_end": last.loc[t, "fiscal_period_end"].date(),
            "revenue_bn": last.loc[t, "revenue"] / 1e9,
            "ocf_bn": last.loc[t, "operating_cash_flow"] / 1e9,
            "capex_bn": last.loc[t, "capex"] / 1e9,
            "fcf_bn": last.loc[t, "free_cash_flow"] / 1e9,
            "capex_to_ocf": last.loc[t, "capex_to_ocf"],
            "capex_to_revenue": last.loc[t, "capex_to_revenue"],
            "fcf_margin": last.loc[t, "fcf_margin"],
            f"capex_cagr_3y": (a.loc[fy, "capex"] / a.loc[base, "capex"]) ** (1 / 3) - 1,
            "capex_to_ocf_3y_earlier": a.loc[base, "capex_to_ocf"],
            "shareholder_returns_bn": last.loc[t, "shareholder_returns"] / 1e9,
            "ttm_end": s.loc[t, "ttm_capex_end"],
            "ttm_capex_bn": s.loc[t, "ttm_capex"] / 1e9,
            "ttm_ocf_bn": s.loc[t, "ttm_operating_cash_flow"] / 1e9,
            "ttm_fcf_bn": s.loc[t, "ttm_fcf"] / 1e9,
            "ttm_capex_to_ocf": s.loc[t, "ttm_capex_to_ocf"],
            "latest_ratings_at_pricing": f"{rate.moodys_at_pricing.iloc[0]} / {rate.sp_at_pricing.iloc[0]} ({rate.filing_date.iloc[0].date()})" if len(rate) else "",
        })
    return pd.DataFrame(rows)


def table2(annual, snap, mat, tr):
    last = annual.sort_values("fiscal_period_end").groupby("ticker").tail(1).set_index("ticker")
    s = snap.set_index("ticker")
    rows = []
    for t in ORDER:
        fpe = last.loc[t, "fiscal_period_end"]
        post = tr[(tr.ticker == t) & (tr.filing_date > fpe)].principal_usd.sum()
        flease = s.loc[t, "finance_lease_liability"]
        rows.append({
            "ticker": t, "balance_sheet_date": s.loc[t, "cash_asof"],
            "cash_sti_bn": s.loc[t, "cash_and_sti"] / 1e9,
            "gross_debt_bn": s.loc[t, "gross_debt"] / 1e9,
            "debt_basis": s.loc[t, "debt_basis"],
            "finance_lease_liab_bn": flease / 1e9 if pd.notna(flease) else np.nan,
            "net_debt_bn": s.loc[t, "net_debt"] / 1e9,
            "net_debt_to_ttm_ebitda": s.loc[t, "net_debt_to_ttm_ebitda"],
            "gross_debt_incl_fin_leases_to_ttm_ebitda": (s.loc[t, "gross_debt"] + (flease if pd.notna(flease) else 0)) / s.loc[t, "ttm_ebitda"],
            "ttm_ebitda_to_interest": s.loc[t, "ttm_ebitda_to_interest"],
            "maturities_next_12m_10k_bn": last.loc[t, "maturity_y1"] / 1e9,
            "maturities_next_3y_10k_bn": last.loc[t, "maturities_next_3y"] / 1e9,
            "cash_sti_to_next3y_maturities": s.loc[t, "cash_and_sti"] / last.loc[t, "maturities_next_3y"],
            "ttm_fcf_less_next12m_maturities_bn": (s.loc[t, "ttm_fcf"] - last.loc[t, "maturity_y1"]) / 1e9,
            "registered_issuance_after_fye_bn": post / 1e9,
        })
    return pd.DataFrame(rows)


def main():
    viz.set_style()
    annual, snap, mat, orcl, tr, ext, fred, nfci = load()
    annual = annual[annual.ticker.isin(ORDER)]
    assert tr.filing_date.max() <= CUTOFF and fred.date.max() <= CUTOFF
    tr = ma.add_bond_analytics(tr)
    tr.to_csv(CUR / "bond_issuance_tranches_with_analytics.csv", index=False)
    results: dict = {}

    # ---------------- Analysis 1: capex & cash flow
    t1 = table1(annual, snap, tr)
    save(t1, "table1_issuer_characteristics", "Table 1. Issuer capex, cash flow and capital intensity",
         "Source: SEC EDGAR 10-K/10-Q XBRL (point-in-time, first-reported). USD bn unless ratio. Ratings: as printed in the "
         "most recent pricing term sheet (Moody's / S&P), not current ratings. FCF = OCF − capex.")
    viz.fig1_capex(annual, snap)
    viz.fig2_ocf_capex(annual, snap)

    # ---------------- Analysis 2: maturities & refinancing
    t2 = table2(annual, snap, mat, tr)
    save(t2, "table2_liquidity_leverage_refinancing", "Table 2. Liquidity, leverage and refinancing indicators",
         "Balance sheet at latest 10-Q (Sep-2026; ORCL Aug-2026). EBITDA = operating income + D&A (TTM). Maturities from latest 10-K "
         "contractual schedule (fiscal-year buckets) and therefore exclude debt issued after fiscal year-end. ORCL debt is carrying "
         "value (10-Q lacks principal tag); others principal + commercial paper.")
    fye = {t: annual[annual.ticker == t].fiscal_period_end.max() for t in ORDER}
    viz.fig3_maturities(mat, tr, fye)
    tenor_post = tr[tr.apply(lambda r: r.filing_date > fye[r.ticker], axis=1)]
    ms = tenor_post.assign(b=pd.cut(tenor_post.maturity_year, [2026, 2029, 2033, 2045, 2100],
                                    labels=["2027-29", "2030-33", "2034-45", "2046+"]))
    results["post_fye_issuance_by_maturity_bn"] = (ms.groupby("b", observed=False).principal_usd.sum() / 1e9).round(2).to_dict()

    # ---------------- Analysis 3: issuance & concentration
    summ = ma.issuance_summary(tr)
    save(summ, "table_s1_issuance_summary_by_issuer_year", "Table S1. SEC-registered bond issuance by issuer and year",
         "Source: SEC EDGAR final prospectus supplements. USD-equivalent at FRED H.10 FX on/before filing date. Tenor approx. = "
         "maturity year − issue year. Gross issuance, not net or outstanding.")
    conc = ma.concentration_vs_sifma(tr, ext)
    save(conc, "table_s2_issuance_concentration_vs_sifma", "Table S2. Five-issuer USD registered issuance vs SIFMA market issuance",
         "Numerator: five issuers' USD-denominated SEC-registered issuance by final prospectus date. Denominator: SIFMA (B, published). "
         "IG-only denominator available only for 3Q26 (SIFMA IG share 74.3%).")
    viz.fig4_issuance(tr, conc)
    nis = ma.new_issue_vs_index(tr, fred)
    nis.to_csv(TAB / "table_s3_new_issue_spread_vs_ice_oas_tranche_level.csv", index=False)
    g = nis[nis.tenor_years_approx.between(8, 12)].groupby(["ticker", nis.filing_date.dt.to_period("Q").astype(str)]).agg(
        n=("spread_to_ust_bp", "size"), sp_rating=("sp_at_pricing", "first"),
        new_issue_spread_bp=("spread_to_ust_bp", "mean"), rating_index_oas_bp=("index_oas_bp", "mean"),
        diff_bp=("spread_minus_rating_index_oas_bp", "mean")).reset_index().rename(columns={"filing_date": "quarter"})
    save(g, "table_s3_new_issue_spread_vs_ice_oas_8_12y", "Table S3. 8–12y new-issue spread vs same-rating ICE OAS",
         "New-issue spread to benchmark UST from FWP term sheets (validated vs YTM − benchmark). Index OAS: ICE BofA AA/A/BBB on the "
         "business day before the final prospectus date. AAA-rated Microsoft mapped to AA bucket. Different spread measures; indicative only.")
    viz.fig_s1_new_issue_spreads(nis, fred)
    dv = sc.new_issue_spread_dv01(tr)
    save(dv, "table_s4_new_issue_spread_dv01_2025_2026", "Table S4. At-issue spread DV01 and DTS of verified 2025–26 USD fixed-rate issues",
         "Par-based; spread duration ≈ modified duration of a bullet bond at the re-offer yield; DTS = duration × spread (years × bp). "
         "Covers only verified SEC-registered USD fixed-rate tranches; NOT index-level DTS contribution.")
    tenor_shift = tr[tr.currency == "USD"].assign(period=np.where(tr[tr.currency == "USD"].issue_year >= 2025, "2025-26", "2020-24"))
    results["tenor_by_period"] = tenor_shift.groupby("period").apply(
        lambda x: {"pw_tenor": float(np.average(x.tenor_years_approx, weights=x.principal_usd)),
                   "median_tenor": float(x.tenor_years_approx.median()),
                   "share_over_25y": float(x.principal_usd[x.tenor_years_approx > 25].sum() / x.principal_usd.sum()),
                   "usd_bn": float(x.principal_usd.sum() / 1e9)}, include_groups=False).to_dict()

    # ---------------- Analysis 4: macro
    corr = pd.DataFrame([
        ma.full_period_corr(fred, "DGS10", "BAA10Y", "2018-01-01"),
        ma.full_period_corr(fred, "DGS10", "BAA10Y", "2018-01-01", freq="W-FRI"),
        ma.full_period_corr(fred, "DGS10", "BAMLC0A0CM", "2023-11-13"),
        ma.full_period_corr(fred, "DGS10", "BAMLC0A0CM", "2023-11-13", freq="W-FRI"),
        ma.full_period_corr(fred, "DGS10", "BAMLC0A0CM", "2025-10-01"),
        ma.full_period_corr(fred, "DGS10", "BAMLC0A2CAA", "2025-10-01"),
        ma.full_period_corr(fred, "DGS30", "BAMLC0A0CM", "2023-11-13"),
    ])
    save(corr, "table_s5_rate_spread_correlations", "Table S5. Correlation of Treasury yield changes and credit-spread changes",
         "Pearson correlation of first differences (and of levels). Descriptive; no causal interpretation.")
    epi = ma.rate_shock_episodes(fred)
    save(epi, "table_s6_10y_rate_shock_episodes", "Table S6. Episodes of ≥50bp rise in 10Y UST over 63 business days",
         "Non-overlapping windows; concurrent spread changes in bp. NaN where ICE series unavailable (before 13-Nov-2023).")
    reg = ma.regime_table(fred)
    save(reg, "table_s7_macro_regimes", "Table S7. Average yield and spread levels by descriptive regime (bp)",
         "Regime dates are descriptive conventions chosen by the author; ICE series only from 13-Nov-2023.")
    viz.fig5_macro(fred, nfci)
    rc_l = ma.rolling_corr(fred, "DGS10", "BAA10Y")
    rc_i = ma.rolling_corr(fred, "DGS10", "BAMLC0A0CM")
    viz.fig_s2_rolling_corr(rc_l, rc_i)
    f = fred.set_index("date")
    pts = {}
    for d in ["2023-12-29", "2024-12-31", "2025-09-30", "2025-12-31", "2026-06-30", "2026-11-11"]:
        row = f.loc[:d].ffill().iloc[-1]
        pts[d] = {c: round(float(row[c]) * (100 if c.startswith(("BAML", "BAA", "AAA")) else 1), 2)
                  for c in ["DGS10", "DGS30", "BAMLC0A0CM", "BAMLC0A2CAA", "BAMLC0A3CA", "BAMLC0A4CBBB", "BAA10Y"]}
    results["fred_points"] = pts

    # ---------------- Analysis 5: scenarios
    recent = tr[(tr.issue_year >= 2025) & tr.mod_duration_at_issue.notna()]
    bucket_d = recent.groupby(pd.cut(recent.tenor_years_approx, [0, 6, 12, 25, 35, 60]), observed=True).mod_duration_at_issue.median()
    durations = {"5y": recent[recent.tenor_years_approx.between(4, 6)].mod_duration_at_issue.median(),
                 "10y": recent[recent.tenor_years_approx.between(9, 11)].mod_duration_at_issue.median(),
                 "30y": recent[recent.tenor_years_approx.between(29, 31)].mod_duration_at_issue.median(),
                 "40y": recent[recent.tenor_years_approx.between(39, 41)].mod_duration_at_issue.median(),
                 "pw": float(np.average(recent.mod_duration_at_issue, weights=recent.principal_usd)),
                 "index_pub": 6.4}
    labels = {"5y": f"5y new issue, median D={durations['5y']:.1f} (A)",
              "10y": f"10y new issue, median D={durations['10y']:.1f} (A)",
              "30y": f"30y new issue, median D={durations['30y']:.1f} (A)",
              "40y": f"40y new issue, median D={durations['40y']:.1f} (A)",
              "pw": f"2025–26 five-issuer USD issuance, principal-wtd D={durations['pw']:.1f} (A)",
              "index_pub": "US IG index duration 6.4 (B: bfinance, Bloomberg data)"}
    grid = sc.price_sensitivity_grid(durations)
    grid.reset_index().to_csv(TAB / "fig6_data_price_sensitivity_grid.csv", index=False)
    viz.fig6_sensitivity(grid, labels)
    results["durations_used"] = {k: round(float(v), 2) for k, v in durations.items()}

    fin = sc.financing_cost_scenarios(snap.set_index("ticker").loc[ORDER].reset_index(), annual)
    save(fin, "table3_financing_cost_scenarios", "Table 3. Hypothetical incremental annual interest cost under rate and spread shocks",
         "HYPOTHETICAL (C). Δcost = (next-3y 10-K contractual maturities + debt-financed TTM FCF shortfall, if any) × (ΔUST + Δspread). "
         "Assumes full refinancing at shocked rates and instant pass-through; ignores existing floating-rate debt, CP, leases, cash "
         "usage, hedges and timing. Pro forma coverage = TTM EBITDA / (TTM interest + Δcost). Not a forecast.")
    pr_rows = []
    for k in ["10y", "30y", "pw"]:
        p = sc.scenario_price_table(durations[k], durations[k])
        p.insert(0, "duration_profile", labels[k])
        pr_rows.append(p)
    pr = pd.concat(pr_rows)
    save(pr, "table3b_first_order_price_impact", "Table 3b. First-order price impact by scenario (fraction of value)",
         "HYPOTHETICAL (C). Rate duration and spread duration set equal to modified duration for non-callable fixed bullets; for "
         "floating-rate or callable bonds they differ. Excludes convexity.")
    cr = sc.coupon_reset(tr, orcl, annual, snap)
    save(cr, "table_s8_coupon_reset", "Table S8. Coupon on near-term legacy maturities vs latest new-issue yield",
         "Legacy = notes issued before 2025 maturing 2027–2029, observed in note-level data (ORCL) or in verified 2020–24 registered "
         "offerings (others; pre-2020 notes unobserved, so observed amount ≠ 10-K schedule). Latest yield = re-offer yield of most "
         "recent 8–12y USD fixed tranche. Implied average cost = TTM interest expense ÷ gross debt (interest may be net of capitalised "
         "interest, which understates the cost).")

    # ---------------- validation diagnostics
    checks = []
    a = annual.copy()
    checks.append(("fcf_identity", bool(np.allclose(a.free_cash_flow, a.operating_cash_flow - a.capex, equal_nan=True))))
    m = a.dropna(subset=["maturity_schedule_total", "debt_principal"])
    checks.append(("maturity_sum_vs_principal_max_abs_gap_pct",
                   float(((m.maturity_schedule_total - m.debt_principal).abs() / m.debt_principal).max())))
    checks.append(("no_duplicate_issuer_years", bool(not a.duplicated(["ticker", "fiscal_year"]).any())))
    checks.append(("no_duplicate_tranches", bool(not tr.duplicated(["accession", "currency", "principal_local", "coupon_pct", "maturity_year", "rate_type"]).any())))
    checks.append(("all_dates_le_cutoff", bool(tr.filing_date.max() <= CUTOFF and a.filed_10k.max() <= CUTOFF and fred.date.max() <= CUTOFF)))
    v = tr.dropna(subset=["spread_to_ust_bp", "reoffer_yield_pct", "benchmark_yield_pct"])
    checks.append(("spread_identity_max_abs_err_bp", float(((v.reoffer_yield_pct - v.benchmark_yield_pct) * 100 - v.spread_to_ust_bp).abs().max())))
    checks.append(("usd_fixed_tranches_with_spread", f"{tr[(tr.currency=='USD')&(tr.rate_type=='fixed')].spread_to_ust_bp.notna().sum()}/{((tr.currency=='USD')&(tr.rate_type=='fixed')).sum()}"))
    pd.DataFrame(checks, columns=["check", "result"]).to_csv(DIAG / "validation_checks.csv", index=False)
    results["checks"] = dict(checks)
    (DIAG / "analysis_key_results.json").write_text(json.dumps(results, indent=2, default=str))
    print(json.dumps(results, indent=1, default=str))


if __name__ == "__main__":
    main()
