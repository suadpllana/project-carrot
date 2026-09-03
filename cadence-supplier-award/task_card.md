# Task description

The attempt acts as a **sourcing analyst at Cadence Instruments LLC**, a
mid-size industrial flow-meter manufacturer in Aurora, Illinois. The SP-40
stainless valve seat is currently split across several suppliers on expiring
agreements. The steering committee has decided to consolidate FY2026 onto a
**single supplier for the full contract year** and four suppliers have returned
offers. The attempt must decide **which of the four candidate suppliers is
awarded the FY2026 SP-40 contract, how many pieces are contracted with it and
what the contract year costs**, and make the case for it.

The environment ships sixteen input files across four formats — four Markdown
contract term sheets, a standing finance policy memo, a demand-planning
handover note, an XLSX supplier master with an alias sheet, four CSV
purchasing extracts (purchase orders, goods receipts, a purchase-order
crosswalk, FX dailies) plus a demand extract and a freight tariff, a JSONL
inspection log, a data dictionary and an IT change record. Nothing has been
reconciled; the systems disagree with each other about supplier names and,
since the July ERP go-live, about purchase-order numbers.

**Deliverables**, all written to `/workspace/output/`:

1. `supplier_costs.csv` — four rows, one per candidate, fixed seven-field
   header, ranked, with per-field precision stated in the prompt. Its rank-1
   row is the decision: the supplier, the quantity contracted and the
   contract-year cost.
2. `defect_rates.csv` — four rows, fixed five-field header, sorted by supplier
   code, `reject_rate_pct` to three decimals.
3. `recommendation.md` — the committee memo, with five level-2 headings
   spelled and ordered exactly as specified; its Recommendation section states
   the same three decision figures.

The prompt states the deliverable contract exactly and says nothing about
method: it never names a metric to compute, a column to use, a file to join, a
record to exclude or a figure to reach. All input data is synthetic and
author-generated; the generator is retained under `solution/_provenance/`.

# Complexity justification

Nine reasoning challenges are planted in the data. **Eight of them decide the
recommendation on their own**: get any one wrong and the award goes to a
different supplier. None is asked for by the prompt. The three hardest are of
the kind a careful attempt does not find by checking rows against reference
tables — a population question and two silent joins — and are described
first.

**0a. CRUX — the inspection log is two populations.**
*Planted:* `quality/incoming_inspection_2025.jsonl` carries 33 `SOURCE`
records among the 260 `INCOMING` ones: pre-shipment inspections performed by a
Cadence supplier-quality engineer at the supplier's plant, 22 of them on
SUP-1042 lots at a 12.1% reject rate (SUP-2318 and SUP-3155 have a few as
well, so it is not a one-supplier gimmick). The data dictionary states what a
source inspection is — rejected pieces are replaced before the lot ships, are
never received or invoiced, and the same lot is inspected again on receipt —
and says nothing about what to do with the records. Every source record shares
its `lot_id` with the incoming record of the same lot, and half of them were
keyed before that record and half after, so neither "keep the first record per
lot" nor "keep the last" gets it right.
*Correct attempt:* restricts the reject rates to `INCOMING` records, which
are the pieces Cadence pays for and scraps: SUP-1042 at 1.820%.
*Careless attempt:* pools the two and reads SUP-1042 at 3.68% (dedupe either
way) or 4.55% (no dedupe), buys 9,500–14,000 more pieces from it, and awards
SUP-4077. Measured 0.191–0.239 with 0 of 101 test-side decision points.

**0b. CRUX — the ERP cutover breaks the receipt join without an error.**
*Planted:* purchasing and receiving moved to a new ERP on 2025-07-01
(`it/CHG-2025-0417_erp_cutover.md`). The 62 goods receipts posted from that
date carry the ERP's ten-digit purchase order number; the purchasing extract
carries the reporting mart's `PO-45xxx` numbers throughout; the crosswalk
between them is a separate file. A join of receipts to purchase orders on
`po_id` matches every pre-cutover receipt and silently matches nothing after
it, so the lots received after go-live drop out of the reject rates with no
symptom. They are not a random sample: SUP-3155's post-cutover lots run at
8.0% (named) and 14.2% (unnamed) against 2.4% before.
*Correct attempt:* resolves post-cutover receipts through the crosswalk and
attributes all 63 SUP-3155 lots: 6.100%.
*Careless attempt:* reads SUP-3155 at 3.42% on 43 lots, buys 14,000 fewer
pieces from it, and awards SUP-3155. Measured 0.191 with 0 of 101 decision
points.

**1. Attribution off the free-text supplier field.**
*Planted:* the inspection log's `supplier` field is empty or `null` on 59 of
the incoming records and inconsistently spelled on the rest (the change record
explains why). Every lot is nonetheless attributable: `lot_id` → goods receipt
→ purchase order → the supplier master's `name_aliases` sheet → supplier code.
The blank-field lots carry SUP-3155's worst quality: 7.5% before the cutover
and 14.2% after it, against 2.4% on its named pre-cutover lots.
*Correct attempt:* attributes through the receipt join.
*Careless attempt:* groups on the field that is right there, reads SUP-3155 at
3.43%, and awards SUP-3155. Measured 0.191 with 0 of 101 decision points.

Challenges 0b and 1 are independent: an attempt that joins through the
receipts but not the crosswalk loses the post-cutover lots, one that uses the
crosswalk but the free-text field loses the blank ones, and both land on the
same wrong supplier. Only an attempt that does both reaches 6.100%.

**2. Scope of demand has to be inferred from a dirty cube extract.**
*Planted:* `demand/forecast_2026.csv` is a raw planning-cube dump. It carries
the superseded October S&OP cycle beside the frozen November one (`plan_cycle`
column; 538,600 SP-40 pieces against 486,000), a `TOTAL` subtotal row per part
and cycle, and twelve monthly rows for SP-22, a different part on a separate
agreement. The handover note says the plan was frozen at the November cycle,
that the cube keeps the last two cycles and that the dump is not cleaned; it
does not do the filtering.
*Correct attempt:* sums the twelve monthly SP-40 rows of the November cycle →
486,000 good units.
*Careless attempt:* plans on the October cycle, sums both cycles, or counts
the subtotal rows — each pushes the purchase quantity above 520,000 pieces and
hands the award to SUP-4077 through a rebate that is not really earned.
Measured 0.303 with 0 of 101 decision points, all three ways.

**3. Quoted prices are not comparable as quoted.**
*Planted:* the four offers are in four currencies, and SUP-2318 quotes EUR
178.00 **per 100-piece box** while the others quote per piece. The finance memo
mandates fixed FY2026 planning rates and explicitly rules out the 2025 daily FX
export, which is also shipped and whose averages sit materially below the
planning rates. *Correct attempt:* restates all four to USD per single piece —
1.9450 / 1.9313 / 1.8966 / 1.8889. *Careless attempt:* uses 2025 average rates
and awards SUP-3155 (measured 0.356, 0 decision points).

**4. Rejects are a purchase-quantity problem, not a line item.**
*Planted:* clause 5.4 of all four term sheets — identically worded, so no
supplier is advantaged by a hidden term — states that rejected pieces are
scrapped by the buyer with no credit and no replacement, and that the buyer
must order enough to meet its net good-unit requirement. The demand column is
explicitly labelled net good units. Clause 5 of each contract separately states
a *specification limit* on the reject rate and says in terms that it is not a
forecast. SUP-2318's clause 1 adds that partial boxes are not tendered.
*Correct attempt:* grosses up, `ceil(486,000 / (1 − r))`, a spread of 22,562
pieces between best and worst supplier, and rounds SUP-2318 up to 4,922 whole
boxes. *Careless attempt:* buys 486,000 pieces from everyone, and the award
flips to SUP-3155 (measured 0.330, 0 decision points).

**5. Incoterms decide who pays freight.**
*Planted:* two offers are FCA at the seller's works and two are DDP. The
freight tariff lists all four lanes with a neutral note that applicability
depends on the Incoterm in the supply contract, so the tariff itself does not
say which lanes to charge. *Correct attempt:* charges the DE and UK lanes only,
at twelve shipments per year as each contract's clause 2 states. *Careless
attempt:* charges nobody, and the award flips to SUP-4077 (measured 0.378).

**6. Two rebate structures that do not pay what they appear to.**
*Planted:* SUP-2318's clause 4.2 is a **banded** rebate — each rate applies only
to the volume inside its band, and clause 4.2 says so in terms. SUP-4077's
clause 4.2 grants 4.0% on all pieces but **only if** contract-year volume
reaches 520,000, and clause 4.1 separately commits the buyer to that same
520,000 with a GBP 0.35 per-piece shortfall charge. The correct purchase
quantity, 497,951, sits 4.2% below that threshold — so the threshold can only
be evaluated after challenges 0a, 0b, 1, 2 and 4 are done right. *Correct
attempt:* SUP-2318 earns USD 11,136 and SUP-4077 earns nothing while owing
USD 9,816. *Careless attempt:* re-rates SUP-2318's whole year at 3.0% (USD
28,518) and awards SUP-2318 (measured 0.410), or treats SUP-4077's rebate as
earned and awards SUP-4077 (measured 0.378).

**7. Working capital and the cash discount.**
*Planted:* the finance memo values payment terms against Net 30 at 9.0% WACC
on invoiced spend, and says that a cash discount taken reduces the spend base
before the earlier date is valued. SUP-4077 offers 2/10 Net 60. This does not
flip the award, but every total in the costs file depends on it, and the
decision includes the awarded total to the cent.

# Taxonomy tags

Objectives: cost modelling, total-cost-of-ownership comparison, supplier
selection, data reconciliation across systems, entity resolution, contract
interpretation, scope determination, quality-cost analysis, working-capital
valuation.

Reasoning phases scored by the rubric: explore, analyze, synthesize, recommend,
instruction_following.

Domain: business / operations / procurement finance. Formats: CSV, XLSX,
JSONL, Markdown, plain text.

# Expected difficulty range

Target band: **strong model mean reward at or under 0.6, weak model mean at or
under 0.35 over four trials each.**

The previous revision missed the band: the weak model scored 0.87–0.94 across
four trials (mean 0.889) while failing the exact total-cost and memo checks.
Two things were wrong with it. Every trap it planted was a **documented
step** — the free-text field is visibly blank, the subtotal rows are labelled
`TOTAL`, the finance memo names the FX rule, each contract clause states its
own reading — and an attempt that works carefully through the documents
reaches the supplier without ever getting the figures right. And the reward
let it: the decision was one figure (the supplier) worth 38% of the weight,
the numeric checks allowed 0.4–2% bands, and the rubric paid for a
well-written memo regardless of the analysis behind it.

Both were changed rather than tuned around.

**The decision is now three figures**, all in the rank-1 row of
`supplier_costs.csv` and repeated in the memo: the supplier, the quantity
contracted (495,010 pieces) and the contract-year cost (USD 963,017.63, exact
to the cent). The quantity is reachable only with the frozen plan cycle, the
incoming-only reject rate on every attributed lot and the gross-up; the cost
only with all of that plus the freight, rebate, shortfall, scrap and
payment-terms readings. The decision carries **47.7% of total positive weight**
(203 of 426: 101 of 188 test-side, 102 of 238 rubric-side).

**Three population traps were added that no checklist finds** — the two
inspection populations, the silent post-cutover join, and the superseded plan
cycle — each fatal on its own, each with a different wrong supplier at the end
of it, and the reject mass laid out so that the two attribution failures are
independent of each other. Measured against the shipped verifier by mutating
the reference solution, one omission per row:

| Single omission | Lands on | Contract qty | Contract cost | Tests | Decision |
| --- | --- | --- | --- | --- | --- |
| pools the SOURCE inspections (dedupe keeps first record) | SUP-4077 | 497,951 | USD 976,280.36 | 0.239 | 0 / 101 |
| pools the SOURCE inspections (dedupe keeps last record) | SUP-4077 | 497,951 | USD 976,280.36 | 0.239 | 0 / 101 |
| pools the SOURCE inspections, no dedupe | SUP-4077 | 497,251 | USD 974,955.21 | 0.191 | 0 / 101 |
| joins receipts without the ERP crosswalk | SUP-3155 | 503,199 | USD 954,531.10 | 0.191 | 0 / 101 |
| attributes lots on the free-text supplier field | SUP-3155 | 503,259 | USD 954,669.25 | 0.191 | 0 / 101 |
| plans on the October S&OP cycle | SUP-4077 | 551,845 | USD 1,028,695.25 | 0.303 | 0 / 101 |
| sums both S&OP cycles | SUP-4077 | 1,049,796 | USD 1,951,295.81 | 0.303 | 0 / 101 |
| counts the TOTAL subtotal rows | SUP-4077 | 995,902 | USD 1,851,441.12 | 0.303 | 0 / 101 |
| no yield gross-up | SUP-3155 | 486,000 | USD 914,929.19 | 0.330 | 0 / 101 |
| 2025 average FX instead of planning rates | SUP-3155 | 517,572 | USD 889,957.85 | 0.356 | 0 / 101 |
| charges no inbound freight | SUP-4077 | 497,951 | USD 941,159.20 | 0.378 | 0 / 101 |
| re-rates SUP-2318's whole year at 3.0% | SUP-2318 | 492,200 | USD 960,948.68 | 0.410 | 0 / 101 |
| treats SUP-4077's rebate as earned, no shortfall | SUP-4077 | 497,951 | USD 928,840.56 | 0.378 | 0 / 101 |
| ignores payment terms | SUP-1042 | 495,010 | USD 966,578.65 | 0.718 | 64 / 101 |
| ignores scrap disposal | SUP-1042 | 495,010 | USD 959,233.43 | 0.745 | 69 / 101 |
| ignores SUP-2318's whole-box rule | SUP-1042 | 495,010 | USD 963,017.63 | 0.899 | 101 / 101 |
| multiplies by the 4-dp rounded price | SUP-1042 | 495,010 | USD 963,017.63 | 0.883 | 91 / 101 |
| reference solution | SUP-1042 | 495,010 | USD 963,017.63 | 1.000 | 101 / 101 |

Thirteen single-step omissions land on a different supplier and score between
0.191 and 0.410 test-side, every one of them with 0 of 101 test-side decision
points. They are not variations on one idea: a population question, two
silent-join questions, a plan-version question, a currency rule, a yield
question, an Incoterm reading and two rebate readings. An attempt has to get
all of them right to score above 0.45, and the three population traps are the
ones the previous revision's weak-model runs would not have met.

Free credit is small: the twelve structural checks carry 20 of 188 test-side
points, the instruction-following rubric criteria 27 of 238, together 11% of
the total; every other rubric criterion names a specific finding or figure.
Four sentinel checks worth 24 points name the population corrections and are
earned only by an attempt that made them. Every reported figure is checked to
half a unit in its last reported place, so a supplier reached by a different
route is not rescued by a band.

The floor is protected: three test penalties and two rubric penalties total
−26 against 426 positive weight (6%), and none fires on a merely incomplete
answer.

Risk of being too hard is bounded: the deliverables are three plain files, the
environment preinstalls what is needed to open every shipped format, the data
dictionary and change record describe every population the attempt has to
reason about, and the reference solution runs from the shipped inputs with the
standard library plus `openpyxl`.

# Ground truth recommendation and rationale

**Award the FY2026 SP-40 contract to SUP-1042, Meridian Precision Works, LLC:
495,010 pieces for USD 963,017.63.**

FY2026 good-unit requirement: 486,000 SP-40 pieces (frozen November cycle).

| rank | supplier | quoted USD/piece | reject rate | units to buy | FY2026 total USD | USD/good unit |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | SUP-1042 | 1.9450 | 1.820% | 495,010 | 963,017.63 | 1.9815 |
| 2 | SUP-4077 | 1.8889 | 2.400% | 497,951 | 976,280.36 | 2.0088 |
| 3 | SUP-2318 | 1.9313 | 1.250% | 492,200 | 978,330.38 | 2.0130 |
| 4 | SUP-3155 | 1.8966 | 6.100% | 517,572 | 987,625.94 | 2.0322 |

Margin over the runner-up: **USD 13,262.73**, or 1.38%.

The figures that force it: SUP-1042 is DDP, so it carries no inbound freight
where SUP-2318 and SUP-4077 carry USD 36,276 and USD 35,121; it has the
second-best incoming quality, so its buy quantity is 22,562 pieces below
SUP-3155's; it has no volume commitment, where SUP-4077 owes USD 9,816 in
shortfall charges and earns none of its 4.0% rebate; and its Net 45 terms are
worth USD 3,561 against the Net 30 baseline at 9.0% WACC.

Why the plausible wrong answers are wrong:

- **SUP-4077** looks cheapest on quoted price (USD 1.8889) and appears to carry
  a 4.0% rebate plus a 2/10 cash discount. But at 497,951 pieces it misses its
  own 520,000-piece rebate threshold entirely and additionally owes a GBP 0.35
  per-piece shortfall charge on 22,049 pieces. Its buyer-paid UK freight adds
  USD 35,121 back. It finishes second, USD 13,263 behind — and it wins every
  analysis that inflates SUP-1042's reject rate with the source inspections
  or inflates demand past the threshold.
- **SUP-3155** is second-cheapest on quoted price and is DDP with Net 60 terms,
  so it wins every analysis that skips the yield gross-up, that loses its
  post-cutover lots to the ERP renumbering, or that reads the inspection log
  off the free-text supplier field. Its true 6.100% reject rate forces a
  517,572-piece buy and USD 13,260 of scrap disposal, putting it last.
- **SUP-2318** has the best incoming quality at 1.250%, and wins if its banded
  rebate is re-rated at a flat 3.0%. Read correctly the rebate is USD 11,136
  rather than USD 28,518, and its buyer-paid German freight of USD 36,276
  leaves it third.

Determinism: every figure follows from the shipped files plus the mandated
planning constants in the finance memo, with intermediates carried unrounded
and only the reported figure rounded, as `instruction.md` states. Using the
clause 5 specification limits in place of observed 2025 performance is a
conservative reading rather than an error and also reaches SUP-1042, so the
supplier is stable under it; the quantity and cost are not, and the prompt
asks for the observed record.

# Expected reasoning trajectory

A golden solution is included (`solution/solve.py`, `solution/solve.sh`,
`solution/gold.patch`). The reasoning path it encodes:

1. Inventory `/workspace/data`, read the data dictionary, the change record,
   the four term sheets and the finance memo, and notice that the four offers
   differ in currency, unit of measure, Incoterm, payment terms and volume
   structure.
2. Establish scope from the demand dump: keep the frozen November cycle, filter
   to SP-40, drop the `TOTAL` subtotal rows, sum the twelve monthly rows →
   486,000 good units.
3. Resolve supplier identity: load the supplier master, build the alias → code
   map, and map every purchase order to a supplier code.
4. Build `lot_id → purchase order → supplier code` from the goods receipts,
   resolving post-cutover receipts through the ERP crosswalk, so that every
   inspection lot is attributed by key rather than by name.
5. Restrict the inspection log to `INCOMING` records, deduplicate on `lot_id`,
   drop the non-candidate SUP-9001, and aggregate lots, units and rejects per
   candidate.
6. Recognise from clause 5.4 that rejects are scrapped without credit, gross the
   buy quantity up to `ceil(486,000 / (1 − r))`, and round SUP-2318 up to whole
   boxes.
7. Price each offer: convert at the mandated planning rates, divide SUP-2318's
   box price by 100, add the lane tariff plus brokerage over twelve shipments
   for the two FCA suppliers only, apply each rebate as its clause actually
   reads, add SUP-4077's shortfall charge, add scrap disposal at USD 0.42 per
   rejected piece, and value payment terms against Net 30 at 9.0% WACC, taking
   SUP-4077's cash discount on the reduced spend base.
8. Rank on cost per good unit, write the two CSVs, and write the memo: the
   decision with its three figures, the comparison, the basis, the exclusions
   and the risks — including that SUP-1042's incoming rate rests on its
   source-sort cadence.

The verifier is 38 checks (35 positive, 3 penalties) driven by
`tests/test_weights.json`; the rubric is 45 criteria (43 positive, 2
penalties). Local checks: the nop agent scores 0.000, the oracle scores 1.000
(188 of 188 positive weight, with only the three penalty checks correctly
declining to fire), and `solution/_provenance/verify_design.py` reproduces the
Measured table above.
