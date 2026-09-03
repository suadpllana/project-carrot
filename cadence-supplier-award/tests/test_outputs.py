"""Programmatic checks over the attempt's FINAL OUTPUT FILES only.

Nothing here reads the trajectory, the environment, or how the work was done -
only what landed in /workspace/output. Deterministic: no network, no clock, no
randomness.

Tests whose name starts with `test_penalty_` are penalties. Each is written to
PASS only when the specific defect it names is present, so it fails on the
reference solution and the grader charges its negative weight only when the
defect is really there.
"""
from __future__ import annotations

import csv
import io
import os
import re
from pathlib import Path

GRADED = ["supplier_costs.csv", "defect_rates.csv", "recommendation.md"]

# The runner's output directory, resolved ABSOLUTELY. Never relative to this
# file: the tests directory is mounted somewhere the attempt never writes, so
# a relative path resolves into the verifier's own tree and scores every run,
# the reference solution included, exactly 0.
OUT_ENV = ("CADENCE_OUT", "OUTPUT_DIR")
OUT_DEFAULT = Path("/workspace/output")


def _resolve_output_dir():
    """First configured directory that holds a graded file, else the default.

    A relative override is ignored rather than resolved against the working
    directory, which is the runner's to choose and not the attempt's.
    """
    candidates = []
    for key in OUT_ENV:
        raw = os.environ.get(key, "").strip()
        if raw and Path(raw).is_absolute():
            candidates.append(Path(raw))
    candidates.append(OUT_DEFAULT)
    for cand in candidates:
        if any((cand / name).is_file() for name in GRADED):
            return cand
    return candidates[0]


OUTPUT_DIR = _resolve_output_dir()

COSTS = OUTPUT_DIR / GRADED[0]
DEFECTS = OUTPUT_DIR / GRADED[1]
MEMO = OUTPUT_DIR / GRADED[2]

CANDIDATES = ["SUP-1042", "SUP-2318", "SUP-3155", "SUP-4077"]
AWARD = "SUP-1042"
RUNNER_UP = "SUP-4077"
NON_CANDIDATE = "SUP-9001"

GOOD_UNITS = 486000

COSTS_HEADER = ["supplier_code", "supplier_name", "quoted_price_usd_per_unit",
                "units_to_purchase", "total_fy2026_cost_usd",
                "cost_per_good_unit_usd", "rank"]
DEFECTS_HEADER = ["supplier_code", "lots_inspected", "units_inspected",
                  "units_rejected", "reject_rate_pct"]

REQUIRED_SECTIONS = ["## Recommendation", "## Cost Comparison",
                     "## Basis of Decision", "## Data Quality and Exclusions",
                     "## Risks and Sensitivities"]

GOLD_PRICE = {"SUP-1042": 1.9450, "SUP-2318": 1.9313,
              "SUP-3155": 1.8966, "SUP-4077": 1.8889}
GOLD_UNITS = {"SUP-1042": 495010, "SUP-2318": 492152,
              "SUP-3155": 517572, "SUP-4077": 497951}
GOLD_TOTAL = {"SUP-1042": 963017.63, "SUP-2318": 978217.33,
              "SUP-3155": 987625.94, "SUP-4077": 976373.13}
GOLD_PER_GOOD = {"SUP-1042": 1.9815, "SUP-2318": 2.0128,
                 "SUP-3155": 2.0322, "SUP-4077": 2.0090}
GOLD_RANK = {"SUP-1042": 1, "SUP-4077": 2, "SUP-2318": 3, "SUP-3155": 4}
GOLD_DEFECTS = {
    "SUP-1042": dict(lots=60, units=180000, rejected=3276, rate=1.820),
    "SUP-2318": dict(lots=58, units=176000, rejected=2200, rate=1.250),
    "SUP-3155": dict(lots=63, units=190000, rejected=11590, rate=6.100),
    "SUP-4077": dict(lots=61, units=182000, rejected=4368, rate=2.400),
}
GOLD_MARGIN = GOLD_TOTAL[RUNNER_UP] - GOLD_TOTAL[AWARD]   # 13355.50

NUMERIC_OK = re.compile(r"^-?\d+(\.\d+)?$")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def read_rows(path, header):
    """Parsed data rows keyed by supplier_code, or {} if unusable."""
    if not path.is_file():
        return {}, []
    text = path.read_text(encoding="utf-8", errors="replace")
    rows = list(csv.reader(io.StringIO(text)))
    rows = [r for r in rows if any(c.strip() for c in r)]
    if not rows:
        return {}, []
    body = rows[1:] if [c.strip() for c in rows[0]] == header else rows
    out = {}
    for r in body:
        if len(r) == len(header) and r[0].strip():
            out[r[0].strip()] = [c.strip() for c in r]
    return out, body


def costs_rows():
    return read_rows(COSTS, COSTS_HEADER)


def defects_rows():
    return read_rows(DEFECTS, DEFECTS_HEADER)


def memo_text():
    return MEMO.read_text(encoding="utf-8", errors="replace") if MEMO.is_file() else ""


def section(name):
    """Body of one level-2 section of the memo."""
    text = memo_text()
    if not text:
        return ""
    m = re.search(r"^##\s+" + re.escape(name.lstrip("# ").strip()) + r"\s*$",
                  text, re.MULTILINE | re.IGNORECASE)
    if not m:
        return ""
    rest = text[m.end():]
    nxt = re.search(r"^##\s+", rest, re.MULTILINE)
    return rest[:nxt.start()] if nxt else rest


def numbers_in(text):
    """Every number in `text`, tolerating $ signs and thousands separators."""
    out = []
    for tok in re.findall(r"-?\$?\d[\d,]*(?:\.\d+)?", text):
        try:
            out.append(float(tok.replace("$", "").replace(",", "")))
        except ValueError:
            pass
    return out


def close(a, b, rel=0.01):
    return abs(a - b) <= abs(b) * rel


def has_number(text, target, rel=0.01):
    return any(close(v, target, rel) for v in numbers_in(text))


def decimals(value):
    return len(value.split(".")[1]) if "." in value else 0


# ---------------------------------------------------------------------------
# file gate
# ---------------------------------------------------------------------------
def test_supplier_costs_file_exists():
    assert COSTS.is_file(), "missing /workspace/output/supplier_costs.csv"


def test_defect_rates_file_exists():
    assert DEFECTS.is_file(), "missing /workspace/output/defect_rates.csv"


def test_recommendation_file_exists():
    assert MEMO.is_file(), "missing /workspace/output/recommendation.md"


# ---------------------------------------------------------------------------
# supplier_costs.csv - shape and formatting
# ---------------------------------------------------------------------------
def test_supplier_costs_header_exact():
    assert COSTS.is_file(), "supplier_costs.csv not produced"
    first = next(csv.reader(io.StringIO(
        COSTS.read_text(encoding="utf-8", errors="replace"))), [])
    assert [c.strip() for c in first] == COSTS_HEADER, (
        "header is %r, expected %r" % (first, COSTS_HEADER))


def test_supplier_costs_has_four_candidate_rows():
    rows, body = costs_rows()
    assert len(body) == 4, "expected exactly 4 data rows, found %d" % len(body)
    assert sorted(rows) == sorted(CANDIDATES), (
        "supplier_code set is %s, expected %s" % (sorted(rows), sorted(CANDIDATES)))


def test_supplier_costs_numeric_formatting():
    rows, _ = costs_rows()
    assert rows, "no parsable rows in supplier_costs.csv"
    for code, r in rows.items():
        for idx in (2, 3, 4, 5, 6):
            assert NUMERIC_OK.match(r[idx]), (
                "%s field %s is %r; digits, one optional minus and one decimal "
                "point only" % (code, COSTS_HEADER[idx], r[idx]))
        assert decimals(r[2]) == 4, "%s quoted_price_usd_per_unit needs 4 dp" % code
        assert decimals(r[4]) == 2, "%s total_fy2026_cost_usd needs 2 dp" % code
        assert decimals(r[5]) == 4, "%s cost_per_good_unit_usd needs 4 dp" % code
        assert decimals(r[3]) == 0, "%s units_to_purchase must be an integer" % code
        assert decimals(r[6]) == 0, "%s rank must be an integer" % code


def test_supplier_costs_sorted_by_rank():
    rows, body = costs_rows()
    assert len(body) == 4, "expected 4 data rows"
    ranks = [int(float(r[6])) for r in body if len(r) == 7]
    assert ranks == [1, 2, 3, 4], "rows must be sorted by rank ascending, got %s" % ranks


def test_supplier_names_match_master():
    rows, _ = costs_rows()
    assert rows, "no parsable rows in supplier_costs.csv"
    expect = {
        "SUP-1042": "meridian precision works",
        "SUP-2318": "rheinwerk feinmechanik",
        "SUP-3155": "talleres nortenos",
        "SUP-4077": "brackenridge tooling",
    }
    for code, frag in expect.items():
        assert code in rows, "row for %s missing" % code
        assert frag in rows[code][1].casefold(), (
            "%s supplier_name is %r, expected the legal name from the supplier "
            "master" % (code, rows[code][1]))


# ---------------------------------------------------------------------------
# defect_rates.csv
# ---------------------------------------------------------------------------
def test_defect_rates_header_exact():
    assert DEFECTS.is_file(), "defect_rates.csv not produced"
    first = next(csv.reader(io.StringIO(
        DEFECTS.read_text(encoding="utf-8", errors="replace"))), [])
    assert [c.strip() for c in first] == DEFECTS_HEADER, (
        "header is %r, expected %r" % (first, DEFECTS_HEADER))


def test_defect_rates_four_rows_sorted_by_code():
    rows, body = defects_rows()
    assert len(body) == 4, "expected exactly 4 data rows, found %d" % len(body)
    codes = [r[0].strip() for r in body if r]
    assert codes == sorted(CANDIDATES), (
        "rows must be the four candidates sorted by supplier_code, got %s" % codes)
    assert NON_CANDIDATE not in codes, (
        "%s is not a candidate for the FY2026 award and must not appear" % NON_CANDIDATE)


def test_defect_rates_precision():
    rows, _ = defects_rows()
    assert rows, "no parsable rows in defect_rates.csv"
    for code, r in rows.items():
        for idx in (1, 2, 3, 4):
            assert NUMERIC_OK.match(r[idx]), (
                "%s field %s is %r" % (code, DEFECTS_HEADER[idx], r[idx]))
        assert decimals(r[4]) == 3, "%s reject_rate_pct needs 3 dp" % code
        for idx in (1, 2, 3):
            assert decimals(r[idx]) == 0, (
                "%s %s must be an integer" % (code, DEFECTS_HEADER[idx]))


def test_defect_rates_lot_counts_correct():
    rows, _ = defects_rows()
    assert rows, "no parsable rows in defect_rates.csv"
    for code, gold in GOLD_DEFECTS.items():
        assert code in rows, "row for %s missing" % code
        got = int(float(rows[code][1]))
        assert got == gold["lots"], (
            "%s lots_inspected is %d, expected %d distinct inspected lots"
            % (code, got, gold["lots"]))


def test_defect_rates_volumes_correct():
    rows, _ = defects_rows()
    assert rows, "no parsable rows in defect_rates.csv"
    for code, gold in GOLD_DEFECTS.items():
        assert code in rows, "row for %s missing" % code
        units = float(rows[code][2])
        rejected = float(rows[code][3])
        assert close(units, gold["units"], 0.005), (
            "%s units_inspected is %s, expected %d" % (code, units, gold["units"]))
        assert close(rejected, gold["rejected"], 0.005), (
            "%s units_rejected is %s, expected %d" % (code, rejected, gold["rejected"]))


def test_defect_rates_values_correct():
    rows, _ = defects_rows()
    assert rows, "no parsable rows in defect_rates.csv"
    for code, gold in GOLD_DEFECTS.items():
        assert code in rows, "row for %s missing" % code
        got = float(rows[code][4])
        assert abs(got - gold["rate"]) <= 0.05, (
            "%s reject_rate_pct is %s, expected %.3f" % (code, got, gold["rate"]))


# ---------------------------------------------------------------------------
# supplier_costs.csv - analysis correctness
# ---------------------------------------------------------------------------
def test_quoted_prices_normalized():
    rows, _ = costs_rows()
    assert rows, "no parsable rows in supplier_costs.csv"
    for code, gold in GOLD_PRICE.items():
        assert code in rows, "row for %s missing" % code
        got = float(rows[code][2])
        assert abs(got - gold) <= 0.0005, (
            "%s quoted_price_usd_per_unit is %s, expected %.4f USD per single "
            "piece" % (code, got, gold))


def test_units_to_purchase_correct():
    rows, _ = costs_rows()
    assert rows, "no parsable rows in supplier_costs.csv"
    for code, gold in GOLD_UNITS.items():
        assert code in rows, "row for %s missing" % code
        got = float(rows[code][3])
        assert got > GOOD_UNITS, (
            "%s units_to_purchase is %s, which is not above the FY2026 good-unit "
            "requirement" % (code, got))
        assert close(got, gold, 0.004), (
            "%s units_to_purchase is %s, expected %d" % (code, got, gold))


def test_total_costs_correct():
    rows, _ = costs_rows()
    assert rows, "no parsable rows in supplier_costs.csv"
    for code, gold in GOLD_TOTAL.items():
        assert code in rows, "row for %s missing" % code
        got = float(rows[code][4])
        assert close(got, gold, 0.01), (
            "%s total_fy2026_cost_usd is %s, expected %.2f" % (code, got, gold))


def test_cost_per_good_unit_correct():
    rows, _ = costs_rows()
    assert rows, "no parsable rows in supplier_costs.csv"
    for code, gold in GOLD_PER_GOOD.items():
        assert code in rows, "row for %s missing" % code
        got = float(rows[code][5])
        assert close(got, gold, 0.01), (
            "%s cost_per_good_unit_usd is %s, expected %.4f" % (code, got, gold))


def test_cost_per_good_unit_consistent_with_total():
    rows, _ = costs_rows()
    assert rows, "no parsable rows in supplier_costs.csv"
    for code, r in rows.items():
        total, per = float(r[4]), float(r[5])
        assert close(per * GOOD_UNITS, total, 0.02), (
            "%s cost_per_good_unit_usd %s does not reconcile with "
            "total_fy2026_cost_usd %s" % (code, per, total))


def test_full_ranking_correct():
    rows, _ = costs_rows()
    assert rows, "no parsable rows in supplier_costs.csv"
    got = {c: int(float(r[6])) for c, r in rows.items()}
    assert got == GOLD_RANK, "ranking is %s, expected %s" % (got, GOLD_RANK)


# ---------------------------------------------------------------------------
# the decision
# ---------------------------------------------------------------------------
def test_award_is_correct_supplier():
    rows, _ = costs_rows()
    assert rows, "no parsable rows in supplier_costs.csv"
    top = [c for c, r in rows.items() if r[6].strip() in ("1", "1.0")]
    assert len(top) == 1, "expected exactly one rank-1 row, found %s" % top
    assert top[0] == AWARD, (
        "supplier_costs.csv ranks %s first; the FY2026 award goes to %s"
        % (top[0], AWARD))


def test_recommendation_names_correct_supplier():
    body = section("Recommendation")
    assert body.strip(), "## Recommendation section missing or empty"
    codes = re.findall(r"SUP-\d{4}", body)
    assert codes, "## Recommendation names no supplier code"
    assert codes[0] == AWARD, (
        "## Recommendation puts forward %s; the award goes to %s" % (codes[0], AWARD))
    assert "meridian" in body.casefold(), (
        "## Recommendation does not name the awarded supplier's legal name")


def test_recommendation_states_total_and_margin():
    body = section("Recommendation")
    assert body.strip(), "## Recommendation section missing or empty"
    assert has_number(body, GOLD_TOTAL[AWARD], 0.01), (
        "## Recommendation does not state the awarded supplier's FY2026 total "
        "cost near USD %.2f" % GOLD_TOTAL[AWARD])
    assert has_number(body, GOLD_MARGIN, 0.05), (
        "## Recommendation does not state the USD margin over the second-ranked "
        "supplier near USD %.2f" % GOLD_MARGIN)


def test_runner_up_identified():
    rows, _ = costs_rows()
    assert rows, "no parsable rows in supplier_costs.csv"
    second = [c for c, r in rows.items() if r[6].strip() in ("2", "2.0")]
    assert second == [RUNNER_UP], (
        "supplier_costs.csv ranks %s second; expected %s" % (second, RUNNER_UP))


# ---------------------------------------------------------------------------
# recommendation.md - structure and required content
# ---------------------------------------------------------------------------
def test_memo_has_required_sections_in_order():
    text = memo_text()
    assert text.strip(), "recommendation.md missing or empty"
    found = re.findall(r"^##\s+.+$", text, re.MULTILINE)
    found = [h.strip() for h in found]
    missing = [s for s in REQUIRED_SECTIONS if s not in found]
    assert not missing, "missing required level-2 headings: %s" % missing
    idx = [found.index(s) for s in REQUIRED_SECTIONS]
    assert idx == sorted(idx), "required headings are out of order: %s" % found


def test_memo_states_good_unit_requirement():
    body = section("Cost Comparison")
    assert body.strip(), "## Cost Comparison section missing or empty"
    assert has_number(body, GOOD_UNITS, 0.001), (
        "## Cost Comparison does not state the FY2026 good-unit requirement "
        "of %d" % GOOD_UNITS)


def test_memo_cost_comparison_covers_all_four():
    body = section("Cost Comparison")
    assert body.strip(), "## Cost Comparison section missing or empty"
    missing = [c for c in CANDIDATES if c not in body and
               c.split("-")[1] not in body]
    assert not missing, "## Cost Comparison omits %s" % missing


def test_memo_flags_non_candidate_supplier():
    body = section("Data Quality and Exclusions")
    assert body.strip(), "## Data Quality and Exclusions section missing or empty"
    assert (NON_CANDIDATE in body or "old harbor" in body.casefold()), (
        "## Data Quality and Exclusions does not identify %s, the supplier that "
        "appears in the source data but is not a candidate" % NON_CANDIDATE)


def test_memo_totals_agree_with_costs_file():
    rows, _ = costs_rows()
    body = section("Cost Comparison")
    assert rows, "no parsable rows in supplier_costs.csv"
    assert body.strip(), "## Cost Comparison section missing or empty"
    assert has_number(body, float(rows[AWARD][4]), 0.005), (
        "## Cost Comparison does not carry the awarded supplier's total from "
        "supplier_costs.csv")


# ---------------------------------------------------------------------------
# penalties - each passes ONLY when its named defect is present
# ---------------------------------------------------------------------------
def test_penalty_award_is_split_or_deferred():
    """Prompt forbids splitting, dual-sourcing, staging or deferring."""
    body = section("Recommendation")
    if not body.strip():
        assert False, "no ## Recommendation section to judge; penalty not charged"
    low = body.casefold()
    banned = ["dual-source", "dual source", "dual-sourcing", "split the award",
              "split award", "splitting the award", "two suppliers",
              "defer the decision", "defer the award", "stage the award",
              "staged award", "phased award"]
    hit = [p for p in banned if p in low]
    assert hit, "no split/deferral language found; penalty not charged"


def test_penalty_memo_contains_placeholder_values():
    """Prompt forbids placeholder or unfilled figures."""
    text = memo_text()
    if not text.strip():
        assert False, "no memo to judge; penalty not charged"
    hits = re.findall(r"\bTBD\b|\bTODO\b|\bXXX+\b|\[insert[^\]]*\]|\bFIXME\b",
                      text, re.IGNORECASE)
    assert hits, "no placeholder markers found; penalty not charged"


def test_penalty_memo_total_contradicts_costs_file():
    """The memo states a headline FY2026 total that contradicts the value its
    own supplier_costs.csv carries for the awarded supplier.

    Charged only when the memo does state a total-sized figure and that figure
    disagrees. A memo that states no total at all is not charged here - the
    positive check already covers that.
    """
    rows, _ = costs_rows()
    body = section("Recommendation")
    if not rows or not body.strip():
        assert False, "not enough output to judge; penalty not charged"
    # the attempt's OWN rank-1 supplier, not the ground-truth award: this is an
    # internal-contradiction check and must be independent of whether the
    # decision itself is right
    top = [c for c, r in rows.items() if r[6].strip() in ("1", "1.0")]
    if len(top) != 1:
        assert False, "no single rank-1 row to compare against; penalty not charged"
    try:
        stated = float(rows[top[0]][4])
    except ValueError:
        assert False, "rank-1 total is not numeric; penalty not charged"
    candidates = [v for v in numbers_in(body) if 100_000 <= v <= 100_000_000]
    if not candidates:
        assert False, "memo states no total-sized figure; penalty not charged"
    assert not any(close(v, stated, 0.005) for v in candidates), (
        "memo agrees with supplier_costs.csv; penalty not charged")
