# Limitations

## 1. Index-level market-value share and DTS contribution: not computable here

**An exact index-level market-value weight or DTS (duration-times-spread) contribution of the five issuers cannot be computed from openly available data.** It would need the constituent-level index file (ICE BofA US Corporate Index or Bloomberg US Corporate Index): every bond's market value, OAS and spread duration on a common date. These files are licensed. FRED publishes only index-level OAS and yield series, with no constituents, market values or durations.

What this project does instead:

1. **Published estimates (B).** bfinance (28 Oct 2026, citing Bloomberg index data) reports the following for the five issuers:

   | Measure | End-2024 | Latest |
   |---|---|---|
   | Market-value weight | 2.67% | 4.85% |
   | Share of index interest-rate (duration) risk | 3.6% | 6.3% |

   It also reports an average duration of 8.4 years versus 6.4 for the index. J.P. Morgan AM (20 Aug 2026) reports a hyperscaler share of about 3.5% of the USD IG index at the start of 2026. These figures are quoted, not recomputed.
2. **Computed (A), for the verified new issues only.** Tables S4 and 3b report at-issue modified duration, spread, DTS and par-based spread DV01 of the 2025–26 SEC-registered USD fixed-rate issues. These describe the *flow* of new bonds, not the *stock* held in the index.
3. **Index providers differ.** Published weights and durations refer to the Bloomberg US Corporate Index, while spread series refer to ICE BofA indices. The two are never combined in a single calculation. A rough index DTS (Bloomberg duration × ICE OAS) is therefore not reported as a headline ratio.
4. **"Share of debt".** The published market-value weight (4.85%, implying about $354bn of index market value) is the measure of the five's share of IG debt used here. It differs from balance-sheet gross debt ($559bn) because of index eligibility rules, market value versus par, and the exclusion of CP, term loans and non-USD bonds. Total IG debt outstanding is not available from verified sources in this project.

## 2. Data access and truncation

- **ICE BofA OAS series on FRED are restricted to the last three years** (from 13-Nov-2023 in this download). FRED's series notes state: "Starting in April 2026, this series will only include 3 years of observations." Before Nov-2023, only Moody's BAA10Y and AAA10Y are available. These are yield spreads on long-dated seasoned bonds, not OAS, and are shown as a labelled long-history proxy, never as a substitute.
- **SIFMA.** The underlying SIFMA spreadsheets sit behind a registration form and were not accessed. Only figures printed in published SIFMA reports and on SIFMA's web page are used. SIFMA's headline issuance is *all US corporate bonds* (IG, HY, private placements and convertibles). An IG-only share is printed only for some quarters (74.3% in 3Q26). SIFMA revised its 2024 total from $1,957.0bn to $1,968.9bn, and the 4Q25 report carries an apparent date misprint ("January 2025").
- **No bond-level secondary-market data.** Neither TRACE prices nor dealer quotes were used, so current OAS, realised spread changes after issuance, and bond-level liquidity for the issuers' bonds are not observed. Equity and ETF prices were deliberately not used as a spread proxy.
- **FRED vintages.** FRED values are the latest vintage, not real-time vintages. This matters little for market series, but NFCI is revised weekly.

## 3. Coverage of issuance and debt

- **SEC-registered public offerings only.** 144A deals, private placements, bank term loans, commercial paper, and joint-venture or project-finance structures are missing.
  - Oracle's FY2023 cash-flow statement shows $33.5bn of debt proceeds against $12.25bn of registered bond issuance; the gap is mainly term loans.
  - Project-finance and JV structures are reported in the press for some data-centre campuses (for example, financing associated with Meta's Hyperion campus in 2025). They are not in this dataset and were not independently verified.
  - The issuance figures are therefore a **lower bound** on debt financing.
- **Gross, not net.** Issuance figures are gross; redemptions and buybacks of bonds are not netted. Issuance must not be read as an increase in outstanding debt. Balance-sheet debt is taken from the 10-K and 10-Q filings.
- **Use of proceeds.** Prospectuses typically state "general corporate purposes". Issuance is **not** labelled AI-specific. Phrases such as "AI-related issuance" appear only when quoting third parties.
- **Leases.**
  - Capex excludes assets obtained under finance leases.
  - Microsoft's finance-lease liability ($71.0bn at Sep-2026) exceeds its bonds outstanding ($41.3bn before the Nov-2026 deal).
  - Lease commitments that have not yet commenced are off-balance-sheet and not captured. J.P. Morgan AM (B) estimates about $1.1tn across hyperscalers.
- **Equity-linked financing.** Mandatory convertible preferred, ATM programmes and forward sales (Alphabet, Meta, Oracle in 2026) are recorded in `non_debt_financing_events.csv` but sized only where the cover states the amount.

## 4. Maturity profile

- 10-K XBRL schedules give years 1–5 after fiscal year-end plus a single "thereafter" bucket. **A 2031–2033 split is available only for Oracle** (note-level XBRL). For the others, maturities in 2031–2033 are visible only for notes issued 2020–26 in the verified issuance dataset (Figure 3b), not for pre-2020 notes.
- Schedules are as of fiscal year-end (Dec-2025, Jun-2026 for MSFT, May-2026 for ORCL). They exclude debt issued later (shown separately in Figure 3b) and repayments made later.
- Fiscal-year buckets differ across issuers, so "Year 1" covers a different calendar window for MSFT and ORCL.

## 5. Measurement choices

- **Point-in-time.** First-reported 10-K values are used, so later restatements are ignored by design. Some issuers re-tag concepts across years (concept priority lists are in `methodology.md`), so comparability across years for one issuer depends on stable tagging.
- **EBITDA** is a simple sum (operating income + depreciation + amortisation). It excludes stock-based compensation add-backs and other adjustments used by rating agencies.
- **Interest expense** is reported net of capitalised interest, which understates the gross cost of debt for heavy builders. For Microsoft it includes finance-lease interest, which inflates the implied cost of debt (7.8%; Table S8).
- **Debt basis.** Oracle's latest 10-Q debt is carrying value, not face value. Other issuers use face value plus CP.
- **Ratings** are as printed at pricing in FWP term sheets, not a current-ratings history. Rating actions between deals (for example, S&P's downgrade of Oracle to BBB- in July 2026, reported by bfinance) are only visible through the next term sheet.
- **Tenor and duration.** Tenor is approximated as maturity year − issue year. Durations assume non-callable bullets and ignore make-whole calls, and par calls shortly before maturity have a minor effect.
- **New-issue spread vs ICE OAS.** The comparison mixes a benchmark spread with an index OAS that spans all maturities (see methodology). Levels are indicative; changes over time are more informative.

## 6. Inference

- Correlations and episode statistics are descriptive. The ICE sample covers about three years (745 daily observations), with one episode of rate shock plus spread widening (Jun–Sep 2026). **No causal or contagion claim is made.**
- Regime windows were chosen by the author for description; results are sensitive to these dates.
- Scenarios (Table 3, Figure 6) are hypothetical first-order calculations, not forecasts, and exclude second-round effects such as rating migration, funding-market closure and fire sales.
- Five issuers are a sample, not the IG market. Their combined issuance share is compared with market totals, but issuer-level findings do not generalise.

## 7. Secondary issuers

Equinix, Digital Realty, Constellation and Vistra were collected but excluded. The reasons are concept gaps (DLR capex coverage, EQIX 2025 debt untagged), Constellation's negative reported OCF, and different business models (REITs, utilities). Their raw and processed data are retained for future work.

## 8. Operational

SEC requests identify the requester through `SEC_USER_AGENT` in `.env` (a real contact email, as SEC's fair-access policy requires). Raw downloads are cached, so re-runs only hit SEC when `--refresh` is used.
