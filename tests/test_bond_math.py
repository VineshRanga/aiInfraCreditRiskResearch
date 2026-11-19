import numpy as np
import pandas as pd
import pytest

import market_analysis as ma
import scenarios as sc


def test_par_bond_prices_at_par():
    assert ma.bond_price(5.0, 5.0, 10) == pytest.approx(100.0, abs=1e-9)


def test_zero_coupon_macaulay_equals_maturity():
    assert ma.macaulay_duration(0.0, 4.0, 7) == pytest.approx(7.0, abs=1e-12)


def test_modified_duration_matches_finite_difference():
    c, y, t = 4.5, 5.2, 30
    h = 0.01  # 1bp in percent units
    num = -(ma.bond_price(c, y + h, t) - ma.bond_price(c, y - h, t)) / (2 * h / 100) / ma.bond_price(c, y, t)
    assert ma.modified_duration(c, y, t) == pytest.approx(num, rel=1e-4)


def test_duration_increases_with_maturity():
    d = [ma.modified_duration(5, 5, t) for t in (2, 5, 10, 30)]
    assert all(np.diff(d) > 0)


def test_first_order_price_change():
    assert ma.first_order_price_change(8.0, 100) == pytest.approx(-0.08)
    assert ma.first_order_price_change(8.0, 0) == 0


def test_scenario_table_separates_rate_and_spread():
    t = sc.scenario_price_table(rate_duration=6.0, spread_duration=4.0).set_index("scenario")
    assert t.loc["UST +100bp", "spread_component"] == 0
    assert t.loc["Spread +50bp", "rate_component"] == 0
    assert t.loc["UST +100bp & spread +100bp", "total_first_order"] == pytest.approx(-0.10)


def test_financing_cost_scenario_arithmetic():
    snap = pd.DataFrame([{"ticker": "X", "ttm_fcf": -10e9, "ttm_interest_expense": 2e9, "ttm_ebitda": 20e9,
                          "ttm_operating_cash_flow": 15e9}])
    ann = pd.DataFrame([{"ticker": "X", "fiscal_period_end": pd.Timestamp("2025-12-31"), "maturities_next_3y": 30e9}])
    r = sc.financing_cost_scenarios(snap, ann).set_index("scenario")
    # (30 + 10) bn × 200bp = 0.8 bn
    assert r.loc["UST +100bp & spread +100bp", "incr_interest_total_usd_bn"] == pytest.approx(0.8)
    assert r.loc["Spread +50bp", "ttm_ebitda_to_interest_pro_forma"] == pytest.approx(20 / 2.2)


def test_positive_fcf_has_no_funding_gap():
    snap = pd.DataFrame([{"ticker": "X", "ttm_fcf": 5e9, "ttm_interest_expense": 1e9, "ttm_ebitda": 20e9,
                          "ttm_operating_cash_flow": 15e9}])
    ann = pd.DataFrame([{"ticker": "X", "fiscal_period_end": pd.Timestamp("2025-12-31"), "maturities_next_3y": 0.0}])
    r = sc.financing_cost_scenarios(snap, ann)
    assert (r.hyp_fcf_gap_usd_bn == 0).all() and (r.incr_interest_total_usd_bn == 0).all()
