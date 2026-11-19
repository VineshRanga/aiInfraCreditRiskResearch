# Systemic-risk framework: transmission channels (theoretical, category D)

This note sets out *how* concentration in AI-infrastructure issuers **could** transmit stress through U.S. investment-grade credit. It is a conceptual map for the final paper, not an empirical finding. Where an observed statistic is relevant it is cited as A (computed here) or B (published), and none of them identifies a channel causally.

## 1. Starting point: concentration of sensitivity, not of default risk

The five issuers hold high ratings (Aaa to Baa2/BBB- at pricing). Their near-term default probability is low. Three of the five (Alphabet, Meta, Microsoft) generate positive TTM free cash flow; Amazon and Oracle do not (A, Table 1). The relevant risk is therefore **mark-to-market and liquidity risk concentrated in a few names with long duration**, rather than credit loss.

- **Interest-rate risk.** An issuer group's share of index interest-rate risk scales with market value × duration. A group with above-average duration (B: 8.4 vs 6.4 years) and rising weight (B: 2.67% to 4.85%) therefore carries a larger share of index duration risk (B: 6.3%) than of index market value.
- **Spread risk.** Spread risk (DTS) additionally scales with the spread level. Its index-level share is not published in the sources used and cannot be computed here; higher new-issue spreads (A, Table S3) suggest it is also above the market-value weight (D).

## 2. Channels

| # | Channel | Mechanism | Observable indicators (in this project) | Amplifiers | Dampeners |
|---|---|---|---|---|---|
| 1 | **Supply / absorption** | Large, rapid, long-dated issuance must be absorbed by duration-constrained investors. New-issue concessions rise and reprice comparable outstanding bonds (same issuer, rating bucket and sector). | Five-issuer share of US corporate issuance 0.9% (2023) to 6.7% (2026 YTD) (A/B); new-issue spread minus rating-index OAS rising (A, Table S3); AA–A OAS gap compressing from about 21bp to 9bp (A, FRED) | Clustered deal timing; index-eligibility rules; dealer balance-sheet limits | Broad foreign and insurance demand for long IG; issuers' ability to switch currency (2026 EUR, GBP, CAD, JPY deals, A) |
| 2 | **Index / benchmark concentration** | Passive and benchmarked portfolios hold the names by construction. A repricing of these issuers moves index returns, and active managers who are underweight face tracking-error pressure. | Market-value weight and duration-risk share (B) | Rising weights; index rebalancing at month-end | Diversified mandates; issuer caps in custom indices |
| 3 | **Fundamental / cash-flow** | Capex growing faster than OCF turns FCF negative, which raises dependence on market funding. If AI revenue disappoints, leverage rises just as funding becomes more expensive. | Capex/OCF: Oracle 1.61, Amazon 1.28 (TTM, A); Oracle net debt/EBITDA 2.7x (A) | Long-lived capex commitments; off-balance-sheet leases (B: about $1.1tn uncommenced) | Large cash balances (Alphabet, Meta); ability to cut buybacks and dividends (latest FY: Oracle $5.9bn to Alphabet $55.8bn; Amazon none, A) |
| 4 | **Rating migration / cliff** | Downgrades move bonds between rating buckets. A fall below BBB- would trigger forced selling by IG-only mandates (fallen-angel dynamics). | Oracle: A3/A+ (2020) to Baa2/BBB- (Nov-2026) at pricing (A); new-issue spread T+310 for 10y versus BBB OAS 116bp (A) | Large index weight of a single issuer (B: Oracle 1.28%) | Investor capacity in BB; issuer equity-raising (Oracle ATM and stock offering, 2026, A) |
| 5 | **Rates / duration** | Long-dated supply adds to the term premium. Duration losses for holders become correlated across names when rate shocks coincide with spread widening. | 10Y peak 5.31% (Oct-2026, A); spreads widened during the Jun–Sep 2026 rate rise, unlike earlier episodes (A, Table S6); rolling Δrate–Δspread correlation near zero in 2026 (A, Fig S2) | Simultaneous rate and spread shocks (Table 3b combined scenario: about −18% for D=8.9, C) | Negative stock-bond correlation regimes; hedging demand |
| 6 | **Common-factor / correlation** | A shared exposure (the same AI demand thesis, shared customers and suppliers, overlapping lenders and lessors) makes spread moves across the five more correlated, reducing diversification within IG. | Not measured here (requires bond-level spread histories) | Concentrated customer contracts (e.g. AI-lab off-take) | Diverse revenue bases at Amazon, Microsoft and Alphabet |
| 7 | **Non-bank and off-balance-sheet** | Private credit, JV/SPV project finance and lease financiers hold exposures outside the public IG market, which can transmit losses or funding stress to banks, insurers and private-credit vehicles. | Not observed (outside SEC-registered data; see limitations) | Opacity; leverage in vehicles | Contractual protections; investment-grade sponsors |

## 3. What would distinguish systemic from idiosyncratic stress (for future testing)

1. Spread changes of *non-AI* IG issuers with similar rating and duration respond to AI-issuer supply or news, after controlling for rates and the market factor (would require bond-level data).
2. New-issue concessions of non-AI issuers rise in weeks with heavy hyperscaler supply.
3. Fund flows and positioning (insurer and mutual-fund holdings) show concentrated ownership.
4. Rating-migration events are followed by forced selling, measured by volume and price pressure (TRACE).

**Correlation alone does not establish any of these.** This project provides only descriptive co-movement (Tables S5–S6) and cannot identify contagion.

## 4. Mapping to scenarios

Table 3 and Figure 6 quantify the *first-order* exposure for channels 3 and 5, i.e. funding cost and price sensitivity, under hypothetical shocks (C). Channels 1, 2, 4, 6 and 7 are described qualitatively. Quantifying them requires index constituent data, bond-level spreads and holdings, which are listed as next steps in `findings.md`.
