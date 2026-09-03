# Task description

The attempt acts as a **sourcing analyst at Cadence Instruments LLC**, a
mid-size industrial flow-meter manufacturer in Aurora, Illinois. The SP-40
stainless valve seat is currently split across several suppliers on expiring
agreements. The steering committee has decided to consolidate FY2026 onto a
**single supplier for the full contract year** and four suppliers have returned
offers. The attempt must decide **which of the four candidate suppliers is
awarded the FY2026 SP-40 contract** and make the case for it.

The environment ships twelve input files across four formats — four Markdown
contract term sheets, a standing finance policy memo, a demand-planning
handover note, an XLSX supplier master with an alias sheet, three CSV extracts
(purchase orders, goods receipts, FX dailies) plus a demand extract and a
freight tariff, and a JSONL incoming-inspection log. Nothing has been
reconciled; the systems disagree with each other about supplier names.

**Deliverables**, all written to `/workspace/output/`:

1. `supplier_costs.csv` — four rows, one per candidate, fixed seven-field
   header, ranked, with per-field precision stated in the prompt.
2. `defect_rates.csv` — four rows, fixed five-field header, sorted by supplier
   code, `reject_rate_pct` to three decimals.
3. `recommendation.md` — the committee memo, with five level-2 headings
   spelled and ordered exactly as specified.

The prompt states the deliverable contract exactly and says nothing about
method: it never names a metric to compute, a column to use, a file to join, or
a figure to reach.

# Complexity justification

Six reasoning challenges are planted. The third is the crux that decides the
recommendation.

**1. Scope of demand has to be inferred from a dirty cube extract.**
*Planted:* `demand/forecast_2026.csv` is a raw planning-cube dump. It carries
twelve monthly SP-40 rows, twelve monthly SP-22 rows for a different part on a
separate agreement, and a `TOTAL` subtotal row per part. The handover note says
the extract is uncleaned and that SP-22 is out of scope, but does not do the
filtering. *Correct attempt:* sums only the twelve monthly SP-40 rows →
486,000 good units. *Careless attempt:* sums the column, or forgets the
subtotal rows, and doubles or inflates demand — which pushes the purchase
quantity above 520,000 pieces and hands the award to SUP-4077 through a rebate
that is not really earned.

**2. Quoted prices are not comparable as quoted.**
*Planted:* the four offers are in four currencies, and SUP-2318 quotes EUR
178.00 **per 100-piece box** while the others quote per piece. The finance memo
mandates fixed FY2026 planning rates and explicitly rules out the 2025 daily FX
export, which is also shipped and whose averages sit materially below the
planning rates. *Correct attempt:* restates all four to USD per single piece —
1.9450 / 1.9313 / 1.8966 / 1.8889. *Careless attempt:* uses 2025 average rates
(award flips to SUP-3155) or mishandles the box UOM.

**3. CRUX — supplier attribution in the inspection log.**
*Planted:* `quality/incoming_inspection_2025.jsonl` has a free-text `supplier`
field that is empty or `null` on a large minority of lots and inconsistently
spelled on the rest. Every lot is nonetheless attributable: `lot_id` → goods
receipt → purchase order → the supplier master's `name_aliases` sheet →
supplier code. The blank-supplier lots are **not randomly distributed** —
SUP-3155's unattributed lots run at 12.6% rejects against 3.1% on its named
lots. The log also double-logs eight lots under a second `inspection_id`, and
carries lots from SUP-9001, a terminated non-candidate. *Correct attempt:*
attributes through the receipt join, deduplicates on `lot_id`, drops the
non-candidate → 1.820% / 1.250% / 6.100% / 2.400%. *Careless attempt:* groups
on the free-text field, silently dropping the blank rows, and reads SUP-3155 at
3.05% instead of 6.10% — which makes SUP-3155 the cheapest supplier and
**reverses the award**.

**4. Rejects are a purchase-quantity problem, not a line item.**
*Planted:* clause 5.4 of all four term sheets — identically worded, so no
supplier is advantaged by a hidden term — states that rejected pieces are
scrapped by the buyer with no credit and no replacement, and that the buyer
must order enough to meet its net good-unit requirement. The demand column is
explicitly labelled net good units. Clause 5 of each contract separately states
a *specification limit* on the reject rate and says in terms that it is not a
forecast. *Correct attempt:* grosses up, `ceil(486,000 / (1 − r))`, a spread of
25,420 pieces between best and worst supplier. *Careless attempt:* buys 486,000
pieces from everyone, and the award flips to SUP-3155.

**5. Incoterms decide who pays freight.**
*Planted:* two offers are FCA at the seller's works and two are DDP. The
freight tariff lists all four lanes with a neutral note that applicability
depends on the Incoterm in the supply contract, so the tariff itself does not
say which lanes to charge. *Correct attempt:* charges the DE and UK lanes only,
at twelve shipments per year as each contract's clause 2 states. *Careless
attempt:* charges nobody (award flips to SUP-3155) or charges everybody.

**6. Two rebate structures that do not pay what they appear to.**
*Planted:* SUP-2318's clause 4.2 is a **banded** rebate — each rate applies only
to the volume inside its band, and clause 4.2 says so in terms. SUP-4077's
clause 4.2 grants 4.0% on all pieces but **only if** contract-year volume
reaches 520,000, and clause 4.1 separately commits the buyer to that same
520,000 with a GBP 0.35 per-piece shortfall charge. The correct purchase
quantity, 497,951, sits 4.2% below that threshold — so the threshold can only
be evaluated after challenges 1, 3 and 4 are done right. *Correct attempt:*
SUP-2318 earns USD 11,133 and SUP-4077 earns nothing while owing USD 9,816.
*Careless attempt:* re-rates SUP-2318's whole year at 3.0% (USD 28,515) or
assumes SUP-4077's rebate is earned — either flips the award.

# Taxonomy tags

Objectives: cost modelling, total-cost-of-ownership comparison, supplier
selection, data reconciliation across systems, entity resolution, contract
interpretation, scope determination, quality-cost analysis, working-capital
valuation.

Reasoning phases scored by the rubric: explore, analyze, synthesize, recommend,
instruction_following.

Domain: business / operations / procurement finance. Formats: CSV, XLSX,
JSONL, Markdown.

# Expected difficulty range

Target band: **strong model mean reward at or under 0.6, weak model mean at or
under 0.35 over four trials each.**

The rubric and tests put 38.96% of the total positive weight on the decision,
so an attempt that produces a well-formed, well-documented memo and lands on
the wrong supplier tops out near 0.6, and one that also misses the structural
and data-quality checks lands well below.

Why a strong attempt misses: the answer is not reachable by elimination on
coarse facts. **The recommended supplier holds the highest quoted price per
piece of the four** and never leads on any partial analysis — the enumeration
in `tools/model_check.py` in the authoring repo shows eight distinct careless
routes, each landing on a different wrong supplier. Reaching SUP-1042 requires
scope, UOM, FX, attribution, dedup, yield gross-up, Incoterms and both rebate
structures to be right together. The crux is challenge 3: attribution through
the receipt join is invisible unless the attempt notices that the inspection
log's supplier field is blank on a large minority of rows *and* checks whether
those rows differ from the named ones. Grouping on the field that is right
there is the natural move, and it produces a clean, confident, wrong answer.

The margin is deliberately tight — 1.39% between first and second — so a
careless computation lands on a different supplier rather than on the right one
by default. The numeric tests accept a figure only at the precision
`instruction.md` asks for it — half a unit in the last reported place — and
`instruction.md` closes the two choices that would otherwise be open, by fixing
that intermediates are carried unrounded and that the purchase quantity rounds
up. A correct analysis therefore lands on the asserted figure exactly rather
than near it, while every wrong route sits at least 1.26% away, orders of
magnitude outside that.

Risk of being too hard is bounded: the deliverables are three plain files, the
environment preinstalls what is needed to open every shipped format, and the
reference solution runs from the shipped inputs with the standard library plus
`openpyxl`.

# Ground truth recommendation and rationale

**Award the FY2026 SP-40 contract to SUP-1042, Meridian Precision Works, LLC.**

FY2026 good-unit requirement: 486,000 SP-40 pieces.

| rank | supplier | quoted USD/piece | reject rate | units to buy | FY2026 total USD | USD/good unit |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | SUP-1042 | 1.9450 | 1.820% | 495,010 | 963,017.63 | 1.9815 |
| 2 | SUP-4077 | 1.8889 | 2.400% | 497,951 | 976,373.13 | 2.0090 |
| 3 | SUP-2318 | 1.9313 | 1.250% | 492,152 | 978,217.33 | 2.0128 |
| 4 | SUP-3155 | 1.8966 | 6.100% | 517,572 | 987,625.94 | 2.0322 |

Margin over the runner-up: **USD 13,355.50**, or 1.39%.

The figures that force it: SUP-1042 is DDP, so it carries no inbound freight
where SUP-2318 and SUP-4077 carry USD 36,273 and USD 35,121; it has the
second-best incoming quality, so its buy quantity is 22,562 pieces below
SUP-3155's; it has no volume commitment, where SUP-4077 owes USD 9,816 in
shortfall charges and earns none of its 4.0% rebate; and its Net 45 terms are
worth USD 3,561 against the Net 30 baseline at 9.0% WACC.

Why the plausible wrong answers are wrong:

- **SUP-4077** looks cheapest on quoted price (USD 1.8889) and appears to carry
  a 4.0% rebate plus a 2/10 cash discount. But at 497,951 pieces it misses its
  own 520,000-piece rebate threshold entirely and additionally owes a GBP 0.35
  per-piece shortfall charge on 22,049 pieces. Its buyer-paid UK freight adds
  USD 35,121 back. It finishes second, USD 13,356 behind.
- **SUP-3155** is second-cheapest on quoted price and is DDP with Net 60 terms,
  so it wins every analysis that skips the yield gross-up or that reads the
  inspection log off the free-text supplier field. Its true 6.100% reject rate
  forces a 517,572-piece buy and USD 13,260 of scrap disposal, putting it last.
- **SUP-2318** has the best incoming quality at 1.250%, and wins if its banded
  rebate is re-rated at a flat 3.0%. Read correctly the rebate is USD 11,133
  rather than USD 28,515, and its buyer-paid German freight of USD 36,273
  leaves it third.

Determinism: every figure follows from the shipped files plus the mandated
planning constants in the finance memo. Using the clause 5 specification limits
in place of observed 2025 performance is a conservative reading rather than an
error and also reaches SUP-1042, so the recommendation is stable under it.

# Expected reasoning trajectory

A golden solution is included (`solution/solve.py`, `solution/solve.sh`,
`solution/gold.patch`). The reasoning path it encodes:

1. Inventory `/workspace/data`, read the four term sheets and the finance memo,
   and notice that the four offers differ in currency, unit of measure,
   Incoterm, payment terms and volume structure.
2. Establish scope from the demand extract: filter to SP-40, drop the `TOTAL`
   subtotal rows, sum the twelve monthly rows → 486,000 good units.
3. Resolve supplier identity: load the supplier master, build the alias → code
   map, and map every purchase order to a supplier code.
4. Build `lot_id → purchase order → supplier code` from the goods receipts, so
   that inspection lots are attributed by key rather than by name.
5. Deduplicate the inspection log on `lot_id`, drop the non-candidate SUP-9001,
   and aggregate lots, units and rejects per candidate.
6. Recognise from clause 5.4 that rejects are scrapped without credit, and
   gross the buy quantity up to `ceil(486,000 / (1 − r))`.
7. Price each offer: convert at the mandated planning rates, divide SUP-2318's
   box price by 100, add the lane tariff plus brokerage over twelve shipments
   for the two FCA suppliers only, apply each rebate as its clause actually
   reads, add SUP-4077's shortfall charge, add scrap disposal at USD 0.42 per
   rejected piece, and value payment terms against Net 30 at 9.0% WACC, taking
   SUP-4077's 2/10 discount because it beats carrying the payable.
8. Rank on cost per good unit, write the two CSVs to the stated precisions, and
   write the memo with the five required headings, stating the award, the
   margin, why each loser loses, what was excluded and what would overturn it.
