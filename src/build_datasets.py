"""Build all processed / curated datasets from cached raw downloads.

Run:  python src/build_datasets.py          (uses cached raw data)
      python src/build_datasets.py --refresh  (re-downloads first)
"""
from __future__ import annotations

import re
import sys

import numpy as np
import pandas as pd

import data_collection as dc
import financial_metrics as fm
import issuance as iss
from sec_facts import annual_values, load_facts
from xbrl_instance import fetch_instance, latest_filings, parse_instance

ROOT = dc.ROOT
PROC = ROOT / "data" / "processed"
CUR = ROOT / "data" / "curated"


def save(df: pd.DataFrame, path_stem, parquet: bool = True) -> None:
    path_stem.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path_stem.with_suffix(".csv"), index=False)
    if parquet:
        df.to_parquet(path_stem.with_suffix(".parquet"), index=False)


# ------------------------------------------------------------------ issuers
def build_issuer_datasets() -> pd.DataFrame:
    panels, provs = [], []
    for t in fm.PRIMARY:
        p, prov = fm.build_annual_panel(t)
        panels.append(p)
        provs.append(prov)
    annual = fm.add_ratios(pd.concat(panels, ignore_index=True))
    annual = annual[annual["fiscal_year"] >= 2018].reset_index(drop=True)
    save(annual, PROC / "issuer_annual_10k")
    prov = pd.concat(provs, ignore_index=True)
    prov = prov[prov["end"] >= "2017-05-01"]
    save(prov[["ticker", "item", "end", "value", "unit", "concept", "form", "accn", "filed"]],
         PROC / "issuer_annual_10k_provenance", parquet=False)

    snap = pd.DataFrame([fm.latest_snapshot(t) for t in fm.PRIMARY])
    snap["cash_and_sti"] = snap["cash"] + snap["short_term_investments"]
    snap["gross_debt"] = snap["debt_principal"] + snap["commercial_paper"].fillna(0)
    snap["net_debt"] = snap["gross_debt"] - snap["cash_and_sti"]
    snap["ttm_fcf"] = snap["ttm_operating_cash_flow"] - snap["ttm_capex"]
    snap["ttm_capex_to_ocf"] = snap["ttm_capex"] / snap["ttm_operating_cash_flow"]
    snap["ttm_fcf_margin"] = snap["ttm_fcf"] / snap["ttm_revenue"]
    snap["ttm_ebitda"] = snap["ttm_operating_income"] + snap["ttm_depreciation"]
    snap["gross_debt_to_ttm_ebitda"] = snap["gross_debt"] / snap["ttm_ebitda"]
    snap["net_debt_to_ttm_ebitda"] = snap["net_debt"] / snap["ttm_ebitda"]
    snap["ttm_ebitda_to_interest"] = snap["ttm_ebitda"] / snap["ttm_interest_expense"]
    save(snap, PROC / "issuer_latest_10q_snapshot")
    return annual


def build_secondary_issuers() -> pd.DataFrame:
    """Limited secondary universe: revenue, OCF, PP&E/real-estate investment, debt."""
    spec = {
        "revenue": ("flow", ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"]),
        "operating_cash_flow": ("flow", ["NetCashProvidedByUsedInOperatingActivities"]),
        "capex": ("flow", ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets",
                           "PaymentsForCapitalImprovements", "PaymentsToDevelopRealEstateAssets"]),
        "long_term_debt": ("instant", ["LongTermDebt", "LongTermDebtNoncurrent", "SeniorNotes"]),
        "cash": ("instant", ["CashAndCashEquivalentsAtCarryingValue"]),
    }
    from sec_facts import first_available
    rows = []
    for t in dc.SECONDARY:
        f = load_facts(t)
        fy = annual_values(f, "NetCashProvidedByUsedInOperatingActivities", "flow")
        fy = fy[fy["end"].dt.month == 12]
        for item, (kind, concepts) in spec.items():
            d = first_available(f, concepts, kind, fy["end"] if kind == "instant" else None)
            d = d[d["end"].isin(set(fy["end"]))]
            for _, r in d.iterrows():
                rows.append({"ticker": t, "fiscal_year": r["end"].year, "item": item, "value": r["value"],
                             "concept": r["concept"], "accn": r["accn"], "filed": r["filed"]})
    long = pd.DataFrame(rows)
    long = long[long["fiscal_year"] >= 2018]
    save(long, PROC / "secondary_issuers_annual_long", parquet=False)
    return long


def build_maturity_schedules(annual: pd.DataFrame) -> pd.DataFrame:
    """Long-format contractual maturity schedule as disclosed in each issuer's latest 10-K."""
    rows = []
    for t, g in annual.groupby("ticker"):
        last = g.sort_values("fiscal_period_end").iloc[-1]
        fy = int(last["fiscal_year"])
        for k in [1, 2, 3, 4, 5]:
            rows.append({"ticker": t, "fiscal_period_end": last["fiscal_period_end"], "source_fiscal_year": fy,
                         "bucket": f"FY{fy + k}", "bucket_order": k, "maturity_fiscal_year": fy + k,
                         "principal_usd": last.get(f"maturity_y{k}"), "accession_10k": last["accession_10k"]})
        rows.append({"ticker": t, "fiscal_period_end": last["fiscal_period_end"], "source_fiscal_year": fy,
                     "bucket": f"After FY{fy + 5}", "bucket_order": 6, "maturity_fiscal_year": np.nan,
                     "principal_usd": last.get("maturity_y6plus"), "accession_10k": last["accession_10k"]})
    df = pd.DataFrame(rows)
    save(df, CUR / "debt_maturity_schedule_latest_10k", parquet=False)
    return df


def build_oracle_note_level() -> pd.DataFrame:
    lf = latest_filings("ORCL", forms=("10-K",)).iloc[-1]
    inst = parse_instance(fetch_instance("ORCL", lf.accessionNumber, lf.primaryDocument))
    d = inst[inst["debt_member"].notna() & (inst["n_dims"] == 1) &
             inst["concept"].isin(["DebtInstrumentFaceAmount", "DebtInstrumentInterestRateStatedPercentage",
                                   "DebtInstrumentMaturityDate", "DebtInstrumentIssuanceDate1",
                                   "DebtInstrumentCarryingAmount"])]
    d = d[(d["instant"] == lf.reportDate.strftime("%Y-%m-%d")) | d["instant"].isna()]
    w = d.pivot_table(index="debt_member", columns="concept", values="value", aggfunc="first").reset_index()
    w = w.rename(columns={"DebtInstrumentFaceAmount": "face_usd", "DebtInstrumentInterestRateStatedPercentage": "coupon",
                          "DebtInstrumentMaturityDate": "maturity_date", "DebtInstrumentIssuanceDate1": "issue_date",
                          "DebtInstrumentCarryingAmount": "carrying_usd"})
    for c in ["face_usd", "coupon", "carrying_usd"]:
        if c in w:
            w[c] = pd.to_numeric(w[c], errors="coerce")
    w["maturity_date"] = pd.to_datetime(w.get("maturity_date"), errors="coerce")
    w["source"] = f"ORCL 10-K {lf.reportDate.date()} XBRL instance, accession {lf.accessionNumber}"
    save(w, CUR / "oracle_note_level_debt_fy2026", parquet=False)
    return w


# ----------------------------------------------------------------- issuance
def _cusip_ok(c: str) -> bool:
    if not re.fullmatch(r"[0-9]{3}[0-9A-Z]{5}[0-9]", c):
        return False
    total = 0
    for i, ch in enumerate(c[:8]):
        v = int(ch) if ch.isdigit() else ord(ch) - 55
        if i % 2:
            v *= 2
        total += v // 10 + v % 10
    return (10 - total % 10) % 10 == int(c[8])


def attach_cusips(tr: pd.DataFrame, docs: pd.DataFrame) -> pd.DataFrame:
    """Attach CUSIPs from FWP term sheets when a 'YYYY Notes: CUSIP' label maps uniquely
    to a single USD fixed-rate tranche maturing in YYYY, and the check digit is valid."""
    tr = tr.copy()
    tr["cusip"] = None
    fwps = docs[docs.doc_class == "fwp_term_sheet"]
    for (tk, acc), g in tr[(tr.currency == "USD")].groupby(["ticker", "accession"]):
        src = g["spread_source"].dropna()
        if src.empty:
            continue
        fdoc = src.iloc[0].rsplit("/", 1)[-1]
        f = fwps[(fwps.ticker == tk) & (fwps.document == fdoc)]
        if f.empty:
            continue
        text = iss.doc_text(ROOT / f.iloc[0].path)
        i = text.find("CUSIP")
        seg = text[i:i + 3000] if i >= 0 else ""
        pairs = re.findall(r"(\d{4})\s+(Fixed Rate\s+|Floating Rate\s+)?Notes\s*:?\s*([0-9]{3}[0-9A-Z]{5}[0-9])", seg)
        for yr, kind, cusip in pairs:
            if kind.strip().lower().startswith("floating") or not _cusip_ok(cusip):
                continue
            m = g[(g.maturity_year == int(yr)) & (g.rate_type == "fixed")]
            if len(m) == 1:
                tr.loc[m.index, "cusip"] = cusip
    return tr


MOODYS = r"\b(Aaa|Aa1|Aa2|Aa3|A1|A2|A3|Baa1|Baa2|Baa3)\b"
SP = r"(?<![A-Za-z])(AAA|AA\+|AA-|AA|A\+|A-|BBB\+|BBB-|BBB)(?![A-Za-z+\-])"


def attach_ratings(tr: pd.DataFrame, docs: pd.DataFrame) -> pd.DataFrame:
    """Expected ratings as printed in the FWP pricing term sheet (point-in-time at pricing)."""
    tr = tr.copy()
    tr["moodys_at_pricing"] = None
    tr["sp_at_pricing"] = None
    tr["ratings_text"] = None
    for src, g in tr.groupby(tr["spread_source"].fillna("")):
        if not src:
            continue
        doc = src.rsplit("/", 1)[-1]
        f = docs[(docs.doc_class == "fwp_term_sheet") & (docs.document == doc) & (docs.ticker == g.ticker.iloc[0])]
        if f.empty:
            continue
        text = iss.doc_text(ROOT / f.iloc[0].path)
        seg = next((text[m.end():m.end() + 260] for m in re.finditer(r"Ratings?[^:]{0,80}:", text)
                    if re.search(MOODYS, text[m.end():m.end() + 120])), None)
        if seg is None:
            continue
        mo = re.search(MOODYS, seg)
        sp_tok = None
        slash = re.search(MOODYS + r"\s*(?:\([^)]*\))?\s*/\s*(AAA|AA[+\-]?|A[+\-]?|BBB[+\-]?)(?![A-Za-z])", seg)
        labelled = (re.search(r"S&P\s*:\s*(AAA|AA[+\-]?|A[+\-]?|BBB[+\-]?)(?![A-Za-z])", seg) or
                    re.search(r"(AAA|AA[+\-]?|A[+\-]?|BBB[+\-]?)\s*(?:/\s*\w+\s*)?(?:\([^)]*\)\s*)?\(?(?:by\s+)?(?:Standard|S&P)", seg))
        if slash and "Standard" not in seg[:slash.end() + 20]:
            sp_tok = slash.group(2)
        elif labelled:
            sp_tok = labelled.group(1)
        tr.loc[g.index, "moodys_at_pricing"] = mo.group(1) if mo else None
        tr.loc[g.index, "sp_at_pricing"] = sp_tok
        tr.loc[g.index, "ratings_text"] = seg[:200]
    for c in ["moodys_at_pricing", "sp_at_pricing", "ratings_text"]:
        tr[c] = tr.groupby("accession")[c].transform(lambda s: s.ffill().bfill())
    return tr


def build_issuance_datasets() -> tuple[pd.DataFrame, pd.DataFrame]:
    docs = iss.build_offering_documents()
    save(docs, CUR / "offering_documents_index", parquet=False)
    tranches, diag = iss.build_issuance(docs)
    tranches = attach_cusips(tranches, docs)
    tranches = attach_ratings(tranches, docs)
    save(tranches, CUR / "bond_issuance_tranches")
    save(diag, ROOT / "outputs" / "diagnostics" / "issuance_spread_validation", parquet=False)
    nd = iss.build_non_debt_financing(docs)
    save(nd, CUR / "non_debt_financing_events", parquet=False)
    return tranches, nd


# --------------------------------------------------------------------- FRED
def build_fred() -> pd.DataFrame:
    frames, meta = [], []
    for sid, desc in dc.FRED_SERIES.items():
        s = dc.fetch_fred_series(sid)
        frames.append(s.set_index("date")["value"].rename(sid))
        m = dc.fred_metadata(sid)
        meta.append({"series_id": sid, "title": m["title"], "description_used": desc, "units": m["units"],
                     "frequency": m["frequency"], "fred_observation_start": m["observation_start"],
                     "fred_observation_end": m["observation_end"], "last_updated": m["last_updated"],
                     "n_obs_retrieved": int(s["value"].notna().sum()),
                     "first_obs_retrieved": s.dropna()["date"].min().date(),
                     "last_obs_retrieved": s.dropna()["date"].max().date()})
    wide = pd.concat(frames, axis=1).sort_index()
    wide.index.name = "date"
    wide = wide[wide.index <= dc.RESEARCH_CUTOFF]
    daily = wide.drop(columns=["NFCI"]).dropna(how="all")
    # ICE month-end weekend prints exist; keep business days only for daily analysis
    daily = daily[daily.index.dayofweek < 5]
    save(daily.reset_index(), PROC / "fred_daily")
    save(wide[["NFCI"]].dropna().reset_index(), PROC / "fred_nfci_weekly")
    save(pd.DataFrame(meta), PROC / "fred_series_metadata", parquet=False)
    return daily


def main(refresh: bool = False) -> None:
    if refresh:
        dc.collect_all(refresh=True)
    annual = build_issuer_datasets()
    build_secondary_issuers()
    build_maturity_schedules(annual)
    build_oracle_note_level()
    build_issuance_datasets()
    build_fred()
    print("datasets built")


if __name__ == "__main__":
    main(refresh="--refresh" in sys.argv)
