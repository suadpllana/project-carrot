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
records belong in a reject rate or which rejected pieces are a loss; the
change record states that receipts carry the posting system's purchase-order
number without saying that a join on it fails; the planning note says the plan
was frozen at the November cycle and that the dump is the cube's whole rolling
fifteen-month horizon, without saying which months the contract covers. What to
do with any of it is the attempt's judgement. Wording that instructs rather
than describes is treated as a defect in this task: it is what put revisions 2
and 3 out of band.

**Deliverables**, all written to `/workspace/output/`:

1. `supplier_costs.csv` — four rows, one per candidate, fixed seven-field
   header, ranked, with per-field precision stated in the prompt. Its rank-1
   row is the decision: the supplier, the quantity contracted and the
   contract-year cost.
2. `defect_rates.csv` — four rows, fixed five-field header, sorted by supplier
   code, `reject_rate_pct` to three decimals.
3. `cost_buildup.csv` — how each supplier's FY2026 total is built up, one row
   per cost element charged, the elements summing to the total filed for that
   supplier. The attempt chooses the elements and their labels; the prompt
   binds only the sum, so the file records the cost model rather than
   prescribing it.
4. `recommendation.md` — the committee memo, with five level-2 headings
   spelled and ordered exactly as specified; its Recommendation section states
   the same three decision figures.

The prompt states the deliverable contract exactly and says nothing about
method: it never names a metric to compute, a column to use, a file to join, a
record to exclude or a figure to reach. All input data is synthetic and
author-generated; the generator is retained under `solution/_provenance/`.

# Complexity justification

**Seven independent judgements gate the answer, and each of the seven lands
on a different supplier when it is missed.** None is asked for by the prompt,
and none is a checklist item a document hands over. Two of them — which
rejected pieces are actually a loss, and which months of the cube the contract
covers — were added in revision 6; the seventh — what a repeated inspection
record is — was added in revision 8 after the weak-model sweep solved the
whole task in two trials of four.

The single most important property of the design is that **the right answer is
invisible from any uncorrected view**. SUP-1042 is not a near miss on a
careless run: on the default reading of the inspection log it is third of four,
and with the source inspections pooled it is fourth. There is no
wrong-but-close ranking that a second look corrects.

**0a. CRUX — a rejected piece is not always a loss.**
*Planted:* every nonconforming piece found at incoming inspection carries a
`disposition` — `SCRAP`, or `REPLACED_BY_SUPPLIER` where the lot went back to
the seller against a return authorisation. The four suppliers do not
disposition alike, because returning is a commercial question rather than a
quality one: SUP-1042 ships from Cleveland on a one-day domestic truck lane
and returned 2,572 of its 3,276 rejected pieces, where SUP-4077 ships ocean
from Sheffield and returned 244 of 4,368. Clause 5.4 of all four term sheets
— identically worded, so no supplier is advantaged by a hidden term — says a
returned piece is replaced at the seller's cost inside the contract year and
is not invoiced again, and that a scrapped piece is a loss with no credit.
QP-07 section 4 describes the two dispositions and stops there. Section 5 of
the finance policy charges disposal at USD 1.25 **per scrapped piece** and
says returned pieces carry no disposal charge.
*Correct attempt:* files every reject in `reject_rate_pct`, as the prompt
defines it, and grosses the purchase quantity up on the scrapped share alone —
0.391% for SUP-1042 against 1.820% rejected.
*Careless attempt:* grosses up on every reject, buys 7,203 pieces too many
from SUP-1042, charges it USD 8,843 of disposal it will never incur, and
awards SUP-4077. Measured 0.238 with 0 of 191 test-side decision points.

**0b. CRUX — the cube horizon is not the contract year.**
*Planted:* the offers run **1 April 2026 – 31 March 2027** (term-sheet header
block; section 6 of the finance policy states Cadence's fiscal year on the same
dates). `demand/forecast_2026.csv` is a raw cube dump on the cube's rolling
**fifteen-month** horizon, 2026-01 through 2027-03, carrying two S&OP cycles
and a `TOTAL` subtotal row per part and cycle. The three readings of the frozen
November cycle are all different numbers and only one of them is the contract
year: 493,000 pieces over April–March, 512,000 read as calendar 2026, 623,600
read whole. Nothing filters it and nothing errors.
*Correct attempt:* 493,000 good units.
*Careless attempt:* any other reading pushes SUP-4077's buy over its
520,000-piece rebate threshold, so a 4.0% rebate it has not earned appears and
the clause 4.1 shortfall charge disappears — a USD 43,000 swing that hands it
the award. Measured 0.212-0.221 on the four wrong readings, 0 of 191 decision
points.

**0c. CRUX — the inspection log is two populations.**
*Planted:* `quality/incoming_inspection_2025.jsonl` carries 33 `SOURCE`
records among the 260 `INCOMING` ones: pre-shipment inspections performed by a
Cadence supplier-quality engineer at the supplier's plant, 22 of them on
SUP-1042 lots at a 12.1% reject rate (SUP-2318 and SUP-3155 have a few as
well, so it is not a one-supplier gimmick). Every record is an SP-40 inspection
of a real lot, so reading the log as one population is the natural default.
The mechanics are recoverable and never assembled for the attempt: QP-07
section 5 says pieces failed at the seller's plant are scrapped or reworked
there at the seller's cost and that the seller makes the tendered quantity good
before the shipment is released, and that a lot released after source
inspection is inspected again at Aurora like any other. (Revision 8 removed the
sentence that went on to say those pieces are never received against a
purchase order and never invoiced — that was the conclusion, assembled.)
Every source record shares its `lot_id` with the incoming record of the same
lot, and half were keyed before that record and half after, so neither "keep
the first record per lot" nor "keep the last" gets it right.
*Correct attempt:* restricts the rates to `INCOMING` records — the pieces
Cadence paid for and dispositioned.
*Careless attempt:* pools the two, lifts the share of SUP-1042's inspected
pieces that Cadence scrapped from 0.391% to 2.54%, and awards SUP-4077.
Measured 0.115-0.127 with 0 of 191 decision points.

**0e. CRUX — a repeated inspection record is a duplicate or an addition.**
*Planted:* a lot can carry more than one `INCOMING` record for two different
reasons, and QP-07 section 2 describes both without saying what to do with
either: the same inspection keyed twice (thirteen lots, identical figures on
both records — twelve of them SUP-4077's returned or cleanest lots), and
pieces identified after the lot was first logged, keyed as a further record
against the same lot with the pieces newly rejected and **no inspected
quantity of its own** (nineteen records; 782 of SUP-4077's scrapped pieces sit
on them, against 176 of SUP-3155's and 28 of SUP-2318's). The data dictionary
says a record keyed for pieces found later carries no inspected quantity, and
stops there. Every such record is an ordinary-looking SP-40 incoming
inspection with a later date and its own QMS number.
*Correct attempt:* counts a repeat once and adds an addition to its lot —
which is what reading each record for what it is comes to.
*Careless attempt:* the **careful** one. An attempt that has read that
duplicates exist and deduplicates on `lot_id`, keeping the first record —
pandas' default — drops every addition, reads SUP-4077's scrap loss rate at
1.836% instead of 2.266%, buys 2,208 pieces too few from it and awards it the
contract. Measured 0.178 with 0 of 191 decision points. An attempt that does
not deduplicate at all double-counts SUP-4077's repeated lots, reads 2.054%,
and awards it too: 0.166. Keeping the last record instead drops the original
inspection of every supplemented lot, which keeps the winner but files
SUP-4077's record wrong: 0.570. The ground truth did not move by a cent: the
pieces were moved between records of the same lots.

**0d. CRUX — the ERP cutover breaks the receipt join without an error.**
*Planted:* purchasing and receiving moved to a new ERP on 2025-07-01
(`it/CHG-2025-0417_erp_cutover.md`). The 62 goods receipts posted from that
date carry the ERP's ten-digit purchase order number; the purchasing extract
carries the reporting mart's `PO-45xxx` numbers throughout. Both series appear
on `purchasing/po_reference_2025.csv`, which is an ordinary reference extract
(buyer, cost centre, commodity code, terms text) and is not labelled as a fix
for anything. A join of receipts to purchase orders on `po_id` matches every
pre-cutover receipt and silently matches nothing after it, so the lots received
after go-live drop out with no symptom. They are not a random sample:
SUP-3155's post-cutover lots run at 8.0% (named) and 14.2% (unnamed) against
2.4% before, and the return authorisations sit on the pre-cutover lots, so the
scrapped share collapses with them.
*Correct attempt:* checks that the join matched, resolves post-cutover
receipts through the reference extract, and attributes all 63 SUP-3155 lots.
*Careless attempt:* reads SUP-3155's scrapped share at 1.497% instead of
4.792%, and awards SUP-3155. Measured 0.120 with 0 of 191 decision points.

**1. Attribution off the free-text supplier field.**
*Planted:* the inspection log's `supplier` field is empty or `null` on 59 of
the incoming records and inconsistently spelled on the rest (the change record
explains why). Every lot is nonetheless attributable: `lot_id` → goods receipt
→ purchase order → the supplier master's `name_aliases` sheet → supplier code.
The blank-field lots carry SUP-3155's worst quality.
*Careless attempt:* groups on the field that is right there and awards
SUP-3155. Measured 0.120 with 0 of 191 decision points. It is independent of
0d: resolving the ERP numbers does not rescue the blank lots and vice versa.

**2. Which plan cycle is the plan.**
*Planted:* the dump carries the superseded October cycle beside the frozen
November one. The handover note designates the November cycle and says nothing
about a second cycle being in the file.
*Careless attempt:* plans on October, 537,300 pieces over the contract year,
crosses SUP-4077's threshold and awards it. Measured 0.221.

**3. Quoted prices are not comparable as quoted.**
The four offers are in four currencies and SUP-2318 quotes EUR 172.00 **per
100-piece box**. The finance memo mandates fixed FY2026 planning rates and
rules out the 2025 daily export, which is also shipped and averages below them.
*Careless attempt:* 2025 averages, awards SUP-3155, measured 0.339.

**4. Rejects are a purchase-quantity problem, not a line item.**
Clause 5.4 makes the buyer responsible for ordering enough to meet its net
good-unit requirement, and the demand column is explicitly labelled net good
units. Clause 5 separately states a *specification limit* and says in terms
that it is not a forecast. SUP-2318's clause 1 adds that partial boxes are not
tendered. *Careless attempt:* buys 493,000 from everyone and awards SUP-3155,
measured 0.269.

**5. Incoterms decide who pays freight.**
Two offers are FCA at the seller's works and two are DDP. The freight tariff
lists all four lanes with a neutral note that applicability depends on the
Incoterm. *Careless attempt:* charges nobody, awards SUP-4077, measured 0.406.

**6. Two rebate structures that do not pay what they appear to.**
SUP-2318's clause 4.2 is **banded** — each rate applies only to the volume
inside its band, USD 11,113 rather than USD 27,909 at a flat 3.0%. SUP-4077's
4.0% rebate is earned only at 520,000 pieces, and clause 4.1 separately commits
the buyer to that same 520,000 with a GBP 0.35 per-piece shortfall charge. The
correct buy, 504,431, sits 3.0% below it — so the threshold can only be
evaluated after 0a, 0b, 0c, 0d and 1 are all done right. *Careless attempts:*
0.430 and 0.406.

**7. The winner's edge is made of the terms a hurried model drops.**
SUP-1042 holds the **highest** quoted price of the four (USD 1.9450 against
USD 1.7905 for SUP-4077) and wins by USD 2,374.70, or 0.25%. Its Net 90 terms
are worth USD 14,242 against the Net 30 baseline at 9.0% WACC where SUP-4077's
Net 60 is worth USD 6,681, and SUP-4077's 1% 10 cash discount is a further trap
for the runner-up's total: at 9.0% the standard date is USD 2,010 cheaper, so a
model that takes a discount because one is offered mis-states it. Dropping
payment terms costs SUP-1042 the award (0.411); so does dropping disposal
(0.416), which is worth far more to SUP-4077 than to the winner.

**8. Coarse-fact shortcuts are dead by construction.** The winner is the most
expensive quote, not the cheapest; it is not the supplier with the lowest
reject rate (SUP-2318 is, at 1.250%); it is not the newest supplier; and it is
not the only DDP offer. Ranking on any single shipped number is wrong.

# Taxonomy tags

Objectives: cost modelling, total-cost-of-ownership comparison, supplier
selection, data reconciliation across systems, entity resolution, contract
interpretation, scope and period determination, quality-cost analysis,
working-capital valuation.

Reasoning phases scored by the rubric: explore, analyze, synthesize, recommend,
instruction_following.

Domain: business / operations / procurement finance. Formats: CSV, XLSX,
JSONL, Markdown, plain text.

# Expected difficulty range

Target band: **strong model mean reward at or under 0.6, weak model mean at or
under 0.35 over four trials each.**

Five revisions have missed the band, and each diagnosis was one layer short of
the last:

* **Revision 2** scored the weak model 0.889. Every planted trap was a
  documented step and the decision was one figure, so an attempt that never got
  a number right still collected it.
* **Revision 3** added population traps and made the decision three figures:
  0.778. The data dictionary still explained the traps, so three judgements had
  been written down as three instructions.
* **Revision 4** removed the instructions: 0.631. The attempt cleared every
  judgement and still reached the right supplier, because the omissions it did
  make happened to help the winner.
* **Revision 5** rebuilt the winner's edge out of exactly the terms a hurried
  cost model drops and thinned the margin to 0.24%: **0.594** (0.600 / 0.580 /
  0.607 / 0.590 over four trials). The scores are tight and high, which says
  the weak model was reaching the right supplier in every trial and losing
  points only on figures. Decision weight was that model's floor, not its risk.

**Revision 8 answers the weak-model sweep.** The sweep on revision 7 scored
the weak model 0.606, 0.241, 0.580 and 0.201: mean 0.407 against the 0.35
ceiling. Two trials at 0.6 are reachable only with all 191 decision points, so
the weak model was solving the whole task, all six layers, in half its trials
and landing on a decoy at `f` in the other half. Nothing about `f` or the
correct-decision score can move that mean; only the solve rate can, from one
half to about one third. So revision 8 plants a seventh independently decisive
judgement (0e above) whose careless path is the careful action, removes the two
sentences that had assembled a conclusion for the attempt — finance policy
section 6 no longer says not to present a case for any period but the contract
year, and QP-07 section 5 no longer says source-failed pieces are never
received or invoiced — and rewords the prompt's exclusions bullet so it asks
how the reject rates were built rather than what was set aside. Building the
layer also surfaced a convention bug: one revision-1 duplicate pair carried
different figures, so keep-first and keep-last had been producing different
`defect_rates.csv` files; a lot keyed twice now carries one set of figures.

**Revision 7's audit round.** The quality audit flagged six checks at 14.8% of
the suite against a 10% limit, and all six were fair. The exactly-one-award
check missed a joint award written in one sentence ("award SUP-1042 and
SUP-4077"); it now flags a second supplier in any awarding statement that is
not a comparison. The disposition-split check demanded two specific pooled
totals in one specific section; it now accepts any figure only a separated
disposition produces - pooled totals, any supplier's returned or scrapped
pieces, or any supplier's scrapped share - anywhere in the memo, and the
prompt now asks for "the lots or pieces involved". The exclusions check wanted
three reasoned topics without saying so; the floor is two, which is what the
prompt's wording ("the records set aside ... and anything else ... and why")
already requires. The three build-up checks matched an amount against at most
four rows; the matcher is now a subset-sum over cents with no cap, and the
prompt states the one limit that remains, sixteen rows per supplier. Nothing
of the answer moved; two receipt-join variants gained the 5-point disposition
check they had always deserved.

**Revision 7 measures rather than asserts.** No crux moved and no figure of
the answer changed; the work was on the harness and the verifier. The reference
solution and the provenance tooling dropped `openpyxl` for a standard-library
`.xlsx` reader, so a review sandbox that installs nothing can execute both. The
mutation harness stopped handing every simulated wrong attempt the reference's
own exclusion statistics and memo prose, so a variant that pooled the source
inspections no longer files a memo claiming it excluded them; that alone moved
the measured wrong paths down 1 to 2 points each. A spec-only harness and a
structural-floor probe were added, and a negative sweep that reformats a
*correct* answer six ways and requires all six to still score 1.000 - which
found and fixed a live 16-point defect. On the verifier, eleven thin contract
checks were merged into three, taking the weight spread from 52:1 to 57:2, and
the pooled decision share to 47.0%.

**Revision 6 attacks the floor.** Two new judgements were planted, both of the
kind that is hard to *notice* rather than hard to execute, and both silent:
what a rejected piece actually costs, and which months of a rolling cube the
contract covers. The prices were retuned around them so that **every one of the
six judgements flips the award on its own**, and so that the winner sits
**third or fourth** on the uncorrected views rather than second. Decision
weight moved from the bottom of the permitted band to the top — 47.0% of
positive weight pooled across the decision tests and the rubric's
recommendation criteria — because the decision is now the hard part rather
than the banked part.

Measured against the shipped verifier by mutating the reference solution, one
omission per row:

| Single omission | Lands on | Contract qty | Contract cost | Tests | Decision |
| --- | --- | --- | --- | --- | --- |
| grosses the buy up on every reject, not the scrapped share | SUP-4077 | 505,123 | USD 955,030.16 | 0.238 | 0 / 191 |
| pools the SOURCE inspections (dedupe keeps first record) | SUP-4077 | 502,223 | USD 947,374.09 | 0.127 | 0 / 191 |
| pools the SOURCE inspections (dedupe keeps last record) | SUP-4077 | 506,860 | USD 959,615.88 | 0.127 | 0 / 191 |
| pools the SOURCE inspections, no dedupe | SUP-4077 | 503,340 | USD 950,323.00 | 0.115 | 0 / 191 |
| dedups on lot_id, keeps the first record (drops the additions) | SUP-4077 | 502,223 | USD 947,374.09 | 0.178 | 0 / 191 |
| dedups on lot_id, keeps the last record | SUP-1042 | 494,936 | USD 950,828.57 | 0.570 | 170 / 191 |
| does not dedup at all (double-counts the repeats) | SUP-4077 | 503,340 | USD 950,323.00 | 0.166 | 0 / 191 |
| joins receipts without the ERP number reference | SUP-3155 | 500,493 | USD 917,735.67 | 0.120 | 0 / 191 |
| attributes lots on the free-text supplier field | SUP-3155 | 500,359 | USD 917,324.96 | 0.120 | 0 / 191 |
| plans on calendar 2026 instead of the contract year | SUP-4077 | 523,871 | USD 944,979.72 | 0.212 | 0 / 191 |
| plans on the whole fifteen-month cube horizon | SUP-4077 | 638,058 | USD 1,149,594.12 | 0.212 | 0 / 191 |
| counts the TOTAL subtotal rows as well | SUP-4077 | 1,142,489 | USD 2,053,499.37 | 0.221 | 0 / 191 |
| plans on the superseded October S&OP cycle | SUP-4077 | 549,758 | USD 991,367.89 | 0.221 | 0 / 191 |
| no yield gross-up | SUP-3155 | 493,000 | USD 894,770.00 | 0.269 | 8 / 191 |
| 2025 average FX instead of planning rates | SUP-3155 | 517,815 | USD 876,622.61 | 0.339 | 0 / 191 |
| charges no inbound freight | SUP-4077 | 504,431 | USD 917,706.27 | 0.406 | 0 / 191 |
| re-rates SUP-2318's whole year at 3.0% | SUP-2318 | 498,500 | USD 945,933.68 | 0.430 | 0 / 191 |
| treats SUP-4077's rebate as earned, no shortfall | SUP-4077 | 504,431 | USD 910,145.26 | 0.406 | 0 / 191 |
| misses the shortfall charge alone (clause 4.1) | SUP-4077 | 504,431 | USD 946,271.95 | 0.406 | 0 / 191 |
| ignores payment terms | SUP-4077 | 504,431 | USD 959,884.23 | 0.411 | 0 / 191 |
| ignores scrap disposal | SUP-4077 | 504,431 | USD 938,914.51 | 0.416 | 0 / 191 |
| ignores SUP-2318's whole-box rule | SUP-1042 | 494,936 | USD 950,828.57 | 0.800 | 191 / 191 |
| multiplies by the 4-dp rounded price | SUP-1042 | 494,936 | USD 950,828.57 | 0.825 | 170 / 191 |
| reference solution | SUP-1042 | 494,936 | USD 950,828.57 | 1.000 | 191 / 191 |

And the same measurement for attempt profiles - a competent attempt that
does every documented step and misses one or two judgements:

| Attempt profile | Lands on | Contract qty | Contract cost | Tests | Decision |
| --- | --- | --- | --- | --- | --- |
| reads the log as one reject population (the default) | SUP-4077 | 505,123 | USD 955,030.16 | 0.238 | 0 / 191 |
| one reject population, pools SOURCE records | SUP-4077 | 502,909 | USD 949,185.15 | 0.115 | 0 / 191 |
| one reject population, calendar-2026 window | SUP-4077 | 524,591 | USD 947,149.52 | 0.200 | 0 / 191 |
| pools SOURCE, joins receipts on po_id as it stands | SUP-3155 | 500,266 | USD 917,039.92 | 0.135 | 8 / 191 |
| free-text attribution, October plan cycle | SUP-4077 | 549,387 | USD 990,249.84 | 0.091 | 0 / 191 |
| every judgement right, whole-box rule and rounded price missed | SUP-1042 | 494,936 | USD 950,828.57 | 0.692 | 170 / 191 |
| every judgement right, payment terms and disposal missed | SUP-4077 | 504,431 | USD 945,595.48 | 0.382 | 0 / 191 |
| every judgement right, cube horizon not trimmed | SUP-4077 | 638,058 | USD 1,149,594.12 | 0.212 | 0 / 191 |
| every judgement right, then dedups on lot_id to be safe | SUP-4077 | 502,223 | USD 947,374.09 | 0.178 | 0 / 191 |

And the spec-only path: an attempt that does everything a shipped document
instructs and forms none of the judgements no document makes for it. It is
given both reconciliations a document states as a fact, so the figure is an
upper bound on what reading rather than analysing can reach:

| Spec-only path | Lands on | Contract qty | Contract cost | Tests | Decision |
| --- | --- | --- | --- | --- | --- |
| spec-only: every documented step, no judgement of its own | SUP-4077 | 636,134 | USD 1,143,795.94 | 0.077 | 0 / 191 |
| spec-only, but reads the cube over calendar 2026 | SUP-4077 | 522,291 | USD 940,218.23 | 0.077 | 0 / 191 |

**Thirty of the thirty-four mutations land on a different supplier, at 0.077
to 0.430 test-side with at most 8 of 191 decision points.** The four that do
not are SUP-2318's whole-box rule, the 4-dp rounded price and keeping the last
record of a repeated lot, none of which changes a figure of the winner's, and
the reference itself. The highest any
wrong-supplier route reaches is 0.430, and that is an attempt that got all seven
judgements and every other cost term right and misread one rebate clause.

Across those thirty wrong-decision paths the score cap is **max 0.430,
mean 0.228**. Read through `mean = q**k + (1 - q**k) * f`, with `k = 7`
independently decisive judgements, that puts the strong ceiling of 0.60 at
`q <= 0.901` per layer and the weak ceiling of 0.35 at `q <= 0.768`. **The weak
ceiling is the binding one**, and it is the one a model sweep still has to
settle: it requires a weak attempt to miss roughly one layer in four. The revision-7
sweep measured the weak model solving all six layers in two trials of four,
which is `q**6 = 0.5`, `q = 0.89`. At that `q` a seventh independent layer
takes the solve rate to 0.45 and the mean to about 0.39; the seventh layer
shipped in revision 8 is built so that its careless path is the careful action,
which is where a weak attempt's `q` should be lowest. If the sweep comes back
over 0.35 again the answer is an eighth layer of the same kind, not another
reweighting - reweighting moves `f` by hundredths.

What a well-formed but analytically empty answer banks is **measured, not
asserted**: `verify_design.py` files a structurally perfect set of deliverables
with naive figures behind every one of them - prices as the clauses quote them,
the whole fifteen-month cube as the requirement, no gross-up, freight, rebate,
terms or disposal - and it scores **0.050**, 21 of the 416 test-side positive
weight, on file shape, the self-consistency checks and the three memo checks
that do not turn on a figure. Seven sentinel checks worth 77 points name the
corrections one at a time and are earned only by an attempt that made them.

The verifier is also checked in the other direction, against a **correct**
answer written down the way some other competent attempt would write it:
re-wrapped at 34 columns, money as `$1,234.56`, totals rounded to the whole
dollar, CRLF line endings, the legal names in another house style, and the cost
build-up itemised into finer elements. All six score 1.000. The last of them
found a live defect - the build-up checks matched each element against a single
filed row, so an attempt that split inbound freight into the lane tariff and the
brokerage, which the prompt's own "give each element its own row" rule
encourages, lost 16 points on an analytically perfect answer. The checks now
match an amount against any subset of the rows filed, which changed no mutation
score.

The floor is protected: three test penalties total -15 against 416 positive
weight, and none fires on a merely incomplete answer. Every one is written to
pass only when its specific defect is present, so all three correctly decline
to fire on the reference solution.

Risk of being too hard is bounded, and deliberately so: the deliverables are
four plain files; the environment preinstalls what is needed to open every
shipped format; every population the attempt has to reason about is described
in a shipped document and every date, rate and clause it needs is stated
somewhere in `/workspace/data`; and the reference solution runs from the
shipped inputs with the standard library alone. Nothing an analyst
would obviously have is withheld — what is withheld is the conclusion.

# Ground truth recommendation and rationale

**Award the FY2026 SP-40 contract to SUP-1042, Meridian Precision Works, LLC:
494,936 pieces for USD 950,828.57.**

FY2026 good-unit requirement: 493,000 SP-40 pieces — the twelve monthly SP-40
rows of the frozen November 2025 S&OP cycle that fall in the contract year
1 April 2026 – 31 March 2027.

| rank | supplier | quoted USD/piece | rejected | scrapped | units to buy | FY2026 total USD | USD/good unit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | SUP-1042 | 1.9450 | 1.820% | 0.391% | 494,936 | 950,828.57 | 1.9287 |
| 2 | SUP-4077 | 1.7905 | 2.400% | 2.266% | 504,431 | 953,203.26 | 1.9335 |
| 3 | SUP-2318 | 1.8662 | 1.250% | 1.100% | 498,500 | 962,729.48 | 1.9528 |
| 4 | SUP-3155 | 1.8285 | 6.100% | 4.792% | 517,815 | 970,826.72 | 1.9692 |

Margin over the runner-up: **USD 2,374.70**, or 0.25%.

The figures that force it: SUP-1042 is DDP, so it carries no inbound freight
where SUP-2318 and SUP-4077 carry USD 36,667 and USD 35,497; it returns four
fifths of what it fails, so only 0.391% of its inspected pieces are a loss and
its buy is 22,879 pieces below SUP-3155's; it has no volume commitment, where
SUP-4077 owes USD 6,931 in shortfall charges and earns none of its 4.0%
rebate; and its Net 90 terms are worth USD 14,242 against the Net 30 baseline
at 9.0% WACC where SUP-4077's Net 60 is worth USD 6,681. The shortfall charge,
the payment-terms gap and the disposal gap are each larger than the USD 2,375
margin.

Why the plausible wrong answers are wrong:

- **SUP-4077** is the cheapest quote and appears to carry a 4.0% rebate plus a
  1% 10 cash discount. At 504,431 pieces it misses its own 520,000-piece
  rebate threshold entirely and owes GBP 0.35 per piece on the 15,569-piece
  shortfall, USD 6,931; the discount is not worth taking. Its buyer-paid UK
  freight adds USD 35,497 back. It finishes second by USD 2,375 — and it wins
  every analysis that grosses the buy up on every reject, pools the source
  inspections, mis-cuts the demand window, reads clause 4.2 without clause 4.1,
  or leaves payment terms or disposal out of the cost build-up.
- **SUP-3155** is DDP with Net 60 terms, so it wins every analysis that skips
  the yield gross-up, that loses its post-cutover lots to the ERP renumbering,
  that reads the inspection log off the free-text supplier field, or that
  restates the offers at 2025 average FX. Read correctly, 4.792% of its
  inspected pieces were scrapped, which forces a 517,815-piece buy and USD
  31,019 of disposal, putting it last.
- **SUP-2318** has the best incoming reject rate at 1.250%, and wins if its
  banded rebate is re-rated at a flat 3.0%. Read correctly the rebate is USD
  11,113 rather than USD 27,909, and its buyer-paid German freight of USD
  36,667 leaves it third.

Determinism: every figure follows from the shipped files plus the mandated
planning constants in the finance memo, with intermediates carried unrounded
and only the reported figure rounded, as `instruction.md` states. Using the
clause 5 specification limits in place of observed 2025 performance is a
conservative reading rather than an error; its figures differ throughout, and
the prompt asks for the observed record.

# Expected reasoning trajectory

A golden solution is included (`solution/solve.py`, `solution/solve.sh`,
`solution/gold.patch`). The reasoning path it encodes:

1. Inventory `/workspace/data`, read the data dictionary, the change record,
   the four term sheets and the finance memo, and notice that the four offers
   differ in currency, unit of measure, Incoterm, payment terms, volume
   structure — and that they all run 1 April 2026 to 31 March 2027.
2. Establish scope from the demand dump: keep the frozen November cycle, filter
   to SP-40, drop the `TOTAL` subtotal rows, and cut the cube's fifteen-month
   horizon down to the contract year → 493,000 good units.
3. Resolve supplier identity: load the supplier master, build the alias → code
   map, and map every purchase order to a supplier code.
4. Build `lot_id → purchase order → supplier code` from the goods receipts,
   checking that the join actually matches and resolving post-cutover receipts
   through the purchase-order reference extract, so that every inspection lot
   is attributed by key rather than by name.
5. Restrict the inspection log to `INCOMING` records, deduplicate on `lot_id`,
   drop the non-candidate SUP-9001, and aggregate lots, inspected pieces,
   rejected pieces and — separately — the pieces dispositioned `SCRAP`.
6. Recognise from clause 5.4 that a returned piece is replaced free inside the
   contract year and a scrapped one is not, so the buy is
   `ceil(493,000 / (1 − scrapped share))`, and round SUP-2318 up to whole boxes.
7. Price each offer: convert at the mandated planning rates, divide SUP-2318's
   box price by 100, add the lane tariff plus brokerage over twelve shipments
   for the two FCA suppliers only, apply each rebate as its clause actually
   reads, add SUP-4077's shortfall charge, add disposal at USD 1.25 per scrapped
   piece, and value payment terms against Net 30 at 9.0% WACC, checking
   SUP-4077's cash discount against its standard date and finding it is not
   worth taking.
8. Rank on cost per good unit, write the three CSVs, and write the memo: the
   decision with its three figures, the comparison, the basis, the exclusions
   and the risks.

The verifier is 41 checks (38 positive, 3 penalties) driven by
`tests/test_weights.json`; the rubric is 50 criteria (48 positive, 2
penalties). Every criterion names the exact figure or claim it grades against a
deliverable `instruction.md` asks for. Local checks: the nop agent scores
0.000, the oracle scores 1.000 (416 of 416 positive weight, with only the three
penalty checks correctly declining to fire), and
`solution/_provenance/verify_design.py` reproduces every table above - the
mutation sweep, the attempt profiles, the spec-only path, the structural floor
and the negative sweep - reading only `environment/data/` and the shipped
verifier, with the standard library alone.
