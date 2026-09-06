#!/usr/bin/env python3
"""Independent re-derivation of the ground truth from the SHIPPED files only,
followed by the single-omission sweep against the SHIPPED verifier.

Part 1 re-reads environment/data/ with its own compact pipeline (no reuse of
solve.py) and proves the answer is recoverable from what the attempt sees.

Part 2 imports solve.py, re-runs it with exactly one wrong analysis choice at
a time, writes each variant's deliverables to a scratch directory and scores
them with tests/test.sh - the same verifier the platform runs. It prints the
"Measured" table that task_card.md quotes: which supplier each omission lands
on, the test-side reward, and how many test-side decision points survive.

Run from anywhere:  python solution/_provenance/verify_design.py
Standard library only, so a review sandbox that installs nothing can run it.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

# importing solve.py and running the checks would otherwise leave
# __pycache__ directories inside the task tree, and a stray .pyc in the
# upload archive has had an intake refuse the package before now
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "environment" / "data"
TESTS = ROOT / "tests"
SOLVE = ROOT / "solution" / "solve.py"

CANDIDATES = ["SUP-1042", "SUP-2318", "SUP-3155", "SUP-4077"]
# independently decisive judgements the design plants (task_card.md, 0a-0e, 1, 2)
LAYERS = 7


# ===========================================================================
# Part 1 - independent re-derivation
# ===========================================================================
def rows_of(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def sheet_rows(path, sheet_name):
    """Rows of one worksheet, read straight out of the .xlsx zip.

    Deliberately neither openpyxl nor solve.py's reader: this file has to
    reach the ground truth by its own route, and it has to run in a review
    sandbox that installs nothing. The sheets it reads are dense grids, so
    text nodes in document order are the row; a ragged row would break that
    assumption, so it is asserted rather than assumed.
    """
    with zipfile.ZipFile(path) as zf:
        book = zf.read("xl/workbook.xml").decode("utf-8")
        rels = zf.read("xl/_rels/workbook.xml.rels").decode("utf-8")
        rid = dict(re.findall(r'<sheet[^>]*name="([^"]*)"[^>]*r:id="([^"]*)"',
                              book))[sheet_name]
        target = {i: t for t, i in re.findall(
            r'<Relationship[^>]*Target="([^"]*)"[^>]*Id="([^"]*)"', rels)}
        part = target[rid].lstrip("/")
        if not part.startswith("xl/"):
            part = "xl/" + part
        xml = zf.read(part).decode("utf-8")
    rows = [re.findall(r"<t[^>]*>(.*?)</t>", row, re.S)
            for row in re.findall(r"<row[^>]*>(.*?)</row>", xml, re.S)]
    widths = {len(r) for r in rows}
    assert len(widths) == 1, "ragged sheet %s: widths %s" % (sheet_name, sorted(widths))
    return rows


def rederive():
    alias = {r[0].strip().casefold(): r[1].strip()
             for r in sheet_rows(DATA / "master" / "supplier_master.xlsx",
                                 "name_aliases")[1:] if r and r[0]}
    po_sup = {r["po_id"]: alias.get(r["supplier_name"].strip().casefold())
              for r in rows_of(DATA / "purchasing" / "purchase_orders_2025.csv")}
    xwalk = {r["erp_po_number"]: r["mart_po_id"]
             for r in rows_of(DATA / "purchasing" / "po_reference_2025.csv")}
    lot_sup = {}
    for r in rows_of(DATA / "purchasing" / "goods_receipts_2025.csv"):
        lot_sup[r["lot_id"]] = po_sup.get(xwalk.get(r["po_id"], r["po_id"]))

    recs = [json.loads(l) for l in open(DATA / "quality" / "incoming_inspection_2025.jsonl",
                                        encoding="utf-8") if l.strip()]
    n_source = sum(1 for r in recs if r["inspection_point"] == "SOURCE")
    # one physical lot may carry several INCOMING records: a repeat of the
    # same inspection (identical figures - count once) or pieces found after
    # the lot was first logged (no inspected quantity - add to the lot)
    incoming = sorted((r for r in recs if r["part_number"] == "SP-40"
                       and r["inspection_point"] == "INCOMING"),
                      key=lambda r: r["inspection_id"])
    keep, figures = [], set()
    for r in incoming:
        fig = (r["lot_id"], r["qty_inspected"], r["qty_rejected"], r["disposition"])
        if r["qty_inspected"] == 0 or fig not in figures:
            figures.add(fig)
            keep.append(r)
    defects = {c: [0, 0, 0, 0] for c in CANDIDATES}   # lots, inspected, rejected, scrapped
    lots_seen = set()
    for r in keep:
        c = lot_sup.get(r["lot_id"])
        if c in defects:
            if r["lot_id"] not in lots_seen:
                defects[c][0] += 1
                lots_seen.add(r["lot_id"])
            defects[c][1] += r["qty_inspected"]
            defects[c][2] += r["qty_rejected"]
            if r["disposition"] == "SCRAP":
                defects[c][3] += r["qty_rejected"]

    # the offers all run 1 April 2026 - 31 March 2027; the cube dump is a
    # rolling fifteen-month horizon carrying two cycles and its own subtotals
    demand = rows_of(DATA / "demand" / "forecast_2026.csv")
    cycles = sorted({r["plan_cycle"] for r in demand})
    good = sum(int(r["good_units_required"]) for r in demand
               if r["part_number"] == "SP-40" and r["month"] != "TOTAL"
               and r["plan_cycle"] == cycles[-1]
               and "2026-04" <= r["month"] <= "2027-03")

    tariff = {r["lane_id"]: (float(r["usd_per_1000_pieces"]), float(r["brokerage_usd_per_shipment"]))
              for r in rows_of(DATA / "logistics" / "freight_tariff_2026.csv")}

    fx = {"USD": 1.0, "EUR": 1.0850, "GBP": 1.2720, "MXN": 0.0545}
    terms = {  # price, per-uom pieces, ccy, buyer freight lane, net days, cash discount
        "SUP-1042": (1.9450, 1, "USD", None, 90, None),
        "SUP-2318": (172.00, 100, "EUR", "LANE-DE-01", 30, None),
        "SUP-3155": (33.55, 1, "MXN", None, 60, None),
        "SUP-4077": (1.4076, 1, "GBP", "LANE-UK-01", 60, (0.01, 10)),
    }
    out = {}
    for c, (price, per, ccy, lane, days, disc) in terms.items():
        loss = defects[c][3] / defects[c][1]
        unit = price * fx[ccy] / per
        units = math.ceil(good / (1 - loss))
        if per > 1:
            units = int(math.ceil(units / per) * per)
        material = units * unit
        frt = units / 1000.0 * tariff[lane][0] + 12 * tariff[lane][1] if lane else 0.0
        reb = 0.0
        if c == "SUP-2318":
            for lo, hi, pct in ((0, 200000, 0.0), (200000, 400000, 0.015), (400000, None, 0.03)):
                top = units if hi is None else min(units, hi)
                if top > lo:
                    reb += (top - lo) * unit * pct
        if c == "SUP-4077" and units >= 520000:
            reb = material * 0.04
        short = (520000 - units) * 0.35 * fx["GBP"] if c == "SUP-4077" and units < 520000 else 0.0
        disposal = (units - good) * 1.25
        wc = material * 0.09 * (30 - days) / 365.0
        if disc:
            early = -material * disc[0] + material * (1 - disc[0]) * 0.09 * (30 - disc[1]) / 365.0
            wc = min(early, wc)
        total = material + frt - reb + short + disposal + wc
        out[c] = dict(rate=defects[c][2] / defects[c][1], loss=loss, lots=defects[c][0],
                      units_inspected=defects[c][1], rejected=defects[c][2],
                      scrapped=defects[c][3], unit_price=unit, units=units,
                      total=total, per_good=total / good)
    order = sorted(CANDIDATES, key=lambda c: out[c]["per_good"])
    return dict(good=good, cycles=cycles, n_source=n_source, rows=out, order=order)


# ===========================================================================
# Part 2 - single-omission sweep through the shipped verifier
# ===========================================================================
def load_solve():
    spec = importlib.util.spec_from_file_location("solve", SOLVE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.DATA = DATA          # the shipped inputs, wherever this checkout lives
    return mod


def run_verifier(out_dir):
    logs = Path(tempfile.mkdtemp(prefix="cadence-logs-"))
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", "/"),
           "OUTPUT_DIR": str(out_dir), "CADENCE_LOGS": str(logs), "CADENCE_TESTS": str(TESTS)}
    subprocess.run(["bash", str(TESTS / "test.sh")], env=env, capture_output=True, text=True)
    reward = json.loads((logs / "reward.json").read_text())["reward"]
    ctrf = json.loads((logs / "ctrf.json").read_text())
    passed = {t["name"].split("::")[-1] for t in ctrf["results"]["tests"] if t["status"] == "passed"}
    shutil.rmtree(logs, ignore_errors=True)
    return reward, passed


ROUTES = [
    ("grosses the buy up on every reject, not the scrapped share",
     dict(build_kw=dict(loss="all"))),
    ("pools the SOURCE inspections (dedupe keeps first record)",
     dict(defect_kw=dict(points=None, keep="first"))),
    ("pools the SOURCE inspections (dedupe keeps last record)",
     dict(defect_kw=dict(points=None, keep="last"))),
    ("pools the SOURCE inspections, no dedupe",
     dict(defect_kw=dict(points=None, keep="none"))),
    ("dedups on lot_id, keeps the first record (drops the additions)",
     dict(defect_kw=dict(keep="first"))),
    ("dedups on lot_id, keeps the last record",
     dict(defect_kw=dict(keep="last"))),
    ("does not dedup at all (double-counts the repeats)",
     dict(defect_kw=dict(keep="none"))),
    ("joins receipts without the ERP number reference",
     dict(lot_kw=dict(use_crosswalk=False))),
    ("attributes lots on the free-text supplier field",
     dict(defect_kw=dict(attribute_by="field"))),
    ("plans on calendar 2026 instead of the contract year",
     dict(demand_kw=dict(window="calendar"))),
    ("plans on the whole fifteen-month cube horizon",
     dict(demand_kw=dict(window="horizon"))),
    ("counts the TOTAL subtotal rows as well",
     dict(demand_kw=dict(include_totals=True))),
    ("plans on the superseded October S&OP cycle",
     dict(demand_kw=dict(cycle="2025-10"))),
    ("no yield gross-up", dict(build_kw=dict(gross_up=False))),
    ("2025 average FX instead of planning rates", dict(build_kw=dict(fx="avg"))),
    ("charges no inbound freight", dict(build_kw=dict(charge_freight=False))),
    ("re-rates SUP-2318's whole year at 3.0%", dict(build_kw=dict(banded=False))),
    ("treats SUP-4077's rebate as earned, no shortfall",
     dict(build_kw=dict(threshold=False, shortfall=False))),
    ("misses the shortfall charge alone (clause 4.1)",
     dict(build_kw=dict(shortfall=False))),
    ("ignores payment terms", dict(build_kw=dict(terms=False))),
    ("ignores scrap disposal", dict(build_kw=dict(disposal=False))),
    ("ignores SUP-2318's whole-box rule", dict(build_kw=dict(whole_packs=False))),
    ("multiplies by the 4-dp rounded price", dict(build_kw=dict(rounded_price=True))),
    ("reference solution", dict()),
]

# what a competent attempt that does every DOCUMENTED step but misses one or
# two judgements actually scores - the profile the model sweep produces
PROFILES = [
    ("reads the log as one reject population (the default)",
     dict(build_kw=dict(loss="all"))),
    ("one reject population, pools SOURCE records",
     dict(defect_kw=dict(points=None, keep="first"), build_kw=dict(loss="all"))),
    ("one reject population, calendar-2026 window",
     dict(build_kw=dict(loss="all"), demand_kw=dict(window="calendar"))),
    ("pools SOURCE, joins receipts on po_id as it stands",
     dict(defect_kw=dict(points=None, keep="first"), lot_kw=dict(use_crosswalk=False))),
    ("free-text attribution, October plan cycle",
     dict(defect_kw=dict(attribute_by="field"), demand_kw=dict(cycle="2025-10"))),
    ("every judgement right, whole-box rule and rounded price missed",
     dict(build_kw=dict(whole_packs=False, rounded_price=True))),
    ("every judgement right, payment terms and disposal missed",
     dict(build_kw=dict(terms=False, disposal=False))),
    ("every judgement right, cube horizon not trimmed",
     dict(demand_kw=dict(window="horizon"))),
    ("every judgement right, then dedups on lot_id to be safe",
     dict(defect_kw=dict(keep="first"))),
]

# The spec-only path: an attempt that does everything a SHIPPED DOCUMENT tells
# it to and forms none of the judgements no document makes for it. Mutation
# testing cannot find this, because a mutation already assumes the analysis is
# happening; only writing the document-following attempt and scoring it says
# whether the package can be solved by reading rather than analysing.
#
# It is deliberately GENEROUS, so the number it produces is an upper bound on
# the spec-only path: it is given both reconciliations a document states as a
# fact - the ERP reference extract carries both number series (CHG-2025-0417),
# and the QMS supplier field is keyed by hand and unvalidated, so lots are
# attributed through the receipt - and it is given the November cycle and the
# dedupe, which the planning note and QP-07 section 2 respectively describe.
# What it does not do is the four things no document decides for it: which
# months of the cube the contract covers, which inspection records are the
# reject population, which rejected pieces are actually a loss, and what a
# repeated record for a lot is (it deduplicates on lot_id, as the existence
# of duplicates in QP-07 section 2 invites).
SPEC_ONLY = [
    ("spec-only: every documented step, no judgement of its own",
     dict(defect_kw=dict(points=None, keep="first"), demand_kw=dict(window="horizon"),
          build_kw=dict(loss="all"))),
    ("spec-only, but reads the cube over calendar 2026",
     dict(defect_kw=dict(points=None, keep="first"), demand_kw=dict(window="calendar"),
          build_kw=dict(loss="all"))),
]


def sweep(solve):
    weights = json.loads((TESTS / "test_weights.json").read_text())
    decision = {w["test_name"]: w["weight"] for w in weights if w.get("decision")}
    dec_total = sum(decision.values())

    names, alias = solve.load_master()
    po = solve.load_po_supplier(alias)
    xwalk = solve.load_crosswalk()
    freight = solve.load_freight()

    def variant(label, *, lot_kw=None, defect_kw=None, demand_kw=None, build_kw=None):
        """One attempt, wrong in exactly the named way and consistent everywhere else.

        The deliverables all come out of the SAME mutated run: the ranking is
        the ranking this attempt reached, the quantities are the ones it sized,
        and the memo describes the analysis it actually did rather than the
        reference one. A simulated attempt that files a correct memo beside a
        wrong table collects credit no real attempt could, and the number this
        harness exists to produce is what a wrong path really scores.
        """
        raw_kw = dict(lot_kw=lot_kw, defect_kw=defect_kw,
                      demand_kw=demand_kw, build_kw=build_kw)
        build_kw = dict(build_kw or {})
        if build_kw.get("fx") == "avg":
            build_kw["fx"] = solve.load_fx_2025_average()
        lot_map = solve.load_lot_supplier(po, xwalk, **(lot_kw or {}))
        defects = solve.load_defect_rates(lot_map, alias, **(defect_kw or {}))
        good = solve.load_demand(**(demand_kw or {}))
        rows, order = solve.build(good, defects, freight, **build_kw)
        # this attempt's own view of the populations, not the reference's
        stats = solve.source_statistics(lot_map, xwalk, alias, good, freight)
        out = Path(tempfile.mkdtemp(prefix="cadence-out-"))
        solve.OUT = out
        solve.write_outputs(names, defects, rows, order, good, freight, stats,
                            choices=raw_kw)
        reward, passed = run_verifier(out)
        shutil.rmtree(out, ignore_errors=True)
        dec = sum(w for n, w in decision.items() if n in passed)
        return dict(label=label, lands=order[0], reward=reward, dec=dec,
                    units=rows[order[0]]["units"], total=rows[order[0]]["total"])

    def table(title, rows_):
        print("\n| %s | Lands on | Contract qty | Contract cost | Tests | Decision |" % title)
        print("| --- | --- | --- | --- | --- | --- |")
        for r in rows_:
            print("| %s | %s | %s | USD %s | %.3f | %d / %d |" % (
                r["label"], r["lands"], "{:,}".format(r["units"]), "{:,.2f}".format(r["total"]),
                r["reward"], r["dec"], dec_total))

    results = [variant(label, **kw) for label, kw in ROUTES]
    table("Single omission", results)
    combos = [variant(label, **kw) for label, kw in PROFILES]
    table("Attempt profile", combos)
    spec = [variant(label, **kw) for label, kw in SPEC_ONLY]
    table("Spec-only path", spec)
    return results + combos + spec


# ===========================================================================
# Part 3 - negative mutations: a CORRECT answer, written down differently
# ===========================================================================
# "Does a wrong answer get caught" is only half the harness. The other half is
# "does a right answer still pass once it is written the way some other
# competent attempt would write it" - a check that matches a literal string, a
# single row or one spelling fails here and nowhere else.
def rewrap(text, width=34):
    """Hard-wrap the prose of a markdown document, leaving tables alone."""
    out = []
    for line in text.split("\n"):
        stripped = line.lstrip()
        if not stripped or stripped.startswith(("|", "#")):
            out.append(line)
            continue
        words, cur = stripped.split(), ""
        for word in words:
            if cur and len(cur) + 1 + len(word) > width:
                out.append(cur)
                cur = word
            else:
                cur = (cur + " " + word).strip()
        out.append(cur)
    return "\n".join(out)


def reformat(out_dir, kind, solve):
    """Rewrite a correct deliverable set the way another attempt might."""
    memo = out_dir / "recommendation.md"
    if kind == "memo re-wrapped at 34 columns":
        memo.write_text(rewrap(memo.read_text(encoding="utf-8")), encoding="utf-8")
    elif kind == "memo money as $1,234.56 with separators":
        text = re.sub(r"USD ([\d,]+\.\d{2})", r"$\1", memo.read_text(encoding="utf-8"))
        text = re.sub(r"\$(\d{4,})(\.\d{2})",
                      lambda m: "$" + format(int(m.group(1)), ",") + m.group(2), text)
        memo.write_text(text, encoding="utf-8")
    elif kind == "memo totals rounded to whole dollars":
        # instruction.md allows the memo's figures to the cent OR to the dollar
        text = re.sub(r"USD (\d+)\.(\d{2})",
                      lambda m: "USD " + format(int(m.group(1)) + (1 if int(m.group(2)) >= 50 else 0)),
                      memo.read_text(encoding="utf-8"))
        memo.write_text(text, encoding="utf-8")
    elif kind == "CSVs with CRLF line endings":
        for name in ("supplier_costs.csv", "defect_rates.csv", "cost_buildup.csv"):
            path = out_dir / name
            path.write_bytes(path.read_text(encoding="utf-8").replace("\n", "\r\n")
                             .encode("utf-8"))
    elif kind == "supplier names in another house style":
        for name in ("supplier_costs.csv", "recommendation.md"):
            path = out_dir / name
            text = path.read_text(encoding="utf-8")
            for before, after in (("Meridian Precision Works, LLC", "Meridian Precision Works LLC"),
                                  ("Talleres Nortenos, S.A. de C.V.", "Talleres Nortenos SA de CV"),
                                  ("Rheinwerk Feinmechanik GmbH", "Rheinwerk Feinmechanik G.m.b.H."),
                                  ("Brackenridge Tooling Ltd", "Brackenridge Tooling Ltd.")):
                text = text.replace(before, after)
            path.write_text(text, encoding="utf-8")
    elif kind == "build-up itemised into finer elements":
        rows = list(csv.reader((out_dir / "cost_buildup.csv")
                               .read_text(encoding="utf-8").splitlines()))
        header, body = rows[0], rows[1:]
        freight = solve.load_freight()
        split = []
        costs = list(csv.reader((out_dir / "supplier_costs.csv")
                                .read_text(encoding="utf-8").splitlines()))[1:]
        bought = {r[0]: float(r[3]) for r in costs if r}
        for code, element, amount in body:
            spec = solve.CONTRACTS[code]
            if element == "inbound_freight" and float(amount):
                units = bought[code]
                per_k, brokerage = freight[spec["freight_lane"]]
                split.append([code, "customs_brokerage",
                              "{:.2f}".format(spec["shipments_per_year"] * brokerage)])
                split.append([code, "freight_tariff",
                              "{:.2f}".format(units / 1000.0 * per_k)])
            else:
                split.append([code, element, amount])
        split.sort(key=lambda r: (r[0], r[1]))
        with open(out_dir / "cost_buildup.csv", "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(header)
            w.writerows(split)
    else:
        raise AssertionError("unknown reformat %r" % kind)


REFORMATS = [
    "memo re-wrapped at 34 columns",
    "memo money as $1,234.56 with separators",
    "memo totals rounded to whole dollars",
    "CSVs with CRLF line endings",
    "supplier names in another house style",
    "build-up itemised into finer elements",
]


def floor_probe(solve):
    """What the SHAPE alone banks: a well-formed answer with no analysis in it.

    Every file has the right header, the right rows, the right precision and
    the master's legal names; the memo has all five sections, names the
    non-candidate supplier, covers all four offers and quotes figures that
    agree with its own CSVs. Every number behind it is naive - prices as the
    clauses quote them without restating currency or unit of measure, the whole
    fifteen-month cube as the requirement, no gross-up, no freight, no rebate,
    no terms, no disposal - so nothing analytical is right. This is the free
    credit a wrong attempt harvests, and the number the task card quotes.
    """
    names, _ = solve.load_master()
    good = solve.load_demand(window="horizon")
    naive = {}
    for code in CANDIDATES:
        spec = solve.CONTRACTS[code]
        price = spec["price"]                      # not restated: the trap
        total = good * price
        naive[code] = dict(price=price, units=good, total=total,
                           per_good=total / good)
    order = sorted(CANDIDATES, key=lambda c: naive[c]["price"])

    out = Path(tempfile.mkdtemp(prefix="cadence-floor-"))
    with open(out / "supplier_costs.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["supplier_code", "supplier_name", "quoted_price_usd_per_unit",
                    "units_to_purchase", "total_fy2026_cost_usd",
                    "cost_per_good_unit_usd", "rank"])
        for rank, code in enumerate(order, start=1):
            r = naive[code]
            w.writerow([code, names[code], "{:.4f}".format(r["price"]), r["units"],
                        "{:.2f}".format(r["total"]), "{:.4f}".format(r["per_good"]),
                        rank])
    with open(out / "defect_rates.csv", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("supplier_code,lots_inspected,units_inspected,units_rejected,"
                 "reject_rate_pct\n")
        for code in sorted(CANDIDATES):
            fh.write("%s,50,150000,3000,2.000\n" % code)
    with open(out / "cost_buildup.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["supplier_code", "cost_element", "amount_usd"])
        for code in sorted(CANDIDATES):
            w.writerow([code, "material", "{:.2f}".format(naive[code]["total"])])

    win = order[0]
    margin = naive[order[1]]["total"] - naive[win]["total"]
    memo = ["# FY2026 SP-40 valve-seat sourcing award\n"]
    memo.append("## Recommendation\n")
    memo.append("Award the FY2026 SP-40 contract to **%s (%s)**, contracting "
                "%d pieces for the year at a total FY2026 cost of USD %.2f. "
                "That is USD %.2f less over the year than the second-ranked "
                "offer, and it is the lowest quoted price of the four offers "
                "returned to us for this part.\n"
                % (names[win], win, naive[win]["units"], naive[win]["total"],
                   margin))
    memo.append("## Cost Comparison\n")
    memo.append("All four offers were compared over the FY2026 requirement of "
                "%d SP-40 pieces taken from the planning cube extract for this "
                "part, covering the months the extract carries. The totals "
                "are: %s. Ranking follows the total cost over that volume.\n"
                % (good, ", ".join("%s USD %.2f" % (c, naive[c]["total"])
                                   for c in order)))
    memo.append("## Basis of Decision\n")
    memo.append("The ranking is driven by quoted price across the four offers, "
                "which is the largest single component of the cost of this "
                "part. %s loses on price, %s loses on price, and %s loses on "
                "price against the recommended supplier; each of the three "
                "quotes more per piece over the contract volume than the offer "
                "we are recommending here.\n"
                % (order[1], order[2], order[3]))
    memo.append("## Data Quality and Exclusions\n")
    memo.append("SUP-9001, Old Harbor Machine Company, appears throughout the "
                "2025 purchasing and inspection data but returned no FY2026 "
                "offer, so it is not a candidate and is excluded. Cancelled "
                "purchase orders were excluded because they brought in no "
                "stock. SP-22 rows were excluded because they are a different "
                "part on a separate agreement. Source inspection records were "
                "counted in the reject rates because they are inspections of "
                "the same part on the same log.\n")
    memo.append("## Risks and Sensitivities\n")
    memo.append("The recommendation rests on quoted price, so it would be "
                "overturned if the recommended supplier's price rose by more "
                "than USD %.2f over the contract year, or if quality "
                "performance moved materially against it. Concentrating the "
                "part on one supplier also removes the current split and "
                "leaves no qualified running alternative.\n" % margin)
    (out / "recommendation.md").write_text("\n".join(memo) + "\n", encoding="utf-8")

    reward, passed = run_verifier(out)
    shutil.rmtree(out, ignore_errors=True)
    return reward, passed


def negative_sweep(solve):
    """Every reformat of a CORRECT answer must still score 1.000."""
    names, alias = solve.load_master()
    lots = solve.load_lot_supplier(solve.load_po_supplier(alias), solve.load_crosswalk())
    defects = solve.load_defect_rates(lots, alias)
    good, freight = solve.load_demand(), solve.load_freight()
    rows, order = solve.build(good, defects, freight)
    stats = solve.source_statistics(lots, solve.load_crosswalk(), alias, good, freight)

    print("\n| Correct answer, written differently | Tests | Verdict |")
    print("| --- | --- | --- |")
    bad = []
    for kind in REFORMATS:
        out = Path(tempfile.mkdtemp(prefix="cadence-neg-"))
        solve.OUT = out
        solve.write_outputs(names, defects, rows, order, good, freight, stats)
        reformat(out, kind, solve)
        reward, _ = run_verifier(out)
        shutil.rmtree(out, ignore_errors=True)
        print("| %s | %.3f | %s |" % (kind, reward, "ok" if reward == 1.0 else "REGRESSION"))
        if reward != 1.0:
            bad.append((kind, reward))
    return bad


def main():
    gt = rederive()
    print("independent re-derivation from environment/data/")
    print("  plan cycles in the dump : %s (frozen = %s)" % (", ".join(gt["cycles"]), gt["cycles"][-1]))
    print("  FY2026 good units       : %d  (contract year 2026-04 .. 2027-03)" % gt["good"])
    print("  SOURCE records excluded : %d" % gt["n_source"])
    for c in gt["order"]:
        r = gt["rows"][c]
        print("  %s  lots=%d inspected=%d rejected=%d (%.3f%%) scrapped=%d (%.3f%%)  "
              "price=%.4f units=%d total=%.2f per_good=%.4f"
              % (c, r["lots"], r["units_inspected"], r["rejected"], 100 * r["rate"],
                 r["scrapped"], 100 * r["loss"], r["unit_price"], r["units"],
                 r["total"], r["per_good"]))
    print("  award                   : %s   margin over %s: USD %.2f"
          % (gt["order"][0], gt["order"][1],
             gt["rows"][gt["order"][1]]["total"] - gt["rows"][gt["order"][0]]["total"]))

    solve = load_solve()
    names, alias = solve.load_master()
    lots = solve.load_lot_supplier(solve.load_po_supplier(alias), solve.load_crosswalk())
    rows, order = solve.build(solve.load_demand(), solve.load_defect_rates(lots, alias),
                              solve.load_freight())
    for c in CANDIDATES:
        assert rows[c]["units"] == gt["rows"][c]["units"], c
        assert abs(rows[c]["total"] - gt["rows"][c]["total"]) < 1e-6, c
    assert order == gt["order"]
    print("  solve.py agrees with the re-derivation on every figure")

    if "--no-sweep" in sys.argv:
        return
    print("\nsingle-omission sweep through tests/test.sh")
    results = sweep(solve)
    ref = [r for r in results if r["label"] == "reference solution"][0]
    assert ref["reward"] == 1.0, "reference does not score 1.0: %s" % ref
    flips = [r for r in results if r["lands"] != ref["lands"]]
    others = [r["reward"] for r in results
              if r["lands"] == ref["lands"] and r["label"] != "reference solution"]
    print("\n%d of %d omissions land on a different supplier; worst non-flipping "
          "omission scores %.3f"
          % (len(flips), len(results) - 1, max(others) if others else 0.0))

    # f, for the calibration arithmetic: mean ~ q**k + (1 - q**k) * f, where q
    # is the chance a strong attempt clears one non-checklist layer and k is
    # the number of independently decisive layers. f is what a wrong decision
    # can still bank, so it is the ceiling every sweep is measured against.
    wrong = [r["reward"] for r in results if r["lands"] != ref["lands"]]
    if wrong:
        f_max, f_mean = max(wrong), sum(wrong) / len(wrong)
        print("f (wrong-decision score cap): max %.3f, mean %.3f over %d paths"
              % (f_max, f_mean, len(wrong)))
        for target, ceiling in (("strong", 0.60), ("weak", 0.35)):
            room = (ceiling - f_mean) / (1 - f_mean) if f_mean < 1 else 0.0
            print("  %-6s ceiling %.2f needs q**k <= %.3f  (k=%d: q <= %.3f)"
                  % (target, ceiling, room, LAYERS, room ** (1.0 / LAYERS)))

    floor, floor_passed = floor_probe(solve)
    print("structural floor (well-formed, no analysis): %.3f  [%s]"
          % (floor, ", ".join(sorted(floor_passed)) or "nothing"))

    print("\nnegative sweep: a correct answer, written down differently")
    bad = negative_sweep(solve)
    assert not bad, ("a correct answer scored below 1.000 after reformatting: %s"
                     % "; ".join("%s -> %.3f" % b for b in bad))


if __name__ == "__main__":
    main()
