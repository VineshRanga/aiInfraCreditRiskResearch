"""Build a security-level issuance dataset from SEC EDGAR offering documents.

Sources (all downloaded to data/raw/sec/docs/ by data_collection.fetch_sec_document):
  * Final prospectus supplements (424B2 / 424B5, non-preliminary): tranche
    currency, principal, coupon, maturity year. These are the legal record of
    what was sold and are treated as authoritative.
  * Free-writing prospectus pricing term sheets (FWP): spread to benchmark
    Treasury, re-offer yield and benchmark yield. Spreads are only attached
    when the number of spread quotes equals the number of USD fixed-rate
    tranches AND re-offer yield minus benchmark yield reproduces each spread.

Only SEC-registered offerings are visible. 144A deals, private placements,
bank loans, commercial paper and off-balance-sheet project financings are
NOT captured.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "data" / "raw" / "sec" / "docs"
FILINGS_INDEX = ROOT / "data" / "raw" / "sec" / "filings_index_primary.csv"

CURRENCY_TOKENS = {
    "US$": "USD", "$": "USD", "€": "EUR", "EUR": "EUR", "£": "GBP", "GBP": "GBP",
    "C$": "CAD", "A$": "AUD", "¥": "JPY", "JPY": "JPY", "CHF": "CHF", "SFr.": "CHF", "SFr": "CHF",
}
# FRED H.10 series and whether quoted as USD per foreign unit (True) or foreign per USD (False)
FX_SERIES = {"EUR": ("DEXUSEU", True), "GBP": ("DEXUSUK", True), "AUD": ("DEXUSAL", True),
             "CAD": ("DEXCAUS", False), "JPY": ("DEXJPUS", False), "CHF": ("DEXSZUS", False)}

MIN_TRANCHE_LOCAL = 1e8

_CUR = r"(US\$|C\$|A\$|\$|€|£|¥|CHF\s?|JPY\s?|EUR\s?|GBP\s?|SFr\.?\s?)"
TRANCHE_RE = re.compile(
    _CUR + r"\s?([\d,]+(?:\.\d+)?)\s*(billion|million)?\s+"
    r"(?:aggregate principal amount\s+)?(?:of\s+)?(?:(?:our|its|the|their)\s+)?"
    r"(\d+\.\d+\s?%|floating rate)\s+(?:senior\s+)?(?:fixed rate\s+)?notes\s+due\s+(\d{4})",
    re.I,
)
SPREAD_TOKEN = re.compile(r"(?:\bT\s*\+\s*|(?<![\w.])\+\s*)(\d{1,3}(?:\.\d+)?)\s*(?:bps|bp|basis points)", re.I)
PCT_TOKEN = re.compile(r"(\d+\.\d+)\s?%")
SPREAD_LABEL = re.compile(r"Spread to (?:the )?Benchmark(?: Treasury)?(?: Security)?\s*\**:", re.I)
YTM_LABEL = re.compile(r"(?:Yield to Maturity|Re-?offer Yield)\s*\**:", re.I)
YTM_LABEL_FALLBACK = re.compile(r"(?<!Treasury )(?<!Benchmark )(?<!/)(?<!and )\bYield\s*\**:", re.I)
BENCH_LABEL = re.compile(r"Benchmark Treasury (?:Price\s*(?:/|and)\s*)?Yield\s*\**:", re.I)


def doc_text(path: Path) -> str:
    s = path.read_text(errors="ignore")
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s).replace("\u200b", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", s)


def parse_doc_name(path: Path) -> dict:
    ticker, form, date, accn, *_ = path.name.split("_")
    return {"ticker": ticker, "form": form, "filing_date": pd.Timestamp(date), "accession": accn,
            "document": path.name.split("_", 4)[-1]}


def classify(text: str) -> str:
    head = text[:6000].upper()
    if "PRELIMINARY PROSPECTUS" in head or "SUBJECT TO COMPLETION" in head:
        return "preliminary"
    if parse_tranches(text):
        return "debt_final"
    m = re.search(r"prospectus supplement", text, re.I)
    cover = text[m.start():m.start() + 700].upper() if m else head[:700]
    if re.search(r"WE ARE OFFERING [\d,]+ SHARES|OFFERING [\d,]+ SHARES OF OUR", cover):
        return "common_stock"
    if "MANDATORY CONVERTIBLE PREFERRED" in cover:
        return "mandatory_convertible_preferred"
    if "EQUITY DISTRIBUTION AGREEMENT" in head or "AT THE MARKET" in head:
        return "equity_atm_program"
    if re.search(r"SHARES (OF )?(OUR )?(CLASS A )?COMMON STOCK", head) and "NOTES DUE" not in head[:2500]:
        return "common_stock"
    if "NOTES DUE" in head:
        return "debt_final"
    return "other"


def _amount(num: str, scale: str | None) -> float:
    v = float(num.replace(",", ""))
    if scale:
        v *= 1e9 if scale.lower() == "billion" else 1e6
    return v


def parse_tranches(text: str) -> list[dict]:
    """Parse tranches from the cover of a final prospectus supplement."""
    m = re.search(r"prospectus supplement", text, re.I)
    start = m.start() if m else 0
    cover = text[start:start + 12000]
    out, seen = [], set()
    for cur, num, scale, cpn, yr in TRANCHE_RE.findall(cover):
        key = (CURRENCY_TOKENS[cur.strip()], _amount(num, scale or None), cpn.lower().replace(" ", ""), int(yr))
        # registration-fee tables place fee amounts (e.g. $299,881) next to tranche titles
        if key in seen or key[1] < MIN_TRANCHE_LOCAL:
            continue
        seen.add(key)
        floating = "floating" in cpn.lower()
        out.append({"currency": key[0], "principal_local": key[1],
                    "coupon_pct": np.nan if floating else float(cpn.replace("%", "").strip()),
                    "rate_type": "floating" if floating else "fixed", "maturity_year": int(yr)})
    return out


def _pcts(s: str) -> list[float]:
    return [float(x) for x in re.findall(r"(\d+\.\d+)%", s)]


def _labelled_values(text: str, label: re.Pattern, token: re.Pattern, n: int) -> list[float]:
    """Values following each occurrence of a field label, up to n in total.

    Handles both term-sheet layouts: one field listing all tranches, or one
    block per tranche repeating the field."""
    hits = list(label.finditer(text))
    per_tranche_blocks = len(hits) >= n > 1
    vals: list[float] = []
    for i, m in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
        seg = text[m.end():min(end, m.end() + 900)]
        found = [float(x) for x in token.findall(seg)]
        vals += found[:1] if per_tranche_blocks else found
        if len(vals) >= n:
            break
    return vals[:n]


def parse_fwp_spreads(text: str, n: int) -> dict:
    ytm = _labelled_values(text, YTM_LABEL, PCT_TOKEN, n)
    if len(ytm) < n:
        ytm = _labelled_values(text, YTM_LABEL_FALLBACK, PCT_TOKEN, n)
    return {"spreads_bp": _labelled_values(text, SPREAD_LABEL, SPREAD_TOKEN, n),
            "ytm_pct": ytm,
            "bench_pct": _labelled_values(text, BENCH_LABEL, PCT_TOKEN, n)}


def build_offering_documents() -> pd.DataFrame:
    rows = []
    for p in sorted(DOCS.glob("*")):
        meta = parse_doc_name(p)
        if meta["form"] not in {"424B2", "424B5", "FWP"}:
            continue
        t = doc_text(p)
        meta["doc_class"] = "fwp_term_sheet" if meta["form"] == "FWP" else classify(t)
        meta["path"] = str(p.relative_to(ROOT))
        rows.append(meta)
    return pd.DataFrame(rows)


def fx_to_usd(currency: str, date: pd.Timestamp) -> tuple[float, str]:
    if currency == "USD":
        return 1.0, "n/a"
    from data_collection import fetch_fred_series  # cached locally
    sid, usd_per_unit = FX_SERIES[currency]
    fx = fetch_fred_series(sid, start="2018-01-01").dropna().set_index("date")["value"]
    rate = fx.loc[:date].iloc[-1]  # last available on/before the filing date
    return (rate if usd_per_unit else 1.0 / rate), sid


def build_issuance(docs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    tranches = []
    finals = docs[docs.doc_class == "debt_final"]
    fwps = docs[docs.doc_class == "fwp_term_sheet"]
    for _, d in finals.iterrows():
        text = doc_text(ROOT / d.path)
        tr = parse_tranches(text)
        for i, t in enumerate(tr):
            tranches.append({**t, "ticker": d.ticker, "filing_date": d.filing_date, "form": d.form,
                             "accession": d.accession, "document": d.document, "tranche_order": i,
                             "source_url": _edgar_url(d.ticker, d.accession, d.document)})
    df = pd.DataFrame(tranches)
    # Exchange offers / remarketings are not in scope; all finals here are new issues.
    df["fx_usd_per_unit"], df["fx_series"] = zip(*[fx_to_usd(c, dt) for c, dt in zip(df.currency, df.filing_date)])
    df["principal_usd"] = df.principal_local * df.fx_usd_per_unit
    df["issue_year"] = df.filing_date.dt.year
    df["tenor_years_approx"] = df.maturity_year - df.issue_year

    # attach FWP spreads for USD fixed-rate tranches
    df["spread_to_ust_bp"] = np.nan
    df["reoffer_yield_pct"] = np.nan
    df["benchmark_yield_pct"] = np.nan
    df["spread_source"] = None
    diag = []
    for (tk, acc), g in df[(df.currency == "USD")].groupby(["ticker", "accession"]):
        fdate = g.filing_date.iloc[0]
        cand = fwps[(fwps.ticker == tk) & (fwps.filing_date <= fdate) &
                    (fwps.filing_date >= fdate - pd.Timedelta(days=6))]
        fixed = g[g.rate_type == "fixed"].sort_values("tranche_order")
        status = "no_fwp"
        for _, f in cand.sort_values("filing_date", ascending=False).iterrows():
            txt = doc_text(ROOT / f.path)
            if "€" in txt[:3000] or "£" in txt[:3000] or "C$" in txt[:3000]:
                continue
            n = len(fixed)
            sp = parse_fwp_spreads(txt, n)
            s, y, b = sp["spreads_bp"], sp["ytm_pct"], sp["bench_pct"]
            if not (len(s) == len(y) == len(b) == n):
                status = f"incomplete(spreads={len(s)},ytm={len(y)},bench={len(b)},tranches={n})"
                continue
            if not all(abs((yy - bb) * 100 - ss) <= 1.5 for yy, bb, ss in zip(y, b, s)):
                status = "failed_ytm_minus_benchmark_check"
                continue
            status = "validated_ytm_minus_benchmark"
            df.loc[fixed.index, "spread_to_ust_bp"] = s
            df.loc[fixed.index, "reoffer_yield_pct"] = y
            df.loc[fixed.index, "benchmark_yield_pct"] = b
            df.loc[fixed.index, "spread_source"] = _edgar_url(f.ticker, f.accession, f.document)
            break
        diag.append({"ticker": tk, "accession": acc, "filing_date": fdate, "n_fixed_usd": len(fixed),
                     "fwp_candidates": len(cand), "spread_status": status})
    cols = ["ticker", "filing_date", "issue_year", "currency", "principal_local", "fx_usd_per_unit", "fx_series",
            "principal_usd", "rate_type", "coupon_pct", "maturity_year", "tenor_years_approx",
            "spread_to_ust_bp", "reoffer_yield_pct", "benchmark_yield_pct", "form", "accession",
            "document", "source_url", "spread_source", "tranche_order"]
    return df[cols].sort_values(["filing_date", "ticker", "tranche_order"]).reset_index(drop=True), pd.DataFrame(diag)


def _edgar_url(ticker: str, accession: str, document: str) -> str:
    from data_collection import ALL_ISSUERS
    return f"https://www.sec.gov/Archives/edgar/data/{ALL_ISSUERS[ticker]}/{accession.replace('-', '')}/{document}"


def build_non_debt_financing(docs: pd.DataFrame) -> pd.DataFrame:
    """Equity and hybrid financing events (registered), documented but not quantified
    beyond what the cover discloses."""
    out = []
    for _, d in docs[docs.doc_class.isin(["mandatory_convertible_preferred", "equity_atm_program", "common_stock"])].iterrows():
        text = doc_text(ROOT / d.path)
        i = text.lower().find("prospectus supplement")
        cover = text[i:i + 1500] if i >= 0 else text[:1500]
        m = re.search(r"Up to \$([\d,]+)", cover)
        sh = re.search(r"(?:offering|offering of)\s+([\d,]+)\s+(?:shares|of our Series|Series|depositary)", cover, re.I)
        out.append({"ticker": d.ticker, "filing_date": d.filing_date, "form": d.form, "doc_class": d.doc_class,
                    "program_cap_usd": float(m.group(1).replace(",", "")) if m else np.nan,
                    "shares_or_depositary_shares": float(sh.group(1).replace(",", "")) if sh else np.nan,
                    "is_supplement_amendment": bool(re.search(r"being filed to reflect|supersedes and replaces", cover)),
                    "cover_excerpt": cover[:400],
                    "source_url": _edgar_url(d.ticker, d.accession, d.document)})
    return pd.DataFrame(out)
