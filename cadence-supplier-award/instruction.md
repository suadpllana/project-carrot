# FY2026 valve-seat sourcing award

You are a sourcing analyst at Cadence Instruments LLC, a mid-size manufacturer
of industrial flow meters in Aurora, Illinois.

The SP-40 stainless valve seat is currently split across several suppliers on
expiring purchase agreements. For FY2026 the steering committee has decided to
consolidate the part onto a **single supplier for the full contract year**, and
four suppliers have returned offers. The committee meets next week and has
asked you for the award recommendation.

Everything you have been given is in `/workspace/data/`: the four FY2026 offer
term sheets, the FY2026 demand plan, last year's purchasing and goods-receipt
extracts, the quality log and the receiving procedure, the supplier master, the
treasury FX export, the logistics tariff, the standing finance planning memo,
and the data dictionary and IT change record that came across with the
extracts. It is the raw handover — nothing has been reconciled or cleaned for
you, the systems do not agree with each other, and you should expect to have to
decide for yourself what bears on the question and what does not.

Work out which of the four candidate suppliers Cadence should award the FY2026
SP-40 contract to, and make the case for it.

## Deliverables

Write all three files to `/workspace/output/`. Only files in that directory are
reviewed; nothing you say outside of them counts.

### 1. `/workspace/output/supplier_costs.csv`

The FY2026 cost comparison, one row per candidate supplier — **exactly four
data rows** — sorted by `rank` ascending, with this header line exactly:

```
supplier_code,supplier_name,quoted_price_usd_per_unit,units_to_purchase,total_fy2026_cost_usd,cost_per_good_unit_usd,rank
```

| Field | Type and precision |
| --- | --- |
| `supplier_code` | The supplier's code as it appears in the supplier master |
| `supplier_name` | The supplier's legal name as it appears in the supplier master |
| `quoted_price_usd_per_unit` | The FY2026 offered price restated as US dollars per single piece, 4 decimal places |
| `units_to_purchase` | Whole pieces to be bought from that supplier across FY2026, integer |
| `total_fy2026_cost_usd` | That supplier's full FY2026 cost to Cadence in US dollars, 2 decimal places |
| `cost_per_good_unit_usd` | `total_fy2026_cost_usd` divided by the FY2026 good-unit requirement, 4 decimal places |
| `rank` | Integer 1–4, where 1 is the lowest `cost_per_good_unit_usd` |

Numeric fields carry digits, an optional leading minus sign and a decimal point
only: no currency symbols, no thousands separators, no percent signs, no
quoting. Both files are RFC 4180 CSV — a text field containing a comma must be
double-quoted, and at least one supplier's legal name does contain one.

Round only what you report. Every figure is computed from unrounded
intermediate values — do not feed a figure you have already rounded into a
later calculation — and only the number written into the file is rounded, to
the precision named above. `units_to_purchase` is the whole number of pieces
that has to be bought for the FY2026 good-unit requirement still to be covered
in full at that supplier's own observed reject performance: round it **up** to
the next whole piece, or to the next whole pack where a supplier's offer only
sells whole packs. `supplier_name` is the master's legal name in full, legal
suffix and all; punctuation and spacing may follow your own house style.

### 2. `/workspace/output/defect_rates.csv`

The incoming-inspection record for the four candidate suppliers, **exactly four
data rows**, sorted by `supplier_code` ascending, with this header line exactly:

```
supplier_code,lots_inspected,units_inspected,units_rejected,reject_rate_pct
```

`lots_inspected`, `units_inspected` and `units_rejected` are integers.
`reject_rate_pct` is the rejected pieces as a percentage of the inspected
pieces, to 3 decimal places (for example `4.250` means 4.25%). The same numeric
formatting and rounding rules as above apply.

### 3. `/workspace/output/recommendation.md`

The memo for the steering committee, containing these five level-2 headings,
spelled exactly this way and in this order:

```
## Recommendation
## Cost Comparison
## Basis of Decision
## Data Quality and Exclusions
## Risks and Sensitivities
```

- `## Recommendation` names **exactly one** awarded supplier, by both its
  supplier code and its full legal name, and states the FY2026 purchase
  quantity you would contract with it, that supplier's FY2026 total cost in
  US dollars, and the US-dollar amount by which it beats the second-ranked
  supplier over FY2026.
- `## Cost Comparison` shows all four suppliers with the figures behind the
  ranking, including each supplier's FY2026 total cost, and states the FY2026
  good-unit requirement you worked to.
- `## Basis of Decision` explains what drives the ranking and, naming each of
  them, why the three suppliers you did not pick lose.
- `## Data Quality and Exclusions` states what you excluded from the source
  data and why, and identifies every supplier that appears in the source data
  but is not a candidate for this award.
- `## Risks and Sensitivities` gives the risks attached to the supplier you
  picked and quantifies what would have to change to overturn the
  recommendation.

Each of the five sections has to carry that content: a heading with nothing
under it, or a line of filler, is not a section. Figures repeated in the memo
are the figures you filed — quote them as they stand in the two CSVs, to the
cent or rounded to the nearest whole dollar, never at some other value.

## Constraints

- Award the full FY2026 volume to one supplier. Do not recommend splitting the
  award, dual-sourcing, staging the award, or deferring the decision.
- Every figure in the deliverables must be derived from the files in
  `/workspace/data/`. Do not introduce outside market prices, benchmarks,
  indices or placeholder values, and do not leave any required field blank or
  marked "TBD".
- Report US dollars throughout.
