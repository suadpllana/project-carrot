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
Needs openpyxl (the environment image preinstalls it).
"""
from __future__ import annotations

import collections
import csv
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "environment" / "data"
TESTS = ROOT / "tests"
SOLVE = ROOT / "solution" / "solve.py"

CANDIDATES = ["SUP-1042", "SUP-2318", "SUP-3155", "SUP-4077"]


# ===========================================================================
# Part 1 - independent re-derivation
# ===========================================================================
def rows_of(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def rederive():
    wb = openpyxl.load_workbook(DATA / "master" / "supplier_master.xlsx", data_only=True)
    alias = {str(r[0]).strip().casefold(): str(r[1]).strip()
             for r in wb["name_aliases"].iter_rows(min_row=2, values_only=True) if r and r[0]}
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
    seen = {}
    for r in recs:
        if r["part_number"] != "SP-40" or r["inspection_point"] != "INCOMING":
            continue
        if r["lot_id"] not in seen or r["inspection_id"] < seen[r["lot_id"]]["inspection_id"]:
            seen[r["lot_id"]] = r
    defects = {c: [0, 0, 0] for c in CANDIDATES}
    for r in seen.values():
        c = lot_sup.get(r["lot_id"])
        if c in defects:
            defects[c][0] += 1
            defects[c][1] += r["qty_inspected"]
            defects[c][2] += r["qty_rejected"]

    demand = rows_of(DATA / "demand" / "forecast_2026.csv")
    cycles = sorted({r["plan_cycle"] for r in demand})
    good = sum(int(r["good_units_required"]) for r in demand
               if r["part_number"] == "SP-40" and r["month"] != "TOTAL"
               and r["plan_cycle"] == cycles[-1])

    tariff = {r["lane_id"]: (float(r["usd_per_1000_pieces"]), float(r["brokerage_usd_per_shipment"]))
              for r in rows_of(DATA / "logistics" / "freight_tariff_2026.csv")}

    fx = {"USD": 1.0, "EUR": 1.0850, "GBP": 1.2720, "MXN": 0.0545}
    terms = {  # price, per-uom pieces, ccy, buyer freight lane, net days, cash discount
        "SUP-1042": (1.9450, 1, "USD", None, 45, None),
        "SUP-2318": (178.00, 100, "EUR", "LANE-DE-01", 30, None),
        "SUP-3155": (34.80, 1, "MXN", None, 60, None),
        "SUP-4077": (1.4700, 1, "GBP", "LANE-UK-01", 60, (0.02, 10)),
    }
    out = {}
    for c, (price, per, ccy, lane, days, disc) in terms.items():
        rate = defects[c][2] / defects[c][1]
        unit = price * fx[ccy] / per
        units = math.ceil(good / (1 - rate))
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
        scrap = (units - good) * 0.42
        wc = material * 0.09 * (30 - days) / 365.0
        if disc:
            early = -material * disc[0] + material * (1 - disc[0]) * 0.09 * (30 - disc[1]) / 365.0
            wc = min(early, wc)
        total = material + frt - reb + short + scrap + wc
        out[c] = dict(rate=rate, lots=defects[c][0], units_inspected=defects[c][1],
                      rejected=defects[c][2], unit_price=unit, units=units,
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


def sweep(solve):
    weights = json.loads((TESTS / "test_weights.json").read_text())
    decision = {w["test_name"]: w["weight"] for w in weights if w.get("decision")}
    dec_total = sum(decision.values())

    names, alias = solve.load_master()
    po = solve.load_po_supplier(alias)
    xwalk = solve.load_crosswalk()
    lots = solve.load_lot_supplier(po, xwalk)
    freight = solve.load_freight()
    stats = solve.source_statistics(lots, xwalk, alias, solve.load_demand())

    def variant(label, *, lot_kw=None, defect_kw=None, demand_kw=None, build_kw=None):
        lot_map = solve.load_lot_supplier(po, xwalk, **(lot_kw or {}))
        defects = solve.load_defect_rates(lot_map, alias, **(defect_kw or {}))
        good = solve.load_demand(**(demand_kw or {}))
        rows, order = solve.build(good, defects, freight, **(build_kw or {}))
        out = Path(tempfile.mkdtemp(prefix="cadence-out-"))
        solve.OUT = out
        solve.write_outputs(names, defects, rows, order, good, freight, stats)
        reward, passed = run_verifier(out)
        shutil.rmtree(out, ignore_errors=True)
        dec = sum(w for n, w in decision.items() if n in passed)
        return dict(label=label, lands=order[0], reward=reward, dec=dec,
                    units=rows[order[0]]["units"], total=rows[order[0]]["total"])

    routes = [
        ("pools the SOURCE inspections (dedupe keeps first record)", dict(defect_kw=dict(points=None, keep="first"))),
        ("pools the SOURCE inspections (dedupe keeps last record)", dict(defect_kw=dict(points=None, keep="last"))),
        ("pools the SOURCE inspections, no dedupe", dict(defect_kw=dict(points=None, keep="none"))),
        ("joins receipts without the ERP number reference", dict(lot_kw=dict(use_crosswalk=False))),
        ("attributes lots on the free-text supplier field", dict(defect_kw=dict(attribute_by="field"))),
        ("plans on the October S&OP cycle", dict(demand_kw=dict(cycle="2025-10"))),
        ("sums both S&OP cycles", dict(demand_kw=dict(cycle="all"))),
        ("counts the TOTAL subtotal rows", dict(demand_kw=dict(include_totals=True))),
        ("no yield gross-up", dict(build_kw=dict(gross_up=False))),
        ("2025 average FX instead of planning rates", dict(build_kw=dict(fx=solve.load_fx_2025_average()))),
        ("charges no inbound freight", dict(build_kw=dict(charge_freight=False))),
        ("re-rates SUP-2318's whole year at 3.0%", dict(build_kw=dict(banded=False))),
        ("treats SUP-4077's rebate as earned, no shortfall", dict(build_kw=dict(threshold=False, shortfall=False))),
        ("misses the shortfall charge alone (clause 4.1)", dict(build_kw=dict(shortfall=False))),
        ("ignores payment terms", dict(build_kw=dict(terms=False))),
        ("ignores scrap disposal", dict(build_kw=dict(scrap=False))),
        ("ignores SUP-2318's whole-box rule", dict(build_kw=dict(whole_packs=False))),
        ("multiplies by the 4-dp rounded price", dict(build_kw=dict(rounded_price=True))),
        ("reference solution", dict()),
    ]
    # what a competent attempt that does every DOCUMENTED step but misses a
    # judgement actually scores - the profile the model sweep produces
    profiles = [
        ("pools SOURCE records (the default if the log is read as one population)",
         dict(defect_kw=dict(points=None, keep="first"))),
        ("pools SOURCE, joins receipts on po_id as it stands",
         dict(defect_kw=dict(points=None, keep="first"), lot_kw=dict(use_crosswalk=False))),
        ("pools SOURCE, attributes on the free-text supplier field",
         dict(defect_kw=dict(points=None, keep="first", attribute_by="field"))),
        ("joins receipts on po_id as it stands, sums both plan cycles",
         dict(lot_kw=dict(use_crosswalk=False), demand_kw=dict(cycle="all"))),
        ("free-text attribution, October plan cycle",
         dict(defect_kw=dict(attribute_by="field"), demand_kw=dict(cycle="2025-10"))),
        ("every judgement right, whole-box rule and rounded price missed",
         dict(build_kw=dict(whole_packs=False, rounded_price=True))),
        ("every judgement right, payment terms and scrap missed",
         dict(build_kw=dict(terms=False, scrap=False))),
    ]

    def table(title, rows_):
        print("\n| %s | Lands on | Contract qty | Contract cost | Tests | Decision |" % title)
        print("| --- | --- | --- | --- | --- | --- |")
        for r in rows_:
            print("| %s | %s | %s | USD %s | %.3f | %d / %d |" % (
                r["label"], r["lands"], "{:,}".format(r["units"]), "{:,.2f}".format(r["total"]),
                r["reward"], r["dec"], dec_total))

    results = [variant(label, **kw) for label, kw in routes]
    table("Single omission", results)
    combos = [variant(label, **kw) for label, kw in profiles]
    table("Attempt profile", combos)
    return results + combos


def main():
    gt = rederive()
    print("independent re-derivation from environment/data/")
    print("  plan cycles in the dump : %s (frozen = %s)" % (", ".join(gt["cycles"]), gt["cycles"][-1]))
    print("  FY2026 good units       : %d" % gt["good"])
    print("  SOURCE records excluded : %d" % gt["n_source"])
    for c in gt["order"]:
        r = gt["rows"][c]
        print("  %s  lots=%d inspected=%d rejected=%d rate=%.3f%%  price=%.4f units=%d total=%.2f per_good=%.4f"
              % (c, r["lots"], r["units_inspected"], r["rejected"], 100 * r["rate"],
                 r["unit_price"], r["units"], r["total"], r["per_good"]))
    print("  award                   : %s   margin over %s: USD %.2f"
          % (gt["order"][0], gt["order"][1],
             gt["rows"][gt["order"][1]]["total"] - gt["rows"][gt["order"][0]]["total"]))

    solve = load_solve()
    ref = {}
    names, alias = solve.load_master()
    lots = solve.load_lot_supplier(solve.load_po_supplier(alias), solve.load_crosswalk())
    rows, order = solve.build(solve.load_demand(), solve.load_defect_rates(lots, alias), solve.load_freight())
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
    print("\n%d of %d omissions land on a different supplier; worst non-flipping omission scores %.3f"
          % (len(flips), len(results) - 1,
             max(r["reward"] for r in results if r["lands"] == ref["lands"] and r["label"] != "reference solution")))


if __name__ == "__main__":
    main()
