# Gold solution — FY2026 valve-seat sourcing award

Never staged into the environment image; the attempt cannot see any of this.

## Files

- `solve.py` — the analysis. Reads only `/workspace/data`, writes the three
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
  - `generate_data.py` — seeded generator that builds the inspection log, the
    goods receipts, the demand dump, the purchase-order reference extract, the
    IT change record, QP-07 and the data dictionary from the revision-1
    extracts kept in `v1_inputs/`. Re-running reproduces `environment/data/`
    byte for byte. Its documents describe the systems and decide nothing: any
    wording that tells the attempt what to exclude turns a judgement into a
    checklist item, which is what put the earlier revisions out of band.
  - `verify_design.py` — re-derives the ground truth from the shipped files
    with its own pipeline, checks `solve.py` against it, then runs the
    single-omission sweep through `tests/test.sh` and prints the Measured
    table quoted in `task_card.md`.
  - `make_gold_patch.py` — regenerates `gold.patch`.

`solve.py` runs on the environment image as built: it needs only the standard
library plus `openpyxl`, which the Dockerfile preinstalls.

## Ground truth

**Award the FY2026 SP-40 contract to SUP-1042, Meridian Precision Works, LLC:
495,010 pieces for USD 959,812.87.**

| supplier | reject rate | units to buy | FY2026 total USD | USD / good unit | rank |
| --- | --- | --- | --- | --- | --- |
| SUP-1042 | 1.820% | 495,010 | 959,812.87 | 1.9749 | 1 |
| SUP-4077 | 2.400% | 497,951 | 962,135.40 | 1.9797 | 2 |
| SUP-2318 | 1.250% | 492,200 | 972,920.77 | 2.0019 | 3 |
| SUP-3155 | 6.100% | 517,572 | 997,031.30 | 2.0515 | 4 |

FY2026 good-unit requirement: 486,000 SP-40 pieces (the frozen November S&OP
cycle). Winning margin over the runner-up: USD 2,322.53, or 0.24%.

SUP-1042 holds the **highest** quoted price of the four (USD 1.9450 per piece
against USD 1.8254 for SUP-4077) and still wins on total cost. The margin is
deliberately a quarter of a percent, and the winner's edge is built from the
terms a hurried cost model drops: its Net 90 payment terms are worth USD
14,244 against SUP-4077's USD 6,724, and its scrap bill is USD 3,676 smaller.
Leave out payment terms, leave out scrap, stop at clause 4.2 without clause
4.1, or re-rate SUP-2318's rebate at a flat 3.0%, and the award goes
elsewhere. Every route that skips part of the analysis lands somewhere else —
that is the point of the task, and `_provenance/verify_design.py` measures
each route against the shipped verifier.

## What the analysis has to get right

1. **Which inspection records count.** The QMS log pools `SOURCE` records
   (pre-shipment inspections at the supplier's plant, 33 of them, 22 on
   SUP-1042 lots at a 12% reject rate) with the `INCOMING` ones. Source rejects
   are replaced before shipment and never received or invoiced, and the same
   lot is inspected again on receipt (QP-07 sections 4 and 5 state the
   mechanics; nothing states the conclusion). Only `INCOMING` records enter the
   reject rates. Pooling lifts SUP-1042 to about 3.7% and hands the award to
   SUP-4077; no deduplication rule rescues it, because half the source records
   were keyed before their incoming twin and half after.
2. **Lot attribution across the ERP cutover.** Attribution runs
   `lot_id → goods receipt → purchase order → alias table → supplier code`.
   Receipts posted from 2025-07-01 carry the ERP's ten-digit purchase order
   number (CHG-2025-0417); the purchasing extract carries mart numbers. The
   reference extract resolves them. Joining without it silently drops every
   post-cutover lot, and those carry most of SUP-3155's rejects: its rate
   reads 3.42% instead of 6.10% and the award flips to SUP-3155. No shipped
   document says the join needs resolving; the change record states only that
   receipts carry the posting system's number and that both series appear on
   the reference extract.
3. **Lot attribution off the free-text field.** The log's `supplier` field is
   blank on a large minority of lots. Attributing on it drops them, and they
   are not randomly distributed: SUP-3155 again reads about 3.4% and wins.
4. **Scope of demand.** The cube dump carries the superseded October cycle
   (538,600 pieces) beside the frozen November one (486,000), a `TOTAL` row
   per part and cycle, and SP-22. Only the twelve November SP-40 rows count.
   Any of the other readings pushes the buy past 520,000 pieces and hands
   SUP-4077 a rebate it does not earn.
5. **Deduplication.** Repeated `INCOMING` records share a `lot_id`. One
   physical lot each.
6. **Yield gross-up.** Rejects are scrapped with no credit and no replacement
   (clause 5.4 of every term sheet), so purchase quantity is
   `ceil(good_units / (1 − reject_rate))`, and for SUP-2318 rounded up to a
   whole 100-piece box (clause 1: partial boxes are not tendered), 492,200.
7. **Unit of measure and FX.** SUP-2318 quotes per 100-piece box. Conversions
   use the mandated FY2026 planning rates, not the 2025 daily export.
8. **Incoterms.** SUP-2318 and SUP-4077 are FCA origin, so Cadence pays the
   lane tariff plus brokerage on twelve shipments. SUP-1042 and SUP-3155 are
   DDP and carry no separate freight.
9. **Rebates.** SUP-2318's rebate is banded — each rate applies only to the
   volume inside its band, USD 11,010.75 rather than USD 28,197.15 at a flat
   3.0%; the flat reading hands SUP-2318 the award. SUP-4077's 4.0% rebate is
   earned only at 520,000 pieces; the buy is 497,951, so it earns nothing and
   additionally owes the clause 4.1 shortfall charge on 22,049 pieces, USD
   9,816.21 — larger than the winning margin, so clause 4.1 decides the award
   by itself.
10. **Payment terms.** Valued against a Net 30 baseline at 9.0% WACC on the
    invoiced spend. SUP-1042's Net 90 is worth USD 14,244.08; SUP-4077's 1% 10
    Net 60 is worth USD 6,723.99 on the standard date, and taking the discount
    would cost USD 2,071.99 more (finance memo, section 3: plan on whichever
    is cheaper). Leaving payment terms out of the model hands SUP-4077 the
    award.
11. **Scrap.** USD 1.25 per rejected piece at incoming (finance memo, section
    5): USD 11,262.50 for SUP-1042 against USD 14,938.75 for SUP-4077. Leaving
    it out hands SUP-4077 the award.

## What the memo has to disclose

`instruction.md` asks each memo section for the basis behind its figures, not
just the figures: the build-up of every supplier's FY2026 total (every element
charged, labelled, in US dollars, adding to the filed total); which inspection
records were counted and which set aside, with the reason; where the good-unit
requirement came from and how each purchase quantity follows from it; and the
basis on which quoted prices were restated. That is a duty to disclose method,
never a list of the method's steps — nothing tells the attempt which records to
set aside, which purchase-order numbers need resolving, or which plan cycle is
the plan of record beyond the handover note's designation.

It exists for two reasons. It makes the rubric gradable from the deliverable:
every criterion scores a disclosure the prompt asks for by name, which is what
the audit failed the previous revision for. And it exposes the whole cost model
to checking, so an attempt that never computes scrap or the working-capital
value of payment terms cannot hide that behind a fluent memo.

## Regenerating

    python solution/_provenance/generate_data.py      # needs openpyxl
    python solution/_provenance/verify_design.py      # re-derive + sweep
    python solution/_provenance/make_gold_patch.py

If the dataset is regenerated, the constants at the top of
`tests/test_outputs.py` must be re-read from `verify_design.py`'s
re-derivation, and `task_card.md`'s Measured table from its sweep.

## Notes

- Contract commercial terms are transcribed into `CONTRACTS` in `solve.py`
  with the governing clause cited, exactly as an analyst reading the four term
  sheets would record them. Every other figure is computed from the data.
- Using the clause 5 specification limits instead of observed 2025 performance
  also reaches SUP-1042. That is a defensible conservative reading rather than
  an error, and the decision is stable under it; the figures are not, and
  `instruction.md` asks for the observed record.
