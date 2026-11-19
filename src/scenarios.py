"""Transparent, first-order credit-tightening scenarios.

All outputs are HYPOTHETICAL illustrations, not forecasts. Price effects use
ΔP/P ≈ −D × Δy with rate duration and spread duration kept separate; convexity,
spread-curve reshaping, call options, liquidity and default effects are ignored.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

SCENARIOS = {
    "UST +100bp": {"d_rate_bp": 100, "d_spread_bp": 0},
    "Spread +50bp": {"d_rate_bp": 0, "d_spread_bp": 50},
    "Spread +100bp": {"d_rate_bp": 0, "d_spread_bp": 100},
    "UST +100bp & spread +100bp": {"d_rate_bp": 100, "d_spread_bp": 100},
}


def price_sensitivity_grid(durations: dict[str, float], max_bp: int = 200, step: int = 5) -> pd.DataFrame:
    shocks = np.arange(0, max_bp + step, step)
    return pd.DataFrame({name: -d * shocks / 10_000 for name, d in durations.items()}, index=shocks).rename_axis("d_spread_bp")


def scenario_price_table(rate_duration: float, spread_duration: float) -> pd.DataFrame:
    rows = []
    for name, s in SCENARIOS.items():
        rows.append({"scenario": name,
                     "rate_component": -rate_duration * s["d_rate_bp"] / 10_000,
                     "spread_component": -spread_duration * s["d_spread_bp"] / 10_000})
    t = pd.DataFrame(rows)
    t["total_first_order"] = t.rate_component + t.spread_component
    return t


def financing_cost_scenarios(snap: pd.DataFrame, annual: pd.DataFrame) -> pd.DataFrame:
    """Incremental annual interest from repricing (a) contractual maturities due in the next
    three fiscal years (latest 10-K schedule) and (b) a hypothetical debt-financed TTM FCF
    shortfall (zero if TTM FCF ≥ 0). Δcost = amount × (Δrate + Δspread)."""
    last = annual.sort_values("fiscal_period_end").groupby("ticker").tail(1).set_index("ticker")
    rows = []
    for _, s in snap.iterrows():
        t = s["ticker"]
        mat3 = last.loc[t, "maturities_next_3y"]
        fcf_gap = max(-s["ttm_fcf"], 0.0)
        base_int = s["ttm_interest_expense"]
        ebitda = s["ttm_ebitda"]
        for name, sc in SCENARIOS.items():
            d = (sc["d_rate_bp"] + sc["d_spread_bp"]) / 10_000
            inc_mat = mat3 * d
            inc_gap = fcf_gap * d
            inc = inc_mat + inc_gap
            rows.append({
                "ticker": t, "scenario": name,
                "next3y_maturities_usd_bn": mat3 / 1e9,
                "hyp_fcf_gap_usd_bn": fcf_gap / 1e9,
                "incr_interest_maturities_usd_bn": inc_mat / 1e9,
                "incr_interest_fcf_gap_usd_bn": inc_gap / 1e9,
                "incr_interest_total_usd_bn": inc / 1e9,
                "incr_interest_pct_ttm_ebitda": inc / ebitda,
                "incr_interest_pct_ttm_ocf": inc / s["ttm_operating_cash_flow"],
                "ttm_ebitda_to_interest_base": ebitda / base_int,
                "ttm_ebitda_to_interest_pro_forma": ebitda / (base_int + inc),
            })
    return pd.DataFrame(rows)


def coupon_reset(tr: pd.DataFrame, oracle_notes: pd.DataFrame, annual: pd.DataFrame, snap: pd.DataFrame,
                 cutoff: str = "2026-11-13", legacy_before: str = "2025-01-01") -> pd.DataFrame:
    """Principal-weighted coupon of legacy notes (issued before `legacy_before`) maturing in the
    three calendar years after the cutoff vs the issuer's most recent USD 8-12y re-offer yield.

    Maturing-note coupons come from (i) Oracle's note-level 10-K XBRL, (ii) for other issuers,
    notes in the verified issuance dataset (2020+ registered offerings); pre-2020 notes are not
    observed for non-Oracle issuers, so observed amounts can differ from the 10-K schedule."""
    cut = pd.Timestamp(cutoff)
    legacy = pd.Timestamp(legacy_before)
    y0, y1 = cut.year + 1, cut.year + 3
    last = annual.sort_values("fiscal_period_end").groupby("ticker").tail(1).set_index("ticker")
    s = snap.set_index("ticker")
    rows = []
    for t in sorted(tr.ticker.unique()):
        usd = tr[(tr.ticker == t) & (tr.currency == "USD") & (tr.rate_type == "fixed")]
        if t == "ORCL":
            m = oracle_notes[oracle_notes.maturity_date.dt.year.between(y0, y1) & (oracle_notes.issue_date < legacy)].dropna(subset=["coupon"])
            amt, cpn = m.face_usd, m.coupon * 100
            source = "ORCL FY2026 10-K note-level XBRL"
        else:
            m = usd[usd.maturity_year.between(y0, y1) & (usd.filing_date < legacy)]
            amt, cpn = m.principal_usd, m.coupon_pct
            source = "Verified 2020-24 registered offerings"
        recent = usd[usd.tenor_years_approx.between(8, 12)].sort_values("filing_date").tail(1)
        rows.append({
            "ticker": t, "maturing_notes_observed_usd_bn": amt.sum() / 1e9,
            "pw_coupon_maturing_pct": np.average(cpn, weights=amt) if amt.sum() > 0 else np.nan,
            "latest_8_12y_reoffer_yield_pct": recent.reoffer_yield_pct.iloc[0] if len(recent) else np.nan,
            "latest_8_12y_issue_date": recent.filing_date.iloc[0].date() if len(recent) else None,
            "next3y_maturities_10k_usd_bn": last.loc[t, "maturities_next_3y"] / 1e9,
            "implied_avg_cost_of_debt_pct": s.loc[t, "ttm_interest_expense"] / s.loc[t, "gross_debt"] * 100,
            "maturing_coupon_source": source,
        })
    out = pd.DataFrame(rows)
    out.insert(1, "maturity_window", f"{y0}-{y1}")
    out["coupon_reset_bp"] = (out.latest_8_12y_reoffer_yield_pct - out.pw_coupon_maturing_pct) * 100
    return out


def new_issue_spread_dv01(tr: pd.DataFrame, since: str = "2025-01-01") -> pd.DataFrame:
    """Par-based spread DV01 of verified USD fixed-rate new issues: Σ principal × D_mod × 0.0001.
    Uses at-issue modified duration as a spread-duration proxy and par as the market-value proxy."""
    x = tr[(tr.filing_date >= since) & tr.mod_duration_at_issue.notna()].copy()
    x["spread_dv01_usd"] = x.principal_usd * x.mod_duration_at_issue * 1e-4
    g = x.groupby("ticker").agg(principal_usd_bn=("principal_usd", lambda s: s.sum() / 1e9),
                                spread_dv01_usd_mn=("spread_dv01_usd", lambda s: s.sum() / 1e6),
                                pw_mod_duration=("mod_duration_at_issue", lambda s: np.average(s, weights=x.loc[s.index, "principal_usd"])),
                                pw_spread_bp=("spread_to_ust_bp", lambda s: np.average(s, weights=x.loc[s.index, "principal_usd"])))
    g["pw_dts_at_issue"] = g.pw_mod_duration * g.pw_spread_bp
    g["value_change_spread_+100bp_usd_bn"] = -g.spread_dv01_usd_mn * 100 / 1e3
    return g.reset_index()
