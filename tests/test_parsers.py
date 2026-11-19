"""Parser tests. All text below is synthetic TEST-ONLY fixture text, not research data."""
import numpy as np
import pandas as pd

import issuance as iss
from build_datasets import _cusip_ok
from financial_metrics import _safe_div

FINAL_COVER = (
    "PROSPECTUS SUPPLEMENT (To Prospectus dated May 1, 2024) "
    "$1,000,000,000 4.100% Notes due 2031 $750,000,000 Floating Rate Notes due 2028 "
    "$2,000,000,000 5.250% Notes due 2056 Registration fee $299,881 4.100% Notes due 2031 "
)
ORACLE_STYLE = "Prospectus Supplement $3,000,000,000 aggregate principal amount of 5.800% notes due 2036"
EUR_COVER = "Prospectus supplement €1,500,000,000 3.250% Notes due 2034"

FWP_ONE_FIELD = (
    "Benchmark Treasury Yield: 4.000% / 4.500% "
    "Spread to Benchmark Treasury: T+60 bps / T+95 bps "
    "Yield to Maturity: 4.600% / 5.450%"
)
FWP_BLOCKS = (
    "2031 Notes: Benchmark Treasury Yield: 4.000% Spread to Benchmark Treasury: +60 bps Yield to Maturity: 4.600% "
    "2056 Notes: Benchmark Treasury Yield: 4.500% Spread to Benchmark Treasury: +95 bps Yield to Maturity: 5.450%"
)


def test_parse_tranches_and_drop_fee_amounts():
    t = iss.parse_tranches(FINAL_COVER)
    assert [(x["principal_local"], x["maturity_year"], x["rate_type"]) for x in t] == [
        (1e9, 2031, "fixed"), (7.5e8, 2028, "floating"), (2e9, 2056, "fixed")]
    assert np.isnan(t[1]["coupon_pct"]) and t[0]["coupon_pct"] == 4.1


def test_parse_tranches_without_possessive_and_non_usd():
    assert iss.parse_tranches(ORACLE_STYLE)[0]["coupon_pct"] == 5.8
    e = iss.parse_tranches(EUR_COVER)[0]
    assert e["currency"] == "EUR" and e["principal_local"] == 1.5e9


def test_fwp_spreads_both_layouts():
    for txt in (FWP_ONE_FIELD, FWP_BLOCKS):
        r = iss.parse_fwp_spreads(txt, 2)
        assert r["spreads_bp"] == [60, 95]
        assert r["ytm_pct"] == [4.6, 5.45]
        assert r["bench_pct"] == [4.0, 4.5]
        assert all(abs((y - b) * 100 - s) < 1e-9 for y, b, s in zip(r["ytm_pct"], r["bench_pct"], r["spreads_bp"]))


def test_classify():
    assert iss.classify("PRELIMINARY PROSPECTUS SUPPLEMENT Subject to Completion " + FINAL_COVER) == "preliminary"
    assert iss.classify(FINAL_COVER) == "debt_final"
    assert iss.classify("Prospectus Supplement We are offering 10,000,000 shares of our common stock") == "common_stock"


def test_cusip_check_digit():
    assert _cusip_ok("037833100")  # Apple Inc. common stock
    assert _cusip_ok("594918104")  # Microsoft Corp. common stock
    assert not _cusip_ok("037833101")
    assert not _cusip_ok("ABC")


def test_safe_div_zero_and_nan():
    r = _safe_div(pd.Series([1.0, 1.0, np.nan]), pd.Series([0.0, 2.0, 1.0]))
    assert np.isnan(r[0]) and r[1] == 0.5 and np.isnan(r[2])
