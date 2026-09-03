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

Pieces found nonconforming at receiving inspection are moved to the scrap cage
and disposed of under the Aurora waste contract at the burdened rate set by
Corporate FP&A. Under the standing supply agreements the supplier issues no
credit and no replacement for pieces rejected at receiving inspection, and the
quantity is not re-ordered automatically: cover for the shortfall is a
planning matter, not a receiving one.

## 5. Source inspection at supplier plants

Where the commodity team has placed a supplier on source inspection, a Cadence
supplier-quality engineer inspects the lot at the supplier's plant before it
is released for shipment. Pieces found nonconforming there are held back at
the plant and replaced by the supplier at its own cost before the shipment is
tendered; they are not shipped to Aurora and do not appear on the supplier's
invoice.

Source-inspection trip reports are entered into the same QMS log as receiving
inspections, under the engineer's own inspector identifier, and are keyed on
the engineer's return rather than on the day of the visit. A lot released
after source inspection is received and inspected at Aurora under section 3
like any other lot.

## 6. Records

Inspection records are retained for seven years. The QMS log is extracted
nightly for reporting.
