"""Publication exhibits for the paper (outputs/figures/paper/), built only from verified
datasets and outputs of run_analysis.py. Sized for a 7in text block. Run after src/run_analysis.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import market_analysis as ma  # noqa: E402
import visualization as viz  # noqa: E402
from visualization import GREY, ISSUER_COLORS, ISSUER_NAMES  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "figures" / "paper"
PROC, CUR, TAB = ROOT / "data" / "processed", ROOT / "data" / "curated", ROOT / "outputs" / "tables"
ORDER = ["AMZN", "GOOGL", "MSFT", "META", "ORCL"]
W = 7.0
SUPPLY_WAVE_START = pd.Timestamp("2025-10-01")
CUTOFF = pd.Timestamp("2026-11-13")


def ext_value(ext: pd.DataFrame, sid: str) -> float:
    return float(ext.loc[ext.stat_id == sid, "value"].iloc[0])


def panel_title(ax, text):
    ax.set_title(text, loc="left", fontsize=plt.rcParams["axes.titlesize"], fontweight="bold")


# --------------------------------------------------------------- Exhibit 1
def exhibit_weight_vs_risk(ext: pd.DataFrame, dv: pd.DataFrame, tr: pd.DataFrame):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W, 3.0), gridspec_kw={"width_ratios": [1, 1.2]})
    periods = ["End-2024", "c. Sep-2026"]
    mv = [ext_value(ext, "bfin_mv_share_2024"), ext_value(ext, "bfin_mv_share")]
    dur = [ext_value(ext, "bfin_dur_share_2024"), ext_value(ext, "bfin_dur_share")]
    x = np.arange(2)
    w = 0.36
    b1 = a1.bar(x - w / 2, mv, w, color="#9fb7cf", label="Market-value weight")
    b2 = a1.bar(x + w / 2, dur, w, color="#1f3b63", label="Share of index duration risk")
    for bars in (b1, b2):
        for b in bars:
            a1.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.12, f"{b.get_height():.2f}%", ha="center", fontsize=6.6)
    for i in range(2):
        a1.text(x[i], max(mv[i], dur[i]) + 0.75, f"{dur[i] / mv[i]:.2f}× weight", ha="center", fontsize=6.6, color=GREY)
    a1.set_xticks(x)
    a1.set_xticklabels(periods)
    a1.set_ylabel("% of Bloomberg US Corporate Index")
    a1.set_ylim(0, 9.6)
    a1.legend(loc="upper left")
    a1.grid(axis="x", visible=False)
    panel_title(a1, "(a) Index weight vs duration-risk share")

    r = tr[(tr.issue_year >= 2025) & tr.mod_duration_at_issue.notna()]
    d = dv.set_index("ticker").reindex(ORDER).pw_mod_duration.tolist()
    d.append(float(np.average(r.mod_duration_at_issue, weights=r.principal_usd)))
    labels = [ISSUER_NAMES[t] for t in ORDER] + ["All five"]
    y = np.arange(len(labels))[::-1]
    a2.barh(y, d, color=[ISSUER_COLORS[t] for t in ORDER] + ["black"], height=0.62)
    for yi, v in zip(y, d):
        a2.text(v + 0.12, yi, f"{v:.1f}", va="center", fontsize=6.6)
    a2.set_yticks(y)
    a2.set_yticklabels(labels)
    for v, lab, ls in [(ext_value(ext, "bfin_dur_hyp"), "Five issuers' index bonds, 8.4y", "--"),
                       (ext_value(ext, "bfin_dur_index"), "Index average, 6.4y", ":")]:
        a2.axvline(v, color=GREY, ls=ls, lw=0.9, label=lab)
    a2.legend(loc="upper center", bbox_to_anchor=(0.45, -0.2), ncol=2, frameon=False)
    a2.set_xlim(0, 11.2)
    a2.set_ylim(-0.6, len(labels) - 0.4)
    a2.set_xlabel("Modified duration at pricing, years")
    a2.grid(axis="y", visible=False)
    panel_title(a2, "(b) Duration of 2025–26 USD new issues")
    fig.subplots_adjust(wspace=0.42, top=0.82)
    return viz.finish(fig, "exhibit1_weight_vs_duration_risk",
                      "Exhibit 1: The five issuers hold 4.85% of the IG index but 6.3% of its duration risk",
                      "(a) bfinance, 'AI, hyperscalers and corporate bond indices: signal or narrative?', 28-Oct-2026, citing "
                      "Bloomberg index data. (b) Author calculations from SEC EDGAR pricing term sheets: 162 SEC-registered USD "
                      "fixed-rate tranches priced Jan-2025 to 13-Nov-2026.",
                      "Panel (a) shares are duration-weighted (interest-rate risk). Panel (b) shows principal-weighted modified "
                      "duration of new issues at the re-offer yield, assuming bullet maturities; it describes the 2025–26 flow "
                      "of new bonds, not the stock of bonds held in the index.", outdir=OUT, chrome=False)


# --------------------------------------------------------------- Exhibit 2
def exhibit_issuance(tr: pd.DataFrame, conc: pd.DataFrame):
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(W, 4.5), sharex=True, gridspec_kw={"height_ratios": [2.1, 1]})
    years = list(range(2018, 2027))
    usd = tr[tr.currency == "USD"].pivot_table(index="issue_year", columns="ticker", values="principal_usd",
                                               aggfunc="sum").reindex(years).fillna(0) / 1e9
    nonusd = tr[tr.currency != "USD"].groupby("issue_year").principal_usd.sum().reindex(years).fillna(0) / 1e9
    bottom = np.zeros(len(years))
    for t in ORDER:
        ax.bar(years, usd[t], bottom=bottom, color=ISSUER_COLORS[t], label=f"{ISSUER_NAMES[t]} (USD)", width=0.66)
        bottom += usd[t].values
    ax.bar(years, nonusd, bottom=bottom, color="white", edgecolor=GREY, hatch="////", lw=0.5,
           label="Non-USD tranches, all five (USD-equiv.)", width=0.66)
    tot = bottom + nonusd.values
    for yv, v in zip(years, tot):
        if v > 0:
            ax.text(yv, v + 4, f"{v:,.0f}", ha="center", fontsize=6.8)
    ax.set_ylabel("Gross issuance, USD bn")
    ax.set_ylim(0, tot.max() * 1.15)
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left", frameon=False)
    panel_title(ax, "(a) SEC-registered bond issuance by Amazon, Alphabet, Microsoft, Meta and Oracle")
    c = conc.set_index("period")
    xs = [2023, 2024, 2025, 2026]
    vals = [c.loc[p, "share_of_denominator"] * 100 for p in ["FY2023", "FY2024", "FY2025", "2026 Jan-Sep"]]
    ax2.plot(xs, vals, color="black", marker="s", ms=4, lw=1.1, label="÷ SIFMA total US corporate issuance (2026: Jan–Sep)")
    for xv, v in zip(xs, vals):
        ax2.annotate(f"{v:.1f}%", (xv, v), textcoords="offset points",
                     xytext=(0, 6 if xv < 2026 else -11), ha="center", fontsize=6.8)
    ig = c.loc["3Q26 (IG-only denominator)", "share_of_denominator"] * 100
    ax2.plot([2026], [ig], marker="D", ms=5, color="#c07a2c", ls="none", label="÷ SIFMA investment-grade issuance, 3Q26")
    ax2.annotate(f"{ig:.1f}%", (2026, ig), textcoords="offset points", xytext=(0, 5),
                 ha="center", fontsize=6.8, color="#c07a2c")
    ax2.set_ylim(0, 13.5)
    ax2.set_ylabel("% of market issuance")
    ax2.legend(loc="upper left", frameon=False)
    panel_title(ax2, "(b) USD issuance by the five as a share of SIFMA market issuance")
    ax2.set_xticks(years)
    ax2.set_xticklabels([str(y) if y < 2026 else "2026 YTD" for y in years])
    fig.subplots_adjust(hspace=0.32, top=0.9)
    return viz.finish(fig, "exhibit2_issuance_vs_market",
                      "Exhibit 2: Registered issuance by the five reached $284bn in 2026, about 7% of U.S. corporate supply",
                      "SEC EDGAR final prospectus supplements (424B2/424B5), 38 debt offerings, author dataset; SIFMA Research "
                      "Quarterly 4Q24, 4Q25 and 3Q26; FRED H.10 exchange rates for non-USD tranches. 2026 YTD = to 13-Nov-2026.",
                      "SEC-registered offerings only (excludes 144A, private placements, term loans, commercial paper and "
                      "project finance). Panel (b) uses USD-denominated issuance with numerator and denominator over the same "
                      "months; SIFMA's annual total covers all U.S. corporate bonds (IG, HY, private placements, convertibles). "
                      "No registered issuance by the five in 2018–19.", outdir=OUT, chrome=False)


# --------------------------------------------------------------- Exhibit 3
def exhibit_capex_intensity(annual: pd.DataFrame, snap: pd.DataFrame):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W, 3.05))
    years = list(range(2018, 2027))
    cats = [f"FY{str(y)[2:]}" for y in years] + ["TTM"]
    xpos = list(range(9)) + [9.55]
    s = snap.set_index("ticker")
    # Alphabet, Meta and Microsoft sit within 0.20 of each other; nudge the labels apart.
    label_nudge = {"ORCL": (6, 2), "AMZN": (6, -2), "GOOGL": (6, 7), "META": (6, 0), "MSFT": (6, -8)}
    for t in ORDER:
        g = annual[annual.ticker == t].set_index("fiscal_year").reindex(years)
        cap = g.capex / 1e9
        ratio = g.capex_to_ocf
        ttm_cap = float(s.loc[t, "ttm_capex"] / 1e9)
        ttm_ratio = float(s.loc[t, "ttm_capex_to_ocf"])
        a1.plot(xpos[:9], cap, marker="o", ms=2.6, color=ISSUER_COLORS[t], label=ISSUER_NAMES[t], lw=1.15)
        a2.plot(xpos[:9], ratio, marker="o", ms=2.6, color=ISSUER_COLORS[t], lw=1.15)
        for ax, series, ttm in ((a1, cap, ttm_cap), (a2, ratio, ttm_ratio)):
            observed = series.dropna()
            if len(observed):
                last_year = int(observed.index[-1])
                ax.plot([xpos[years.index(last_year)], xpos[9]], [float(observed.iloc[-1]), ttm],
                        color=ISSUER_COLORS[t], lw=0.75, ls=(0, (1.6, 1.3)))
            ax.plot(xpos[9], ttm, marker="D", ms=3.8, mfc="white", mec=ISSUER_COLORS[t], mew=1.05)
        dx, dy = label_nudge[t]
        a2.annotate(f"{ttm_ratio:.2f}", (xpos[9], ttm_ratio), textcoords="offset points",
                    xytext=(dx, dy), fontsize=6.1, color=ISSUER_COLORS[t], va="center")
    for ax in (a1, a2):
        ax.axvline(8.85, color=GREY, lw=0.5, ls=":")
        ax.set_xticks(xpos)
        ax.set_xticklabels(cats, fontsize=6.0)
        ax.set_xlim(-0.35, 11.35)
        ax.tick_params(axis="x", pad=1)
    a2.axhline(1.0, color="black", lw=0.7, zorder=0)
    a2.text(0.05, 1.08, "Capex = OCF", fontsize=5.8, color=GREY, ha="left", va="bottom")
    a1.set_ylabel("USD bn")
    a2.set_ylabel("Capex / OCF")
    panel_title(a1, "(a) Capital expenditure")
    panel_title(a2, "(b) Capex intensity (above 1.0 = negative FCF)")
    # Hollow diamond marks TTM; solid markers are fiscal-year ends.
    ttm_proxy = plt.Line2D([0], [0], marker="D", color=GREY, markerfacecolor="white",
                           markeredgecolor=GREY, markersize=4.2, lw=0, label="TTM")
    handles, labels = a1.get_legend_handles_labels()
    a1.legend(handles + [ttm_proxy], labels + ["TTM"], loc="upper left", fontsize=6.0,
              frameon=False, borderaxespad=0.15, handlelength=1.5, labelspacing=0.2)
    fig.subplots_adjust(wspace=0.32, top=0.86, bottom=0.16)
    return viz.finish(fig, "exhibit3_capex_intensity",
                      "Exhibit 3: Capex has caught up with operating cash flow; Oracle and Amazon are FCF-negative",
                      "SEC EDGAR XBRL Company Facts: 10-K (first-reported values) and 10-Q filings; author calculations.",
                      "Fiscal years labelled by calendar year of year-end: December (Amazon, Alphabet, Meta), June (Microsoft), "
                      "May (Oracle). Hollow diamonds show trailing twelve months to Sep-2026 (Oracle Aug-2026). Capex is purchases "
                      "of property and equipment and excludes finance-lease additions. Amazon's FY21–22 ratios reflect "
                      "unusually low operating cash flow.", outdir=OUT, chrome=False)


# --------------------------------------------------------------- Exhibit 4
def exhibit_spreads(nis: pd.DataFrame, fred: pd.DataFrame):
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(W, 4.75), sharex=True, gridspec_kw={"height_ratios": [1.25, 1]})
    f = fred.set_index("date").loc["2023-11-13":]
    for sid, lab, ls, col in [("BAMLC0A2CAA", "ICE AA OAS", "-", GREY), ("BAMLC0A3CA", "ICE A OAS", "--", GREY),
                              ("BAMLC0A4CBBB", "ICE BBB OAS", ":", GREY), ("BAMLH0A0HYM2", "ICE High Yield OAS", "-.", "#b5b5b5")]:
        a1.plot(f.index, f[sid] * 100, color=col, ls=ls, lw=0.9, label=lab)
    x = nis[nis.tenor_years_approx.between(8, 12)].copy()
    label_nudge = {"AMZN": (4, -9), "GOOGL": (4, 4), "MSFT": (4, -10), "META": (4, 2), "ORCL": (4, 2)}
    for t in ORDER:
        g = x[x.ticker == t].sort_values("filing_date")
        if len(g):
            a1.scatter(g.filing_date, g.spread_to_ust_bp, s=18, color=ISSUER_COLORS[t], edgecolor="white", lw=0.4,
                       zorder=3, label=f"{ISSUER_NAMES[t]} ({g.sp_at_pricing.iloc[-1]})")
            a2.plot(g.filing_date, g.spread_minus_rating_index_oas_bp, marker="o", ms=3, color=ISSUER_COLORS[t], lw=1.0)
            last = g.iloc[-1]
            dx, dy = label_nudge[t]
            a2.annotate(f"{last.spread_minus_rating_index_oas_bp:+.0f}",
                        (last.filing_date, last.spread_minus_rating_index_oas_bp),
                        textcoords="offset points", xytext=(dx, dy), fontsize=6.4, color=ISSUER_COLORS[t])
    a1.set_ylabel("bp")
    a1.set_ylim(0, 400)
    # Compact legend in the open band between BBB and High Yield OAS.
    a1.legend(ncol=2, loc="center left", bbox_to_anchor=(0.01, 0.58), frameon=True, fancybox=False,
              edgecolor="#dddddd", framealpha=0.94, fontsize=5.7, handletextpad=0.35, columnspacing=0.75,
              borderpad=0.35, labelspacing=0.25)
    panel_title(a1, "(a) 8–12y new-issue spread vs ICE OAS by rating (S&P at latest pricing)")
    a2.axhline(0, color="black", lw=0.6)
    a2.set_ylabel("bp")
    a2.set_ylim(-30, 220)
    panel_title(a2, "(b) New-issue spread minus same-rating ICE OAS on the pricing date")
    a2.xaxis.set_major_formatter(mdates.DateFormatter("%b-%y"))
    a2.set_xlim(pd.Timestamp("2023-11-01"), pd.Timestamp("2026-12-15"))
    fig.subplots_adjust(hspace=0.22, top=0.92)
    return viz.finish(fig, "exhibit4_new_issue_spreads",
                      "Exhibit 4: New-issue spreads have moved above rating benchmarks, most sharply for Oracle and Meta",
                      "SEC EDGAR FWP pricing term sheets (spread, re-offer yield and benchmark yield reconciled within 1.5bp); "
                      "FRED: ICE BofA AA, A, BBB and US High Yield OAS (available on FRED from 13-Nov-2023). Author calculations.",
                      "New-issue spreads are quoted to an on-the-run benchmark Treasury; ICE OAS is option-adjusted to the spot "
                      "curve and averages all index maturities, so panel (b) is most informative as a change over time. Index OAS "
                      "taken on the business day before the final prospectus date; Microsoft (AAA) is mapped to the AA index.",
                      outdir=OUT, chrome=False)


# --------------------------------------------------------------- Exhibit 6
def exhibit_sensitivity(durations: dict, ext: pd.DataFrame):
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(W, 3.9), gridspec_kw={"height_ratios": [1.25, 1]})
    prof = [("5y new issue", durations["5y"], "#8fb3d9", "A"), ("10y new issue", durations["10y"], "#4f7cac", "A"),
            ("30y new issue", durations["30y"], "#1f3b63", "A"),
            ("2025–26 issuance, principal-weighted", durations["pw"], "#8c2d2d", "A"),
            ("IG index average (published)", ext_value(ext, "bfin_dur_index"), "black", "B")]
    sh = np.arange(0, 201, 5)
    for name, d, col, tag in prof:
        yv = -d * sh / 100
        a1.plot(sh, yv, color=col, lw=1.2, ls="-" if tag == "A" else "--")
        a1.text(205, yv[-1], f"{name}, D = {d:.1f}", fontsize=6.4, color=col, va="center")
    for s in (50, 100):
        a1.axvline(s, color=GREY, lw=0.5, ls=":")
    a1.set_xlim(0, 305)
    a1.set_xticks([0, 50, 100, 150, 200])
    a1.set_xlabel("Parallel spread widening, bp")
    a1.set_ylabel("Price change, %")
    panel_title(a1, "(a) Spread widening: ΔP/P ≈ −D × Δs")
    rows = prof[1:]
    yy = np.arange(len(rows))[::-1]
    rate = [-d for _, d, _, _ in rows]
    spr = [-d for _, d, _, _ in rows]
    short = {
        "10y new issue": "10y new issue",
        "30y new issue": "30y new issue",
        "2025–26 issuance, principal-weighted": "2025–26 issuance (wtd)",
        "IG index average (published)": "IG index average",
    }
    a2.barh(yy, rate, color="#9fb7cf", height=0.55, label="Treasury +100bp (rate duration)")
    a2.barh(yy, spr, left=rate, color="#8c2d2d", height=0.55, label="Spread +100bp (spread duration)")
    for yi, r_, s_ in zip(yy, rate, spr):
        a2.text(r_ + s_ - 0.5, yi, f"{r_ + s_:.1f}%", va="center", ha="right", fontsize=6.6)
    a2.set_yticks(yy)
    a2.set_yticklabels([short.get(n, n) for n, _, _, _ in rows])
    a2.set_xlim(-34, 0)
    a2.set_xlabel("Price change, %")
    a2.legend(loc="lower left", ncol=1, frameon=False)
    a2.grid(axis="y", visible=False)
    panel_title(a2, "(b) Combined shock: Treasury +100bp and spread +100bp")
    fig.subplots_adjust(hspace=0.52, top=0.9)
    return viz.finish(fig, "exhibit6_duration_spread_sensitivity",
                      "Exhibit 6: Hypothetical first-order price sensitivity to rate and spread shocks",
                      "Durations: author calculations from SEC EDGAR pricing term sheets (median of 2025–26 USD fixed-rate new "
                      "issues by tenor, and principal-weighted average). Index duration: bfinance, citing Bloomberg (dashed).",
                      "Illustrative scenarios, not forecasts. First-order approximation excluding convexity, curve reshaping, "
                      "carry, call options and rating migration. Rate and spread duration are entered separately; for "
                      "fixed-rate bullets they are numerically equal.", outdir=OUT, chrome=False)


# --------------------------------------------------------------- Appendix A1
def appendix_rating_spreads(fred: pd.DataFrame):
    f = fred.set_index("date").loc["2023-11-13":]
    fig, axes = plt.subplots(3, 1, figsize=(W, 5.0), sharex=True, gridspec_kw={"height_ratios": [1, 1.1, 0.8]})
    axes[0].plot(f.index, f.DGS10, color="#1f3b63", lw=1.0, label="10Y")
    axes[0].plot(f.index, f.DGS30, color="#8c2d2d", lw=1.0, label="30Y")
    axes[0].set_ylabel("%")
    axes[0].legend(loc="upper left", ncol=2)
    panel_title(axes[0], "(a) Treasury constant-maturity yields")
    for sid, lab, ls in [("BAMLC0A2CAA", "AA", "-"), ("BAMLC0A3CA", "A", "--"), ("BAMLC0A4CBBB", "BBB", ":")]:
        axes[1].plot(f.index, f[sid] * 100, color="#1f3b63", ls=ls, lw=1.0, label=f"ICE BofA {lab} OAS")
    axes[1].set_ylabel("bp")
    axes[1].legend(loc="upper right", ncol=3)
    panel_title(axes[1], "(b) Investment-grade OAS by rating")
    gap = ((f.BAMLC0A3CA - f.BAMLC0A2CAA) * 100).dropna()
    axes[2].plot(gap.index, gap, color="#c07a2c", lw=0.9, label="Daily")
    axes[2].plot(gap.index, gap.rolling(21).mean(), color="black", lw=0.9, label="21-day average")
    axes[2].set_ylabel("bp")
    axes[2].legend(loc="upper right", ncol=2)
    panel_title(axes[2], "(c) A minus AA OAS")
    x_end = min(CUTOFF, f.index.max())
    for ax in axes:
        ax.axvspan(SUPPLY_WAVE_START, x_end, color="#f2e6d9", alpha=0.6, lw=0)
        ax.set_xlim(f.index.min(), x_end)
    axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%b-%y"))
    fig.subplots_adjust(hspace=0.32, top=0.91)
    return viz.finish(fig, "appendixA1_rating_spreads",
                      "Exhibit A1: AA spreads widened relative to A and BBB through the supply wave",
                      "FRED: DGS10, DGS30 (Federal Reserve H.15); BAMLC0A2CAA, BAMLC0A3CA, BAMLC0A4CBBB (ICE Data Indices). "
                      "Daily, 13-Nov-2023 to 11-Nov-2026; author calculations.",
                      "Shading marks the period of heavy hyperscaler issuance from Oct-2025, an author convention. ICE series on "
                      "FRED cover the latest three years only.", outdir=OUT, chrome=False)


def main():
    viz.set_style(paper=True)
    annual = pd.read_csv(PROC / "issuer_annual_10k.csv", parse_dates=["fiscal_period_end"])
    snap = pd.read_csv(PROC / "issuer_latest_10q_snapshot.csv")
    tr = pd.read_csv(CUR / "bond_issuance_tranches_with_analytics.csv", parse_dates=["filing_date"])
    ext = pd.read_csv(CUR / "external_published_statistics.csv")
    fred = pd.read_csv(PROC / "fred_daily.csv", parse_dates=["date"])
    nfci = pd.read_csv(PROC / "fred_nfci_weekly.csv", parse_dates=["date"])
    conc = pd.read_csv(TAB / "table_s2_issuance_concentration_vs_sifma.csv")
    dv = pd.read_csv(TAB / "table_s4_new_issue_spread_dv01_2025_2026.csv")
    nis = pd.read_csv(TAB / "table_s3_new_issue_spread_vs_ice_oas_tranche_level.csv", parse_dates=["filing_date"])
    mat = pd.read_csv(CUR / "debt_maturity_schedule_latest_10k.csv", parse_dates=["fiscal_period_end"])
    durations = json.loads((ROOT / "outputs" / "diagnostics" / "analysis_key_results.json").read_text())["durations_used"]
    annual = annual[annual.ticker.isin(ORDER)]
    fye = {t: annual[annual.ticker == t].fiscal_period_end.max() for t in ORDER}

    exhibit_weight_vs_risk(ext, dv, tr)
    exhibit_issuance(tr, conc)
    exhibit_capex_intensity(annual, snap)
    exhibit_spreads(nis, fred)
    viz.fig3_maturities(mat, tr, fye, name="exhibit5_maturity_profile",
                        title="Exhibit 5: Near-term maturities are small next to the volume of new long-dated debt",
                        outdir=OUT, figsize=(W, 5.25), chrome=False)
    exhibit_sensitivity(durations, ext)
    appendix_rating_spreads(fred)
    viz.fig5_macro(fred, nfci, name="appendixA2_rates_spreads_conditions",
                   title="Exhibit A2: Treasury yields, IG spreads and financial conditions, Jan-2018 to Nov-2026",
                   outdir=OUT, figsize=(W, 6.0), chrome=False)
    viz.fig_s2_rolling_corr(ma.rolling_corr(fred, "DGS10", "BAA10Y"), ma.rolling_corr(fred, "DGS10", "BAMLC0A0CM"),
                            name="appendixA3_rolling_correlation",
                            title="Exhibit A3: Rolling six-month correlation of 10Y yield changes and credit-spread changes",
                            outdir=OUT, figsize=(W, 2.7), chrome=False)
    print("paper figures written to", OUT)


if __name__ == "__main__":
    main()
