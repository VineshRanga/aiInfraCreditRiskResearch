"""Publication figures: restrained institutional style, PNG (300 dpi) + PDF."""
from __future__ import annotations

import textwrap
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "outputs" / "figures"

ISSUER_COLORS = {"AMZN": "#1f3b63", "GOOGL": "#4f7cac", "MSFT": "#8fb3d9",
                 "META": "#c07a2c", "ORCL": "#8c2d2d"}
ISSUER_NAMES = {"AMZN": "Amazon", "GOOGL": "Alphabet", "MSFT": "Microsoft", "META": "Meta", "ORCL": "Oracle"}
GREY = "#6b6b6b"


def set_style(paper: bool = False) -> None:
    plt.rcParams.update({
        "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
        "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold",
        "axes.labelsize": 9, "axes.edgecolor": "#444444", "axes.linewidth": 0.6,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
        "grid.color": "#e3e3e3", "grid.linewidth": 0.5, "legend.frameon": False, "legend.fontsize": 8,
        "xtick.labelsize": 8, "ytick.labelsize": 8, "lines.linewidth": 1.4,
        "figure.titlesize": 11, "pdf.fonttype": 42,
    })
    if paper:
        # Sized for a ~6.5–7in text block; DejaVu Sans is always available.
        plt.rcParams.update({
            "font.family": "DejaVu Sans", "font.size": 7.5, "axes.titlesize": 7.8, "axes.labelsize": 7.5,
            "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 6.4, "lines.linewidth": 1.15,
            "figure.titlesize": 9.5, "axes.linewidth": 0.5, "xtick.major.width": 0.5, "ytick.major.width": 0.5,
        })


def finish(fig, name: str, title: str, source: str, note: str | None = None, outdir: Path = FIG,
           chrome: bool = True) -> list[Path]:
    """If chrome=False, omit embedded title/source (for LaTeX captions in the research note)."""
    if chrome:
        fig.suptitle(title, x=0.01, ha="left", fontsize=plt.rcParams["figure.titlesize"], fontweight="bold")
        note_size = max(plt.rcParams["font.size"] * 0.8, 6.0)
        width = int(fig.get_figwidth() * 72 / (0.5 * note_size))
        txt = "\n".join(textwrap.wrap(f"Source: {source}", width))
        if note:
            txt += "\n" + "\n".join(textwrap.wrap(f"Note: {note}", width))
        fig.canvas.draw()
        bottom = min(ax.get_tightbbox().transformed(fig.transFigure.inverted()).y0 for ax in fig.axes)
        fig.text(0.01, bottom - 0.012, txt, ha="left", va="top", fontsize=note_size, color=GREY, linespacing=1.35)
    else:
        fig.tight_layout(pad=0.4)
    outdir.mkdir(parents=True, exist_ok=True)
    out = []
    for ext in ("png", "pdf"):
        p = outdir / f"{name}.{ext}"
        fig.savefig(p, dpi=300 if ext == "png" else None, bbox_inches="tight", pad_inches=0.08)
        out.append(p)
    plt.close(fig)
    return out


# ----------------------------------------------------------- Figure 1
def fig1_capex(annual: pd.DataFrame, snap: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for t, g in annual.groupby("ticker"):
        g = g.sort_values("fiscal_year")
        ax.plot(g.fiscal_year, g.capex / 1e9, marker="o", ms=3.5, color=ISSUER_COLORS[t], label=ISSUER_NAMES[t])
        s = snap.set_index("ticker").loc[t]
        x = g.fiscal_year.max() + (0.75 if t in ("AMZN", "GOOGL", "META") else 0.25)
        ax.plot([g.fiscal_year.max(), x], [g.capex.iloc[-1] / 1e9, s.ttm_capex / 1e9], ls=":", color=ISSUER_COLORS[t], lw=1)
        ax.plot(x, s.ttm_capex / 1e9, marker="D", ms=5, mfc="white", mec=ISSUER_COLORS[t], mew=1.3)
    ax.set_xlabel("Fiscal year (labelled by calendar year of fiscal year-end)")
    ax.set_ylabel("Purchases of property & equipment, USD bn")
    ax.set_xticks(range(2018, 2027))
    ax.legend(ncol=5, loc="upper left")
    ax.text(0.99, 0.02, "Hollow diamonds = trailing twelve months to latest 10-Q\n(Sep-2026; Oracle Aug-2026)",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=7, color=GREY)
    return finish(fig, "fig1_capex_by_issuer",
                  "Figure 1. Annual capital expenditure by issuer, FY2018 to latest fiscal year and TTM",
                  "SEC EDGAR Company Facts (10-K, 10-Q XBRL); author calculations.",
                  "Cash capex as reported (Amazon: purchases of property and equipment, gross of incentives). Excludes assets "
                  "acquired under finance leases (material for Microsoft and Amazon). Fiscal years end Dec (AMZN, GOOGL, META), "
                  "Jun (MSFT), May (ORCL). Observation period FY2018–FY2025/26; TTM through Sep-2026 (ORCL Aug-2026).")


# ----------------------------------------------------------- Figure 2
def fig2_ocf_capex(annual: pd.DataFrame, snap: pd.DataFrame):
    order = ["AMZN", "GOOGL", "MSFT", "META", "ORCL"]
    fig, axes = plt.subplots(1, 5, figsize=(11, 3.6), sharey=False)
    for ax, t in zip(axes, order):
        g = annual[annual.ticker == t].sort_values("fiscal_year")
        g = g[g.fiscal_year >= 2019]
        s = snap.set_index("ticker").loc[t]
        labels = [f"FY{str(y)[2:]}" for y in g.fiscal_year] + ["TTM"]
        ocf = list(g.operating_cash_flow / 1e9) + [s.ttm_operating_cash_flow / 1e9]
        cap = list(g.capex / 1e9) + [s.ttm_capex / 1e9]
        fcf = np.array(ocf) - np.array(cap)
        x = np.arange(len(labels))
        w = 0.4
        ax.bar(x - w / 2, ocf, w, color="#9fb7cf", label="Operating cash flow")
        ax.bar(x + w / 2, cap, w, color=ISSUER_COLORS[t], label="Capex")
        ax.plot(x, fcf, color="black", marker="o", ms=3, lw=1, label="FCF = OCF − capex")
        ax.axhline(0, color="black", lw=0.6)
        ax.bar(x[-1:] - w / 2, ocf[-1:], w, color="none", edgecolor="black", hatch="///", lw=0)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=90, fontsize=7)
        ax.set_title(ISSUER_NAMES[t])
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("USD bn")
    axes[0].legend(loc="upper left", fontsize=6.5)
    fig.subplots_adjust(wspace=0.35, top=0.82, bottom=0.25)
    return finish(fig, "fig2_ocf_vs_capex",
                  "Figure 2. Operating cash flow versus capital expenditure, with free cash flow",
                  "SEC EDGAR Company Facts (10-K, 10-Q XBRL); author calculations.",
                  "FCF = net cash from operating activities − purchases of property and equipment. TTM = last fiscal year + "
                  "current YTD − prior-year YTD (Amazon reports TTM directly). Note different y-axis scales. "
                  "Negative FCF is not by itself evidence of credit distress.")


# ----------------------------------------------------------- Figure 3
def fig3_maturities(mat: pd.DataFrame, tr: pd.DataFrame, fye: dict, name: str = "fig3_debt_maturity_schedule",
                    title: str = "Figure 3. Debt maturity profile: 10-K contractual schedule and subsequently issued notes",
                    outdir: Path = FIG, figsize=(8.5, 6.6), chrome: bool = True):
    order = ["AMZN", "GOOGL", "MSFT", "META", "ORCL"]
    title_fs = plt.rcParams["axes.titlesize"]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=figsize, gridspec_kw={"height_ratios": [1, 1]})
    w = 0.16
    buckets = [1, 2, 3, 4, 5]
    near_bits = []
    for i, t in enumerate(order):
        m = mat[(mat.ticker == t)].sort_values("bucket_order")
        vals = [m[m.bucket_order == b].principal_usd.iloc[0] / 1e9 for b in buckets]
        near = Decimal(str(sum(vals[:3]))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        thereafter = m[m.bucket_order == 6].principal_usd.iloc[0] / 1e9
        near_bits.append(f"{ISSUER_NAMES[t]} \\${near}bn / \\${thereafter:,.0f}bn")
        a1.bar(np.arange(5) + (i - 2) * w, vals, w, color=ISSUER_COLORS[t], label=ISSUER_NAMES[t])
    a1.set_xticks(np.arange(5))
    a1.set_xticklabels(["Year 1", "Year 2", "Year 3", "Year 4", "Year 5"])
    a1.set_ylabel("Principal due, USD bn")
    a1.set_title("(a) Contractual principal maturities in the latest 10-K (years after fiscal year-end)",
                 loc="left", fontsize=title_fs, fontweight="bold")
    a1.set_ylim(0, a1.get_ylim()[1] * 1.18)
    a1.legend(fontsize=6.2, ncol=5, loc="upper left", frameon=False)
    a1.text(0.0, -0.18,
            "Years 1–3 / thereafter: " + "; ".join(near_bits),
            transform=a1.transAxes, fontsize=5.5, color=GREY, ha="left", va="top")
    a1.grid(axis="x", visible=False)

    post = tr.copy()
    post = post[post.apply(lambda r: r.filing_date > fye[r.ticker], axis=1)]
    # Start at 2028: no post-FYE registered notes mature in 2027 in this sample.
    yrs = list(range(2028, 2034))
    cats = [str(y) for y in yrs] + ["2034-45", "2046-55", "2056+"]
    cat_labels = [str(y) for y in yrs] + ["2034–45\n(12 yrs)", "2046–55\n(10 yrs)", "2056+"]

    def cat(y):
        if y <= 2033:
            return str(y)
        return "2034-45" if y <= 2045 else ("2046-55" if y <= 2055 else "2056+")
    post["mcat"] = post.maturity_year.apply(cat)
    piv = post.pivot_table(index="mcat", columns="ticker", values="principal_usd", aggfunc="sum").reindex(cats).fillna(0) / 1e9
    bottom = np.zeros(len(cats))
    for t in order:
        if t in piv:
            a2.bar(cats, piv[t], bottom=bottom, color=ISSUER_COLORS[t], label=ISSUER_NAMES[t], width=0.7)
            bottom += piv[t].values
    a2.set_xticks(range(len(cats)))
    a2.set_xticklabels(cat_labels)
    a2.set_ylabel("Principal issued, USD-equiv. bn")
    a2.set_title("(b) Notes issued after each issuer's latest fiscal year-end, by maturity year (to 13-Nov-2026)",
                 loc="left", fontsize=title_fs, fontweight="bold")
    a2.set_ylim(0, bottom.max() * 1.18)
    a2.legend(fontsize=6.4, ncol=5, loc="upper left", frameon=False)
    a2.grid(axis="x", visible=False)
    fig.subplots_adjust(hspace=0.42, top=0.92, bottom=0.10)
    return finish(fig, name, title,
                  "SEC EDGAR: 10-K XBRL maturity tags (LongTermDebtMaturitiesRepaymentsOfPrincipal*); final prospectus "
                  "supplements (424B2/424B5); FRED H.10 FX rates for non-USD tranches. Author calculations.",
                  "Panel (a) uses fiscal-year buckets (MSFT FY ends Jun-2026; ORCL May-2026; others Dec-2025). Panel (b) adds gross "
                  "new issuance only; repayments after the 10-K date, commercial paper, term loans, leases and 144A/private debt are "
                  "not shown. Contractual maturities do not necessarily require new issuance.", outdir=outdir, chrome=chrome)


# ----------------------------------------------------------- Figure 4
def fig4_issuance(tr: pd.DataFrame, conc: pd.DataFrame):
    order = ["AMZN", "GOOGL", "MSFT", "META", "ORCL"]
    fig, ax = plt.subplots(figsize=(8, 4.4))
    years = list(range(2018, 2027))
    usd = tr[tr.currency == "USD"].pivot_table(index="issue_year", columns="ticker", values="principal_usd", aggfunc="sum").reindex(years).fillna(0) / 1e9
    nonusd = tr[tr.currency != "USD"].groupby("issue_year").principal_usd.sum().reindex(years).fillna(0) / 1e9
    bottom = np.zeros(len(years))
    for t in order:
        if t in usd:
            ax.bar(years, usd[t], bottom=bottom, color=ISSUER_COLORS[t], label=f"{ISSUER_NAMES[t]} (USD)", width=0.7)
            bottom += usd[t].values
    ax.bar(years, nonusd, bottom=bottom, color="white", edgecolor=GREY, hatch="////", lw=0.6,
           label="Non-USD tranches, all five (USD-equiv.)", width=0.7)
    ax.set_ylabel("Gross SEC-registered bond issuance, USD bn")
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) if y < 2026 else "2026\n(to 13-Nov)" for y in years])
    ax.grid(axis="x", visible=False)
    ax2 = ax.twinx()
    ax2.spines["right"].set_visible(True)
    ax2.grid(False)
    c = conc[conc.period.str.startswith("FY") | (conc.period == "2026 Jan-Oct")].copy()
    xs = [2023, 2024, 2025, 2026]
    ax2.plot(xs, c.share_of_denominator.values * 100, color="black", marker="s", ms=5, lw=1.2,
             label="Five-issuer USD issuance ÷ SIFMA total US corporate issuance (RHS; 2026 = Jan–Oct)")
    for x, v in zip(xs, c.share_of_denominator.values * 100):
        ax2.annotate(f"{v:.1f}%", (x, v), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=7.5)
    ax2.set_ylabel("Share of total US corporate issuance, %")
    ax2.set_ylim(0, max(c.share_of_denominator.values * 100) * 1.6)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=7)
    return finish(fig, "fig4_issuance_vs_market",
                  "Figure 4. Hyperscaler bond issuance versus the broader U.S. corporate bond market",
                  "SEC EDGAR final prospectus supplements (424B2/424B5), author-curated tranche dataset; SIFMA Research Quarterly "
                  "(4Q24, 4Q25, 3Q26) and SIFMA US Corporate Bonds Statistics page (2-Nov-2026); FRED H.10 FX rates.",
                  "Coverage: SEC-registered public offerings only (no 144A, private placements, term loans, CP, project-finance/JV "
                  "debt). SIFMA denominator is ALL US corporate issuance (IG+HY+private placement+convertible), so the ratio "
                  "understates the share of IG-only issuance. Proceeds are not assumed to be AI-specific.")


def fig_s1_new_issue_spreads(nis: pd.DataFrame, fred: pd.DataFrame):
    order = ["AMZN", "GOOGL", "MSFT", "META", "ORCL"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    f = fred.set_index("date").loc["2023-11-01":]
    for sid, lab, ls in [("BAMLC0A2CAA", "ICE AA OAS", "-"), ("BAMLC0A3CA", "ICE A OAS", "--"), ("BAMLC0A4CBBB", "ICE BBB OAS", ":")]:
        ax.plot(f.index, f[sid] * 100, color=GREY, ls=ls, lw=1.1, label=lab)
    x = nis[nis.tenor_years_approx.between(8, 12)]
    for t in order:
        g = x[x.ticker == t]
        if len(g):
            ax.scatter(g.filing_date, g.spread_to_ust_bp, s=g.principal_usd / 1e8 * 2.2, color=ISSUER_COLORS[t],
                       edgecolor="white", lw=0.4, label=f"{ISSUER_NAMES[t]} 8–12y new issue", zorder=3)
    ax.set_ylabel("Basis points")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%y"))
    ax.legend(fontsize=7, ncol=2, loc="upper left")
    return finish(fig, "figS1_new_issue_spreads_vs_index",
                  "Supplementary Figure S1. New-issue spreads of 8–12 year tranches versus ICE rating-bucket OAS",
                  "SEC EDGAR FWP pricing term sheets (spread to benchmark Treasury); FRED (ICE BofA OAS series, available from "
                  "13-Nov-2023 only).",
                  "Marker area ∝ tranche size. New-issue spread is to an on-the-run benchmark Treasury at pricing; ICE OAS is an "
                  "option-adjusted spread to the spot Treasury curve for a market-value-weighted index of all maturities. The two "
                  "are related but not identical measures.")


# ----------------------------------------------------------- Figure 5
def fig5_macro(fred: pd.DataFrame, nfci: pd.DataFrame, name: str = "fig5_rates_spreads_conditions",
               title: str = "Figure 5. Treasury yields, investment-grade credit spreads and financial conditions, Jan-2018 to Nov-2026",
               outdir: Path = FIG, figsize=(8, 7.6), chrome: bool = True):
    f = fred.set_index("date")
    n = nfci.set_index("date")
    fig, axes = plt.subplots(3, 1, figsize=figsize, sharex=True, gridspec_kw={"height_ratios": [1.1, 1.1, 0.7]})
    for sid, lab, c in [("DGS2", "2Y", "#8fb3d9"), ("DGS10", "10Y", "#1f3b63"), ("DGS30", "30Y", "#8c2d2d")]:
        axes[0].plot(f.index, f[sid], color=c, lw=1.1, label=lab)
    axes[0].set_ylabel("Treasury CMT yield, %")
    title_fs = plt.rcParams["axes.titlesize"]
    axes[0].legend(ncol=3, loc="upper left")
    axes[0].set_title("(a) U.S. Treasury yields", loc="left", fontsize=title_fs, fontweight="bold")
    axes[1].plot(f.index, f["BAA10Y"] * 100, color="#c07a2c", lw=1.1, label="Moody's seasoned Baa − 10Y CMT (full period)")
    axes[1].plot(f.index, f["BAMLC0A0CM"] * 100, color="#1f3b63", lw=1.1, label="ICE BofA US Corporate (IG) OAS")
    axes[1].plot(f.index, f["BAMLC0A4CBBB"] * 100, color="#8c2d2d", lw=1.0, label="ICE BofA BBB OAS")
    axes[1].plot(f.index, f["BAMLC0A2CAA"] * 100, color="#4f7cac", lw=1.0, ls="--", label="ICE BofA AA OAS")
    axes[1].axvline(pd.Timestamp("2023-11-13"), color=GREY, lw=0.7, ls=":")
    axes[1].text(pd.Timestamp("2023-10-15"), 45, "ICE series on FRED\nstart 13-Nov-2023 →",
                 fontsize=6.5, color=GREY, va="bottom", ha="right")
    axes[1].set_ylabel("Spread, bp")
    axes[1].legend(fontsize=6.2, loc="upper right", frameon=True, fancybox=False,
                   edgecolor="#dddddd", framealpha=0.92)
    axes[1].set_title("(b) Corporate credit spreads", loc="left", fontsize=title_fs, fontweight="bold")
    axes[2].plot(n.index, n["NFCI"], color="black", lw=1.0)
    axes[2].axhline(0, color=GREY, lw=0.6)
    axes[2].set_ylabel("NFCI (index)")
    axes[2].set_title("(c) Chicago Fed National Financial Conditions Index (positive = tighter than average)",
                      loc="left", fontsize=title_fs, fontweight="bold")
    x_end = min(pd.Timestamp("2026-11-13"), f.index.max())
    for ax in axes:
        ax.axvspan(pd.Timestamp("2025-10-01"), x_end, color="#f2e6d9", alpha=0.6, lw=0)
        ax.set_xlim(pd.Timestamp("2018-01-01"), x_end)
    axes[0].text(pd.Timestamp("2025-10-10"), axes[0].get_ylim()[0] + 0.2, "Hyperscaler\nsupply wave", fontsize=6.5, color=GREY)
    axes[2].xaxis.set_major_locator(mdates.YearLocator())
    axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.subplots_adjust(hspace=0.3, top=0.92, bottom=0.1)
    return finish(fig, name, title,
                  "FRED: DGS2, DGS10, DGS30, BAA10Y (Moody's), BAMLC0A0CM, BAMLC0A4CBBB, BAMLC0A2CAA (ICE Data Indices), NFCI "
                  "(Chicago Fed). Retrieved 13-Nov-2026.",
                  "Daily data except NFCI (weekly). ICE BofA OAS series are restricted on FRED to the most recent three years "
                  "(from 13-Nov-2023). Moody's Baa−10Y is a yield spread on long-dated seasoned bonds, not an OAS, and is shown as "
                  "a long-history proxy, not a substitute. Shading marks a descriptive period, not an identified causal event.",
                  outdir=outdir, chrome=chrome)


def fig_s2_rolling_corr(rc_long: pd.Series, rc_ig: pd.Series, name: str = "figS2_rolling_correlation",
                       title: str = "Supplementary Figure S2. Rolling 126-business-day correlation: 10Y Treasury yield vs credit spreads",
                       outdir: Path = FIG, figsize=(8, 3.4), chrome: bool = True):
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(rc_long.index, rc_long, color="#c07a2c", lw=1.1, label="ΔDGS10 vs ΔBAA10Y (Moody's)")
    ax.plot(rc_ig.index, rc_ig, color="#1f3b63", lw=1.1, label="ΔDGS10 vs ΔICE IG OAS")
    ax.axhline(0, color="black", lw=0.6)
    ax.set_ylabel("Correlation of daily changes")
    ax.set_ylim(-1, 1)
    x_end = max(rc_long.dropna().index.max(), rc_ig.dropna().index.max())
    ax.set_xlim(rc_long.dropna().index.min(), x_end)
    ax.legend(loc="lower left")
    return finish(fig, name, title,
                  "FRED; author calculations.",
                  "Correlation of daily first differences; window ≈ 6 months. BAA10Y is mechanically linked to DGS10 (it is "
                  "measured relative to it), which biases its correlation downward. Correlation does not imply causation.", outdir=outdir, chrome=chrome)


# ----------------------------------------------------------- Figure 6
def fig6_sensitivity(grid: pd.DataFrame, labels: dict):
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    cols = ["#8fb3d9", "#4f7cac", "#1f3b63", "#c07a2c", "#8c2d2d", "black"]
    for c, col in zip(grid.columns, cols):
        ax.plot(grid.index, grid[c] * 100, color=col, label=labels.get(c, c))
    for s in (50, 100):
        ax.axvline(s, color=GREY, lw=0.6, ls=":")
        ax.text(s + 2, -0.5, f"+{s}bp", fontsize=7, color=GREY)
    ax.set_xlabel("Parallel credit-spread widening, bp")
    ax.set_ylabel("Approximate price change, % (first-order)")
    ax.legend(fontsize=7, loc="lower left")
    return finish(fig, "fig6_spread_sensitivity",
                  "Figure 6. Illustrative bond price sensitivity to credit-spread widening, by spread duration (HYPOTHETICAL)",
                  "Durations computed by the author from coupon, re-offer yield and tenor disclosed in SEC EDGAR pricing term "
                  "sheets (at issue).",
                  "ΔP/P ≈ −D_spread × Δs. First-order approximation; excludes convexity, curve reshaping, call options and "
                  "carry. Spread duration approximated by at-issue modified duration of fixed-rate bullet bonds. Not a forecast "
                  "and not realised returns.")
