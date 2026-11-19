# AI Infrastructure and the Concentration of Credit Risk in U.S. Investment-Grade Markets

Quantitative research foundation (not the final paper) on whether five AI-infrastructure issuers account for a disproportionate share of IG credit-portfolio sensitivity relative to their share of debt. The five are Amazon, Alphabet, Microsoft, Meta and Oracle.

- **Window:** Jan-2023 to 13-Nov-2026 (primary); from 2018 (extended).
- **Cutoff:** no information published after 13-Nov-2026 is used.
- **Data:** public sources only (SEC EDGAR, FRED), plus published SIFMA, bfinance and J.P. Morgan AM statistics with attribution.

Start with `research/findings.md`, then `research/limitations.md`. The drafted research note is `paper/main.pdf` (source: `paper/main.tex`).

## Setup

Requires Python 3.11 or later (developed on 3.12).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then set FRED_API_KEY and a real SEC_USER_AGENT contact
```

`.env` is git-ignored. Keys are read from environment variables only.

## Reproduce

```bash
python src/data_collection.py     # download + cache raw SEC/FRED data (logs to data/raw/retrieval_log.csv)
python src/build_datasets.py      # processed + curated datasets
python src/run_analysis.py        # tables, figures, diagnostics
pytest -q tests                   # 26 validation and unit tests
jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb
```

Raw downloads are cached, so later runs work offline. Use `python src/build_datasets.py --refresh` to re-download.

## Layout

```
data/raw/            SEC Company Facts, submissions, offering documents, XBRL instances, FRED JSON; retrieval_log.csv
data/processed/      issuer_annual_10k (+provenance), issuer_latest_10q_snapshot, fred_daily, fred_nfci_weekly, secondary issuers
data/curated/        bond_issuance_tranches(_with_analytics), offering_documents_index, non_debt_financing_events,
                     debt_maturity_schedule_latest_10k, oracle_note_level_debt_fy2026, external_published_statistics
src/                 data_collection, sec_facts, financial_metrics, xbrl_instance, issuance, build_datasets,
                     market_analysis, scenarios, visualization, run_analysis
notebooks/           01_issuer_fundamentals, 02_credit_market_analysis, 03_stress_scenarios (thin readers of outputs)
outputs/figures/     fig1–fig6, figS1–figS2 (PNG 300 dpi + PDF)
outputs/tables/      table1–3, table3b, table_s1–s8 (CSV + Markdown)
outputs/diagnostics/ validation_checks.csv, issuance_spread_validation.csv, analysis_key_results.json
research/            findings, methodology, limitations, systemic_risk_framework, source_registry.csv
tests/               bond math, parsers (synthetic test-only fixtures), data integrity
```

## Evidence tags

Outputs label each claim with one of four tags:

| Tag | Meaning |
|---|---|
| A | Computed here |
| B | Published third-party statistic |
| C | Hypothetical scenario |
| D | Interpretation |

Scenarios are not forecasts. Issuance is not labelled AI-specific. Correlation is not presented as contagion.
