# Sourcing handover extract — data dictionary

Extract assembled for the FY2026 SP-40 sourcing award. All files are UTF-8.
Dates are ISO `YYYY-MM-DD` unless the source system wrote them otherwise; the
purchasing extract in particular carries several date styles.

---

## `contracts/SUP-*_terms.md`

The four FY2026 offer term sheets, one per candidate supplier, as returned by
the suppliers. Commercial terms are in the numbered clauses.

## `demand/forecast_2026.csv`

Direct dump of the FY2026 demand cube, one row per part, month and S&OP
cycle.

| Column | Notes |
| --- | --- |
| `month` | `YYYY-MM`, or `TOTAL` on the cube's subtotal rows. |
| `part_number` | `SP-40` (stainless valve seat) or `SP-22` (brass orifice plate). |
| `plan_cycle` | The S&OP cycle the row belongs to, `YYYY-MM`. |
| `good_units_required` | Net demand in finished good pieces that must pass incoming inspection and reach the line. |
| `planning_note` | Free text; populated on subtotal rows only. |

See `demand/demand_planning_note.md`.

## `purchasing/purchase_orders_2025.csv`

Calendar-2025 purchase orders for SP-40 and SP-22 from the purchasing reporting
mart. One row per purchase order.

| Column | Notes |
| --- | --- |
| `po_id` | The mart's reporting number for the order, `PO-45xxx`. |
| `supplier_name` | Free text as keyed on the order. Not validated against the vendor master. |
| `order_date`, `promised_date` | As keyed; several date styles. |
| `currency`, `unit_price`, `uom` | Price per `uom` in `currency`; `uom` is `PIECE` or `BOX100`. |
| `qty_ordered` | In `uom`. |
| `status` | `CLOSED` or `CANCELLED`. A cancelled order has no receipts. |

## `purchasing/goods_receipts_2025.csv`

One row per lot received against a purchase order.

| Column | Notes |
| --- | --- |
| `receipt_id` | Receipt transaction. |
| `po_id` | The purchase order number as written by the system that posted the receipt. |
| `lot_id` | Lot identifier assigned at receiving. It is the lot identifier incoming inspection uses. |
| `receipt_date` | Posting date. |
| `qty_received_pieces` | Pieces received. |

## `purchasing/po_reference_2025.csv`

Reference extract of 2025 purchase orders as the mart holds them: reporting
number, ERP number, responsible buyer, cost centre, commodity code and the
payment terms text keyed on the order.

## `quality/incoming_inspection_2025.jsonl`

The QMS inspection log for SP-40, one JSON object per inspection record.

| Field | Notes |
| --- | --- |
| `inspection_id` | QMS record number, assigned when the record is keyed. Unique per record. |
| `lot_id` | The lot inspected, as identified at receiving. |
| `inspected_on` | Date the inspection was performed. |
| `part_number` | Always `SP-40` in this extract. |
| `supplier` | Free text keyed by the inspector; empty or `null` where nothing was keyed. Not validated. |
| `inspection_point` | `INCOMING` for the Aurora receiving dock under QP-07, `SOURCE` for an inspection performed at the supplier's plant by a Cadence supplier-quality engineer. |
| `qty_inspected` | Pieces inspected. |
| `qty_rejected` | Pieces found nonconforming at that inspection. |
| `inspector` | `QA-nn` Aurora quality, `SQE-nn` supplier quality. |
| `defect_codes` | Nonconformance codes recorded. |
| `disposition` | Disposition of the rejected pieces as recorded by the inspector: `SCRAP` or `REPLACED_BY_SUPPLIER`. |

## `master/supplier_master.xlsx`

Sheet `suppliers`: one row per supplier code with legal name, location,
currency and approval status. Sheet `name_aliases`: free-text spellings seen in
each source system, mapped to the supplier code. Sheet `notes`.

## `fx/fx_daily_2025.csv`

Treasury export of 2025 daily USD rates for EUR, GBP and MXN.

## `logistics/freight_tariff_2026.csv`

Standing 2026 inbound tariff per lane: USD per 1,000 pieces plus a brokerage
charge per inbound shipment. The tariff does not say which lanes Cadence pays
for; the Incoterm in the supply contract does.

## `finance/planning_assumptions_2026.md`

The standing finance policy for FY2026 planning: mandatory exchange rates,
cost of capital, the payment-terms valuation formula, freight budgeting and
scrap disposal rates.

## `it/CHG-2025-0417_erp_cutover.md`

The change record for the 2025-07-01 ERP go-live in purchasing and receiving.

## `quality/QP-07_incoming_inspection.md`

The Aurora receiving-inspection procedure: what is inspected on receipt, how
lots are identified and how nonconforming pieces are dispositioned.
