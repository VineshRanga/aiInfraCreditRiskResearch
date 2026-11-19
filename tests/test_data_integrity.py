"""Validation checks on the built research datasets."""
import numpy as np
import pandas as pd

from conftest import CUTOFF

PRIMARY = {"AMZN", "GOOGL", "MSFT", "META", "ORCL"}
FY_END_MONTH = {"AMZN": 12, "GOOGL": 12, "META": 12, "MSFT": 6, "ORCL": 5}


def test_no_post_cutoff_information(annual, tranches, fred):
    assert annual.filed_10k.max() <= CUTOFF
    assert annual.fiscal_period_end.max() <= CUTOFF
    assert tranches.filing_date.max() <= CUTOFF
    assert fred.date.max() <= CUTOFF


def test_unique_issuer_years(annual):
    assert not annual.duplicated(["ticker", "fiscal_year"]).any()
    assert set(annual.ticker) == PRIMARY


def test_fiscal_year_ends_consistent(annual):
    assert (annual.fiscal_period_end.dt.month == annual.ticker.map(FY_END_MONTH)).all()
    assert (annual.fiscal_period_end.dt.year == annual.fiscal_year).all()


def test_annual_values_come_from_10k_filed_after_period(annual):
    assert (annual.filed_10k > annual.fiscal_period_end).all()
    assert annual.accession_10k.notna().all()


def test_fcf_and_ratio_arithmetic(annual):
    a = annual.dropna(subset=["operating_cash_flow", "capex"])
    assert np.allclose(a.free_cash_flow, a.operating_cash_flow - a.capex)
    assert np.allclose(a.capex_to_ocf, a.capex / a.operating_cash_flow)


def test_no_zero_filled_core_flows(annual):
    for c in ["revenue", "operating_cash_flow", "capex", "operating_income"]:
        assert (annual[c].dropna() != 0).all(), c


def test_maturity_schedule_reconciles_to_principal(annual):
    m = annual.dropna(subset=["maturity_schedule_total", "debt_principal"])
    m = m[m.debt_principal > 0]
    gap = (m.maturity_schedule_total - m.debt_principal).abs() / m.debt_principal
    assert len(m) > 0 and gap.max() < 0.02


def test_snapshot_ttm_identities(snapshot):
    s = snapshot
    assert np.allclose(s.ttm_fcf, s.ttm_operating_cash_flow - s.ttm_capex)
    assert np.allclose(s.net_debt, s.gross_debt - s.cash_and_sti)


def test_tranches_unique_and_positive(tranches):
    key = ["accession", "currency", "principal_local", "coupon_pct", "maturity_year", "rate_type"]
    assert not tranches.duplicated(key).any()
    assert (tranches.principal_local >= 1e8).all()
    assert (tranches.maturity_year > tranches.issue_year).all()
    assert (tranches.issue_year == tranches.filing_date.dt.year).all()


def test_spreads_validated(tranches):
    v = tranches.dropna(subset=["spread_to_ust_bp"])
    err = ((v.reoffer_yield_pct - v.benchmark_yield_pct) * 100 - v.spread_to_ust_bp).abs()
    assert err.max() <= 1.5
    assert (v.currency == "USD").all()


def test_fx_conversion(tranches):
    usd = tranches[tranches.currency == "USD"]
    assert np.allclose(usd.principal_usd, usd.principal_local)
    non = tranches[tranches.currency != "USD"]
    assert non.fx_series.notna().all() and np.allclose(non.principal_usd, non.principal_local * non.fx_usd_per_unit)


def test_fred_units_and_gaps(fred):
    assert fred.DGS10.dropna().between(0, 10).all()
    assert fred.BAMLC0A0CM.dropna().between(0, 10).all()  # percent
    ice_start = fred.loc[fred.BAMLC0A0CM.notna(), "date"].min()
    assert ice_start >= pd.Timestamp("2023-11-01")  # FRED truncation documented in limitations.md
