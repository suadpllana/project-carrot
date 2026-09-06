#!/usr/bin/env python3
"""Deterministic generator for the shipped dataset under environment/data/.

Starts from the revision-1 extracts preserved in v1_inputs/ (the inspection
log and the goods receipts) and layers on the population traps described in
task_card.md:

  * SOURCE inspection records pooled with INCOMING ones (double counts the
    lots, and counts pieces Cadence never bought or scrapped);
  * incoming rejects are dispositioned two ways - scrapped at Aurora, or
    returned to the seller and replaced free of charge - and only the
    scrapped share is a loss the purchase quantity has to carry;
  * goods receipts posted after the 2025-07-01 ERP go-live carry ERP purchase
    order numbers, so a join on the purchasing extract's mart numbers silently
    drops every post-cutover lot;
  * the demand cube is a rolling fifteen-month horizon and retains the
    superseded October S&OP cycle beside the frozen November one, so the
    contract-year window has to be cut out of it.

The shipped documents DESCRIBE these fields and systems and never say what to
do about them: what a reject rate is defined over, which rejected pieces are
actually lost, that a join lost two fifths of its rows, and which months of
the cube the contract year covers are the attempt's judgements to make. Any
wording here that instructs rather than describes is a defect - it turns a
judgement into a checklist item and the task scores too easily.

Everything else in environment/data/ is authored by hand and left untouched.
Re-running reproduces the three regenerated files and the generated documents
byte for byte: one seed, no clock, no file-order dependence.

Run from anywhere:  python solution/_provenance/generate_data.py
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import random
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "environment" / "data"
V1 = HERE / "v1_inputs"

SEED = 20260901
CUTOVER = dt.date(2025, 7, 1)
CANDIDATES = ["SUP-1042", "SUP-2318", "SUP-3155", "SUP-4077"]

# SUP-3155's rejects are re-laid across four lot groups so that dropping either
# the blank-supplier lots or the post-cutover lots understates its rate enough
# to hand it the award. Rates for three groups are fixed; the fourth carries
# whatever remains of the unchanged total.
REJECT_TOTAL_3155 = 11590
RATE_NAMED_PRE = 0.024      # named supplier, received before go-live
RATE_NAMED_POST = 0.080     # named supplier, received after go-live
RATE_BLANK_PRE = 0.075      # blank supplier, received before go-live
N_BLANK_POST, N_BLANK_PRE = 12, 9

# source inspections: (lots chosen, of which post-cutover, reject-rate band)
SOURCE_PLAN = {
    "SUP-1042": dict(n=22, n_post=8, band=(0.10, 0.14), transit_days=3),
    "SUP-2318": dict(n=6, n_post=2, band=(0.02, 0.03), transit_days=34),
    "SUP-3155": dict(n=5, n_post=5, band=(0.13, 0.17), transit_days=6),
}
SOURCE_ALIAS = {"SUP-1042": "Meridian Precision Works, LLC",
                "SUP-2318": "Rheinwerk Feinmechanik GmbH",
                "SUP-3155": "Talleres Nortenos, S.A. de C.V."}
ALIAS_3155 = ["Talleres Nortenos S.A. de C.V.", "Talleres Nortenos SA de CV",
              "TALLERES NORTENOS", "Talleres Nortenos, S.A. de C.V."]

# The planning cube is a rolling fifteen-month horizon. The frozen November
# cycle below is authored month by month so that the three readings an attempt
# can take of it are all different numbers:
#
#   contract year (2026-04 .. 2027-03) 493,000   <- the offers' own term
#   calendar 2026 (2026-01 .. 2026-12) 512,000
#   every monthly row / the TOTAL row  623,600
#
# and so that both of the wrong ones put SUP-4077 over its 520,000-piece
# rebate threshold once the buy is grossed up.
MONTHS_SP40 = [
    ("2026-01", 44000), ("2026-02", 41600), ("2026-03", 45000),
    ("2026-04", 43200), ("2026-05", 44100), ("2026-06", 42600),
    ("2026-07", 38900), ("2026-08", 36700), ("2026-09", 43400),
    ("2026-10", 44800), ("2026-11", 43900), ("2026-12", 43800),
    ("2027-01", 36800), ("2027-02", 35400), ("2027-03", 39400),
]
MONTHS_SP22 = [
    ("2026-01", 17800), ("2026-02", 16900), ("2026-03", 18600),
    ("2026-04", 19100), ("2026-05", 18400), ("2026-06", 17200),
    ("2026-07", 15900), ("2026-08", 16300), ("2026-09", 18800),
    ("2026-10", 19400), ("2026-11", 18100), ("2026-12", 16900),
    ("2027-01", 15200), ("2027-02", 14800), ("2027-03", 16100),
]
CONTRACT_MONTHS = [m for m, _ in MONTHS_SP40 if "2026-04" <= m <= "2027-03"]
OCT_SCALE_SP40 = 1.090
OCT_SCALE_SP22 = 1.030

# Incoming rejects are dispositioned lot by lot: scrapped at Aurora, or
# returned to the seller under an RMA and replaced free of charge. Only the
# scrapped share is a loss the FY2026 purchase quantity has to carry. The
# domestic supplier returns most of what it fails because the return is a
# one-day truck movement; the overseas lanes scrap in place. Target share of
# each supplier's rejected pieces that ends up SCRAP:
SCRAP_SHARE = {"SUP-1042": 0.215, "SUP-2318": 0.880,
               "SUP-3155": 0.780, "SUP-4077": 0.940}


def d(s):
    return dt.date.fromisoformat(s)


# ---------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------
def load_master():
    wb = openpyxl.load_workbook(DATA / "master" / "supplier_master.xlsx", data_only=True)
    alias = {}
    for row in wb["name_aliases"].iter_rows(min_row=2, values_only=True):
        if row and row[0]:
            alias[str(row[0]).strip().casefold()] = str(row[1]).strip()
    return alias


def load_csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def spread(total, weights):
    """Split integer `total` across `weights` proportionally, largest
    remainder rounding, so the parts sum exactly."""
    raw = [total * w / sum(weights) for w in weights]
    parts = [int(x) for x in raw]
    short = total - sum(parts)
    order = sorted(range(len(raw)), key=lambda i: raw[i] - parts[i], reverse=True)
    for i in order[:short]:
        parts[i] += 1
    return parts


def main():
    rng = random.Random(SEED)
    alias = load_master()

    pos = load_csv(DATA / "purchasing" / "purchase_orders_2025.csv")
    po_supplier = {r["po_id"]: alias[r["supplier_name"].strip().casefold()] for r in pos}

    receipts = load_csv(V1 / "goods_receipts_2025.csv")
    lot_supplier = {r["lot_id"]: po_supplier[r["po_id"]] for r in receipts}
    lot_received = {r["lot_id"]: d(r["receipt_date"]) for r in receipts}

    recs = load_jsonl(V1 / "incoming_inspection_2025.jsonl")
    for r in recs:
        r["inspection_point"] = "INCOMING"

    # -------------------------------------------------- SUP-3155 regroup --
    lots_3155 = sorted({r["lot_id"] for r in recs if lot_supplier[r["lot_id"]] == "SUP-3155"})
    post = [l for l in lots_3155 if lot_received[l] >= CUTOVER]
    pre = [l for l in lots_3155 if lot_received[l] < CUTOVER]
    blank = set(rng.sample(sorted(post), N_BLANK_POST)) | set(rng.sample(sorted(pre), N_BLANK_PRE))

    groups = {"A": [], "B": [], "C": [], "D": []}   # A blank/post B blank/pre C named/post D named/pre
    primary = {}
    for r in recs:
        lot = r["lot_id"]
        if lot_supplier[lot] != "SUP-3155":
            continue
        if lot in blank:
            r["supplier"] = "" if rng.random() < 0.5 else None
        elif not r["supplier"]:
            r["supplier"] = rng.choice(ALIAS_3155)
        if lot not in primary:
            primary[lot] = r
            key = ("A" if lot in blank else "C") if lot_received[lot] >= CUTOVER else ("B" if lot in blank else "D")
            groups[key].append(r)

    def assign(rows, rate):
        return sum(rows_set(rows, [int(round(rate * r["qty_inspected"])) for r in rows]))

    def rows_set(rows, values):
        for r, v in zip(rows, values):
            r["qty_rejected"] = v
        return values

    used = 0
    used += assign(groups["D"], RATE_NAMED_PRE)
    used += assign(groups["C"], RATE_NAMED_POST)
    used += assign(groups["B"], RATE_BLANK_PRE)
    remainder = REJECT_TOTAL_3155 - used
    rows_set(groups["A"], spread(remainder, [r["qty_inspected"] for r in groups["A"]]))

    def summary(rows):
        u = sum(r["qty_inspected"] for r in rows)
        j = sum(r["qty_rejected"] for r in rows)
        return "%2d lots %7d units %6d rejects %5.2f%%" % (len(rows), u, j, 100.0 * j / u)

    print("SUP-3155 lot groups")
    for k, label in (("A", "blank, post-cutover"), ("B", "blank, pre-cutover"),
                     ("C", "named, post-cutover"), ("D", "named, pre-cutover")):
        print("  %-22s %s" % (label, summary(groups[k])))
    assert all(r["qty_rejected"] <= 0.22 * r["qty_inspected"] for r in groups["A"])

    # ------------------------------------------------ reject disposition --
    # One disposition per physical lot: the pieces a lot failed on are either
    # scrapped at Aurora under the waste contract, or returned to the seller
    # under an RMA and replaced free of charge. Nothing in the shipped files
    # says which of the two a purchase quantity has to carry.
    lot_rejects = {}
    for r in recs:
        lot_rejects.setdefault(r["lot_id"], r["qty_rejected"])

    def rtv_pref(code, lot):
        """Return authorisations are arranged lot by lot. For SUP-3155 they
        sit on the lots that were cleanly identified at receipt, so the groups
        a careless join drops are the ones that were scrapped."""
        if code != "SUP-3155":
            return 0
        return 0 if (lot not in blank and lot_received[lot] < CUTOVER) else 1

    scrap_stats = {}
    for code in CANDIDATES:
        lots = sorted(l for l in lot_rejects if lot_supplier[l] == code)
        total = sum(lot_rejects[l] for l in lots)
        target_returned = total - int(round(SCRAP_SHARE[code] * total))
        order = sorted(lots, key=lambda l: (rtv_pref(code, l), -lot_rejects[l], l))
        returned, got = set(), 0
        for l in order:
            if got + lot_rejects[l] <= target_returned:
                returned.add(l)
                got += lot_rejects[l]
        scrap_stats[code] = dict(lots=len(lots), rejects=total, returned=got,
                                 scrapped=total - got, rtv_lots=len(returned))
        for r in recs:
            if lot_supplier[r["lot_id"]] != code:
                continue
            r["disposition"] = ("REPLACED_BY_SUPPLIER" if r["lot_id"] in returned
                                else "SCRAP")

    print("incoming reject disposition (one disposition per lot)")
    for code in CANDIDATES:
        st = scrap_stats[code]
        print("  %s  %2d lots  %5d rejected  %5d scrapped (%5.1f%%)  %5d returned on %2d lots"
              % (code, st["lots"], st["rejects"], st["scrapped"],
                 100.0 * st["scrapped"] / st["rejects"], st["returned"], st["rtv_lots"]))

    # ------------------------------------------------- source inspections --
    first = {}
    for r in recs:
        first.setdefault(r["lot_id"], r)
    source_rows = []
    for code, plan in SOURCE_PLAN.items():
        lots = sorted(l for l in first if lot_supplier[l] == code)
        post_l = [l for l in lots if lot_received[l] >= CUTOVER]
        pre_l = [l for l in lots if lot_received[l] < CUTOVER]
        chosen = rng.sample(post_l, plan["n_post"]) + rng.sample(pre_l, plan["n"] - plan["n_post"])
        chosen.sort()
        late = set(rng.sample(chosen, len(chosen) // 2))    # entered in batch after the trip
        for lot in chosen:
            twin = first[lot]
            rate = rng.uniform(*plan["band"])
            qty = twin["qty_inspected"]
            inspected = lot_received[lot] - dt.timedelta(days=plan["transit_days"])
            logged = (d(twin["inspected_on"]) + dt.timedelta(days=21)) if lot in late else inspected
            source_rows.append({
                "inspection_id": None,
                "lot_id": lot,
                "inspected_on": inspected.isoformat(),
                "part_number": "SP-40",
                "supplier": SOURCE_ALIAS[code],
                "inspection_point": "SOURCE",
                "qty_inspected": qty,
                "qty_rejected": int(round(rate * qty)),
                "inspector": rng.choice(["SQE-02", "SQE-05"]),
                "defect_codes": list(twin["defect_codes"]) or [rng.choice(["D-104", "D-140"])],
                # pieces failed at the seller's own plant are scrapped or
                # reworked there, at the seller's cost, and never shipped
                "disposition": "SCRAP",
                "_logged": logged,
            })
        print("%s source inspections: %d lots, %d rejects on %d pieces (%.1f%%), %d logged after the incoming record"
              % (code, len(chosen), sum(x["qty_rejected"] for x in source_rows if lot_supplier[x["lot_id"]] == code),
                 sum(x["qty_inspected"] for x in source_rows if lot_supplier[x["lot_id"]] == code),
                 100.0 * sum(x["qty_rejected"] for x in source_rows if lot_supplier[x["lot_id"]] == code)
                 / sum(x["qty_inspected"] for x in source_rows if lot_supplier[x["lot_id"]] == code),
                 sum(1 for x in source_rows if lot_supplier[x["lot_id"]] == code and x["lot_id"] in late)))

    # ------------------------------------------------------- renumbering --
    for r in recs:
        r["_logged"] = d(r["inspected_on"])
        r["_old"] = r["inspection_id"]
    for r in source_rows:
        r["_old"] = "S" + r["lot_id"]
    everything = recs + source_rows
    everything.sort(key=lambda r: (r["_logged"], r["_old"]))
    out = []
    for i, r in enumerate(everything, start=1):
        row = {
            "inspection_id": "QC-2025-%05d" % i,
            "lot_id": r["lot_id"],
            "inspected_on": r["inspected_on"],
            "part_number": r["part_number"],
            "supplier": r["supplier"],
            "inspection_point": r["inspection_point"],
            "qty_inspected": r["qty_inspected"],
            "qty_rejected": r["qty_rejected"],
            "inspector": r["inspector"],
            "defect_codes": r["defect_codes"],
            "disposition": r["disposition"],
        }
        out.append(row)
    with open(DATA / "quality" / "incoming_inspection_2025.jsonl", "w", encoding="utf-8", newline="\n") as fh:
        for row in out:
            fh.write(json.dumps(row) + "\n")
    print("inspection log: %d rows (%d source)" % (len(out), len(source_rows)))

    # ---------------------------------------------- ERP cutover: receipts --
    erp = {}
    n = 118201 + rng.randint(0, 400)
    for r in pos:
        n += rng.randint(1, 9)
        erp[r["po_id"]] = "4500%06d" % n
    buyers = ["A. Whitfield", "R. Castellanos", "T. Okonkwo"]
    with open(DATA / "purchasing" / "po_reference_2025.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["mart_po_id", "erp_po_number", "buyer", "cost_center",
                    "commodity_code", "payment_terms_text"])
        for r in pos:
            w.writerow([r["po_id"], erp[r["po_id"]], rng.choice(buyers),
                        rng.choice(["CC-4410", "CC-4415"]), "COM-STL-VS",
                        rng.choice(["Net 30", "Net 45", "Net 60"])])
    moved = 0
    with open(DATA / "purchasing" / "goods_receipts_2025.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["receipt_id", "po_id", "lot_id", "receipt_date", "qty_received_pieces"])
        for r in receipts:
            po = r["po_id"]
            if d(r["receipt_date"]) >= CUTOVER:
                po = erp[po]
                moved += 1
            w.writerow([r["receipt_id"], po, r["lot_id"], r["receipt_date"], r["qty_received_pieces"]])
    print("goods receipts: %d rows, %d posted after go-live carry ERP numbers" % (len(receipts), moved))

    # ------------------------------------------------ demand plan cycles --
    months = {"SP-40": list(MONTHS_SP40), "SP-22": list(MONTHS_SP22)}
    oct_sp40 = [100 * int(round(v * OCT_SCALE_SP40 / 100.0)) for _, v in months["SP-40"]]
    oct_sp22 = [100 * int(round(v * OCT_SCALE_SP22 / 100.0)) for _, v in months["SP-22"]]
    cycles = {"2025-10": {"SP-40": oct_sp40, "SP-22": oct_sp22},
              "2025-11": {"SP-40": [v for _, v in months["SP-40"]],
                          "SP-22": [v for _, v in months["SP-22"]]}}
    with open(DATA / "demand" / "forecast_2026.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["month", "part_number", "plan_cycle", "good_units_required", "planning_note"])
        for cycle in ("2025-10", "2025-11"):
            for part in ("SP-40", "SP-22"):
                vals = cycles[cycle][part]
                for (m, _), v in zip(months[part], vals):
                    w.writerow([m, part, cycle, v, ""])
                w.writerow(["TOTAL", part, cycle, sum(vals),
                            "Cube subtotal over the %d %s rows of cycle %s above"
                            % (len(vals), part, cycle)])

    def window(cycle, lo="2026-04", hi="2027-03"):
        return sum(v for (m, _), v in zip(months["SP-40"], cycles[cycle]["SP-40"])
                   if lo <= m <= hi)

    print("demand dump: SP-40 by reading")
    for cycle in ("2025-10", "2025-11"):
        print("  cycle %s  contract year %d  calendar 2026 %d  all rows %d"
              % (cycle, window(cycle), window(cycle, "2026-01", "2026-12"),
                 sum(cycles[cycle]["SP-40"])))
    good_units = window("2025-11")
    for label, value in (("calendar 2026", window("2025-11", "2026-01", "2026-12")),
                         ("all fifteen rows", sum(cycles["2025-11"]["SP-40"])),
                         ("October contract year", window("2025-10"))):
        assert value != good_units, "%s reads the same as the contract year" % label

    # ------------------------------------------------- generated documents --
    write_docs()

    # ------------------------------------------------- design self-check ---
    self_check(out, erp, lot_supplier, lot_received)


# ---------------------------------------------------------------------------
# documents
# ---------------------------------------------------------------------------
def write_docs():
    (DATA / "it").mkdir(exist_ok=True)
    (DATA / "it" / "CHG-2025-0417_erp_cutover.md").write_text(CHANGE_NOTE, encoding="utf-8", newline="\n")
    (DATA / "quality" / "QP-07_incoming_inspection.md").write_text(QP07, encoding="utf-8", newline="\n")
    (DATA / "DATA_DICTIONARY.md").write_text(DICTIONARY, encoding="utf-8", newline="\n")
    note = DATA / "demand" / "demand_planning_note.md"
    text = note.read_text(encoding="utf-8")
    stale = ("- The cube keeps the last two S&OP cycles side by side and the dump is not\n"
             "  filtered to one of them; the `plan_cycle` column says which cycle a row\n"
             "  belongs to.\n")
    if stale in text:      # revision-2 wording; it told the attempt what to do
        note.write_text(text.replace(stale, ""), encoding="utf-8", newline="\n")


QP07 = """\
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
"""


CHANGE_NOTE = """\
================================================================================
CADENCE INSTRUMENTS LLC - IT CHANGE RECORD
================================================================================
Change          : CHG-2025-0417
Title           : Purchasing and receiving go-live on the new ERP
Requested by    : D. Okafor, Supply Chain Systems
Go-live         : 2025-07-01 06:00 CT
Status          : Closed - complete
Affected systems: ERP (purchasing, receiving), purchasing reporting mart,
                  QMS incoming-inspection interface
================================================================================

SUMMARY
-------
Purchase order entry and goods receiving moved from the legacy system to the
new ERP at 06:00 on 2025-07-01. Open purchase orders were migrated into the
ERP that morning. The ERP numbers purchase orders in its own ten-digit range
(4500xxxxxx); the legacy PO-45xxx numbers do not exist in the ERP.

The purchasing reporting mart, which produces the purchase-order extract used
by Sourcing and Finance, was NOT re-platformed. It continues to key every
purchase order under a PO-45xxx reporting number.

Goods receipts are posted in the system of record for the posting date and
carry that system's purchase order number.

Both number series appear on the mart's 2025 purchase-order reference extract.

INTERFACE NOTE
--------------
The QMS inspection interface receives the lot identifier from the receiving
transaction. It does not receive the supplier name; where a supplier name
appears on an inspection record it was keyed by hand and is not validated
against the vendor master.

ACTIONS
-------
  ACT-1  Migrate open purchase orders ........................ DONE 2025-07-01
  ACT-2  Publish ERP / mart number reference extract ......... DONE 2025-07-02
  ACT-3  Notify Sourcing, Finance, Quality ................... DONE 2025-07-02
  ACT-4  Restore supplier name on the QMS interface .......... DEFERRED (FY2027)
================================================================================
"""

DICTIONARY = """\
# Sourcing handover extract — data dictionary

Extract assembled for the FY2026 SP-40 sourcing award. All files are UTF-8.
Dates are ISO `YYYY-MM-DD` unless the source system wrote them otherwise; the
purchasing extract in particular carries several date styles.

---

## `contracts/SUP-*_terms.md`

The four FY2026 offer term sheets, one per candidate supplier, as returned by
the suppliers. The contract-year dates are in the header block; commercial and
quality terms are in the numbered clauses.

## `demand/forecast_2026.csv`

Direct dump of the FY2026 demand cube, one row per part, month and S&OP
cycle.

| Column | Notes |
| --- | --- |
| `month` | `YYYY-MM`, over whatever horizon the cube was exported for, or `TOTAL` on the cube's subtotal rows. |
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
| `disposition` | What was physically done with the pieces found nonconforming on that inspection, as recorded by the inspector: `SCRAP` (moved to the scrap cage and disposed of) or `REPLACED_BY_SUPPLIER` (packed back to the seller against a return authorisation and made good by the seller). One disposition per inspection record. |

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
"""


# ---------------------------------------------------------------------------
# design self-check: do the careless routes move the numbers that decide?
# ---------------------------------------------------------------------------
# The cost model lives in solution/solve.py and the authority on what each
# route scores is solution/_provenance/verify_design.py, which runs the real
# model through the shipped verifier. What is checked here is narrower and
# cheaper: that the populations came out of the generator far enough apart
# that a wrong reading cannot land on the right numbers by accident.
MIN_SEPARATION = 0.004          # 0.4 points of reject rate


def self_check(rows, erp, lot_supplier, lot_received):
    import collections

    def rates(*, include_source=False, dedupe="first", drop_blank=False,
              drop_post=False, scrap_only=True):
        seen = {}
        for r in rows:
            if r["inspection_point"] == "SOURCE" and not include_source:
                continue
            if drop_blank and not r["supplier"]:
                continue
            if drop_post and lot_received[r["lot_id"]] >= CUTOVER:
                continue
            key = r["lot_id"] if dedupe != "none" else r["inspection_id"]
            if key not in seen or dedupe == "last":
                seen[key] = r
        agg = collections.defaultdict(lambda: [0, 0])
        for r in seen.values():
            code = lot_supplier[r["lot_id"]]
            agg[code][0] += r["qty_inspected"]
            if scrap_only and r["disposition"] != "SCRAP":
                continue
            agg[code][1] += r["qty_rejected"]
        return {c: agg[c][1] / agg[c][0] for c in CANDIDATES}

    def show(label, rt):
        print("  %-46s %s" % (label, "  ".join("%s %6.3f%%" % (c, 100 * rt[c])
                                               for c in CANDIDATES)))

    print("\nself-check: the loss rate the purchase quantity is grossed up by")
    ref = rates()
    show("reference (INCOMING, scrapped pieces only)", ref)
    routes = [
        ("counts every reject, not just the scrapped ones", dict(scrap_only=False)),
        ("pools SOURCE rows, dedupe keeps first record", dict(include_source=True)),
        ("pools SOURCE rows, dedupe keeps last record", dict(include_source=True, dedupe="last")),
        ("pools SOURCE rows, no dedupe", dict(include_source=True, dedupe="none")),
        ("free-text supplier field (blank lots dropped)", dict(drop_blank=True)),
        ("no ERP crosswalk (post-cutover lots dropped)", dict(drop_post=True)),
    ]
    close = []
    for label, kw in routes:
        rt = rates(**kw)
        show(label, rt)
        moved = max(abs(rt[c] - ref[c]) for c in CANDIDATES)
        if moved < MIN_SEPARATION:
            close.append("%s (largest move %.3f points)" % (label, 100 * moved))
    assert not close, "routes that barely move any rate: %s" % close
    print("  every route above moves at least one supplier by %.1f points"
          % (100 * MIN_SEPARATION))


if __name__ == "__main__":
    main()
