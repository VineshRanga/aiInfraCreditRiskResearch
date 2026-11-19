import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
CUTOFF = pd.Timestamp("2026-11-13")


def _load(rel, **kw):
    p = ROOT / rel
    if not p.exists():
        pytest.skip(f"{rel} not built; run src/build_datasets.py")
    return pd.read_csv(p, **kw)


@pytest.fixture(scope="session")
def annual():
    return _load("data/processed/issuer_annual_10k.csv", parse_dates=["fiscal_period_end", "filed_10k"])


@pytest.fixture(scope="session")
def snapshot():
    return _load("data/processed/issuer_latest_10q_snapshot.csv")


@pytest.fixture(scope="session")
def tranches():
    return _load("data/curated/bond_issuance_tranches.csv", parse_dates=["filing_date"])


@pytest.fixture(scope="session")
def fred():
    return _load("data/processed/fred_daily.csv", parse_dates=["date"])
