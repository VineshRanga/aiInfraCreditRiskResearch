# Findings: AI infrastructure and the concentration of credit risk in U.S. IG markets

**Research foundation, not the final paper.** Cutoff: 13-Nov-2026. Issuers: Amazon, Alphabet, Microsoft, Meta, Oracle ("the five").

Every number carries an evidence tag:

| Tag | Meaning |
|---|---|
| A | Computed here from SEC EDGAR or FRED |
| B | Published third-party statistic |
| C | Hypothetical scenario |
| D | Interpretation |

Methods are in `methodology.md` and caveats in `limitations.md`.

---

## Primary question: does AI infrastructure account for a disproportionate share of IG portfolio sensitivity relative to its share of debt, and why?

**Answer (qualified): yes, on the evidence available, but the index-level magnitude rests on published estimates (B), not on a calculation made here.**

- **Index-level shares (B).** bfinance (Bloomberg index data, 28-Oct-2026) puts the five at 4.85% of IG index market value but 6.3% of its interest-rate (duration) risk, about 1.3× their weight. Both shares were 2.67% and 3.6% at end-2024. The group's duration is 8.4 years versus 6.4 for the index. J.P. Morgan AM gives about 3.5% of the USD IG index at the start of 2026.
- **"Share of debt" means index market-value weight.**
  - The 4.85% applied to a roughly $7.3tn index implies about $354bn of index-eligible market value. This is below the five's balance-sheet gross debt of $559bn at the latest 10-Qs, before $66.8bn issued in Nov-2026.
  - The gap reflects index eligibility (USD, fixed-rate, minimum size and maturity), market value versus par, and the exclusion of CP, term loans and non-USD debt.
  - No verified denominator for total IG debt outstanding is available in our data.
- **Snapshot dates.** The bfinance figures date from about Sep-2026 and predate the $66.8bn issued in Nov-2026, so they likely understate the current weight. They are not extrapolated here.
- **Computed explanations (A).** Three independently computed facts explain why the risk share exceeds the weight and why it is rising:
  1. **Volume.** Registered issuance rose from $13.8bn (2023, all USD) to $284.1bn USD-equivalent in 2026 to 13-Nov. Headline market share: **7.2% of all US corporate issuance in Jan–Sep 2026** (matched months to SIFMA), up from 0.9% in 2023; **10.4% of IG issuance in 3Q26**. (Jan–Oct share is 6.7%; the five had no registered issuance in October.)
  2. **Duration.** The principal-weighted at-issue modified duration of 2025–26 USD issuance is 8.9 years, consistent with the published 8.4 and above the published index 6.4 (B).
  3. **Spread.** New-issue spreads widened relative to same-rating ICE indices (Table S3). The principal-weighted at-issue DTS of 2025–26 issuance is 945 years×bp.
- **Comparing DTS with the index.** A rough index DTS (Bloomberg duration 6.4 × ICE IG OAS 80–90bp ≈ 510–580) mixes two index providers and dates. It is not used as a headline ratio.
- **Interpretation (D).** The published evidence covers *interest-rate duration* share. Concentration of *spread* risk is supported indirectly by above-index new-issue spreads and at-issue DTS. An index-level DTS share is not available from open sources (`limitations.md` §1).
- **Cross-check against J.P. Morgan AM (A vs B).**
  - Our registered 2026 issuance to 20-Aug is $211.6bn, of which $54.6bn is non-USD.
  - J.P. Morgan AM reports $219bn, of which $62bn is non-USD.
  - The USD components match ($157bn). The gap lies in non-USD deals and may reflect FX conversion or non-SEC-registered euro deals.
- **Cross-check against bfinance (A vs B).** On spreads, bfinance's AA move from 45bp to 60bp, with A and BBB flat (Bloomberg), matches FRED ICE: AA 48bp at end-2024 to a 59bp Sep-2026 average, A 69 to 68, BBB 102 to 98.

---

## Analysis 1: capex and cash generation

**Question.** How has capex evolved, and how does it affect cash generation?

**Sources and period.** SEC EDGAR XBRL, 10-K for FY2018 to latest FY (Dec-2025; MSFT Jun-2026; ORCL May-2026) and 10-Q TTM to Sep-2026 (ORCL Aug-2026).

**Method.** FCF = OCF − capex; capex/OCF; first-reported 10-K values.

**Results (A).**
- Combined capex was $149.0bn in FY2023 and $378.7bn in FY2025 (fiscal years ending May–Dec 2025). TTM capex is **$691.0bn**, against TTM OCF of $723.8bn, so combined capex/OCF is about **0.95**.
- TTM capex/OCF and FCF by issuer:

| Issuer | TTM capex/OCF | TTM FCF | Earlier capex/OCF |
|---|---|---|---|
| Oracle | 1.61 | −$28.7bn | 0.51 (FY23) |
| Amazon | 1.28 | −$46.9bn | 0.62 (FY23); 1.36 in FY22, when OCF was depressed |
| Alphabet | 0.89 | +$19.8bn | 0.34 (FY22) |
| Meta | 0.78 | +$28.7bn | 0.62 (FY22) |
| Microsoft | 0.69 | +$60.0bn | 0.32 (FY23) |

- Three-year capex CAGR to the latest FY: Oracle 86%, Microsoft 60%, Alphabet 43%, Meta 30%, Amazon 27%.
- Shareholder returns in the latest FY continued: Alphabet $55.8bn, Microsoft $48.7bn, Meta $31.6bn, Oracle $5.9bn, Amazon none.

**Interpretation (D).**
- Capex now absorbs nearly all operating cash flow of the group.
- Two issuers (Oracle and Amazon) are FCF-negative and depend on external financing for growth capex.
- The other three still self-fund but with sharply less headroom.
- Negative FCF in a build phase is not by itself evidence of credit distress.

**Limitations.** Capex excludes finance-lease additions, which are large at MSFT and AMZN. Fiscal windows differ across issuers.

**Files.** `fig1_capex_by_issuer.{png,pdf}`, `fig2_ocf_vs_capex.{png,pdf}`, `table1_issuer_characteristics.{csv,md}`.

**Thesis.** Supports. The capex surge is the mechanical source of new debt supply.

---

## Analysis 2: leverage, liquidity, maturities and refinancing

**Question.** How do capex and funding needs translate into leverage and refinancing pressure?

**Sources and period.** Latest 10-K maturity schedules, 10-Q balance sheets (Sep-2026 / Aug-2026), Oracle note-level XBRL, and registered offerings to 13-Nov-2026.

**Results (A).**
- **Debt growth.** Combined gross debt rose from approximately $244.5bn at FY2023 to **$559.4bn** at the latest 10-Qs. Fiscal year-ends differ (MSFT Jun-2023, ORCL May-2023, others Dec-2023). Debt is face value plus CP, except Oracle's latest figure, which is carrying value. A further $66.8bn was issued in Nov-2026, after those balance-sheet dates: MSFT $25.0bn, META $25.0bn, ORCL $10.0bn, GOOGL $6.7bn.
- **Leverage and coverage.** Net debt/TTM EBITDA is 2.72× for Oracle, 0.42× for Amazon, and about zero or negative for the other three. EBITDA/interest is 6.4× for Oracle versus 35–63× for the others.
- **Leases.** Including finance leases, Oracle's gross debt is 4.1× TTM EBITDA. Microsoft's finance-lease liability ($71.0bn) exceeds its bonds.
- **Near-term maturities.** Maturities over the next three years total only $60.4bn across the five: ORCL $22.9bn, AMZN $16.3bn, MSFT $11.3bn, GOOGL $5.7bn, META $4.3bn. Cash and STI cover them 1.6× at Oracle and 5.7–46.7× elsewhere. TTM FCF less next-12-month maturities is −$49.6bn at AMZN and −$35.9bn at ORCL.
- **Post-FYE issuance by maturity.** Notes issued after the latest fiscal year-end mature as follows: 2027–29 $38.1bn, 2030–33 $74.7bn, 2034–45 $64.8bn, 2046+ $80.2bn. New issuance therefore pushed maturities long rather than creating a near-term wall.
- **Coupon reset (Table S8).** Legacy notes issued before 2025 and maturing 2027–29 carry much lower coupons than the issuers' latest 8–12y new-issue yields:

| Issuer | Legacy coupon | Latest 8–12y yield | Reset |
|---|---|---|---|
| Oracle | 3.54% | 8.02% | +447bp |
| Amazon | 3.15% | 5.34% | +219bp |
| Meta | 4.48% | 6.55% | +207bp |

**Interpretation (D).**
- Refinancing walls are small. The pressure is *new-money* funding of capex, not rollover.
- Credit risk is concentrated in Oracle, where leverage, coverage and FCF are all materially weaker. Amazon is a funding-dependence story with low leverage.

**Limitations.** Maturities are split into five fiscal-year buckets plus "thereafter". A 2031–33 split exists only for Oracle. Registered-only coverage misses term loans and project finance.

**Files.** `fig3_debt_maturity_schedule`, `table2_liquidity_leverage_refinancing`, `table_s8_coupon_reset`, `data/curated/debt_maturity_schedule_latest_10k.csv`, `oracle_note_level_debt_fy2026.csv`.

**Thesis.** Supports the concentration of *issuer-specific* risk in Oracle. Inconclusive on systemic refinancing risk, which looks limited.

---

## Analysis 3: issuance, concentration and new-issue pricing

**Question.** How has issuance evolved versus the IG market, and what does pricing show?

**Sources and period.** 38 final prospectus supplements and the matching FWPs (2020–2026; there was no registered issuance in 2018–19). SIFMA quarterly reports and web page (B). FRED ICE OAS from 13-Nov-2023.

**Results (A unless tagged).**
- **Volume.** Gross registered issuance was $40.0bn (2020), $33.5bn, $28.0bn, $13.8bn, $16.8bn, $108.3bn (2025), and $284.1bn (2026 to 13-Nov). The 2026 total comprises USD $207.0bn, EUR $44.0bn, CAD $16.3bn, GBP $13.2bn, and JPY $3.6bn.
- **Share of all US corporate issuance (SIFMA denominator, B):**

| Period | Share |
|---|---|
| 2023 | 0.9% |
| 2024 | 0.9% |
| 2025 | 4.2% |
| 2026 Jan–Sep | 7.2% |
| 2026 Jan–Oct | 6.7% |
| 3Q26, IG-only denominator | **10.4%** |

  Published comparators (B): J.P. Morgan AM expects a 9% hyperscaler share of USD IG issuance in 2026, versus 2% in 2022–24. bfinance estimates "AI-related" issuers at about 18% of US IG issuance in 2026, using a broader set.
- **Tenor.** Principal-weighted tenor was 17.6 years (2020–24) and 16.4 years (2025–26). The median is 10 years in both periods. The share of principal above 25 years fell from 37% to 30%. Duration exposure is growing through volume, not through tenor lengthening.
- **New-issue spread minus same-rating ICE OAS, 8–12y tranches (Table S3):**

| Issuer | Path |
|---|---|
| Amazon | +2bp (4Q25), +19bp (1Q26), +27bp (3Q26) |
| Alphabet | −12bp (2Q25), +13/+14bp, +28bp (3Q26) |
| Meta | +16bp (3Q24), +31bp, +38bp, **+93bp** (Nov-26, T+160) |
| Oracle | −20bp (3Q24), −4bp, +10bp, +52bp, **+194bp** (Nov-26, T+310 vs BBB OAS 116bp; comparable in level to the 330bp HY OAS, a different measure) |
| Microsoft (AAA) | −5bp (Nov-26) |

- **Ratings at pricing.** Oracle went from A3/A+ (2020) to Baa2/BBB (2025) and Baa2/BBB- (Nov-2026). Meta's S&P outlook was negative in Nov-2026 (term sheet text).
- **At-issue risk of 2025–26 USD fixed-rate issuance (Table S4).** Par-based spread DV01 of $259.8m per bp on $292bn of principal, so a +100bp spread move equals about −$26bn of par value. The principal-weighted DTS by issuer ranges from 492 (MSFT) to 1,271 (ORCL).
- **Equity-linked financing in 2026.**
  - Alphabet: $40bn ATM programme, two mandatory convertible preferred series, and common stock.
  - Meta: mandatory convertible preferred and a 40m-share forward sale.
  - Oracle: $20bn ATM, Series D mandatory convertible preferred, and 86.2m shares (Nov-2026).

**Interpretation (D).**
- The market is charging a rising, issuer-specific concession on top of rating-bucket spreads, most visibly for Oracle and Meta.
- The shift towards equity-linked funding suggests issuers are managing leverage and rating constraints.

**Limitations.**
- SEC-registered only.
- The SIFMA denominator includes HY and private placements.
- Benchmark spread and index OAS are different measures.
- Proceeds are not attributed to AI.

**Files.** `fig4_issuance_vs_market`, `figS1_new_issue_spreads_vs_index`, `table_s1`–`table_s4`, `data/curated/bond_issuance_tranches*.csv`, `non_debt_financing_events.csv`, `external_published_statistics.csv`.

**Thesis.** Supports, strongly on volume and pricing.

---

## Analysis 4: rates, spreads and financing conditions

**Question.** How do rates, spreads and financial conditions relate to refinancing pressure?

**Sources and period.** FRED daily data from Jan-2018 to 11/12-Nov-2026 (ICE series from 13-Nov-2023 only).

**Results (A).**
- **Treasury yields.** The 10Y was 3.88% (end-2023), 4.58% (end-2024) and 4.18% (end-2025), peaked at **5.31% on 5-Oct-2026**, and was 4.98% on 11-Nov-2026. The 30Y peaked at 5.67%.
- **Spread levels (bp):**

| Index | End-2023 | End-2024 | Sep-2025 | Jun-2026 | 11-Nov-2026 |
|---|---|---|---|---|---|
| IG OAS | 104 | 82 | 76 | 76 | 90 |
| AA | 55 | 48 | 43 | 52 | 65 |
| A | 88 | 69 | 63 | 63 | 74 |
| BBB | 129 | 102 | 97 | 95 | 112 |

  HY OAS was 330bp. Moody's Baa−10Y was about 151bp.
- **AA bucket.** The AA bucket, where four of the five sit, widened most: +22bp from Sep-2025 versus +11bp for A and +15bp for BBB. The quarterly average A–AA gap fell from 21bp (3Q25) to 9bp (3Q26).
- **Correlations.** The correlation of daily ΔDGS10 with ΔIG OAS is −0.25 since Nov-2023 and −0.16 since Oct-2025. The 126-day rolling correlation rose to about zero in late 2026.
- **Rate-shock episodes (≥50bp over 63 days).** IG OAS moved −17bp (1H24), −20bp (2H24), −5bp (Feb–May 2026), and **+5bp** in Jun–Sep 2026, when AA moved +10bp. The usual cushioning of rate rises by tighter spreads disappeared in the latest episode.
- **Financial conditions.** NFCI was −0.46 on 6-Nov-2026 and ranged −0.57 to −0.46 since Oct-2025, which is looser than average.

**Interpretation (D).**
- AA spreads widening while A spreads widened less, together with the AA–A compression, is *consistent with* supply pressure from AA-rated hyperscalers. It is **not** identified as causal; rates, the term premium and other AA issuers could also contribute.
- Broad financial conditions stayed loose. The stress is concentrated, not generalised.

**Limitations.** Only three years of ICE data, one relevant episode, descriptive statistics only.

**Files.** `fig5_rates_spreads_conditions`, `figS2_rolling_correlation`, `table_s5`–`table_s7`.

**Thesis.** Partially supports (concentrated AA pressure). Inconclusive on causality.

---

## Analysis 5: scenarios (C, hypothetical, not forecasts)

**Results (C).**
- **First-order price impact (Table 3b, Figure 6):**

| Profile | Duration | +50bp spread | +100bp spread | Combined UST +100 / spread +100 |
|---|---|---|---|---|
| 10y new issue | 7.7 | −3.9% | −7.7% | −15.4% |
| 30y new issue | 13.8 | −6.9% | −13.8% | −27.7% |
| 2025–26 issuance, principal-weighted | 8.9 | −4.4% | −8.9% | −17.8% |
| Published index (B) | 6.4 | −3.2% | −6.4% | −12.8% |

- **Incremental annual interest under the combined shock (Table 3).** Applied to the next three years of maturities plus any debt-financed TTM FCF shortfall:

| Issuer | Incremental interest | % of TTM EBITDA | Coverage before → after |
|---|---|---|---|
| Oracle | $1.03bn | 3.2% | 6.4× → 5.3× |
| Amazon | $1.26bn | 0.8% | 35.3× → 27.5× |
| Others | ≤ $0.23bn | — | — |

**Interpretation (D).** Debt-service capacity is resilient to plausible shocks for four issuers. The material exposure is **mark-to-market for bondholders**, concentrated in long-duration paper, rather than issuers' ability to pay. Oracle is the exception on both counts.

**Limitations.** First-order only; full refinancing at shocked rates is assumed; no rating-migration feedback. Debt-financing the whole FCF shortfall ignores 2026 equity funding (Oracle ATM, mandatory convertible and common stock), so Oracle's figure is an upper bound. Coupon-reset results for Alphabet ($1bn observed) and Microsoft (none observed) are not meaningful. Microsoft's implied cost of debt (7.8%) is inflated by finance-lease interest; it is excluded.

**Files.** `fig6_spread_sensitivity`, `table3_financing_cost_scenarios`, `table3b_first_order_price_impact`, `fig6_data_price_sensitivity_grid.csv`.

**Thesis.** Supports "sensitivity > default risk". Not evidence of systemic loss.

---

## Analysis 6: systemic-risk transmission

See `systemic_risk_framework.md`. Seven channels are mapped: supply and absorption, index concentration, cash flow, rating cliff, rates and duration, common factor, and non-bank. Only the first-order exposure is quantified; contagion is not claimed.

---

## Summary

| Question | Verdict | Evidence |
|---|---|---|
| Disproportionate share of sensitivity vs debt | **Supported**, with magnitude from B | B: 6.3% risk vs 4.85% weight; A: duration 8.9, DTS about 945 |
| Issuance vs market | **Supported** | A/B: 0.9% to 7.2% of all corporates (Jan–Sep 2026), 10.4% of IG in 3Q26 |
| Capex → cash and leverage | **Supported** (ORCL, AMZN); limited elsewhere | A |
| Vulnerability characteristics | **Supported** (ORCL concentrated) | A |
| Rates and spreads → refinancing pressure | **Inconclusive / limited** | A, C |
| Systemic implications | **Inconclusive** (channels plausible, not identified) | D |

## Open questions

1. What is the exact index DTS contribution and how has it evolved (needs ICE or Bloomberg constituents)?
2. How large are 144A, term-loan and project-finance volumes (e.g. JV and SPV data-centre financings)?
3. Do non-AI AA issuers' spreads respond to hyperscaler supply weeks?
4. Is there concentrated ownership by insurers and funds?
5. What are the timing and size of the commitments behind about $1.1tn of uncommenced leases (B)?

## Next steps

1. Licence or obtain index constituent data (ICE/Bloomberg) for exact market-value, duration and DTS shares.
2. Add TRACE bond-level prices for secondary spreads and event studies around deal days.
3. Add Mergent/FISD or Refinitiv data for 144A and private placements.
4. Build a supply-event panel: daily AA OAS changes on hyperscaler pricing days versus other days, with controls.
5. Extend note-level maturities using 10-K debt footnote tables (HTML) for AMZN, GOOGL, MSFT and META.
6. Add rating-agency action history (press releases) as point-in-time events.
