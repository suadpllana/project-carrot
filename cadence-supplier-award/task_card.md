# Task description

The attempt acts as a **sourcing analyst at Cadence Instruments LLC**, a
mid-size industrial flow-meter manufacturer in Aurora, Illinois. The SP-40
stainless valve seat is currently split across several suppliers on expiring
agreements. The steering committee has decided to consolidate FY2026 onto a
**single supplier for the full contract year** and four suppliers have returned
offers. The attempt must decide **which of the four candidate suppliers is
awarded the FY2026 SP-40 contract, how many pieces are contracted with it and
what the contract year costs**, and make the case for it.

The environment ships seventeen input files across four formats — four Markdown
contract term sheets, a standing finance policy memo, a demand-planning
handover note, the receiving-inspection procedure QP-07, an XLSX supplier
master with an alias sheet, four CSV purchasing extracts (purchase orders,
goods receipts, a purchase-order reference extract, FX dailies) plus a demand
extract and a freight tariff, a JSONL inspection log, a data dictionary and an
IT change record. Nothing has been reconciled; the systems disagree with each
other about supplier names and, since the July ERP go-live, about
purchase-order numbers.

**Every shipped document describes its system and decides nothing.** The data
dictionary defines `inspection_point` and `disposition` without saying which
records belong in a reject rate; the change record states that receipts carry
the posting system's purchase-order number without saying that a join on it
fails; the planning note says the plan was frozen at the November cycle without
saying that the dump also carries October. What to do with any of it is the
attempt's judgement. Wording that instructs rather than describes is treated as
a defect in this task: it is what put revisions 2 and 3 out of band.

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

Ten reasoning challenges are planted in the data. **Nine of them decide the
recommendation on their own**: get any one wrong and the award goes to a
different supplier. None is asked for by the prompt, and none is a checklist
item a document hands over. The three hardest are of the kind a careful attempt
does not find by checking rows against a reference table — a population
question and two silent joins — and are described first.

**0a. CRUX — the inspection log is two populations.**
*Planted:* `quality/incoming_inspection_2025.jsonl` carries 33 `SOURCE`
records among the 260 `INCOMING` ones: pre-shipment inspections performed by a
Cadence supplier-quality engineer at the supplier's plant, 22 of them on
SUP-1042 lots at a 12.1% reject rate (SUP-2318 and SUP-3155 have a few as
well, so it is not a one-supplier gimmick). Every record is an SP-40 inspection
of a real lot, so reading the log as one population is the natural default.
The mechanics are recoverable and never assembled for the attempt: QP-07
section 5 says pieces rejected at a supplier's plant are held back and replaced
before the shipment is tendered and that the lot is inspected again at Aurora,
section 4 says pieces rejected at receiving are scrapped by Cadence, and clause
5.4 of every term sheet says the buyer carries that loss. The conclusion — that
a purchase quantity is grossed up for what is lost at receiving, not for what
never shipped — is the attempt's to draw. Every source record shares its
`lot_id` with the incoming record of the same lot, and half were keyed before
that record and half after, so neither "keep the first record per lot" nor
"keep the last" gets it right.
*Correct attempt:* restricts the reject rates to `INCOMING` records, which
are the pieces Cadence pays for and scraps: SUP-1042 at 1.820%.
*Careless attempt:* pools the two and reads SUP-1042 at 3.68% (dedupe either
way) or 4.55% (no dedupe), buys 9,500–14,000 more pieces from it, and awards
SUP-4077. Measured 0.159–0.222 with 0 of 93 test-side decision points.

**0b. CRUX — the ERP cutover breaks the receipt join without an error.**
*Planted:* purchasing and receiving moved to a new ERP on 2025-07-01
(`it/CHG-2025-0417_erp_cutover.md`). The 62 goods receipts posted from that
date carry the ERP's ten-digit purchase order number; the purchasing extract
carries the reporting mart's `PO-45xxx` numbers throughout. Both series appear
on `purchasing/po_reference_2025.csv`, which is an ordinary reference extract
(buyer, cost centre, commodity code, terms text) and is not labelled as a fix
for anything. A join of receipts to purchase orders on
`po_id` matches every pre-cutover receipt and silently matches nothing after
it, so the lots received after go-live drop out of the reject rates with no
symptom. They are not a random sample: SUP-3155's post-cutover lots run at
8.0% (named) and 14.2% (unnamed) against 2.4% before.
*Correct attempt:* checks that the join matched, resolves post-cutover
receipts through the reference extract, and attributes all 63 SUP-3155 lots:
6.100%.
*Careless attempt:* reads SUP-3155 at 3.42% on 43 lots, buys 14,000 fewer
pieces from it, and awards SUP-3155. Measured 0.159 with 0 of 93 decision
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
3.43%, and awards SUP-3155. Measured 0.159 with 0 of 93 decision points.

Challenges 0b and 1 are independent: an attempt that joins through the
receipts but not the reference extract loses the post-cutover lots, one that
resolves the numbers but attributes on the free-text field loses the blank
ones, and both land on the same wrong supplier. Only an attempt that does both
reaches 6.100%.

**2. Scope of demand has to be inferred from a dirty cube extract.**
*Planted:* `demand/forecast_2026.csv` is a raw planning-cube dump. It carries
the superseded October S&OP cycle beside the frozen November one (`plan_cycle`
column; 538,600 SP-40 pieces against 486,000), a `TOTAL` subtotal row per part
and cycle, and twelve monthly rows for SP-22, a different part on a separate
agreement. The handover note says the plan was frozen at the November cycle
and that the dump is a direct cube export carrying the cube's own subtotal
rows; it does not say that a second cycle is in the file, and nothing does the
filtering.
*Correct attempt:* sums the twelve monthly SP-40 rows of the November cycle →
486,000 good units.
*Careless attempt:* plans on the October cycle, sums both cycles, or counts
the subtotal rows — each pushes the purchase quantity above 520,000 pieces and
hands the award to SUP-4077 through a rebate that is not really earned.
Measured 0.317 with 0 of 93 decision points, all three ways.

**3. Quoted prices are not comparable as quoted.**
*Planted:* the four offers are in four currencies, and SUP-2318 quotes EUR
176.00 **per 100-piece box** while the others quote per piece. The finance memo
mandates fixed FY2026 planning rates and explicitly rules out the 2025 daily FX
export, which is also shipped and whose averages sit materially below the
planning rates. *Correct attempt:* restates all four to USD per single piece —
1.9450 / 1.9096 / 1.8639 / 1.8254. *Careless attempt:* uses 2025 average rates
and awards SUP-3155 (measured 0.386, 0 decision points).

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
flips to SUP-3155 (measured 0.365, 4 decision points).

**5. Incoterms decide who pays freight.**
*Planted:* two offers are FCA at the seller's works and two are DDP. The
freight tariff lists all four lanes with a neutral note that applicability
depends on the Incoterm in the supply contract, so the tariff itself does not
say which lanes to charge. *Correct attempt:* charges the DE and UK lanes only,
at twelve shipments per year as each contract's clause 2 states. *Careless
attempt:* charges nobody, and the award flips to SUP-4077 (measured 0.407).

**6. Two rebate structures that do not pay what they appear to.**
*Planted:* SUP-2318's clause 4.2 is a **banded** rebate — each rate applies only
to the volume inside its band, and clause 4.2 says so in terms. SUP-4077's
clause 4.2 grants 4.0% on all pieces but **only if** contract-year volume
reaches 520,000, and clause 4.1 separately commits the buyer to that same
520,000 with a GBP 0.35 per-piece shortfall charge. The correct purchase
quantity, 497,951, sits 4.2% below that threshold — so the threshold can only
be evaluated after challenges 0a, 0b, 1, 2 and 4 are done right. *Correct
attempt:* SUP-2318 earns USD 11,011 and SUP-4077 earns nothing while owing
USD 9,816. *Careless attempt:* re-rates SUP-2318's whole year at 3.0% (USD
28,197) and awards SUP-2318 (measured 0.450), or treats SUP-4077's rebate as
earned and awards SUP-4077 (measured 0.407).

**7. The volume commitment is decisive on its own.**
*Planted:* the winning margin is USD 2,322.53, or 0.24% of contract value.
SUP-4077's clause 4.1 shortfall charge is USD 9,816.21 — four times the
margin. An attempt that reads clause 4.2 (the rebate is not earned below
520,000 pieces) but stops before clause 4.1 (the same 520,000 is a commitment
with a per-piece shortfall charge) awards SUP-4077.

**8. The winner's edge is made of the terms a hurried model drops.**
*Planted:* SUP-1042's edge is not in its price, which is the highest of the
four, but in two line items that sit at the end of the cost build-up. Its Net
90 payment terms are worth USD 14,244.08 against a Net 30 baseline at 9.0%
WACC (finance memo, section 3), where SUP-4077's are worth USD 6,723.99; and
its scrap bill at USD 1.25 per rejected piece (section 5) is USD 11,262.50
against SUP-4077's USD 14,938.75. Either line alone exceeds the margin. An
attempt that models material, freight, rebates and the shortfall and stops
there — the profile the previous sweep produced — awards SUP-4077. SUP-4077's
1% 10 cash discount is a further trap for the total: at 9.0% the standard Net
60 date is USD 2,071.99 cheaper, so a model that takes a discount because one
is offered mis-states the runner-up's cost.

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

Three revisions have missed the band, and each diagnosis was one layer short
of the last:

* **Revision 2** scored the weak model 0.889 (0.87 / 0.87 / 0.89 / 0.94). Every
  planted trap was a documented step and the decision was one figure — which
  supplier — so an attempt that never got a number right still collected it.
* **Revision 3** added three population traps and made the decision three
  figures. The weak model scored 0.778 (0.70 / 0.69 / 0.67 / 0.69 test-side).
  It was reaching SUP-1042 in every trial, because the data dictionary
  explained the traps: it told the attempt that source rejects are never
  received or invoiced, that a crosswalk resolves the post-cutover numbers, and
  that the demand dump is not filtered to one cycle. Three judgements had been
  written down as three instructions.
* **Revision 4** removed the instructions: the documents describe fields and
  systems and stop there. The weak model scored 0.631 (0.683 / 0.618 / 0.587
  / 0.634). It cleared every judgement and still reached SUP-1042, and the
  scores say exactly how: 0.683 is the measured reward of an attempt that
  gets everything right and leaves out payment terms, and the other three
  trials sit where one or two more small cost terms are also missing. Those
  omissions did not flip the award because SUP-4077 benefited from payment
  terms and scrap *more* than SUP-1042 did, so dropping them helped the
  winner.

**Revision 5 makes the winner's edge out of exactly those terms.** SUP-1042
moves to Net 90 and SUP-4077 to a 1% 10 Net 60 whose discount is not worth
taking, so payment terms are worth USD 14,244 to the winner and USD 6,724 to
the runner-up; scrap disposal rises to USD 1.25 per rejected piece, so the
winner's better quality is worth USD 3,676 there; SUP-4077's price is retuned
so the margin is **0.24%**. Leaving out payment terms or scrap now each hands
the award to SUP-4077. SUP-2318 and SUP-3155 are repriced so that the
attribution and banded-rebate traps keep their teeth at the new margin. The
rubric stays bound to figures — 91% of its positive weight names a value only
the correct pipeline produces, each with both renderings a memo may use for
it (`USD 9,816.21 or USD 9,816`), so a grader marks it from the deliverable
without a tolerance of its own to invent.

Four independent judgements gate the answer, each landing on a different
wrong supplier, and none of them is a checklist item — and behind them every
line of the cost build-up is decisive too:

| Judgement | What the documents say | What they do not say |
| --- | --- | --- |
| which inspection records are a reject rate | what a source inspection is, what happens to pieces rejected at each point | that source records do not belong in the rate |
| how a lot reaches a supplier | that receipts carry the posting system's PO number; both series are on a reference extract | that a join on `po_id` loses two fifths of the lots |
| whether the free-text supplier field is usable | that it is keyed by hand and not validated | that the lots it omits are the worst ones |
| which plan cycle is the plan | that the plan was frozen at the November cycle | that the dump also carries October and its subtotals |

Measured against the shipped verifier by mutating the reference solution, one
omission per row:

| Single omission | Lands on | Contract qty | Contract cost | Tests | Decision |
| --- | --- | --- | --- | --- | --- |
| pools the SOURCE inspections (dedupe keeps first record) | SUP-4077 | 497,951 | USD 962,135.40 | 0.213 | 0 / 93 |
| pools the SOURCE inspections (dedupe keeps last record) | SUP-4077 | 497,951 | USD 962,135.40 | 0.213 | 0 / 93 |
| pools the SOURCE inspections, no dedupe | SUP-4077 | 497,251 | USD 960,263.08 | 0.152 | 0 / 93 |
| joins receipts without the ERP number reference | SUP-3155 | 503,199 | USD 952,473.38 | 0.152 | 0 / 93 |
| attributes lots on the free-text supplier field | SUP-3155 | 503,259 | USD 952,659.39 | 0.152 | 0 / 93 |
| plans on the October S&OP cycle | SUP-4077 | 551,845 | USD 1,014,420.88 | 0.305 | 0 / 93 |
| sums both S&OP cycles | SUP-4077 | 1,049,796 | USD 1,924,140.73 | 0.305 | 0 / 93 |
| counts the TOTAL subtotal rows | SUP-4077 | 995,902 | USD 1,825,679.70 | 0.305 | 0 / 93 |
| no yield gross-up | SUP-3155 | 486,000 | USD 899,154.55 | 0.350 | 4 / 93 |
| 2025 average FX instead of planning rates | SUP-3155 | 517,572 | USD 901,047.13 | 0.411 | 0 / 93 |
| charges no inbound freight | SUP-4077 | 497,951 | USD 927,014.24 | 0.431 | 0 / 93 |
| re-rates SUP-2318's whole year at 3.0% | SUP-2318 | 492,200 | USD 955,734.37 | 0.472 | 0 / 93 |
| treats SUP-4077's rebate as earned, no shortfall | SUP-4077 | 497,951 | USD 915,959.85 | 0.431 | 0 / 93 |
| misses the shortfall charge alone (clause 4.1) | SUP-4077 | 497,951 | USD 952,319.18 | 0.431 | 0 / 93 |
| ignores payment terms | SUP-4077 | 497,951 | USD 968,859.38 | 0.391 | 0 / 93 |
| ignores scrap disposal | SUP-4077 | 497,951 | USD 947,196.65 | 0.391 | 0 / 93 |
| ignores SUP-2318's whole-box rule | SUP-1042 | 495,010 | USD 959,812.87 | 0.883 | 93 / 93 |
| multiplies by the 4-dp rounded price | SUP-1042 | 495,010 | USD 959,812.87 | 0.863 | 81 / 93 |
| reference solution | SUP-1042 | 495,010 | USD 959,812.87 | 1.000 | 93 / 93 |

And the same measurement for attempt profiles — a competent attempt that does
every documented step and misses one or two judgements:

| Attempt profile | Lands on | Contract qty | Contract cost | Tests | Decision |
| --- | --- | --- | --- | --- | --- |
| pools SOURCE records (the default if the log is read as one population) | SUP-4077 | 497,951 | USD 962,135.40 | 0.213 | 0 / 93 |
| pools SOURCE, joins receipts on po_id as it stands | SUP-3155 | 503,199 | USD 952,473.38 | 0.173 | 4 / 93 |
| pools SOURCE, attributes on the free-text supplier field | SUP-4077 | 496,933 | USD 959,412.51 | 0.152 | 0 / 93 |
| joins receipts on po_id as it stands, sums both plan cycles | SUP-4077 | 1,050,431 | USD 1,926,075.53 | 0.127 | 0 / 93 |
| free-text attribution, October plan cycle | SUP-4077 | 550,716 | USD 1,010,980.90 | 0.127 | 0 / 93 |
| every judgement right, whole-box rule and rounded price missed | SUP-1042 | 495,010 | USD 959,812.87 | 0.782 | 81 / 93 |
| every judgement right, payment terms and scrap missed | SUP-4077 | 497,951 | USD 953,920.63 | 0.391 | 0 / 93 |

Twenty-two of the twenty-five omissions land on a different supplier, at
0.13 to 0.47 test-side with 0 of 93 test-side decision points; the three that
do not are SUP-2318's whole-box rule and the rounded price, which change no
figure of the winner's, and the reference itself.

The rubric adds little to a wrong-supplier attempt, and less than it used to.
`instruction.md` asks `## Cost Comparison` for the **build-up of each
supplier's FY2026 total** — every element charged, labelled, as a US-dollar
amount, adding to the filed total — and asks each other section for the basis
behind its figures: which inspection records were counted and which set aside
and why, where the good-unit requirement came from, how each purchase quantity
follows from it, how quoted prices were restated. That is a duty to disclose
method, not a list of the method's steps: nothing tells the attempt which
records to set aside or which cycle is the plan. It makes the memo's own
figures gradable, so the rubric scores the build-up against values only the
correct pipeline produces rather than prose that could be about anything, and
a wrong route publishes its own wrong build-up. A test scores the same
disclosure: the awarded supplier's build-up has to carry scrap disposal and
the working-capital value of payment terms as US-dollar amounts, which is
exactly what the attempt profile the last sweep produced never computes.

An attempt has to clear all four judgements *and* carry every line of the cost
build-up to score above 0.47.

Free credit is small and bounded: the twelve structural checks carry 14 of 197
test-side points and the instruction-following rubric criteria 18 of 195,
together 8% of the 392 total. Four sentinel checks worth 34 points name the
population corrections and are earned only by an attempt that made them. The
decision carries 38.5% of total positive weight (151 of 392), inside the
30-50% band, and none of it is reachable by naming a supplier alone: two of the
three decision figures are the contracted quantity and the contract-year cost
to the cent.

The floor is protected: three test penalties and two rubric penalties total
−26 against 392 positive weight, and none fires on a merely incomplete answer.

Two checks earn nothing for naming a supplier or a file: `## Basis of Decision`
has to put one of a losing supplier's own figures, or one of the things that
separate the offers, beside its name, and `## Data Quality and Exclusions` has
to report at least three of the populations set aside rather than only the
non-candidate supplier.

Risk of being too hard is bounded: the deliverables are three plain files, the
environment preinstalls what is needed to open every shipped format, every
population the attempt has to reason about is described in a shipped document,
and the reference solution runs from the shipped inputs with the standard
library plus `openpyxl`.

# Ground truth recommendation and rationale

**Award the FY2026 SP-40 contract to SUP-1042, Meridian Precision Works, LLC:
495,010 pieces for USD 959,812.87.**

FY2026 good-unit requirement: 486,000 SP-40 pieces (frozen November cycle).

| rank | supplier | quoted USD/piece | reject rate | units to buy | FY2026 total USD | USD/good unit |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | SUP-1042 | 1.9450 | 1.820% | 495,010 | 959,812.87 | 1.9749 |
| 2 | SUP-4077 | 1.8254 | 2.400% | 497,951 | 962,135.40 | 1.9797 |
| 3 | SUP-2318 | 1.9096 | 1.250% | 492,200 | 972,920.77 | 2.0019 |
| 4 | SUP-3155 | 1.8639 | 6.100% | 517,572 | 997,031.30 | 2.0515 |

Margin over the runner-up: **USD 2,322.53**, or 0.24%.

The figures that force it: SUP-1042 is DDP, so it carries no inbound freight
where SUP-2318 and SUP-4077 carry USD 36,276 and USD 35,121; it has the
second-best incoming quality, so its buy quantity is 22,562 pieces below
SUP-3155's; it has no volume commitment, where SUP-4077 owes USD 9,816 in
shortfall charges and earns none of its 4.0% rebate; its Net 90 terms are
worth USD 14,244 against the Net 30 baseline at 9.0% WACC, where SUP-4077's
Net 60 is worth USD 6,724; and its scrap bill is USD 3,676 smaller. The
shortfall charge, the payment-terms gap and the scrap gap are each larger
than the USD 2,323 margin.

Why the plausible wrong answers are wrong:

- **SUP-4077** is the cheapest quote (USD 1.8254) and appears to carry a 4.0%
  rebate plus a 1% 10 cash discount. But at 497,951 pieces it misses its own
  520,000-piece rebate threshold entirely and additionally owes a GBP 0.35
  per-piece shortfall charge on 22,049 pieces, USD 9,816; the discount is not
  worth taking. Its buyer-paid UK freight adds USD 35,121 back. It finishes
  second, USD 2,323 behind — and it wins every analysis that inflates
  SUP-1042's reject rate with the source inspections, inflates demand past
  the threshold, reads clause 4.2 without clause 4.1, or leaves payment terms
  or scrap out of the cost build-up.
- **SUP-3155** is second-cheapest on quoted price and is DDP with Net 60 terms,
  so it wins every analysis that skips the yield gross-up, that loses its
  post-cutover lots to the ERP renumbering, or that reads the inspection log
  off the free-text supplier field. Its true 6.100% reject rate forces a
  517,572-piece buy and USD 39,465 of scrap disposal, putting it last.
- **SUP-2318** has the best incoming quality at 1.250%, and wins if its banded
  rebate is re-rated at a flat 3.0%. Read correctly the rebate is USD 11,011
  rather than USD 28,197, and its buyer-paid German freight of USD 36,276
  leaves it third.

Determinism: every figure follows from the shipped files plus the mandated
planning constants in the finance memo, with intermediates carried unrounded
and only the reported figure rounded, as `instruction.md` states. Using the
clause 5 specification limits in place of observed 2025 performance is a
conservative reading rather than an error; its figures differ throughout,
and the prompt asks for the observed record.

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
   checking that the join actually matches and resolving post-cutover receipts
   through the purchase-order reference extract, so that every inspection lot
   is attributed by key rather than by name.
5. Restrict the inspection log to `INCOMING` records, deduplicate on `lot_id`,
   drop the non-candidate SUP-9001, and aggregate lots, units and rejects per
   candidate.
6. Recognise from clause 5.4 that rejects are scrapped without credit, gross the
   buy quantity up to `ceil(486,000 / (1 − r))`, and round SUP-2318 up to whole
   boxes.
7. Price each offer: convert at the mandated planning rates, divide SUP-2318's
   box price by 100, add the lane tariff plus brokerage over twelve shipments
   for the two FCA suppliers only, apply each rebate as its clause actually
   reads, add SUP-4077's shortfall charge, add scrap disposal at USD 1.25 per
   rejected piece, and value payment terms against Net 30 at 9.0% WACC,
   checking SUP-4077's cash discount against its standard date and finding it
   is not worth taking.
8. Rank on cost per good unit, write the two CSVs, and write the memo: the
   decision with its three figures, the comparison, the basis, the exclusions
   and the risks — including that SUP-1042's incoming rate rests on its
   source-sort cadence.

The verifier is 39 checks (36 positive, 3 penalties) driven by
`tests/test_weights.json`; the rubric is 47 criteria (45 positive, 2
penalties), each naming the exact figure or claim it grades and each grading a
disclosure `instruction.md` asks the memo for by name. Local checks: the nop agent scores 0.000, the oracle scores 1.000
(188 of 188 positive weight, with only the three penalty checks correctly
declining to fire), and `solution/_provenance/verify_design.py` reproduces the
Measured table above.
