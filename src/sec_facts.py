"""Helpers to extract annual 10-K observations from SEC Company Facts JSON.

Point-in-time convention: for each fiscal-period end we keep the value as
FIRST reported in a 10-K (the earliest-filed 10-K containing that period),
so later restatements do not leak backwards. The accession number and
filing date of the source 10-K are preserved for traceability.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_SEC = ROOT / "data" / "raw" / "sec"

ANNUAL_FORMS = {"10-K", "10-K/A", "10-KT"}


def load_facts(ticker: str) -> dict:
    return json.loads((RAW_SEC / f"companyfacts_{ticker}.json").read_text())


def concept_frame(facts: dict, concept: str, taxonomy: str = "us-gaap") -> pd.DataFrame:
    node = facts["facts"].get(taxonomy, {}).get(concept)
    if node is None:
        return pd.DataFrame()
    rows = []
    for unit, obs in node["units"].items():
        for o in obs:
            rows.append({**o, "unit": unit, "concept": concept})
    df = pd.DataFrame(rows)
    df["end"] = pd.to_datetime(df["end"])
    df["filed"] = pd.to_datetime(df["filed"])
    if "start" in df:
        df["start"] = pd.to_datetime(df["start"])
    return df


def annual_values(facts: dict, concept: str, kind: str, fy_ends: pd.Series | None = None) -> pd.DataFrame:
    """Annual 10-K observations for a concept.

    kind='flow'  : duration facts spanning ~one fiscal year (350-380 days).
    kind='instant': balance-sheet facts at a fiscal year-end date.
    Returns one row per period end: [end, value, unit, filed, accn, form, concept].
    """
    df = concept_frame(facts, concept)
    if df.empty:
        return df
    df = df[df["form"].isin(ANNUAL_FORMS)].copy()
    if df.empty:
        return df
    if kind == "flow":
        if "start" not in df:
            return pd.DataFrame()
        days = (df["end"] - df["start"]).dt.days
        df = df[(days >= 350) & (days <= 380)]
    elif kind == "instant":
        if "start" in df:
            df = df[df["start"].isna()]
        if fy_ends is not None:
            df = df[df["end"].isin(set(fy_ends))]
    else:
        raise ValueError(kind)
    df = df.sort_values(["end", "filed"]).groupby("end", as_index=False).first()
    return df[["end", "val", "unit", "filed", "accn", "form", "concept"]].rename(columns={"val": "value"})


def first_available(facts: dict, concepts: list[str], kind: str, fy_ends=None) -> pd.DataFrame:
    """Combine candidate concepts: for each period end, use the first concept in
    priority order that has a value. The concept used is recorded per row."""
    out = []
    seen: set = set()
    for c in concepts:
        df = annual_values(facts, c, kind, fy_ends)
        if df.empty:
            continue
        df = df[~df["end"].isin(seen)]
        seen |= set(df["end"])
        out.append(df)
    if not out:
        return pd.DataFrame(columns=["end", "value", "unit", "filed", "accn", "form", "concept"])
    return pd.concat(out).sort_values("end").reset_index(drop=True)
