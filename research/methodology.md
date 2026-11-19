# Methodology

Research cutoff: **13 November 2026**. Nothing filed, published or observed after this date is used. All code is in `src/`; the pipeline is `src/data_collection.py` (download + cache + retrieval log) → `src/build_datasets.py` (processed/curated datasets) → `src/run_analysis.py` (tables, figures, diagnostics).

Evidence categories used throughout the outputs:

| Code | Meaning |
|---|---|
| A | Computed by this project from primary data (SEC EDGAR, FRED) |
| B | Published third-party statistic, transcribed with attribution |
| C | Hypothetical scenario / assumption |
| D | Interpretation by the author |

## 1. Issuer universe

Primary: Amazon (AMZN, CIK 1018724), Alphabet (GOOGL, 1652044), Microsoft (MSFT, 789019), Meta Platforms (META, 1326801), Oracle (ORCL, 1341439).

Secondary candidates (Equinix, Digital Realty, Constellation Energy, Vistra) were downloaded and processed (`data/processed/secondary_issuers_annual_long.csv`) but **excluded from the main analysis**. Their data are not comparable to the primary five: Constellation reports negative operating cash flow in recent fiscal years, which makes capex/OCF uninterpretable, Digital Realty's capex concept covers only part of the period, and Equinix's 2025 debt is not tagged at the needed concept. Utilities and REITs also have structurally different capital structures.

## 2. Issuer fundamentals (Analysis 1 and 2)

**Point-in-time extraction.** Values come from the SEC XBRL Company Facts API. For the annual panel only facts from `10-K` forms are used. For each fiscal period end, the *first-reported* value is kept, meaning the fact from the earliest-filed 10-K. Later restatements are therefore ignored, which mirrors what an investor could have known. Flow facts must span 350–380 days, so quarterly values are never mixed into annual data. Every value keeps its concept, accession number and filing date (`data/processed/issuer_annual_10k_provenance.csv`).

**Fiscal years.** Each fiscal year is labelled by the calendar year in which it ends:

| Issuer | Fiscal year ends | Example |
|---|---|---|
| Microsoft | June | FY2026 = Jul-2025 to Jun-2026 |
| Oracle | May | FY2026 = Jun-2025 to May-2026 |
| Others | December | — |

Because the year-ends differ, the "latest FY" covers different calendar windows. Comparisons are therefore also made on a common trailing-twelve-month (TTM) basis.

**Concept map** (priority order; the concept used for each value is recorded).

| Item | Default concept(s) | Issuer overrides |
|---|---|---|
| Revenue | RevenueFromContractWithCustomerExcludingAssessedTax → Revenues → SalesRevenueNet | GOOGL, ORCL: Revenues first |
| Operating cash flow | NetCashProvidedByUsedInOperatingActivities | – |
| Capex | PaymentsToAcquirePropertyPlantAndEquipment | AMZN: PaymentsToAcquireProductiveAssets ("Purchases of property and equipment", gross of incentives) |
| Operating income | OperatingIncomeLoss | – |
| Depreciation / amortisation | Depreciation; AmortizationOfIntangibleAssets | – |
| Interest expense | InterestExpense → InterestExpenseNonoperating | META 10-Q TTM: InterestExpenseDebt fallback |
| Cash; short-term investments | CashAndCashEquivalentsAtCarryingValue; MarketableSecuritiesCurrent | MSFT: ShortTermInvestments; ORCL: AvailableForSaleSecuritiesDebtSecuritiesCurrent |
| Debt principal (face) | LongTermDebt | MSFT, ORCL: DebtInstrumentCarryingAmount (face amount despite the name); META: DebtInstrumentCarryingAmount → LongTermDebtNoncurrent |
| Commercial paper | CommercialPaper | AMZN: ShortTermBorrowings |
| Finance / operating lease liabilities | FinanceLeaseLiability; OperatingLeaseLiability | – |
| Maturity schedule | LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths … AfterYearFive | – |

**Definitions.**
- FCF = OCF − capex.
- Capex intensity = capex / OCF.
- FCF margin = FCF / revenue.
- Gross debt = debt principal + commercial paper. If the issuer reports no CP tag, CP is treated as nil, and the `commercial_paper_reported` flag records this.
- Net debt = gross debt − (cash + short-term investments).
- EBITDA = operating income + depreciation + amortisation of intangibles. Amortisation is set to nil where untagged, and the `amortization_reported` flag records this.
- Finance leases are reported separately and in a "gross debt incl. finance leases" variant. Operating leases are excluded from debt.
- Interest coverage = EBITDA / interest expense. Reported interest is net of capitalised interest, so coverage is flattered for issuers that capitalise heavily.
- Ratios with a zero denominator are set to missing (`_safe_div`). They are never infinite or zero-filled.

**Debt principal reconciles to the maturity schedule.** For every issuer-year where both are tagged, the sum of the contractual maturity schedule equals debt principal within 0.5% (test `test_maturity_schedule_reconciles_to_principal`). This confirms the debt figure is face value of term debt.

**TTM and latest balance sheet.** TTM flows = last FY + current YTD − prior-year YTD, from 10-Q filings. Amazon reports TTM values directly. For each item, the candidate concept with the latest period end is chosen. Balance-sheet values come from the latest 10-Q filed before the cutoff (Sep-2026; Oracle Aug-2026). Oracle's 10-Q does not tag face principal, so its latest debt is *carrying value* (NotesPayableCurrent + LongTermNotesAndLoans) and is labelled `debt_basis = carrying value`. CP values whose date differs from the balance-sheet date are discarded as stale.

**Note-level debt.** XBRL instance documents of the latest 10-K and 10-Q were parsed for dimensional facts (DebtInstrumentAxis and similar). Only Oracle tags every note: 61 notes, $128.0bn face, with coupon, issue date and maturity date (`data/curated/oracle_note_level_debt_fy2026.csv`). The other four tag only aggregates.

## 3. Bond issuance (Analysis 3)

**Discovery.** All 424B2, 424B5 and FWP filings by the five issuers from 2018-01-01 to the cutoff were listed via the EDGAR submissions API and downloaded: 142 documents.

**Classification.** Each document is classified as preliminary, final debt prospectus, common stock, mandatory convertible preferred, ATM equity programme, FWP term sheet, or other. Only *final* debt prospectus supplements create tranches. Equity-linked and ATM filings are recorded separately (`data/curated/non_debt_financing_events.csv`).

**Tranche extraction.** Tranches are parsed by regex from the cover page of each final supplement: currency, principal, coupon (or floating), and maturity year. Amounts below 100m in local currency are rejected, because they are registration-fee lines rather than tranches. Duplicates are removed. Result: 235 tranches across 38 final debt documents.

**USD conversion.** Non-USD tranches use the FRED H.10 noon rate on or before the filing date. This is not the deal's swap rate.

**Pricing terms.** For USD deals, the FWP pricing term sheets filed within six days up to the final supplement provide the spread to the benchmark Treasury, the re-offer yield to maturity, and the benchmark Treasury yield. Values are attached **only if** |(YTM − benchmark) × 100 − spread| ≤ 1.5bp for every tranche. Result: 162 of 162 USD fixed-rate tranches validated (maximum error 0.0bp); diagnostics are in `outputs/diagnostics/issuance_spread_validation.csv`.

**Ratings and CUSIPs.** Ratings are taken *as printed in the term sheet at pricing*, not current ratings. CUSIPs are kept only if the check digit validates and maps uniquely to a tranche (35 of 172 USD tranches).

**Tenor.** Tenor is approximated as maturity year − issue year.

**What issuance is not.** Issuance is gross: it is not net issuance and not outstanding debt. Use of proceeds is **not** assumed to be AI-related. Coverage is limited to SEC-registered public offerings; 144A deals, private placements, term loans, CP, and joint-venture or project-finance debt are out of scope (see `limitations.md`).

**Market comparison.** The five-issuer USD-denominated registered issuance is compared with SIFMA's published *total US corporate issuance* (all types). The only IG-only denominator available is SIFMA's 3Q26 IG share (74.3%) applied to SIFMA's 3Q26 total.

**New-issue spread vs index (Table S3, Figure S1).**
- Each tranche's spread to the benchmark is compared with the ICE BofA OAS of the matching rating bucket: AA for AAA/AA, A, and BBB, using the S&P rating at pricing.
- The OAS value used is from the last business day before the final supplement date, which is approximately the trade date.
- The two measures differ. The benchmark spread is to an on-the-run Treasury, while OAS is to the spot curve and is averaged across all maturities in the index. The *change over time* in the difference is more informative than its level.

**At-issue bond analytics (Table S4).**
- Price and modified duration of a semiannual fixed-rate bullet bond at the re-offer yield.
- Spread duration is approximated by modified duration, which is valid for non-callable bullets. Make-whole calls are ignored, and par calls shortly before maturity have a minor effect.
- DTS = spread duration × spread (years × bp).
- Spread DV01 = Σ principal × D × 0.0001, par-based.
- These describe the verified new issues only. **They are not index-level DTS contributions.**

## 4. Macro conditions (Analysis 4)

**FRED series and units.**
- Treasury CMT yields (DGS2, DGS5, DGS10, DGS30) and ICE BofA OAS series (IG, AA, A, BBB, HY): percent, converted to bp in outputs.
- Moody's BAA10Y and AAA10Y: percent, a long-history supplement.
- NFCI: index, weekly.
- DFF: percent.
- All were downloaded through the FRED API with the key read from the `FRED_API_KEY` environment variable (`.env`, which is git-ignored). Missing observations stay missing.

**Descriptive statistics only.**
- Pearson correlations of daily and weekly first differences.
- Rolling 126-business-day correlations.
- Episodes in which DGS10 rose by at least 50bp over 63 business days, in non-overlapping windows, with concurrent spread changes.
- Regime averages over author-defined descriptive date windows.

No causal identification is attempted. BAA10Y contains −DGS10 mechanically, which biases its correlation with ΔDGS10 downward.

## 5. Scenarios (Analysis 5) — category C

**Price effects.** ΔP/P ≈ −D_rate × Δy − D_spread × Δs. Rate duration and spread duration are kept as separate inputs. For the fixed-rate bullets used here they are numerically equal; for floaters (spread duration > 0, rate duration ≈ 0) and callables they differ. Convexity is excluded. The duration profiles are computed medians of 2025–26 new issues (5y, 10y, 30y and 40y tenors) and the principal-weighted 2025–26 issuance, plus a published index duration of 6.4 years (category B, from bfinance).

**Financing-cost arithmetic (Table 3).** Incremental annual interest = (next-3-year contractual maturities from the latest 10-K + hypothetical debt-financed TTM FCF shortfall, where TTM FCF < 0) × (ΔUST + Δspread). The scenarios are:

| Scenario | ΔUST | Δspread |
|---|---|---|
| UST +100bp | +100bp | 0 |
| Spread +50bp | 0 | +50bp |
| Spread +100bp | 0 | +100bp |
| Combined | +100bp | +100bp |

Results are expressed relative to TTM EBITDA, TTM OCF, and pro forma EBITDA/interest. The calculation assumes immediate refinancing at the shocked rates and full pass-through, and ignores cash usage, hedges and timing.

**Coupon reset (Table S8).** For legacy notes issued before 2025 and maturing in 2027–2029, the principal-weighted coupon is compared with the issuer's most recent 8–12y USD re-offer yield. This is a computed comparison (A); interpreting it as a cost increase is D.

## 6. Validation

`outputs/diagnostics/validation_checks.csv` and `tests/` (26 tests) check:
- the FCF identity;
- the maturity schedule against principal;
- uniqueness of issuer-years and tranches;
- that no dates fall after the cutoff;
- fiscal-year-end consistency;
- that 10-K filing dates come after period ends;
- that core flows are not zero-filled;
- the TTM identities;
- the spread identity;
- FX arithmetic;
- FRED units and the ICE truncation start;
- bond-math identities (par bond prices at par; zero-coupon Macaulay duration equals maturity; modified duration matches a finite difference);
- scenario arithmetic;
- parser fixtures (test-only synthetic text);
- the CUSIP check digit;
- zero-denominator handling.
