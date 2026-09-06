# Gold solution — FY2026 valve-seat sourcing award

Never staged into the environment image; the attempt cannot see any of this.

## Files

- `solve.py` — the analysis. Reads only `/workspace/data`, writes the four
  graded deliverables to `/workspace/output`. Deterministic: no network, no
  clock, no randomness, no reliance on file ordering. Each analysis step takes
  its choices as keyword arguments whose defaults are the correct reading of
  the data, so the provenance tooling can re-run it with one wrong choice at a
  time.
- `solve.sh` — entry point for the oracle run. Locates itself, creates the
  output directory and runs `solve.py`.
- `gold.patch` — unified diff from the fresh workspace to the solved state.
  Regenerate with `_provenance/make_gold_patch.py`; do not hand-edit.
- `_provenance/` — never copied into the environment image:
  - `generate_data.py` — seeded generator that builds the inspection log with
    its two populations and its reject dispositions, the goods receipts across
    the ERP renumbering, the fifteen-month two-cycle demand dump, the
    purchase-order reference extract, the IT change record, QP-07 and the data
    dictionary. The inspection and receipt extracts start from the revision-1
    files kept in `v1_inputs/`; the demand series is authored in the generator
    itself. Re-running reproduces `environment/data/` byte for byte. Its documents describe the systems and decide nothing: any
    wording that tells the attempt what to exclude turns a judgement into a
    checklist item, which is what put the earlier revisions out of band.
  - `verify_design.py` — re-derives the ground truth from the shipped files
    with its own pipeline, checks `solve.py` against it, then runs the
    single-omission sweep through `tests/test.sh` and prints the Measured
    tables quoted in `task_card.md`.
  - `make_gold_patch.py` — regenerates `gold.patch`.

`solve.py` and `verify_design.py` need only the CPython standard library - no
openpyxl, no pandas, no numpy. The supplier master is read straight out of the
`.xlsx` zip with `zipfile` and `xml.etree`. The environment image still
preinstalls pandas and openpyxl for the attempt's own use; the reference
solution deliberately does not rely on them, so a review sandbox that installs
nothing can still execute it. `generate_data.py` is the one exception: it
*writes* the workbook and needs openpyxl, and it is an authoring tool that no
grading or review path runs.

## Ground truth

**Award the FY2026 SP-40 contract to SUP-1042, Meridian Precision Works, LLC:
494,936 pieces for USD 950,828.57.**

| supplier | rejected | scrapped | units to buy | FY2026 total USD | USD / good unit | rank |
| --- | --- | --- | --- | --- | --- | --- |
| SUP-1042 | 1.820% | 0.391% | 494,936 | 950,828.57 | 1.9287 | 1 |
| SUP-4077 | 2.400% | 2.266% | 504,431 | 953,203.26 | 1.9335 | 2 |
| SUP-2318 | 1.250% | 1.100% | 498,500 | 962,729.48 | 1.9528 | 3 |
| SUP-3155 | 6.100% | 4.792% | 517,815 | 970,826.72 | 1.9692 | 4 |

FY2026 good-unit requirement: 493,000 SP-40 pieces — the frozen November S&OP
cycle read over the contract year the four offers run for, 1 April 2026 to
31 March 2027. Winning margin over the runner-up: USD 2,374.70, or 0.25%.

SUP-1042 holds the **highest** quoted price of the four (USD 1.9450 per piece
against USD 1.7905 for SUP-4077) and still wins on total cost. Every single
judgement in the list below flips the award when it is missed, and on any
uncorrected view SUP-1042 is third or fourth rather than second — there is no
wrong-but-close ranking a second look repairs.
`_provenance/verify_design.py` measures each route against the shipped
verifier.

## What the analysis has to get right

1. **Which rejected pieces are actually a loss.** Every incoming reject carries
   a `disposition`: `SCRAP`, or `REPLACED_BY_SUPPLIER` where the lot went back
   to the seller against a return authorisation. Clause 5.4 of every term sheet
   says a returned piece is replaced at the seller's cost inside the contract
   year and is not invoiced again; a scrapped piece is a loss with no credit.
   The mix differs sharply by lane — SUP-1042 returns 2,572 of 3,276 on a
   one-day domestic truck movement, SUP-4077 244 of 4,368 across an ocean lane
   — so the purchase quantity is grossed up on the scrapped share (0.391%
   against 1.820% rejected for SUP-1042) and disposal is charged on the same
   pieces. `defect_rates.csv` still reports every reject, which is what the
   prompt defines `reject_rate_pct` to be. Grossing up on every reject buys
   7,203 pieces too many from SUP-1042 and hands the award to SUP-4077.
2. **Which months the contract covers.** The offers run 1 April 2026 to
   31 March 2027 (term-sheet header block; finance policy section 6). The
   planning-cube dump is the cube's rolling fifteen-month horizon, 2026-01 to
   2027-03, carrying two S&OP cycles and a `TOTAL` row per part and cycle. The
   frozen November cycle reads 493,000 over the contract year, 512,000 as
   calendar 2026 and 623,600 whole. Every wrong reading pushes SUP-4077's buy
   over its 520,000-piece rebate threshold, which is worth about USD 43,000 to
   it, and hands it the award.
3. **Which inspection records count.** The QMS log pools `SOURCE` records
   (pre-shipment inspections at the supplier's plant, 33 of them, 22 on
   SUP-1042 lots at a 12.1% reject rate) with the `INCOMING` ones. Pieces
   failed at source are dealt with at the seller's cost and never received or
   invoiced, and the same lot is inspected again on receipt (QP-07 sections 4
   and 5 state the mechanics; nothing states the conclusion). Only `INCOMING`
   records enter the rates. Pooling lifts SUP-1042's scrapped share to 2.54%
   and hands the award to SUP-4077; no deduplication rule rescues it, because
   half the source records were keyed before their incoming twin and half
   after.
4. **Lot attribution across the ERP cutover.** Attribution runs
   `lot_id → goods receipt → purchase order → alias table → supplier code`.
   Receipts posted from 2025-07-01 carry the ERP's ten-digit purchase order
   number (CHG-2025-0417); the purchasing extract carries mart numbers. The
   reference extract resolves them. Joining without it silently drops every
   post-cutover lot, and those carry most of SUP-3155's scrap: its scrapped
   share reads 1.497% instead of 4.792% and the award flips to SUP-3155.
5. **Lot attribution off the free-text field.** The log's `supplier` field is
   blank on a large minority of lots. Attributing on it drops them, and they
   are not randomly distributed: SUP-3155 again reads about 1.5% and wins.
6. **Which plan cycle is the plan.** The dump carries the superseded October
   cycle beside the frozen November one; only the November cycle counts.
7. **Deduplication.** Repeated `INCOMING` records share a `lot_id`. One
   physical lot each.
8. **Unit of measure and FX.** SUP-2318 quotes per 100-piece box, and its buy
   is rounded up to a whole box (clause 1: partial boxes are not tendered).
   Conversions use the mandated FY2026 planning rates, not the 2025 daily
   export.
9. **Incoterms.** SUP-2318 and SUP-4077 are FCA origin, so Cadence pays the
   lane tariff plus brokerage on twelve shipments. SUP-1042 and SUP-3155 are
   DDP and carry no separate freight.
10. **Rebates.** SUP-2318's rebate is banded — each rate applies only to the
    volume inside its band, USD 11,113.22 rather than USD 27,909.02 at a flat
    3.0%. SUP-4077's 4.0% rebate is earned only at 520,000 pieces; the buy is
    504,431, so it earns nothing and additionally owes the clause 4.1 shortfall
    charge on 15,569 pieces, USD 6,931.32 — larger than the winning margin, so
    clause 4.1 decides the award by itself.
11. **Payment terms.** Valued against a Net 30 baseline at 9.0% WACC on the
    invoiced spend. SUP-1042's Net 90 is worth USD 14,241.95; SUP-4077's 1% 10
    Net 60 is worth USD 6,680.96 on the standard date, and taking the discount
    would cost USD 2,058.73 more (finance memo, section 3: plan on whichever is
    cheaper). Leaving payment terms out hands SUP-4077 the award.
12. **Disposal.** USD 1.25 per **scrapped** piece (finance memo, section 5):
    USD 2,420.00 for SUP-1042 against USD 14,288.75 for SUP-4077. Leaving it
    out hands SUP-4077 the award.

## The cost model is a deliverable

`cost_buildup.csv` takes one row per cost element the attempt charged each
supplier — the attempt's own labels, bound only by the rule that a supplier's
elements sum to the total it filed in `supplier_costs.csv`. Nothing in the
prompt says what the elements are, so it stays a disclosure duty rather than
the specification that made revisions 2 and 3 solvable by transcription.

It is there for two reasons. The verifier and the rubric can grade the whole
cost model as data rather than as prose, which is what the audit kept failing:
regex proxies over a memo are never objective enough. And an attempt that never
separated the scrapped rejects from the returned ones has no row carrying USD
2,420.00 for SUP-1042, so it fails the build-up file as well as every total
that depends on it.

## What the memo has to disclose

What is left in the memo is what prose is good for and a test can settle from
the file: which inspection records were counted towards the reject rates and
which were set aside, with the reason; how the rejected pieces were
dispositioned and how many went back to the seller; where in the demand data
the good-unit requirement came from and what period it covers; why each
supplier that lost loses. Nothing tells the attempt which records to set aside,
which purchase-order numbers need resolving, which months to keep, or which
plan cycle is the plan of record beyond the handover note's designation.

## Regenerating

    python solution/_provenance/generate_data.py      # needs openpyxl
    python solution/_provenance/verify_design.py      # re-derive + sweep
    python solution/_provenance/make_gold_patch.py

If the dataset is regenerated, the constants at the top of
`tests/test_outputs.py` must be re-read from `verify_design.py`'s
re-derivation, and `task_card.md`'s Measured tables from its sweep.

## Notes

- Contract commercial terms are transcribed into `CONTRACTS` in `solve.py`
  with the governing clause cited, exactly as an analyst reading the four term
  sheets would record them. Every other figure is computed from the data.
- Using the clause 5 specification limits instead of observed 2025 performance
  also reaches SUP-1042. That is a defensible conservative reading rather than
  an error, and the decision is stable under it; the figures are not, and
  `instruction.md` asks for the observed record.
- Disposal is charged on `units_to_purchase − good_units`, which is the whole
  number of pieces the gross-up buys to cover scrap. Computing it instead as
  `units × scrapped share` differs by less than one piece and so by less than
  a dollar, inside every tolerance the verifier applies.
