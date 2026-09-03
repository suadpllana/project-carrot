#!/usr/bin/env python3
"""Deterministic generator for the shipped dataset under environment/data/.

Starts from the revision-1 extracts preserved in v1_inputs/ (the inspection
log, the goods receipts and the demand dump) and layers on the three
population traps described in task_card.md:

  * SOURCE inspection records pooled with INCOMING ones (double counts the
    lots, and counts pieces Cadence never bought);
  * goods receipts posted after the 2025-07-01 ERP go-live carry ERP purchase
    order numbers, so a join on the purchasing extract's mart numbers silently
    drops every post-cutover lot;
  * the demand cube retains the superseded October S&OP cycle beside the
    frozen November one.

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

OCT_SCALE_SP40 = 1.108
OCT_TOTAL_SP40 = 538600
OCT_SCALE_SP22 = 1.03


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
                "disposition": "REPLACED_BY_SUPPLIER",
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
    with open(DATA / "purchasing" / "po_crosswalk_erp_cutover.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["mart_po_id", "erp_po_number"])
        for r in pos:
            w.writerow([r["po_id"], erp[r["po_id"]]])
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
    v1 = load_csv(V1 / "forecast_2026.csv")
    months = {"SP-40": [], "SP-22": []}
    for r in v1:
        if r["month"] != "TOTAL":
            months[r["part_number"]].append((r["month"], int(r["good_units_required"])))
    oct_sp40 = spread(OCT_TOTAL_SP40, [v for _, v in months["SP-40"]])
    oct_sp40 = [100 * int(round(x / 100.0)) for x in oct_sp40]
    oct_sp40[-1] += OCT_TOTAL_SP40 - sum(oct_sp40)
    oct_sp22 = [100 * int(round(v * OCT_SCALE_SP22 / 100.0)) for _, v in months["SP-22"]]
    with open(DATA / "demand" / "forecast_2026.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["month", "part_number", "plan_cycle", "good_units_required", "planning_note"])
        for cycle, sp40, sp22 in (("2025-10", oct_sp40, [v for _, v in months["SP-22"]] and oct_sp22),
                                  ("2025-11", [v for _, v in months["SP-40"]], [v for _, v in months["SP-22"]])):
            for part, vals in (("SP-40", sp40), ("SP-22", sp22)):
                for (m, _), v in zip(months[part], vals):
                    w.writerow([m, part, cycle, v, ""])
                w.writerow(["TOTAL", part, cycle, sum(vals),
                            "Sum of the twelve %s rows of cycle %s above" % (part, cycle)])
    print("demand dump: cycle 2025-10 SP-40 total %d, cycle 2025-11 SP-40 total %d"
          % (sum(oct_sp40), sum(v for _, v in months["SP-40"])))

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
    (DATA / "DATA_DICTIONARY.md").write_text(DICTIONARY, encoding="utf-8", newline="\n")
    note = DATA / "demand" / "demand_planning_note.md"
    text = note.read_text(encoding="utf-8")
    marker = "- The plan is frozen for FY2026. Do not re-forecast it.\n"
    addition = ("- The cube keeps the last two S&OP cycles side by side and the dump is not\n"
                "  filtered to one of them; the `plan_cycle` column says which cycle a row\n"
                "  belongs to.\n")
    if addition not in text:
        assert marker in text, "demand note marker missing"
        text = text.replace(marker, marker + addition)
        note.write_text(text, encoding="utf-8", newline="\n")


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
purchase order under a PO-45xxx reporting number, assigning one to each order
raised in the ERP after go-live so that reporting has one continuous series.

Goods receipts posted in the ERP from go-live onward reference the ERP purchase
order number. Receipts posted before go-live reference the legacy number, and
the receipts extract carries whichever number the posting system used.

A crosswalk between the two number series is published with the purchasing
extracts (purchasing/po_crosswalk_erp_cutover.csv) and covers every purchase
order in the mart, whether it was raised before or after go-live.

KNOWN SIDE EFFECT
-----------------
The QMS incoming-inspection interface receives the lot identifier from the
receiving transaction but no longer receives the supplier name, which the
legacy interface had populated. Inspectors may key the supplier name by hand
on the inspection record; the field is free text and is not validated against
the vendor master. This has been the case on some records since before go-live
and is not scheduled to be fixed.

ACTIONS
-------
  ACT-1  Migrate open purchase orders ........................ DONE 2025-07-01
  ACT-2  Publish PO number crosswalk to the mart ............. DONE 2025-07-02
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
the suppliers. Commercial terms are in the numbered clauses.

## `demand/forecast_2026.csv`

Direct dump of the FY2026 demand cube: one row per part, month and S&OP cycle,
plus the cube's own `TOTAL` subtotal row per part and cycle.

| Column | Notes |
| --- | --- |
| `month` | `YYYY-MM`, or `TOTAL` on the cube's subtotal rows. |
| `part_number` | `SP-40` (stainless valve seat) or `SP-22` (brass orifice plate). |
| `plan_cycle` | The S&OP cycle the row belongs to, `YYYY-MM`. The cube keeps the last two cycles. |
| `good_units_required` | Net demand in finished good pieces that must pass incoming inspection and reach the line. |
| `planning_note` | Free text; populated on subtotal rows only. |

See `demand/demand_planning_note.md`.

## `purchasing/purchase_orders_2025.csv`

Calendar-2025 purchase orders for SP-40 and SP-22 from the purchasing reporting
mart. One row per purchase order.

| Column | Notes |
| --- | --- |
| `po_id` | The mart's reporting number, `PO-45xxx`. See `it/CHG-2025-0417_erp_cutover.md` for how this relates to the ERP number. |
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
| `po_id` | The purchase order number as written by the system that posted the receipt: the legacy number before the 2025-07-01 go-live, the ERP number after it. |
| `lot_id` | Lot identifier assigned at receiving. It is the lot identifier incoming inspection uses. |
| `receipt_date` | Posting date. |
| `qty_received_pieces` | Pieces received. |

## `purchasing/po_crosswalk_erp_cutover.csv`

Crosswalk between the mart's `PO-45xxx` reporting numbers and the ERP's
ten-digit purchase order numbers, one row per purchase order.

## `quality/incoming_inspection_2025.jsonl`

The QMS inspection log for SP-40, one JSON object per inspection record.
`inspection_id` is assigned by the QMS when the record is keyed, which for
supplier-quality trip reports is on the engineer's return rather than on the
day of inspection.

| Field | Notes |
| --- | --- |
| `inspection_id` | QMS record number. |
| `lot_id` | The lot inspected, the same identifier the goods receipt carries. |
| `inspected_on` | Date the inspection was performed. |
| `part_number` | Always `SP-40` in this extract. |
| `supplier` | Free text keyed by the inspector; empty or `null` where nothing was keyed. Not validated. |
| `inspection_point` | `INCOMING`: inspection of the received lot at the Aurora dock under QP-07. `SOURCE`: inspection performed at the supplier's plant by a Cadence supplier-quality engineer before the lot is released for shipment. Pieces rejected at source are removed from the lot and replaced by the supplier before it ships, at the supplier's cost; they are not shipped, not invoiced and not received at Aurora. A source-inspected lot is inspected again on receipt under QP-07 like any other lot. |
| `qty_inspected` | Pieces inspected. |
| `qty_rejected` | Pieces found nonconforming at that inspection. |
| `inspector` | `QA-nn` for the Aurora dock, `SQE-nn` for supplier-quality engineers. |
| `defect_codes` | Nonconformance codes recorded. |
| `disposition` | `SCRAP`: rejected pieces moved to the Aurora scrap cage (contract clause 5.4). `REPLACED_BY_SUPPLIER`: rejected pieces held back and replaced by the supplier before shipment. |

The QMS has been known to key the same physical lot more than once.

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
"""


# ---------------------------------------------------------------------------
# design self-check: does each careless route land somewhere else?
# ---------------------------------------------------------------------------
FX = {"USD": 1.0, "EUR": 1.0850, "GBP": 1.2720, "MXN": 0.0545}
GOOD = 486000
PRICE = {"SUP-1042": 1.9450, "SUP-2318": 1.7800 * 1.0850, "SUP-3155": 34.80 * 0.0545, "SUP-4077": 1.4850 * 1.2720}
FREIGHT = {"SUP-2318": (62.0, 480.0), "SUP-4077": (58.0, 520.0)}


def total_cost(code, rate, good=GOOD):
    import math
    units = math.ceil(good / (1 - rate))
    if code == "SUP-2318":
        units = int(math.ceil(units / 100.0) * 100)
    material = units * PRICE[code]
    frt = 0.0
    if code in FREIGHT:
        frt = units / 1000.0 * FREIGHT[code][0] + 12 * FREIGHT[code][1]
    reb = 0.0
    if code == "SUP-2318":
        for lo, hi, pct in ((0, 200000, 0.0), (200000, 400000, 0.015), (400000, None, 0.03)):
            top = units if hi is None else min(units, hi)
            if top > lo:
                reb += (top - lo) * PRICE[code] * pct
    if code == "SUP-4077" and units >= 520000:
        reb = material * 0.04
    short = (520000 - units) * 0.35 * FX["GBP"] if code == "SUP-4077" and units < 520000 else 0.0
    scrap = (units - good) * 0.42
    days = {"SUP-1042": 45, "SUP-2318": 30, "SUP-3155": 60, "SUP-4077": 60}[code]
    terms = material * 0.09 * (30 - days) / 365.0
    if code == "SUP-4077":
        early = -material * 0.02 + material * 0.98 * 0.09 * (30 - 10) / 365.0
        terms = min(early, terms)
    return material + frt - reb + short + scrap + terms


def self_check(rows, erp, lot_supplier, lot_received):
    import collections
    erp_to_mart = {v: k for k, v in erp.items()}

    def rates(include_source=False, dedupe="first", drop_blank=False, drop_post=False):
        seen = {}
        for r in rows:
            if r["inspection_point"] == "SOURCE" and not include_source:
                continue
            if drop_blank and not r["supplier"]:
                continue
            if drop_post and lot_received[r["lot_id"]] >= CUTOVER:
                continue
            key = r["lot_id"] if dedupe != "none" else r["inspection_id"]
            if key not in seen or (dedupe == "last"):
                seen[key] = r
        agg = collections.defaultdict(lambda: [0, 0])
        for r in seen.values():
            code = lot_supplier[r["lot_id"]]
            agg[code][0] += r["qty_inspected"]
            agg[code][1] += r["qty_rejected"]
        return {c: agg[c][1] / agg[c][0] for c in CANDIDATES}

    def winner(rt, good=GOOD):
        tot = {c: total_cost(c, rt[c], good) for c in CANDIDATES}
        best = min(tot, key=tot.get)
        return best, tot

    print("\ndesign self-check (cost model in miniature; the verifier is the authority)")
    ref, tot = winner(rates())
    print("  %-44s -> %s   %s" % ("reference", ref, "  ".join("%s %.0f" % (c, tot[c]) for c in CANDIDATES)))
    print("  reference rates: " + ", ".join("%s %.3f%%" % (c, 100 * r) for c, r in rates().items()))
    routes = [
        ("pools SOURCE rows, dedupe keeps first record", dict(include_source=True, dedupe="first")),
        ("pools SOURCE rows, dedupe keeps last record", dict(include_source=True, dedupe="last")),
        ("pools SOURCE rows, no dedupe", dict(include_source=True, dedupe="none")),
        ("free-text supplier field (blank lots dropped)", dict(drop_blank=True)),
        ("no ERP crosswalk (post-cutover lots dropped)", dict(drop_post=True)),
    ]
    bad = []
    for label, kw in routes:
        w, tot = winner(rates(**kw))
        print("  %-44s -> %s   %s" % (label, w, "  ".join("%s %.0f" % (c, tot[c]) for c in CANDIDATES)))
        if w == ref:
            bad.append(label)
    w, tot = winner(rates(), good=OCT_TOTAL_SP40)
    print("  %-44s -> %s   %s" % ("October plan cycle (%d)" % OCT_TOTAL_SP40, w, "  ".join("%s %.0f" % (c, tot[c]) for c in CANDIDATES)))
    if w == ref:
        bad.append("October plan cycle")
    assert not bad, "routes that still reach the reference answer: %s" % bad
    print("  every route above lands on a different supplier")


if __name__ == "__main__":
    main()
