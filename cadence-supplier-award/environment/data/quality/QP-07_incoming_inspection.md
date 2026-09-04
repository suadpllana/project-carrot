# QP-07 — Receiving Inspection of Purchased Parts

**Owner:** Quality Assurance, Aurora | **Revision:** 6 | **Effective:** 2025-01-02

---

## 1. Purpose and scope

This procedure governs inspection of purchased production parts on receipt at
the Aurora plant. It applies to every lot received against a purchase order,
whatever the Incoterm or the supplier's own quality arrangements.

## 2. Lot identity

Receiving assigns a lot identifier to each received quantity at the point of
posting the goods receipt. The lot identifier is the key under which the lot
is inspected, dispositioned and, where necessary, traced back to the purchase
order that brought it in.

Inspection records are written to the QMS as they are keyed. The QMS assigns
its own record number to each and does not merge records: where the same
inspection is keyed twice, both records stand.

## 3. Inspection

SP-40 valve seats are inspected to the full received quantity. The inspector
records the quantity inspected, the quantity found nonconforming, the
nonconformance codes and the disposition.

Where the receiving transaction supplies a supplier name the QMS carries it
through; otherwise the field is left as keyed by the inspector, and it is not
validated against the vendor master.

## 4. Disposition of nonconforming pieces

Pieces found nonconforming at receiving inspection are dispositioned by
Quality, and the inspection record carries the disposition that was applied to
the pieces.

Where the seller has issued a return authorisation and the return movement is
commercially practical, the pieces are packed back to the seller against that
authorisation and leave the Aurora site on the next outbound consolidation.
Where it is not, the pieces are moved to the scrap cage and disposed of under
the Aurora waste contract at the burdened rate set by Corporate FP&A.

Receiving raises no automatic re-order under either disposition. What the
seller owes Cadence for pieces dispositioned either way is a commercial
question governed by the supply agreement, not by this procedure, and cover
for any shortfall against the build plan is a planning matter.

## 5. Source inspection at supplier plants

Where the commodity team has placed a supplier on source inspection, a Cadence
supplier-quality engineer inspects the lot at the supplier's plant before it
is released for shipment. Pieces found nonconforming there are scrapped or
reworked at the seller's plant, at the seller's cost, and the seller makes the
tendered quantity good before the shipment is released; they are not shipped
to Aurora, are never received against a purchase order, and do not appear on
the seller's invoice.

Source-inspection trip reports are entered into the same QMS log as receiving
inspections, under the engineer's own inspector identifier, and are keyed on
the engineer's return rather than on the day of the visit. A lot released
after source inspection is received and inspected at Aurora under section 3
like any other lot.

## 6. Records

Inspection records are retained for seven years. The QMS log is extracted
nightly for reporting.
