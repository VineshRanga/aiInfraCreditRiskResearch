"""Issuer fundamentals from SEC Company Facts: annual 10-K panel, latest
10-Q balance sheet, trailing-twelve-month flows, and conventional ratios.

Concept selection is issuer-specific because filers use different XBRL tags
for the same economic line item. Every value keeps its concept, accession
number and filing date (see `provenance`).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from sec_facts import annual_values, concept_frame, first_available, load_facts

ROOT = Path(__file__).resolve().parents[1]
PRIMARY = ["AMZN", "GOOGL", "MSFT", "META", "ORCL"]
FY_END_MONTH = {"AMZN": 12, "GOOGL": 12, "META": 12, "MSFT": 6, "ORCL": 5}

_REV = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"]
_INT = ["InterestExpense", "InterestExpenseNonoperating"]
_PPE = ["PaymentsToAcquirePropertyPlantAndEquipment"]

# (kind, concepts in priority order). Lists are combined per period end.
CONCEPTS: dict[str, dict[str, tuple[str, list[str]]]] = {
    t: {
        "revenue": ("flow", _REV),
        "operating_cash_flow": ("flow", ["NetCashProvidedByUsedInOperatingActivities"]),
        "capex": ("flow", _PPE),
        "operating_income": ("flow", ["OperatingIncomeLoss"]),
        "depreciation": ("flow", ["Depreciation"]),
        "amortization_intangibles": ("flow", ["AmortizationOfIntangibleAssets"]),
        "interest_expense": ("flow", _INT),
        "finance_lease_principal_payments": ("flow", ["FinanceLeasePrincipalPayments"]),
        "share_repurchases": ("flow", ["PaymentsForRepurchaseOfCommonStock"]),
        "dividends": ("flow", ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"]),
        "cash": ("instant", ["CashAndCashEquivalentsAtCarryingValue"]),
        "short_term_investments": ("instant", ["MarketableSecuritiesCurrent"]),
        "debt_principal": ("instant", ["LongTermDebt"]),
        "commercial_paper": ("instant", ["CommercialPaper"]),
        "finance_lease_liability": ("instant", ["FinanceLeaseLiability"]),
        "operating_lease_liability": ("instant", ["OperatingLeaseLiability"]),
        "total_assets": ("instant", ["Assets"]),
        "total_liabilities": ("instant", ["Liabilities"]),
        "stockholders_equity": ("instant", ["StockholdersEquity"]),
        "liabilities_and_equity": ("instant", ["LiabilitiesAndStockholdersEquity"]),
    }
    for t in PRIMARY
}
# Issuer-specific overrides (documented in research/methodology.md)
CONCEPTS["AMZN"]["capex"] = ("flow", ["PaymentsToAcquireProductiveAssets"])  # "Purchases of property and equipment" (gross)
CONCEPTS["AMZN"]["commercial_paper"] = ("instant", ["ShortTermBorrowings"])
CONCEPTS["GOOGL"]["revenue"] = ("flow", ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"])
CONCEPTS["ORCL"]["revenue"] = ("flow", ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"])
CONCEPTS["MSFT"]["short_term_investments"] = ("instant", ["ShortTermInvestments"])
CONCEPTS["ORCL"]["short_term_investments"] = ("instant", ["AvailableForSaleSecuritiesDebtSecuritiesCurrent", "MarketableSecuritiesCurrent"])
CONCEPTS["META"]["short_term_investments"] = ("instant", ["MarketableSecuritiesCurrent", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"])
# Face value of term debt; equals the sum of the contractual maturity schedule (tested)
CONCEPTS["MSFT"]["debt_principal"] = ("instant", ["DebtInstrumentCarryingAmount"])
CONCEPTS["META"]["debt_principal"] = ("instant", ["DebtInstrumentCarryingAmount", "LongTermDebtNoncurrent"])
CONCEPTS["ORCL"]["debt_principal"] = ("instant", ["DebtInstrumentCarryingAmount"])
CONCEPTS["ORCL"]["commercial_paper"] = ("instant", ["CommercialPaper"])

MATURITY_CONCEPTS = {
    1: "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths",
    2: "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo",
    3: "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree",
    4: "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFour",
    5: "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFive",
    6: "LongTermDebtMaturitiesRepaymentsOfPrincipalAfterYearFive",
}


def fiscal_year_label(end: pd.Timestamp, ticker: str) -> int:
    """Fiscal year named by the calendar year in which it ends (MSFT FY26 ends Jun-2026)."""
    return end.year


def build_annual_panel(ticker: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    facts = load_facts(ticker)
    fy = annual_values(facts, "NetCashProvidedByUsedInOperatingActivities", "flow")
    fy = fy[fy["end"].dt.month == FY_END_MONTH[ticker]]
    ends = fy["end"]
    wide, prov = {}, []
    for item, (kind, concepts) in CONCEPTS[ticker].items():
        d = first_available(facts, concepts, kind, ends if kind == "instant" else None)
        d = d[d["end"].isin(set(ends))]
        if d.empty:
            continue
        wide[item] = d.set_index("end")["value"]
        prov.append(d.assign(item=item, ticker=ticker))
    panel = pd.DataFrame(wide).reindex(sorted(set(ends)))
    panel.index.name = "fiscal_period_end"
    panel.insert(0, "ticker", ticker)
    panel.insert(1, "fiscal_year", [fiscal_year_label(e, ticker) for e in panel.index])
    # 10-K filing date for the period (the 10-K that first reported operating cash flow)
    panel["filed_10k"] = fy.set_index("end")["filed"].reindex(panel.index)
    panel["accession_10k"] = fy.set_index("end")["accn"].reindex(panel.index)
    # Maturity schedule as disclosed in that 10-K
    for k, c in MATURITY_CONCEPTS.items():
        m = annual_values(facts, c, "instant", ends)
        if not m.empty:
            panel[f"maturity_y{k if k < 6 else '6plus'}"] = m.set_index("end")["value"].reindex(panel.index)
    return panel.reset_index(), pd.concat(prov, ignore_index=True)


def add_ratios(p: pd.DataFrame) -> pd.DataFrame:
    p = p.copy()
    p["free_cash_flow"] = p["operating_cash_flow"] - p["capex"]
    p["capex_to_ocf"] = _safe_div(p["capex"], p["operating_cash_flow"])
    p["fcf_margin"] = _safe_div(p["free_cash_flow"], p["revenue"])
    p["capex_to_revenue"] = _safe_div(p["capex"], p["revenue"])
    p = p.sort_values(["ticker", "fiscal_period_end"])
    p["capex_yoy_growth"] = p.groupby("ticker")["capex"].pct_change(fill_method=None)
    p["cash_and_sti"] = p["cash"] + p["short_term_investments"]
    # Liabilities: Amazon and Oracle do not tag total liabilities; derive from the balance-sheet identity
    derived = p["liabilities_and_equity"] - p["stockholders_equity"]
    p["total_liabilities_derived"] = p["total_liabilities"].isna() & derived.notna()
    p["total_liabilities"] = p["total_liabilities"].fillna(derived)
    p["gross_debt"] = p["debt_principal"] + p["commercial_paper"].fillna(0)
    p["commercial_paper_reported"] = p["commercial_paper"].notna()
    p["gross_debt_incl_finance_leases"] = p["gross_debt"] + p["finance_lease_liability"]
    p["net_debt"] = p["gross_debt"] - p["cash_and_sti"]
    p["ebitda"] = p["operating_income"] + p["depreciation"] + p["amortization_intangibles"].fillna(0)
    p["amortization_reported"] = p["amortization_intangibles"].notna()
    p["gross_debt_to_ebitda"] = _safe_div(p["gross_debt"], p["ebitda"])
    p["net_debt_to_ebitda"] = _safe_div(p["net_debt"], p["ebitda"])
    p["ebitda_to_interest"] = _safe_div(p["ebitda"], p["interest_expense"])
    p["ebit_to_interest"] = _safe_div(p["operating_income"], p["interest_expense"])
    mats = [c for c in p.columns if c.startswith("maturity_y")]
    p["maturity_schedule_total"] = p[mats].sum(axis=1, min_count=len(mats)) if mats else np.nan
    p["maturities_next_3y"] = p[["maturity_y1", "maturity_y2", "maturity_y3"]].sum(axis=1, min_count=3)
    p["cash_sti_to_next3y_maturities"] = _safe_div(p["cash_and_sti"], p["maturities_next_3y"])
    p["fcf_less_next12m_maturities"] = p["free_cash_flow"] - p["maturity_y1"]
    p["shareholder_returns"] = p["share_repurchases"].fillna(0) + p["dividends"].fillna(0)
    return p


def _safe_div(a: pd.Series, b: pd.Series) -> pd.Series:
    b = b.where(b != 0)
    return a / b


# ---------------------------------------------------------------- latest 10-Q
def latest_instant(facts: dict, concepts: list[str], cutoff: pd.Timestamp) -> dict:
    best = None
    for c in concepts:
        df = concept_frame(facts, c)
        if df.empty:
            continue
        if "start" in df:
            df = df[df["start"].isna()]
        df = df[df["form"].isin(["10-K", "10-Q"]) & (df["filed"] <= cutoff)]
        if df.empty:
            continue
        row = df.sort_values(["end", "filed"]).iloc[-1]
        if best is None or row["end"] > best["end"]:
            best = {"value": row["val"], "end": row["end"], "concept": c, "accn": row["accn"],
                    "form": row["form"], "filed": row["filed"]}
    return best or {}


def ttm_flow(facts: dict, concepts: list[str], cutoff: pd.Timestamp) -> dict:
    """TTM = last fiscal year + current YTD - prior-year YTD (all as reported).
    Among candidate concepts, the one with the most recent period end is used."""
    results = [r for r in (_ttm_one(facts, c, cutoff) for c in concepts) if r]
    return max(results, key=lambda r: r["end"]) if results else {}


def _ttm_one(facts: dict, c: str, cutoff: pd.Timestamp) -> dict:
    for c in [c]:
        df = concept_frame(facts, c)
        if df.empty or "start" not in df:
            continue
        df = df[df["form"].isin(["10-K", "10-Q"]) & (df["filed"] <= cutoff)].copy()
        df["days"] = (df["end"] - df["start"]).dt.days
        latest_end = df["end"].max()
        cur = df[df["end"] == latest_end].sort_values("days")
        if cur.empty:
            continue
        ytd = cur.iloc[-1]
        if 350 <= ytd["days"] <= 380:
            return {"value": ytd["val"], "end": latest_end, "concept": c, "method": "fiscal year"}
        fy = df[(df["days"].between(350, 380)) & (df["end"] == ytd["start"] - pd.Timedelta(days=1))]
        prior = df[(df["days"].between(ytd["days"] - 7, ytd["days"] + 7)) &
                   (df["end"].between(latest_end - pd.Timedelta(days=372), latest_end - pd.Timedelta(days=358)))]
        if fy.empty or prior.empty:
            continue
        v = fy.sort_values("filed").iloc[-1]["val"] + ytd["val"] - prior.sort_values("filed").iloc[-1]["val"]
        return {"value": v, "end": latest_end, "concept": c, "method": f"FY + {ytd['days']}d YTD - prior YTD"}
    return {}


def latest_snapshot(ticker: str, cutoff: str = "2026-11-13") -> dict:
    cutoff = pd.Timestamp(cutoff)
    facts = load_facts(ticker)
    spec = CONCEPTS[ticker]
    out = {"ticker": ticker}
    debt_concepts = {
        "AMZN": ["LongTermDebt"], "GOOGL": ["DebtInstrumentCarryingAmount", "LongTermDebt"],
        "MSFT": ["DebtInstrumentCarryingAmount"], "META": ["DebtInstrumentCarryingAmount"],
        "ORCL": ["DebtInstrumentCarryingAmount"],
    }[ticker]
    for item, concepts in [("cash", spec["cash"][1]), ("short_term_investments", spec["short_term_investments"][1]),
                           ("debt_principal", debt_concepts), ("commercial_paper", spec["commercial_paper"][1]),
                           ("finance_lease_liability", spec["finance_lease_liability"][1])]:
        r = latest_instant(facts, concepts, cutoff)
        out[item] = r.get("value", np.nan)
        out[f"{item}_asof"] = r.get("end")
        out[f"{item}_concept"] = r.get("concept")
    out["debt_basis"] = "principal (face)"
    if ticker == "ORCL":
        # Oracle's 10-Q tags only carrying values: current notes + long-term notes and loans
        cur = latest_instant(facts, ["NotesPayableCurrent", "DebtCurrent"], cutoff)
        lt = latest_instant(facts, ["LongTermNotesAndLoans", "LongTermNotesPayable"], cutoff)
        if cur and lt and cur["end"] == lt["end"] and cur["end"] > out["debt_principal_asof"]:
            out["debt_principal"] = cur["value"] + lt["value"]
            out["debt_principal_asof"] = cur["end"]
            out["debt_principal_concept"] = f"{cur['concept']} + {lt['concept']}"
            out["debt_basis"] = "carrying value"
    # Stale commercial-paper observations are not carried forward
    if out.get("commercial_paper_asof") is not None and out["commercial_paper_asof"] != out["cash_asof"]:
        out["commercial_paper"] = np.nan
    for item in ["revenue", "operating_cash_flow", "capex", "operating_income", "depreciation", "interest_expense"]:
        r = ttm_flow(facts, spec[item][1], cutoff)
        out[f"ttm_{item}"] = r.get("value", np.nan)
        out[f"ttm_{item}_end"] = r.get("end")
        out[f"ttm_{item}_method"] = r.get("method")
        out[f"ttm_{item}_concept"] = r.get("concept")
    if ticker == "META" and pd.Timestamp(out["ttm_interest_expense_end"]) < pd.Timestamp(out["ttm_revenue_end"]):
        # Meta's 10-Qs tag interest on debt (InterestExpenseDebt) rather than total interest expense
        r = ttm_flow(facts, ["InterestExpenseDebt"], cutoff)
        out.update({"ttm_interest_expense": r.get("value", np.nan), "ttm_interest_expense_end": r.get("end"),
                    "ttm_interest_expense_method": r.get("method"), "ttm_interest_expense_concept": r.get("concept")})
    return out
