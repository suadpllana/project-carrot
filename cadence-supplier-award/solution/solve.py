#!/usr/bin/env python3
"""Reference solution: FY2026 SP-40 valve-seat sourcing award.

Reads only the shipped inputs under /workspace/data and writes the three
graded deliverables to /workspace/output. Deterministic: no network, no clock,
no randomness.

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
from pathlib import Path

import openpyxl

DATA = Path(os.environ.get("CADENCE_DATA", "/workspace/data"))
OUT = Path(os.environ.get("CADENCE_OUT", "/workspace/output"))

CANDIDATES = ["SUP-1042", "SUP-2318", "SUP-3155", "SUP-4077"]
ERP_GO_LIVE = "2025-07-01"                                        # it/CHG-2025-0417

# --- data/finance/planning_assumptions_2026.md -----------------------------
FX = {"USD": 1.0, "EUR": 1.0850, "GBP": 1.2720, "MXN": 0.0545}   # section 1
WACC = 0.09                                                       # section 2
BASELINE_DAYS = 30                                                # section 3
SCRAP_USD_PER_REJECT = 0.42                                       # section 5

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
        payment_days=45, cash_discount=None,
        rebate=None, min_volume=None, shortfall_per_piece=None,
        spec_limit_pct=3.0),
    "SUP-2318": dict(
        currency="EUR", price=178.00, pieces_per_uom=100, whole_packs_only=True,
        buyer_pays_freight=True, freight_lane="LANE-DE-01", shipments_per_year=12,
        payment_days=30, cash_discount=None,
        # clause 4.2: banded, each rate applies only to the volume inside its band
        rebate=("banded", [(200000, 0.000), (400000, 0.015), (None, 0.030)]),
        min_volume=None, shortfall_per_piece=None,
        spec_limit_pct=2.0),
    "SUP-3155": dict(
        currency="MXN", price=34.80, pieces_per_uom=1, whole_packs_only=False,
        buyer_pays_freight=False, freight_lane=None, shipments_per_year=12,
        payment_days=60, cash_discount=None,
        rebate=None, min_volume=None, shortfall_per_piece=None,
        spec_limit_pct=7.0),
    "SUP-4077": dict(
        currency="GBP", price=1.4700, pieces_per_uom=1, whole_packs_only=False,
        buyer_pays_freight=True, freight_lane="LANE-UK-01", shipments_per_year=12,
        payment_days=60, cash_discount=(0.02, 10),
        # clause 4.2: 4.0% on all pieces, earned ONLY at >= 520,000 pieces
        rebate=("threshold", 520000, 0.040),
        # clause 4.1: minimum commitment with a per-piece shortfall charge
        min_volume=520000, shortfall_per_piece=0.35,
        spec_limit_pct=3.5),
}


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
def load_master():
    wb = openpyxl.load_workbook(DATA / "master" / "supplier_master.xlsx", data_only=True)
    names, alias = {}, {}
    for row in wb["suppliers"].iter_rows(min_row=2, values_only=True):
        if row and row[0]:
            names[str(row[0]).strip()] = str(row[1]).strip()
    for row in wb["name_aliases"].iter_rows(min_row=2, values_only=True):
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
    scraps. SOURCE records are the supplier-quality engineer's pre-shipment
    inspection of the same lot at the supplier's plant: pieces rejected there
    are replaced before the lot ships and never reach Aurora, and the lot is
    inspected again on receipt. Pooling the two counts the lot twice and
    charges Cadence for pieces it never bought.

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

    agg = {c: dict(lots=0, units=0, rejected=0) for c in CANDIDATES}
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
    for code, a in agg.items():
        a["rate"] = a["rejected"] / a["units"]
    return agg


def load_demand(*, cycle="frozen", include_totals=False):
    """FY2026 good-unit requirement for SP-40.

    The planning-cube dump carries the last two S&OP cycles side by side, a
    TOTAL subtotal row per part and cycle, and a second part. The plan of
    record is the cycle the plan was frozen at, which is the latest one in
    the dump; the earlier cycle, the subtotals and SP-22 are all out of scope.
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
    total = sum(int(r["good_units_required"]) for r in rows if r["plan_cycle"].strip() in wanted)
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


def cost_build(code, rate, good_units, freight, *, fx=None, gross_up=True,
               whole_packs=True, charge_freight=True, banded=True,
               threshold=True, shortfall=True, scrap=True, terms=True,
               rounded_price=False):
    spec = CONTRACTS[code]
    fx = fx or FX
    unit_price = spec["price"] * fx[spec["currency"]] / spec["pieces_per_uom"]
    price_used = round(unit_price, 4) if rounded_price else unit_price

    # rejected pieces are scrapped with no supplier credit and no replacement
    # (contracts, clause 5.4), so the purchase quantity has to carry the loss
    units = math.ceil(good_units / (1 - rate)) if gross_up else good_units
    if whole_packs and spec["whole_packs_only"]:
        pack = spec["pieces_per_uom"]
        units = int(math.ceil(units / pack) * pack)
    rejects = units - good_units

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
    scrap_usd = rejects * SCRAP_USD_PER_REJECT if scrap else 0.0
    terms_usd = payment_terms_usd(spec, material) if terms else 0.0

    total = material + frt - reb + short + scrap_usd + terms_usd
    return dict(unit_price=unit_price, units=units, rejects=rejects,
                material=material, freight=frt, rebate=reb,
                shortfall=short, scrap=scrap_usd, terms=terms_usd,
                total=total, per_good=total / good_units, rate=rate)


def breakeven_reject_rate(code, target_total, good_units, freight):
    """Reject rate at which `code` costs exactly `target_total`."""
    lo, hi = 0.0, 0.30
    for _ in range(80):
        mid = (lo + hi) / 2.0
        if cost_build(code, mid, good_units, freight)["total"] < target_total:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def build(good_units, defects, freight, **choices):
    rows = {}
    for code in CANDIDATES:
        rows[code] = cost_build(code, defects[code]["rate"], good_units, freight, **choices)
    order = sorted(CANDIDATES, key=lambda c: rows[c]["per_good"])
    for i, code in enumerate(order, start=1):
        rows[code]["rank"] = i
    return rows, order


# ---------------------------------------------------------------------------
# Deliverables
# ---------------------------------------------------------------------------
def money(x):
    return "{:.2f}".format(x + 0.0)


def write_outputs(names, defects, rows, order, good_units, freight, source_stats):
    OUT.mkdir(parents=True, exist_ok=True)

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

    def line(code):
        r = rows[code]
        return ("| {} | {} | {:.4f} | {:,} | {:.2f} | {:.4f} | {} |".format(
            code, names[code], r["unit_price"], r["units"], r["total"],
            r["per_good"], r["rank"]))

    md = []
    md.append("# FY2026 SP-40 valve-seat sourcing award\n")
    md.append("Prepared for the sourcing steering committee. All figures in US "
              "dollars at the mandated FY2026 planning rates, for the full "
              "contract year 1 January – 31 December 2026.\n")

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
    md.append("The FY2026 good-unit requirement worked to is **{:,} SP-40 "
              "pieces** — the twelve monthly SP-40 rows of the frozen "
              "November S&OP cycle. The cube dump's October cycle, its "
              "`TOTAL` subtotal rows and all SP-22 rows are excluded; SP-22 "
              "is the FM-90 orifice plate and is sourced separately.\n".format(good_units))
    md.append("| supplier_code | supplier_name | quoted USD/piece | units to "
              "purchase | FY2026 total USD | USD per good unit | rank |")
    md.append("| --- | --- | --- | --- | --- | --- | --- |")
    for code in order:
        md.append(line(code))
    md.append("")
    md.append("Cost build-up, in US dollars:\n")
    md.append("| supplier_code | material | inbound freight | volume rebate | "
              "shortfall charge | scrap disposal | payment terms | total |")
    md.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for code in order:
        r = rows[code]
        md.append("| {} | {} | {} | {} | {} | {} | {} | {} |".format(
            code, money(r["material"]), money(r["freight"]),
            money(-r["rebate"]), money(r["shortfall"]), money(r["scrap"]),
            money(r["terms"]), money(r["total"])))
    md.append("")
    md.append("SUP-2318 is bought in whole 100-piece boxes (clause 1: partial "
              "boxes are not tendered), so its purchase quantity is the "
              "grossed-up requirement rounded up to the next box.\n")

    md.append("## Basis of Decision\n")
    md.append("Four things separate these offers, and none of them is the "
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
    md.append("**Incoming quality decides the purchase quantity.** Rejected "
              "pieces are scrapped with no credit and no replacement under "
              "clause 5.4 of all four term sheets, so the buy quantity has to "
              "carry the loss. On 2025 incoming-inspection history the four "
              "suppliers run at {}. That spread moves the purchase quantity "
              "by {:,} pieces between the best and worst supplier and is the "
              "reason {} cannot win on its low peso price.\n".format(
                  ", ".join("{} {:.2f}%".format(c, 100 * rows[c]["rate"])
                            for c in sorted(CANDIDATES)),
                  max(rows[c]["units"] for c in CANDIDATES)
                  - min(rows[c]["units"] for c in CANDIDATES),
                  "SUP-3155"))
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
              "{:,} pieces — {:,} short. So the rebate is worth nothing and "
              "the shortfall charge costs USD {}. Its 2/10 cash discount is "
              "worth taking and is planned on, but it does not close the "
              "gap. Rheinwerk's banded rebate is also worth less than it "
              "looks: clause 4.2 rates each band separately rather than "
              "re-rating the whole year at 3.0%, which is USD {} rather than "
              "USD {}.\n".format(
                  rows["SUP-4077"]["units"],
                  520000 - rows["SUP-4077"]["units"],
                  money(rows["SUP-4077"]["shortfall"]),
                  money(rows["SUP-2318"]["rebate"]),
                  money(rows["SUP-2318"]["material"] * 0.03)))
    md.append("Netting all of it, {} wins on total FY2026 cost despite holding "
              "the highest quoted price. SUP-4077 loses on freight, the "
              "shortfall charge and the rebate it does not earn; SUP-2318 "
              "loses on freight and a smaller rebate than its headline rate; "
              "SUP-3155 loses on the {:.2f}% reject rate that forces the "
              "largest buy and the largest scrap bill.\n".format(
                  win, 100 * rows["SUP-3155"]["rate"]))

    md.append("## Data Quality and Exclusions\n")
    md.append("- **Source inspections excluded from the reject rates.** The "
              "inspection log carries {} `SOURCE` records alongside the "
              "`INCOMING` ones: pre-shipment inspections by Cadence "
              "supplier-quality engineers at the supplier's plant, {} of them "
              "on SUP-1042 lots. Pieces rejected at source are replaced by "
              "the supplier before the lot ships, are never invoiced or "
              "received, and the same lot is inspected again on receipt. "
              "Only `INCOMING` records describe pieces Cadence pays for and "
              "scraps, so only they enter the reject rates. Pooling the two "
              "counts those lots twice and lifts SUP-1042's rate from "
              "{:.2f}% to about {:.2f}%, which hands the award to "
              "SUP-4077.\n".format(
                  source_stats["rows"], source_stats["rows_1042"],
                  100 * rows["SUP-1042"]["rate"], 100 * source_stats["pooled_rate_1042"]))
    md.append("- **Post-cutover receipts resolved to their purchase orders.** "
              "Purchasing and receiving moved to the new ERP on {} "
              "(CHG-2025-0417). Receipts posted from that date carry the "
              "ERP's ten-digit purchase order number, which does not exist "
              "in the purchasing extract; `po_reference_2025.csv` "
              "carries both numbers. Joining receipts to purchase "
              "orders on the number as posted silently loses every lot received "
              "after go-live — {} of {} inspected lots — and those lots carry "
              "most of SUP-3155's rejects: without them its rate reads about "
              "{:.2f}% instead of {:.2f}% and the award flips to "
              "SUP-3155.\n".format(
                  ERP_GO_LIVE, source_stats["post_lots"], source_stats["lots"],
                  100 * source_stats["pre_rate_3155"], 100 * rows["SUP-3155"]["rate"]))
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
              "distributed: doing so understates SUP-3155's reject rate by "
              "roughly half and reverses the award.\n")
    md.append("- **Double-logged inspection lots.** The inspection log "
              "contains repeated `INCOMING` records for the same `lot_id` "
              "under different `inspection_id` values. These are one "
              "physical lot each and were deduplicated on `lot_id` before "
              "any rate was computed.\n")
    md.append("- **Non-candidate supplier.** SUP-9001, Old Harbor Machine "
              "Company, appears throughout the 2025 purchasing, receipt and "
              "inspection data. It is shown as terminated 2025-09-30 in the "
              "supplier master, returned no FY2026 offer, and is excluded from "
              "the award comparison and from the defect table.\n")
    md.append("- **Purchase orders.** Cancelled purchase orders have no "
              "receipts and no inspected lots and affect nothing. SP-22 "
              "purchase orders are a different part and are out of scope.\n")
    md.append("- **Demand.** The planning-cube dump carries the superseded "
              "October S&OP cycle beside the frozen November one, and a "
              "`TOTAL` subtotal row for each part and cycle. Only the twelve "
              "monthly SP-40 rows of the November cycle were used. The "
              "October cycle totals {:,} pieces; planning on it, or on both "
              "cycles together, pushes the buy past SUP-4077's 520,000-piece "
              "rebate threshold and flips the award.\n".format(source_stats["oct_total"]))
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
    breakeven = breakeven_reject_rate(win, s["total"], good_units, freight)
    md.append("- **Quality drift is the live risk.** {}'s 2025 incoming reject "
              "rate is {:.2f}%. Holding everything else, its FY2026 cost "
              "matches the second-ranked offer once its reject rate reaches "
              "about {:.2f}%, and its clause 5 specification cap of {:.1f}% "
              "leaves contractual room to drift that far without breaching "
              "the agreement. Incoming quality, not price, is what this "
              "award rides on.\n".format(
                  win, 100 * rows[win]["rate"], 100 * breakeven,
                  CONTRACTS[win]["spec_limit_pct"]))
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
              "520,000 good units, SUP-4077's rebate would begin to pay and "
              "its shortfall charge would disappear, which is the one demand "
              "scenario that changes the answer.\n")

    with open(OUT / "recommendation.md", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(md) + "\n")


def source_statistics(lot_supplier, crosswalk, alias, good_units):
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
    return dict(rows=rows, rows_1042=rows_1042,
                source_rate_1042=src_rej / src_units,
                pooled_rate_1042=pooled["SUP-1042"]["rate"],
                lots=sum(correct[c]["lots"] for c in CANDIDATES),
                post_lots=sum(correct[c]["lots"] - no_xwalk[c]["lots"] for c in CANDIDATES),
                pre_rate_3155=no_xwalk["SUP-3155"]["rate"],
                oct_total=load_demand(cycle="2025-10"))


def main():
    names, alias = load_master()
    po_supplier = load_po_supplier(alias)
    crosswalk = load_crosswalk()
    lot_supplier = load_lot_supplier(po_supplier, crosswalk)
    defects = load_defect_rates(lot_supplier, alias)
    good_units = load_demand()
    freight = load_freight()
    rows, order = build(good_units, defects, freight)
    stats = source_statistics(lot_supplier, crosswalk, alias, good_units)
    write_outputs(names, defects, rows, order, good_units, freight, stats)

    print("FY2026 SP-40 good units required:", good_units)
    for code in order:
        r = rows[code]
        print("  {} rank={} units={} total={:.2f} per_good={:.4f} reject={:.3f}%".format(
            code, r["rank"], r["units"], r["total"], r["per_good"], 100 * r["rate"]))
    print("award:", order[0])


if __name__ == "__main__":
    main()
