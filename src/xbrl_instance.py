"""Parse dimensional XBRL instance documents (10-K / 10-Q `*_htm.xml`).

Company Facts omits dimensional facts, so note-by-note debt disclosures
(face amount, stated coupon, maturity by debt-instrument member) must be
read from the filing's own instance document.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests

from data_collection import ALL_ISSUERS, RAW, _log, _sec_headers

ROOT = Path(__file__).resolve().parents[1]
INSTANCE_DIR = RAW / "sec" / "xbrl_instances"
FILINGS_INDEX = RAW / "sec" / "filings_index_primary.csv"


def latest_filings(ticker: str, forms=("10-K", "10-Q"), cutoff="2026-11-13") -> pd.DataFrame:
    f = pd.read_csv(FILINGS_INDEX, parse_dates=["filingDate", "reportDate"])
    f = f[(f.ticker == ticker) & f.form.isin(forms) & (f.filingDate <= cutoff)]
    return f.sort_values("filingDate")


def fetch_instance(ticker: str, accession: str, primary_doc: str, refresh: bool = False) -> Path:
    name = primary_doc.replace(".htm", "_htm.xml")
    path = INSTANCE_DIR / f"{ticker}_{accession}_{name}"
    if path.exists() and not refresh:
        return path
    cik = ALL_ISSUERS[ticker]
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/{name}"
    r = requests.get(url, headers=_sec_headers(), timeout=120)
    r.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(r.content)
    _log("SEC EDGAR XBRL instance", url, path)
    return path


def parse_instance(path: Path) -> pd.DataFrame:
    """All numeric/text facts with their period and explicit dimension members."""
    tree = ET.parse(path)
    root = tree.getroot()
    ns_x = "{http://www.xbrl.org/2003/instance}"
    ns_d = "{http://xbrl.org/2006/xbrldi}"
    ctx = {}
    for c in root.iter(f"{ns_x}context"):
        cid = c.get("id")
        per = c.find(f"{ns_x}period")
        inst = per.find(f"{ns_x}instant")
        start = per.find(f"{ns_x}startDate")
        end = per.find(f"{ns_x}endDate")
        dims = {m.get("dimension").split(":")[-1]: (m.text or "").split(":")[-1]
                for m in c.iter(f"{ns_d}explicitMember")}
        ctx[cid] = {
            "instant": inst.text if inst is not None else None,
            "start": start.text if start is not None else None,
            "end": end.text if end is not None else None,
            "dims": dims,
        }
    rows = []
    for el in root:
        cref = el.get("contextRef")
        if cref is None:
            continue
        tag = el.tag
        m = re.match(r"\{(.+)\}(.+)", tag)
        nsuri, local = (m.group(1), m.group(2)) if m else ("", tag)
        c = ctx.get(cref, {})
        rows.append({
            "concept": local, "ns": nsuri, "value": el.text, "unit": el.get("unitRef"),
            "decimals": el.get("decimals"), "context": cref,
            "instant": c.get("instant"), "start": c.get("start"), "end": c.get("end"),
            "dims": c.get("dims", {}),
        })
    df = pd.DataFrame(rows)
    df["n_dims"] = df["dims"].apply(len)
    df["debt_member"] = df["dims"].apply(
        lambda d: d.get("DebtInstrumentAxis") or d.get("LongtermDebtTypeAxis") or d.get("ShortTermDebtTypeAxis"))
    return df
