# Gold solution — FY2026 valve-seat sourcing award

Never staged into the environment image; the attempt cannot see any of this.

## Files

- `solve.py` — the analysis. Reads only `/workspace/data`, writes the three
  graded deliverables to `/workspace/output`. Deterministic: no network, no
  clock, no randomness, no reliance on file ordering.
- `solve.sh` — entry point for the oracle run. Locates itself, creates the
  output directory and runs `solve.py`.
- `gold.patch` — unified diff from the fresh workspace to the solved state.

`solve.py` runs on the environment image as built: it needs only the standard
library plus `openpyxl`, which the Dockerfile preinstalls.

## Ground truth

**Award the FY2026 SP-40 contract to SUP-1042, Meridian Precision Works, LLC.**

| supplier | reject rate | units to buy | FY2026 total USD | USD / good unit | rank |
| --- | --- | --- | --- | --- | --- |
| SUP-1042 | 1.820% | 495,010 | 963,017.63 | 1.9815 | 1 |
| SUP-4077 | 2.400% | 497,951 | 976,373.13 | 2.0090 | 2 |
| SUP-2318 | 1.250% | 492,152 | 978,217.33 | 2.0128 | 3 |
| SUP-3155 | 6.100% | 517,572 | 987,625.94 | 2.0322 | 4 |

FY2026 good-unit requirement: 486,000 SP-40 pieces. Winning margin over the
runner-up: USD 13,355.50, or 1.39%.

SUP-1042 holds the **highest** quoted price of the four (USD 1.9450 per piece
against USD 1.8889 for SUP-4077) and still wins on total cost. Every route that
skips part of the analysis lands somewhere else — that is the point of the
task, and `tools/model_check.py` in the authoring repo enumerates the routes.

## What the analysis has to get right

1. **Scope.** FY2026 demand is the twelve monthly SP-40 rows, 486,000 pieces.
   The planning-cube extract also carries `TOTAL` subtotal rows and a second
   part, SP-22. Counting either inflates demand; pushing the buy above 520,000
   pieces flips the answer to SUP-4077.
2. **Lot attribution.** The inspection log's free-text `supplier` field is
   blank on a large minority of lots. Attribution runs
   `lot_id → goods receipt → purchase order → alias table → supplier code`.
   Using the free-text field drops those lots, and they are not randomly
   distributed: SUP-3155's reject rate reads 3.05% instead of 6.10% and the
   award flips to SUP-3155.
3. **Deduplication.** Repeated inspection records share a `lot_id`. One
   physical lot each.
4. **Yield gross-up.** Rejects are scrapped with no credit and no replacement
   (clause 5.4 of every term sheet), so purchase quantity is
   `ceil(good_units / (1 − reject_rate))`.
5. **Unit of measure and FX.** SUP-2318 quotes per 100-piece box. Conversions
   use the mandated FY2026 planning rates, not the 2025 daily export.
6. **Incoterms.** SUP-2318 and SUP-4077 are FCA origin, so Cadence pays the
   lane tariff plus brokerage on twelve shipments. SUP-1042 and SUP-3155 are
   DDP and carry no separate freight.
7. **Rebates.** SUP-2318's rebate is banded — each rate applies only to the
   volume inside its band, USD 11,133 rather than USD 28,515 at a flat 3.0%.
   SUP-4077's 4.0% rebate is earned only at 520,000 pieces; the buy is 497,951,
   so it earns nothing and additionally owes the clause 4.1 shortfall charge on
   22,049 pieces.
8. **Payment terms.** Valued against a Net 30 baseline at 9.0% WACC. SUP-4077's
   2/10 Net 60 is worth more taken than left, so the cheaper option is planned.

## Notes

- Contract commercial terms are transcribed into `CONTRACTS` in `solve.py`
  with the governing clause cited, exactly as an analyst reading the four term
  sheets would record them. Every other figure is computed from the data.
- Using the clause 5 specification limits instead of observed 2025 performance
  also reaches SUP-1042. That is a defensible conservative reading rather than
  an error, and the ground truth is stable under it.
