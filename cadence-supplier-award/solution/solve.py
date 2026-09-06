#!/usr/bin/env python3
"""Reference solution: FY2026 SP-40 valve-seat sourcing award.

Reads only the shipped inputs under /workspace/data and writes the four graded
deliverables to /workspace/output. Deterministic: no network, no clock, no
randomness.

Contract commercial terms are transcribed below from the four FY2026 term
sheets in data/contracts/, with the governing clause cited on each line. Every
other figure is computed from the data files.

Each analysis step takes its choices as keyword arguments whose defaults are
the correct reading of the data. The provenance tooling under _provenance/
calls the same functions with one wrong choice at a time to measure what each
omission does to the answer; nothing here consults those arguments other than
through its own defaults.
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

DATA = Path(os.environ.get("CADENCE_DATA", "/workspace/data"))
OUT = Path(os.environ.get("CADENCE_OUT", "/workspace/output"))

CANDIDATES = ["SUP-1042", "SUP-2318", "SUP-3155", "SUP-4077"]
ERP_GO_LIVE = "2025-07-01"                                        # it/CHG-2025-0417

# --- data/contracts/SUP-*_terms.md, header block ---------------------------
# Buyer's FY2026 contract year. The planning cube dump is a rolling fifteen
# month horizon, so the requirement has to be cut out of it.
CONTRACT_FROM = "2026-04"
CONTRACT_TO = "2027-03"

# --- data/finance/planning_assumptions_2026.md -----------------------------
FX = {"USD": 1.0, "EUR": 1.0850, "GBP": 1.2720, "MXN": 0.0545}   # section 1
WACC = 0.09                                                       # section 2
BASELINE_DAYS = 30                                                # section 3
DISPOSAL_USD_PER_SCRAPPED = 1.25                                  # section 5

# --- data/contracts/SUP-*_terms.md -----------------------------------------
# price / pieces_per_uom / currency        : clause 1
# whole_packs_only                         : clause 1 (SUP-2318: partial boxes
#                                            are not tendered)
# buyer_pays_freight (Incoterm) + shipments: clause 2
# payment_days, cash_discount              : clause 3
# rebate, minimum volume commitment        : clause 4
CONTRACTS = {
    "SUP-1042": dict(
        currency="USD", price=1.9450, pieces_per_uom=1, whole_packs_only=False,
        buyer_pays_freight=False, freight_lane=None, shipments_per_year=12,
        payment_days=90, cash_discount=None,
        rebate=None, min_volume=None, shortfall_per_piece=None,
        spec_limit_pct=3.0),
    "SUP-2318": dict(
        currency="EUR", price=172.00, pieces_per_uom=100, whole_packs_only=True,
        buyer_pays_freight=True, freight_lane="LANE-DE-01", shipments_per_year=12,
        payment_days=30, cash_discount=None,
        # clause 4.2: banded, each rate applies only to the volume inside its band
        rebate=("banded", [(200000, 0.000), (400000, 0.015), (None, 0.030)]),
        min_volume=None, shortfall_per_piece=None,
        spec_limit_pct=2.0),
    "SUP-3155": dict(
        currency="MXN", price=33.55, pieces_per_uom=1, whole_packs_only=False,
        buyer_pays_freight=False, freight_lane=None, shipments_per_year=12,
        payment_days=60, cash_discount=None,
        rebate=None, min_volume=None, shortfall_per_piece=None,
        spec_limit_pct=7.0),
    "SUP-4077": dict(
        currency="GBP", price=1.4076, pieces_per_uom=1, whole_packs_only=False,
        buyer_pays_freight=True, freight_lane="LANE-UK-01", shipments_per_year=12,
        payment_days=60, cash_discount=(0.01, 10),
        # clause 4.2: 4.0% on all pieces, earned ONLY at >= 520,000 pieces
        rebate=("threshold", 520000, 0.040),
        # clause 4.1: minimum commitment with a per-piece shortfall charge
        min_volume=520000, shortfall_per_piece=0.35,
        spec_limit_pct=3.5),
}


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
# --- XLSX reading, standard library only -----------------------------------
# The supplier master is the one shipped input that is not plain text, and an
# .xlsx is a zip of XML parts, so the standard library reads it: no openpyxl,
# no pandas. The attempt's image preinstalls both and it may use them freely;
# this reference solution deliberately does not, so that it executes wherever
# CPython does and a review sandbox can always run it.
_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_DOC_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def _column_index(ref, fallback):
    """`C7` -> 2. The column letters of a cell reference, zero-based."""
    m = re.match(r"([A-Z]+)", ref or "")
    if not m:
        return fallback
    n = 0
    for ch in m.group(1):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read_xlsx(path):
    """{sheet name: [[cell, ...], ...]}, blank cells as None.

    Handles the two ways a writer stores text - inline `<is>` runs and the
    shared-string table - and otherwise hands back the string the cell
    carries, which is all this task needs from the master.
    """
    with zipfile.ZipFile(path) as zf:
        def xml(name):
            return ElementTree.fromstring(zf.read(name))

        shared = []
        if "xl/sharedStrings.xml" in zf.namelist():
            for si in xml("xl/sharedStrings.xml"):
                shared.append("".join(t.text or "" for t in si.iter(_MAIN + "t")))

        target = {rel.get("Id"): rel.get("Target")
                  for rel in xml("xl/_rels/workbook.xml.rels")}

        sheets = {}
        for sheet in xml("xl/workbook.xml").iter(_MAIN + "sheet"):
            part = target[sheet.get(_DOC_REL + "id")].lstrip("/")
            if not part.startswith("xl/"):
                part = "xl/" + part
            rows = []
            for row in xml(part).iter(_MAIN + "row"):
                cells = []
                for cell in row.iter(_MAIN + "c"):
                    idx = _column_index(cell.get("r"), len(cells))
                    while len(cells) < idx:
                        cells.append(None)
                    if cell.get("t") == "inlineStr":
                        value = "".join(t.text or "" for t in cell.iter(_MAIN + "t"))
                    else:
                        node = cell.find(_MAIN + "v")
                        value = None if node is None else node.text
                        if cell.get("t") == "s" and value is not None:
                            value = shared[int(value)]
                    cells.append(value)
                rows.append(cells)
            sheets[sheet.get("name")] = rows
    return sheets


def load_master():
    book = read_xlsx(DATA / "master" / "supplier_master.xlsx")
    names, alias = {}, {}
    for row in book["suppliers"][1:]:            # row 1 is the header
        if row and row[0]:
            names[str(row[0]).strip()] = str(row[1]).strip()
    for row in book["name_aliases"][1:]:
        if row and row[0]:
            alias[str(row[0]).strip().casefold()] = str(row[1]).strip()
    return names, alias


def load_po_supplier(alias):
    """po_id (mart number) -> supplier_code, resolved through the alias table."""
    out = {}
    with open(DATA / "purchasing" / "purchase_orders_2025.csv", encoding="utf-8",
              newline="") as fh:
        for r in csv.DictReader(fh):
            code = alias.get(r["supplier_name"].strip().casefold())
            if code:
                out[r["po_id"]] = code
    return out


def load_crosswalk():
    """ERP purchase order number -> mart reporting number (CHG-2025-0417)."""
    out = {}
    with open(DATA / "purchasing" / "po_reference_2025.csv", encoding="utf-8",
              newline="") as fh:
        for r in csv.DictReader(fh):
            out[r["erp_po_number"].strip()] = r["mart_po_id"].strip()
    return out


def load_lot_supplier(po_supplier, crosswalk=None, *, use_crosswalk=True):
    """lot_id -> supplier_code. The goods receipt is the authoritative link
    between an inspected lot and the supplier that shipped it.

    Receipts posted after the ERP go-live reference the ERP purchase order
    number, not the mart number the purchasing extract carries; the crosswalk
    resolves them. Without it every post-cutover lot fails to join and drops
    out of the reject rates without a trace.
    """
    crosswalk = crosswalk if (crosswalk is not None and use_crosswalk) else {}
    out = {}
    with open(DATA / "purchasing" / "goods_receipts_2025.csv", encoding="utf-8",
              newline="") as fh:
        for r in csv.DictReader(fh):
            po = r["po_id"].strip()
            po = crosswalk.get(po, po)
            code = po_supplier.get(po)
            if code:
                out[r["lot_id"]] = code
    return out


def load_defect_rates(lot_supplier, alias=None, *, points=("INCOMING",),
                      keep="first", attribute_by="receipt"):
    """Per-supplier incoming inspection, deduplicated on lot_id.

    Only INCOMING records describe pieces Cadence received, pays for and
    dispositions. SOURCE records are the supplier-quality engineer's
    pre-shipment inspection of the same lot at the supplier's plant: pieces
    failed there are scrapped or reworked at the seller's own cost, the seller
    makes the tendered quantity good, and the lot is inspected again on
    receipt. Pooling the two counts the lot twice and charges Cadence for
    pieces it never bought.

    Two reject populations come out of the incoming records, because a lot's
    nonconforming pieces are dispositioned one of two ways (QP-07 section 4):
    scrapped by Cadence, or returned to the seller and replaced free of charge
    within the contract year (clause 5.4). Both are rejects. Only the scrapped
    pieces are a loss the purchase quantity has to carry.

    The free-text `supplier` field in the inspection log is blank on a large
    minority of records and inconsistently spelled on the rest, so attribution
    goes through lot_id, not that field.
    """
    seen = {}
    with open(DATA / "quality" / "incoming_inspection_2025.jsonl", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("part_number") != "SP-40":
                continue
            if points is not None and rec.get("inspection_point") not in points:
                continue
            # a lot keyed twice by the QMS is one physical lot
            key = rec["lot_id"] if keep != "none" else rec["inspection_id"]
            if key not in seen:
                seen[key] = rec
            elif keep == "first" and rec["inspection_id"] < seen[key]["inspection_id"]:
                seen[key] = rec
            elif keep == "last" and rec["inspection_id"] > seen[key]["inspection_id"]:
                seen[key] = rec

    agg = {c: dict(lots=0, units=0, rejected=0, scrapped=0) for c in CANDIDATES}
    for rec in seen.values():
        if attribute_by == "receipt":
            code = lot_supplier.get(rec["lot_id"])
        else:
            code = alias.get((rec.get("supplier") or "").strip().casefold())
        if code not in agg:          # terminated / non-candidate supplier, or unattributed
            continue
        agg[code]["lots"] += 1
        agg[code]["units"] += int(rec["qty_inspected"])
        agg[code]["rejected"] += int(rec["qty_rejected"])
        if rec.get("disposition") == "SCRAP":
            agg[code]["scrapped"] += int(rec["qty_rejected"])
    for code, a in agg.items():
        a["returned"] = a["rejected"] - a["scrapped"]
        a["rate"] = a["rejected"] / a["units"]              # what the file reports
        a["loss_rate"] = a["scrapped"] / a["units"]         # what the buy carries
    return agg


def load_demand(*, cycle="frozen", window="contract", include_totals=False):
    """FY2026 good-unit requirement for SP-40.

    The planning-cube dump carries the last two S&OP cycles side by side, a
    TOTAL subtotal row per part and cycle, a second part, and a rolling
    fifteen-month horizon. The plan of record is the cycle the plan was frozen
    at, which is the latest one in the dump; the period is the contract year
    the four offers cover.
    """
    rows = []
    with open(DATA / "demand" / "forecast_2026.csv", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["part_number"].strip() != "SP-40":
                continue
            if r["month"].strip().upper() == "TOTAL" and not include_totals:
                continue
            rows.append(r)
    cycles = sorted({r["plan_cycle"].strip() for r in rows})
    if cycle == "frozen":
        wanted = {cycles[-1]}
    elif cycle == "all":
        wanted = set(cycles)
    else:
        wanted = {cycle}

    spans = {"contract": (CONTRACT_FROM, CONTRACT_TO),
             "calendar": ("2026-01", "2026-12"),
             "horizon": ("0000-00", "9999-99")}
    lo, hi = spans[window]

    total = 0
    for r in rows:
        if r["plan_cycle"].strip() not in wanted:
            continue
        month = r["month"].strip().upper()
        if month == "TOTAL":
            total += int(r["good_units_required"])
            continue
        if lo <= month <= hi:
            total += int(r["good_units_required"])
    return total


def load_freight():
    out = {}
    with open(DATA / "logistics" / "freight_tariff_2026.csv", encoding="utf-8",
              newline="") as fh:
        for r in csv.DictReader(fh):
            out[r["lane_id"]] = (float(r["usd_per_1000_pieces"]),
                                 float(r["brokerage_usd_per_shipment"]))
    return out


def load_fx_2025_average():
    """2025 daily export averaged - what the finance memo says NOT to use."""
    sums = {"EUR": 0.0, "GBP": 0.0, "MXN": 0.0}
    n = 0
    with open(DATA / "fx" / "fx_daily_2025.csv", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            sums["EUR"] += float(r["usd_per_eur"])
            sums["GBP"] += float(r["usd_per_gbp"])
            sums["MXN"] += float(r["usd_per_mxn"])
            n += 1
    out = {k: v / n for k, v in sums.items()}
    out["USD"] = 1.0
    return out


# ---------------------------------------------------------------------------
# Cost model
# ---------------------------------------------------------------------------
def rebate_usd(spec, units, unit_price_usd, material_usd, *, banded=True, threshold=True):
    if not spec["rebate"]:
        return 0.0
    kind = spec["rebate"][0]
    if kind == "banded":
        if not banded:
            # the careless reading: the whole year re-rated at the top band
            top = spec["rebate"][1][-1][1]
            return material_usd * top
        total, low = 0.0, 0
        for cap, pct in spec["rebate"][1]:
            high = units if cap is None else min(units, cap)
            if high > low:
                total += (high - low) * unit_price_usd * pct
            low = high
            if cap is not None and units <= cap:
                break
        return total
    thr, pct = spec["rebate"][1], spec["rebate"][2]
    if not threshold:
        return material_usd * pct
    return material_usd * pct if units >= thr else 0.0


def payment_terms_usd(spec, material_usd):
    """Negative = benefit. Where a cash discount exists, plan on whichever
    settlement date is cheaper (finance memo, section 3). A discount taken
    reduces the spend base before the earlier date is valued."""
    def carry(spend, days):
        return spend * WACC * (BASELINE_DAYS - days) / 365.0

    standard = carry(material_usd, spec["payment_days"])
    if not spec["cash_discount"]:
        return standard
    pct, day = spec["cash_discount"]
    early = -material_usd * pct + carry(material_usd * (1.0 - pct), day)
    return min(early, standard)


def cost_build(code, defect, good_units, freight, *, fx=None, loss="scrap",
               gross_up=True, whole_packs=True, charge_freight=True, banded=True,
               threshold=True, shortfall=True, disposal=True, terms=True,
               rounded_price=False):
    spec = CONTRACTS[code]
    fx = fx or FX
    unit_price = spec["price"] * fx[spec["currency"]] / spec["pieces_per_uom"]
    price_used = round(unit_price, 4) if rounded_price else unit_price

    # a rejected piece is a loss only where Cadence scraps it: pieces returned
    # on an authorisation are replaced free of charge inside the contract year
    # (contracts, clause 5.4), so the buy has to carry the scrapped share
    rate = defect["loss_rate"] if loss == "scrap" else defect["rate"]
    units = math.ceil(good_units / (1 - rate)) if gross_up else good_units
    if whole_packs and spec["whole_packs_only"]:
        pack = spec["pieces_per_uom"]
        units = int(math.ceil(units / pack) * pack)
    scrapped = units - good_units

    material = units * price_used
    frt = 0.0
    if spec["buyer_pays_freight"] and charge_freight:
        per_k, brokerage = freight[spec["freight_lane"]]
        frt = units / 1000.0 * per_k + spec["shipments_per_year"] * brokerage
    reb = rebate_usd(spec, units, price_used, material, banded=banded, threshold=threshold)
    short = 0.0
    if shortfall and spec["min_volume"] and units < spec["min_volume"]:
        short = ((spec["min_volume"] - units)
                 * spec["shortfall_per_piece"] * fx[spec["currency"]])
    disposal_usd = scrapped * DISPOSAL_USD_PER_SCRAPPED if disposal else 0.0
    terms_usd = payment_terms_usd(spec, material) if terms else 0.0

    total = material + frt - reb + short + disposal_usd + terms_usd
    return dict(unit_price=unit_price, units=units, scrapped=scrapped,
                material=material, freight=frt, rebate=reb,
                shortfall=short, disposal=disposal_usd, terms=terms_usd,
                total=total, per_good=total / good_units,
                rate=defect["rate"], loss_rate=rate)


def breakeven_loss_rate(code, defect, target_total, good_units, freight):
    """Scrap loss rate at which `code` costs exactly `target_total`."""
    lo, hi = 0.0, 0.30
    for _ in range(80):
        mid = (lo + hi) / 2.0
        probe = dict(defect, loss_rate=mid)
        if cost_build(code, probe, good_units, freight)["total"] < target_total:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def build(good_units, defects, freight, **choices):
    rows = {}
    for code in CANDIDATES:
        rows[code] = cost_build(code, defects[code], good_units, freight, **choices)
    order = sorted(CANDIDATES, key=lambda c: rows[c]["per_good"])
    for i, code in enumerate(order, start=1):
        rows[code]["rank"] = i
    return rows, order


# ---------------------------------------------------------------------------
# Deliverables
# ---------------------------------------------------------------------------
def money(x):
    return "{:.2f}".format(x + 0.0)


def analysis_notes(choices=None):
    """What this run actually did, as the booleans the memo describes itself by.

    The memo has to describe the run that produced the figures printed beside
    it. The provenance harness re-runs this module with one analysis choice
    changed at a time; a memo that claimed a correction its own run did not
    make would hand the simulated attempt credit no real attempt could earn,
    and the measured cost of a wrong path is the whole point of running it.
    Defaults are the correct reading, so the reference memo is unchanged.
    """
    c = choices or {}
    lot = c.get("lot_kw") or {}
    defect = c.get("defect_kw") or {}
    demand = c.get("demand_kw") or {}
    build = c.get("build_kw") or {}
    return dict(
        incoming_only=defect.get("points", ("INCOMING",)) is not None,
        by_receipt=defect.get("attribute_by", "receipt") == "receipt",
        deduped=defect.get("keep", "first") != "none",
        crosswalked=lot.get("use_crosswalk", True),
        window=demand.get("window", "contract"),
        cycle=demand.get("cycle", "frozen"),
        totals_dropped=not demand.get("include_totals", False),
        scrapped_only=build.get("loss", "scrap") == "scrap",
        grossed_up=build.get("gross_up", True),
    )


# Per demand window: how the Cost Comparison names the period, how the header
# dates it, and what to call it. Only the first is the contract year.
WINDOW_PROSE = {
    "contract": ("the contract year the four offers cover, April 2026 through "
                 "March 2027", "contract year 1 April 2026 - 31 March 2027"),
    "calendar": ("calendar 2026, January through December 2026",
                 "calendar year 1 January 2026 - 31 December 2026"),
    "horizon": ("the whole rolling fifteen-month cube horizon, January 2026 "
                "through March 2027", "cube horizon January 2026 - March 2027"),
}


def write_outputs(names, defects, rows, order, good_units, freight, source_stats,
                  choices=None):
    OUT.mkdir(parents=True, exist_ok=True)
    did = analysis_notes(choices)
    window_phrase, window_dates = WINDOW_PROSE[did["window"]]

    # legal names contain commas, so the text fields are RFC 4180 quoted
    with open(OUT / "supplier_costs.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["supplier_code", "supplier_name", "quoted_price_usd_per_unit",
                    "units_to_purchase", "total_fy2026_cost_usd",
                    "cost_per_good_unit_usd", "rank"])
        for code in order:
            r = rows[code]
            w.writerow([code, names[code], "{:.4f}".format(r["unit_price"]),
                        r["units"], "{:.2f}".format(r["total"]),
                        "{:.4f}".format(r["per_good"]), r["rank"]])

    # how each total is built up: one row per element charged, summing to the
    # total filed above. The labels are this solution's own; the prompt leaves
    # the decomposition to the attempt and binds only the sum.
    elements = [("material", "material"), ("inbound_freight", "freight"),
                ("volume_rebate", "rebate"), ("shortfall_charge", "shortfall"),
                ("scrap_disposal", "disposal"), ("payment_terms", "terms")]
    with open(OUT / "cost_buildup.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["supplier_code", "cost_element", "amount_usd"])
        for code in sorted(CANDIDATES):
            r = rows[code]
            charged = [(label, -r[key] if key == "rebate" else r[key])
                       for label, key in elements]
            for label, amount in sorted(charged):
                w.writerow([code, label, "{:.2f}".format(amount + 0.0)])

    with open(OUT / "defect_rates.csv", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("supplier_code,lots_inspected,units_inspected,units_rejected,"
                 "reject_rate_pct\n")
        for code in sorted(CANDIDATES):
            d = defects[code]
            fh.write("{},{},{},{},{:.3f}\n".format(
                code, d["lots"], d["units"], d["rejected"], 100.0 * d["rate"]))

    win, second = order[0], order[1]
    w, s = rows[win], rows[second]
    margin = s["total"] - w["total"]
    # what taking SUP-4077's early-settlement discount would cost against
    # its standard date (finance memo, section 3: plan on the cheaper)
    spec4077, mat4077 = CONTRACTS["SUP-4077"], rows["SUP-4077"]["material"]
    pct, day = spec4077["cash_discount"]
    discount_penalty = ((-mat4077 * pct + mat4077 * (1 - pct) * WACC * (BASELINE_DAYS - day) / 365.0)
                        - mat4077 * WACC * (BASELINE_DAYS - spec4077["payment_days"]) / 365.0)

    def line(code):
        r = rows[code]
        return ("| {} | {} | USD {:.4f} | {:,} | USD {:.2f} | USD {:.4f} | {} |".format(
            code, names[code], r["unit_price"], r["units"], r["total"],
            r["per_good"], r["rank"]))

    md = []
    md.append("# FY2026 SP-40 valve-seat sourcing award\n")
    md.append("Prepared for the sourcing steering committee. All figures in US "
              "dollars at the mandated FY2026 planning rates, for the full "
              "{}.\n".format(window_dates))

    md.append("## Recommendation\n")
    md.append("Award the full FY2026 SP-40 volume to **{} ({})**, contracting "
              "**{:,} pieces** for the contract year.\n".format(
                  names[win], win, w["units"]))
    md.append("Its FY2026 total cost to Cadence is **USD {}**, which is "
              "**USD {} lower over the contract year** than the second-ranked "
              "offer from {} ({}, USD {}). On a cost-per-good-unit basis that "
              "is USD {:.4f} against USD {:.4f}, a {:.2f}% advantage.\n".format(
                  money(w["total"]), money(margin), names[second], second,
                  money(s["total"]), w["per_good"], s["per_good"],
                  100.0 * (s["per_good"] / w["per_good"] - 1)))
    md.append("This is a single-supplier award for the full contract-year "
              "volume, as directed.\n")

    md.append("## Cost Comparison\n")
    cycle_phrase = ("the frozen November S&OP cycle" if did["cycle"] == "frozen"
                    else "the superseded October S&OP cycle")
    md.append("The FY2026 good-unit requirement worked to is **{:,} SP-40 "
              "pieces** - the monthly SP-40 rows of {} that fall in {}, with "
              "the `TOTAL` subtotal rows {} and every SP-22 row excluded. "
              "{}\n".format(
                  good_units, cycle_phrase, window_phrase,
                  "excluded" if did["totals_dropped"] else "counted in",
                  ("The cube dump is a rolling fifteen-month horizon, so its "
                   "January-March 2026 rows sit before the contract year and "
                   "are excluded, as is the superseded October cycle. Read as "
                   "calendar 2026 the same cycle gives {:,} pieces and read "
                   "whole it gives {:,}; neither is the period this contract "
                   "covers.".format(source_stats["calendar_units"],
                                    source_stats["horizon_units"])
                   if did["window"] == "contract" else
                   "The dump is the cube's whole rolling fifteen-month horizon "
                   "and is taken over that period as it stands.")))
    md.append("| supplier_code | supplier_name | quoted USD/piece | units to "
              "purchase | FY2026 total USD | USD per good unit | rank |")
    md.append("| --- | --- | --- | --- | --- | --- | --- |")
    for code in order:
        md.append(line(code))
    md.append("")
    md.append("Build-up of each supplier's FY2026 total cost. Every element "
              "charged is shown; the elements add up to the total filed in "
              "supplier_costs.csv.\n")
    md.append("| supplier_code | material | inbound freight | volume rebate | "
              "shortfall charge | scrap disposal | payment terms | total |")
    md.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for code in order:
        r = rows[code]
        md.append("| {} | USD {} | USD {} | USD {} | USD {} | USD {} | USD {} | USD {} |".format(
            code, money(r["material"]), money(r["freight"]),
            money(-r["rebate"]), money(r["shortfall"]), money(r["disposal"]),
            money(r["terms"]), money(r["total"])))
    md.append("")
    if not did["grossed_up"]:
        basis = ("Each purchase quantity is the requirement itself: the buy is "
                 "not grossed up for supplier quality losses. ")
    elif did["scrapped_only"]:
        basis = ("Each purchase quantity follows from that requirement. A "
                 "piece rejected at incoming inspection costs Cadence a piece "
                 "only where Cadence scraps it: pieces returned to the seller "
                 "on an authorisation are replaced at the seller's cost inside "
                 "the contract year and are not invoiced again (clause 5.4 of "
                 "every term sheet). The buy is therefore the requirement "
                 "grossed up for the share of each supplier's inspected pieces "
                 "that Cadence actually scrapped in 2025 - {} - rounded up to "
                 "the next whole piece: {}. ".format(
                     ", ".join("{} {:.3f}%".format(c, 100 * rows[c]["loss_rate"])
                               for c in sorted(CANDIDATES)),
                     ", ".join("{} {:,}".format(c, rows[c]["units"])
                               for c in sorted(CANDIDATES))))
    else:
        basis = ("Each purchase quantity follows from that requirement, "
                 "grossed up for every piece each supplier had rejected at "
                 "incoming inspection in 2025 - {} - rounded up to the next "
                 "whole piece: {}. ".format(
                     ", ".join("{} {:.3f}%".format(c, 100 * rows[c]["rate"])
                               for c in sorted(CANDIDATES)),
                     ", ".join("{} {:,}".format(c, rows[c]["units"])
                               for c in sorted(CANDIDATES))))
    md.append(basis + "SUP-2318 is bought in whole 100-piece boxes (clause "
              "1: partial boxes are not tendered), so its quantity is rounded "
              "up to the next box, {:,} pieces.\n".format(rows["SUP-2318"]["units"]))

    md.append("## Basis of Decision\n")
    md.append("Five things separate these offers, and none of them is the "
              "headline price.\n")
    cheapest = min(CANDIDATES, key=lambda c: rows[c]["unit_price"])
    md.append("**Quoted price is the weakest signal.** Restated in US dollars "
              "per piece at the mandated planning rates, the recommended "
              "supplier {} holds the *highest* quoted price of the four at "
              "USD {:.4f}, against USD {:.4f} for the cheapest quote, {}. "
              "Note that SUP-2318 quotes per 100-piece box rather than per "
              "piece. Ranking on quoted price alone awards the contract to "
              "{}, and it is the wrong answer.\n".format(
                  win, rows[win]["unit_price"], rows[cheapest]["unit_price"],
                  cheapest, cheapest))
    md.append("**What Cadence scraps decides the purchase quantity.** The four "
              "suppliers reject at {} of inspected pieces, but they are not "
              "dispositioned alike: {} of SUP-1042's rejected pieces went back "
              "to the seller on a return authorisation and were replaced free "
              "of charge, against {} of SUP-4077's. On the pieces Cadence "
              "actually scrapped the four run at {}, and that is what the buy "
              "has to carry. It moves the purchase quantity by {:,} pieces "
              "between the best and worst supplier and is the reason SUP-3155 "
              "cannot win on its low peso price.\n".format(
                  ", ".join("{} {:.2f}%".format(c, 100 * rows[c]["rate"])
                            for c in sorted(CANDIDATES)),
                  "{:,} of {:,}".format(defects["SUP-1042"]["returned"],
                                        defects["SUP-1042"]["rejected"]),
                  "{:,} of {:,}".format(defects["SUP-4077"]["returned"],
                                        defects["SUP-4077"]["rejected"]),
                  ", ".join("{} {:.3f}%".format(c, 100 * rows[c]["loss_rate"])
                            for c in sorted(CANDIDATES)),
                  max(rows[c]["units"] for c in CANDIDATES)
                  - min(rows[c]["units"] for c in CANDIDATES)))
    md.append("**Two offers are origin-term, two are delivered.** SUP-2318 and "
              "SUP-4077 are FCA at the seller's works, so Cadence pays inbound "
              "freight, duty and brokerage on those lanes: USD {} and USD {} "
              "respectively across twelve monthly shipments. SUP-1042 and "
              "SUP-3155 are DDP and carry no separate freight.\n".format(
                  money(rows["SUP-2318"]["freight"]),
                  money(rows["SUP-4077"]["freight"])))
    md.append("**The Brackenridge volume terms do not pay out at our "
              "volume.** SUP-4077's 4.0% rebate is earned only at 520,000 "
              "pieces or more in the contract year (clause 4.2), and clause "
              "4.1 commits Cadence to that same 520,000 pieces or a GBP 0.35 "
              "per piece shortfall charge. At our requirement the buy is "
              "{:,} pieces - {:,} short. So the rebate is worth nothing and "
              "the shortfall charge costs USD {}. Its 1% 10 cash discount is "
              "not worth taking: at 9.0% cost of capital the standard Net 60 "
              "date is USD {} cheaper, and that is what is planned on. "
              "Rheinwerk's banded rebate is also worth less than it "
              "looks: clause 4.2 rates each band separately rather than "
              "re-rating the whole year at 3.0%, which is USD {} rather than "
              "USD {}.\n".format(
                  rows["SUP-4077"]["units"],
                  520000 - rows["SUP-4077"]["units"],
                  money(rows["SUP-4077"]["shortfall"]),
                  money(discount_penalty),
                  money(rows["SUP-2318"]["rebate"]),
                  money(rows["SUP-2318"]["material"] * 0.03)))
    md.append("**Payment terms are worth more than the margin.** Valued "
              "against the Net 30 baseline at 9.0% cost of capital, SUP-1042's "
              "Net 90 is worth USD {} to Cadence and SUP-4077's Net 60 USD {}. "
              "The gap between them is larger than the USD {} that separates "
              "the two offers.\n".format(
                  money(-rows["SUP-1042"]["terms"]),
                  money(-rows["SUP-4077"]["terms"]), money(margin)))
    md.append("Netting all of it, {} wins on total FY2026 cost despite holding "
              "the highest quoted price. SUP-4077 loses on freight, the "
              "shortfall charge and the rebate it does not earn, and finishes "
              "USD {} behind at USD {}; SUP-2318 loses on USD {} of freight "
              "and a rebate worth USD {} rather than its headline rate, at USD "
              "{}; SUP-3155 loses on the {:.3f}% of inspected pieces Cadence "
              "scrapped, which forces the largest buy at {:,} pieces and a USD "
              "{} disposal bill, at USD {}.\n".format(
                  win, money(margin), money(rows["SUP-4077"]["total"]),
                  money(rows["SUP-2318"]["freight"]),
                  money(rows["SUP-2318"]["rebate"]),
                  money(rows["SUP-2318"]["total"]),
                  100 * rows["SUP-3155"]["loss_rate"], rows["SUP-3155"]["units"],
                  money(rows["SUP-3155"]["disposal"]),
                  money(rows["SUP-3155"]["total"])))

    md.append("## Data Quality and Exclusions\n")
    if did["incoming_only"]:
        md.append("- **Source inspections excluded from the reject rates.** The "
                  "inspection log carries {} `SOURCE` records alongside the "
                  "`INCOMING` ones: pre-shipment inspections by Cadence "
                  "supplier-quality engineers at the supplier's plant, {} of them "
                  "on SUP-1042 lots. Pieces failed at source are scrapped or "
                  "reworked at the seller's cost, the seller makes the tendered "
                  "quantity good, and the lot is inspected again on receipt. Only "
                  "`INCOMING` records describe pieces Cadence paid for and "
                  "dispositioned, so only they enter the reject rates. Pooling the "
                  "two counts those lots twice and lifts SUP-1042's scrap loss "
                  "rate from {:.3f}% to about {:.3f}%, which hands the award to "
                  "SUP-4077.\n".format(
                      source_stats["rows"], source_stats["rows_1042"],
                      100 * rows["SUP-1042"]["loss_rate"],
                      100 * source_stats["pooled_loss_1042"]))
    else:
        md.append("- **Inspection records counted.** Every SP-40 inspection "
                  "record in the QMS log was counted towards the reject rates, "
                  "including the {} `SOURCE` records the supplier-quality "
                  "engineers keyed at the suppliers' plants: they are "
                  "inspections of the same part and are reported on the same "
                  "log.\n".format(source_stats["rows"]))
    if did["scrapped_only"]:
        md.append("- **Returned pieces excluded from the purchase gross-up.** "
                  "{:,} of the {:,} pieces rejected at incoming inspection across "
                  "the four candidates went back to the seller against a return "
                  "authorisation and were replaced at the seller's cost inside the "
                  "contract year, leaving {:,} scrapped; the returned pieces are "
                  "rejects but they are not a loss and they carry no disposal "
                  "charge. They stay in `reject_rate_pct`, "
                  "which the brief defines as rejected pieces over inspected "
                  "pieces, and they are out of both the purchase quantity and the "
                  "disposal charge. Grossing the buy up on every reject instead "
                  "buys {:,} pieces too many from SUP-1042 and hands the award to "
                  "SUP-4077.\n".format(
                      source_stats["returned_total"], source_stats["rejected_total"],
                      source_stats["rejected_total"] - source_stats["returned_total"],
                      source_stats["overbuy_1042"]))
    else:
        md.append("- **Rejected pieces treated alike.** All {:,} pieces "
                  "rejected at incoming inspection across the four candidates "
                  "were carried in `reject_rate_pct`, in the purchase "
                  "gross-up and in the disposal charge, whichever disposition "
                  "the inspector recorded against them.\n".format(
                      source_stats["rejected_total"]))
    if did["crosswalked"]:
        md.append("- **Post-cutover receipts resolved to their purchase orders.** "
                  "Purchasing and receiving moved to the new ERP on {} "
                  "(CHG-2025-0417). Receipts posted from that date carry the "
                  "ERP's ten-digit purchase order number, which does not exist "
                  "in the purchasing extract; `po_reference_2025.csv` "
                  "carries both numbers. Joining receipts to purchase "
                  "orders on the number as posted silently loses every lot received "
                  "after go-live - {} of {} inspected lots - and those lots carry "
                  "most of SUP-3155's rejects: without them its scrap loss rate "
                  "reads about {:.3f}% instead of {:.3f}% and the award flips to "
                  "SUP-3155.\n".format(
                      ERP_GO_LIVE, source_stats["post_lots"], source_stats["lots"],
                      100 * source_stats["pre_loss_3155"],
                      100 * rows["SUP-3155"]["loss_rate"]))
    else:
        md.append("- **Receipts joined to purchase orders on the posted "
                  "number.** Inspection lots were tied to a supplier through "
                  "the goods receipt's `po_id` as the receipt carries it. "
                  "Receipts that did not match a purchase order in the "
                  "purchasing extract carry no supplier and are not in the "
                  "reject rates.\n")
    if did["by_receipt"]:
        md.append("- **Supplier identity.** Purchasing, quality and the supplier "
                  "master each spell supplier names differently, and the "
                  "inspection log's free-text `supplier` field is blank or null "
                  "on a large minority of lots (the QMS interface stopped "
                  "receiving it at the ERP go-live). Records were resolved to "
                  "supplier codes through the `name_aliases` sheet of the supplier "
                  "master, and inspection lots were attributed by `lot_id` "
                  "through the goods receipt to the purchase order and then to "
                  "the supplier code. Attributing on the free-text field instead "
                  "drops the unattributed lots, and those lots are not randomly "
                  "distributed: doing so understates SUP-3155's loss rate by "
                  "roughly two thirds and reverses the award.\n")
    else:
        md.append("- **Supplier identity.** Inspection records were attributed "
                  "to suppliers on the log's own `supplier` field, resolved to "
                  "supplier codes through the `name_aliases` sheet of the "
                  "supplier master. Records whose `supplier` field is blank or "
                  "null carry no supplier code and are not in the reject "
                  "rates.\n")
    if did["deduped"]:
        md.append("- **Double-logged inspection lots.** The inspection log "
                  "contains repeated `INCOMING` records for the same `lot_id` "
                  "under different `inspection_id` values. These are one "
                  "physical lot each and were deduplicated on `lot_id` before "
                  "any rate was computed.\n")
    else:
        md.append("- **Inspection records counted as keyed.** Every record in "
                  "the QMS log was counted as it stands, including repeated "
                  "records for the same `lot_id` under different "
                  "`inspection_id` values.\n")
    md.append("- **Non-candidate supplier.** SUP-9001, Old Harbor Machine "
              "Company, appears throughout the 2025 purchasing, receipt and "
              "inspection data. It is shown as terminated 2025-09-30 in the "
              "supplier master, returned no FY2026 offer, and is excluded from "
              "the award comparison and from the defect table.\n")
    md.append("- **Purchase orders.** Cancelled purchase orders have no "
              "receipts and no inspected lots and affect nothing. SP-22 "
              "purchase orders are a different part and are out of scope.\n")
    if did["window"] == "contract" and did["cycle"] == "frozen":
        md.append("- **Demand.** The planning-cube dump carries the superseded "
                  "October S&OP cycle beside the frozen November one, a `TOTAL` "
                  "subtotal row for each part and cycle, and a rolling "
                  "fifteen-month horizon that runs three months past the contract "
                  "year. Only the twelve monthly SP-40 rows of the November cycle "
                  "from April 2026 to March 2027 were used. The October cycle "
                  "reads {:,} pieces over the same window and the whole November "
                  "horizon reads {:,}; either one, or the calendar-2026 reading of "
                  "{:,}, pushes the buy past SUP-4077's 520,000-piece rebate "
                  "threshold and flips the award.\n".format(
                      source_stats["oct_units"], source_stats["horizon_units"],
                      source_stats["calendar_units"]))
    else:
        md.append("- **Demand.** The requirement was read off the "
                  "planning-cube dump: the SP-40 rows of {}, over {}. SP-22 is "
                  "a different part on a separate agreement and is out of "
                  "scope.\n".format(cycle_phrase, window_phrase))
    md.append("- **Exchange rates.** FY2026 figures use the mandated Treasury "
              "planning rates from the finance memo, not 2025 daily actuals. "
              "The 2025 daily export averages materially below the planning "
              "rates and using it would flatter the peso and sterling offers.\n")
    md.append("- **Specification limits are not forecasts.** Clause 5 of each "
              "term sheet caps the acceptable reject rate; all four suppliers "
              "ran inside their cap in 2025. The caps are contractual ceilings, "
              "so observed 2025 performance was used for planning.\n")

    md.append("## Risks and Sensitivities\n")
    md.append("- **The margin is {:.2f}% of contract value.** {} beats {} by "
              "USD {} on USD {} of annual spend. It is a real but not "
              "commanding lead, and it is sensitive to quality drift more than "
              "to anything else.\n".format(
                  100.0 * margin / w["total"], win, second, money(margin),
                  money(w["total"])))
    breakeven = breakeven_loss_rate(win, defects[win], s["total"], good_units, freight)
    md.append("- **Quality drift is the live risk.** {}'s 2025 incoming reject "
              "rate is {:.2f}% and the share Cadence scrapped is {:.3f}%. "
              "Holding everything else, its FY2026 cost matches the "
              "second-ranked offer once the scrapped share reaches about "
              "{:.2f}%, and its clause 5 specification cap of {:.1f}% leaves "
              "contractual room to drift that far without breaching the "
              "agreement. Incoming quality, not price, is what this award "
              "rides on.\n".format(
                  win, 100 * rows[win]["rate"], 100 * rows[win]["loss_rate"],
                  100 * breakeven, CONTRACTS[win]["spec_limit_pct"]))
    if did["scrapped_only"]:
        md.append("- **The return route is a commercial arrangement, not a "
                  "quality one.** {}'s advantage rests on {:,} of its {:,} "
                  "rejected pieces going back on a return authorisation rather "
                  "than into the scrap cage, which is practical because the lane "
                  "is a one-day domestic truck movement. If FY2026 returns are "
                  "not authorised at the 2025 rate the buy quantity and the "
                  "disposal bill both move against this recommendation, and the "
                  "award is worth revisiting; an FY2026 return-authorisation "
                  "commitment belongs in the agreement.\n".format(
                      win, defects[win]["returned"], defects[win]["rejected"]))
    if did["incoming_only"]:
        md.append("- **The incoming rate depends on the source sort.** On the {} "
                  "SUP-1042 lots that were source-inspected in 2025, the engineer "
                  "rejected {:.1f}% of pieces at the plant before they shipped. "
                  "The low incoming rate is partly the product of that sorting; "
                  "if source inspection is scaled back in FY2026, incoming "
                  "quality could move toward the breakeven above. Keeping the "
                  "source-inspection cadence is a condition of the award.\n".format(
                      source_stats["rows_1042"], 100 * source_stats["source_rate_1042"]))
    md.append("- **Concentration.** Consolidating the part onto one supplier "
              "removes the current split and leaves no qualified running "
              "alternative. SUP-3155 offers the shortest lead time at 18 days "
              "and is the natural contingency to keep qualified, but its "
              "post-July reject performance has to be corrected first.\n")
    md.append("- **Currency.** The award is priced in US dollars and carries "
              "no FX exposure. The three foreign-currency offers do; the peso "
              "offer explicitly places all currency movement on Cadence. A "
              "10% adverse move against the euro or sterling would widen this "
              "recommendation's lead, not narrow it.\n")
    md.append("- **Volume.** If FY2026 SP-40 demand were to rise above roughly "
              "508,000 good units, SUP-4077's buy would cross 520,000 pieces, "
              "its rebate would begin to pay and its shortfall charge would "
              "disappear, which is the one demand scenario that changes the "
              "answer.\n")

    with open(OUT / "recommendation.md", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(md) + "\n")


def source_statistics(lot_supplier, crosswalk, alias, good_units, freight):
    """Figures the memo quotes about the excluded populations."""
    rows = rows_1042 = src_units = src_rej = 0
    with open(DATA / "quality" / "incoming_inspection_2025.jsonl", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("inspection_point") == "SOURCE":
                rows += 1
                if lot_supplier.get(rec["lot_id"]) == "SUP-1042":
                    rows_1042 += 1
                    src_units += int(rec["qty_inspected"])
                    src_rej += int(rec["qty_rejected"])
    pooled = load_defect_rates(lot_supplier, alias, points=None)
    correct = load_defect_rates(lot_supplier, alias)
    no_xwalk = load_defect_rates(load_lot_supplier(load_po_supplier(alias), crosswalk,
                                                   use_crosswalk=False), alias)
    over = (math.ceil(good_units / (1 - correct["SUP-1042"]["rate"]))
            - math.ceil(good_units / (1 - correct["SUP-1042"]["loss_rate"])))
    return dict(rows=rows, rows_1042=rows_1042,
                source_rate_1042=src_rej / src_units,
                pooled_loss_1042=pooled["SUP-1042"]["loss_rate"],
                lots=sum(correct[c]["lots"] for c in CANDIDATES),
                post_lots=sum(correct[c]["lots"] - no_xwalk[c]["lots"] for c in CANDIDATES),
                pre_loss_3155=no_xwalk["SUP-3155"]["loss_rate"],
                rejected_total=sum(correct[c]["rejected"] for c in CANDIDATES),
                returned_total=sum(correct[c]["returned"] for c in CANDIDATES),
                overbuy_1042=over,
                calendar_units=load_demand(window="calendar"),
                horizon_units=load_demand(window="horizon"),
                oct_units=load_demand(cycle="2025-10"))


def main():
    names, alias = load_master()
    po_supplier = load_po_supplier(alias)
    crosswalk = load_crosswalk()
    lot_supplier = load_lot_supplier(po_supplier, crosswalk)
    defects = load_defect_rates(lot_supplier, alias)
    good_units = load_demand()
    freight = load_freight()
    rows, order = build(good_units, defects, freight)
    stats = source_statistics(lot_supplier, crosswalk, alias, good_units, freight)
    write_outputs(names, defects, rows, order, good_units, freight, stats)

    print("FY2026 SP-40 good units required:", good_units)
    for code in order:
        r = rows[code]
        print("  {} rank={} units={} total={:.2f} per_good={:.4f} reject={:.3f}% "
              "scrapped={:.3f}%".format(
                  code, r["rank"], r["units"], r["total"], r["per_good"],
                  100 * r["rate"], 100 * r["loss_rate"]))
    print("award:", order[0])


if __name__ == "__main__":
    main()
