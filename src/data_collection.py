"""Raw data ingestion: SEC EDGAR Company Facts / submissions, FRED series.

Raw responses are cached under data/raw/ and only re-downloaded when
`refresh=True`. Every download appends a row to data/raw/retrieval_log.csv.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
load_dotenv(ROOT / ".env")

RESEARCH_CUTOFF = pd.Timestamp("2026-11-13")

PRIMARY = {
    "AMZN": 1018724,
    "GOOGL": 1652044,
    "MSFT": 789019,
    "META": 1326801,
    "ORCL": 1341439,
}
SECONDARY = {
    "EQIX": 1101239,
    "DLR": 1297996,
    "CEG": 1868275,
    "VST": 1692819,
}
ALL_ISSUERS = {**PRIMARY, **SECONDARY}

FRED_SERIES = {
    "DGS2": "2Y Treasury CMT yield (%)",
    "DGS5": "5Y Treasury CMT yield (%)",
    "DGS10": "10Y Treasury CMT yield (%)",
    "DGS30": "30Y Treasury CMT yield (%)",
    "BAMLC0A0CM": "ICE BofA US Corporate (IG) OAS (%)",
    "BAMLC0A4CBBB": "ICE BofA BBB US Corporate OAS (%)",
    "BAMLC0A3CA": "ICE BofA Single-A US Corporate OAS (%)",
    "BAMLC0A2CAA": "ICE BofA AA US Corporate OAS (%)",
    "BAMLC0A0CMEY": "ICE BofA US Corporate effective yield (%)",
    "BAMLH0A0HYM2": "ICE BofA US High Yield OAS (%)",
    "NFCI": "Chicago Fed NFCI (index, weekly)",
    "BAA10Y": "Moody's seasoned Baa yield minus 10Y CMT (%)",
    "AAA10Y": "Moody's seasoned Aaa yield minus 10Y CMT (%)",
    "DFF": "Effective federal funds rate (%)",
}


def _sec_headers() -> dict:
    ua = os.environ.get("SEC_USER_AGENT")
    if not ua:
        raise RuntimeError("SEC_USER_AGENT must be set (see .env.example)")
    return {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}


def _log(source: str, url: str, path: Path, note: str = "") -> None:
    log = RAW / "retrieval_log.csv"
    row = pd.DataFrame([{
        "retrieved_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": source, "url": url, "file": str(path.relative_to(ROOT)), "note": note,
    }])
    row.to_csv(log, mode="a", header=not log.exists(), index=False)


def fetch_companyfacts(ticker: str, refresh: bool = False) -> dict:
    cik = ALL_ISSUERS[ticker]
    path = RAW / "sec" / f"companyfacts_{ticker}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text())
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
    r = requests.get(url, headers=_sec_headers(), timeout=60)
    r.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(r.text)
    _log("SEC EDGAR Company Facts", url, path)
    time.sleep(0.2)  # SEC fair-access: <=10 req/s
    return r.json()


def fetch_submissions(ticker: str, refresh: bool = False) -> dict:
    cik = ALL_ISSUERS[ticker]
    path = RAW / "sec" / f"submissions_{ticker}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text())
    url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
    r = requests.get(url, headers=_sec_headers(), timeout=60)
    r.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(r.text)
    _log("SEC EDGAR submissions", url, path)
    time.sleep(0.2)
    return r.json()


def fetch_sec_document(url: str, name: str, refresh: bool = False) -> str:
    """Download an individual EDGAR document (e.g. 424B2 prospectus, 10-K HTML)."""
    path = RAW / "sec" / "docs" / name
    if path.exists() and not refresh:
        return path.read_text(errors="ignore")
    r = requests.get(url, headers=_sec_headers(), timeout=60)
    r.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(r.text)
    _log("SEC EDGAR document", url, path)
    time.sleep(0.2)
    return r.text


def fetch_fred_series(series_id: str, start: str = "2018-01-01", refresh: bool = False) -> pd.DataFrame:
    """Return observations as a DataFrame[date, value]. Missing ('.') -> NaN."""
    path = RAW / "fred" / f"{series_id}.json"
    if not path.exists() or refresh:
        key = os.environ.get("FRED_API_KEY")
        if not key:
            raise RuntimeError("FRED_API_KEY must be set (see .env.example)")
        base = "https://api.stlouisfed.org/fred"
        meta = requests.get(f"{base}/series", params={
            "series_id": series_id, "api_key": key, "file_type": "json"}, timeout=60)
        meta.raise_for_status()
        obs = requests.get(f"{base}/series/observations", params={
            "series_id": series_id, "api_key": key, "file_type": "json",
            "observation_start": start,
            "observation_end": RESEARCH_CUTOFF.strftime("%Y-%m-%d")}, timeout=60)
        obs.raise_for_status()
        payload = {"series": meta.json()["seriess"][0], "observations": obs.json()["observations"]}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload))
        _log("FRED API", f"{base}/series/observations?series_id={series_id}", path,
             note=f"observation_start={start}")
    payload = json.loads(path.read_text())
    df = pd.DataFrame(payload["observations"])[["date", "value"]]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"].replace(".", pd.NA), errors="coerce")
    return df


def fred_metadata(series_id: str) -> dict:
    return json.loads((RAW / "fred" / f"{series_id}.json").read_text())["series"]


def collect_all(refresh: bool = False) -> None:
    for t in ALL_ISSUERS:
        fetch_companyfacts(t, refresh)
        fetch_submissions(t, refresh)
    for s in FRED_SERIES:
        fetch_fred_series(s, refresh=refresh)


if __name__ == "__main__":
    collect_all()
