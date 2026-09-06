"""Programmatic checks over the attempt's FINAL OUTPUT FILES only.

Nothing here reads the trajectory, the environment, or how the work was done -
only what landed in /workspace/output. Deterministic: no network, no clock, no
randomness.

Every numeric check is exact at the precision instruction.md tells the attempt
to report: half a unit in the last reported place, so the latitude is in how a
figure is written down, never in what it is. The prose checks are the mirror of
that - any wording passes, but the substance the prompt asks for has to be
there.

The decision is three figures the committee signs: the supplier, the quantity
contracted with it and its contract-year cost. Each is reachable only through
the whole analysis, so each carries decision weight in test_weights.json. The
sentinel checks below the figure checks name the one population question each
guards; they are earned only by an attempt that made that correction.

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

GRADED = ["supplier_costs.csv", "defect_rates.csv", "cost_buildup.csv",
          "recommendation.md"]

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
BUILDUP = OUTPUT_DIR / GRADED[2]
MEMO = OUTPUT_DIR / GRADED[3]

CANDIDATES = ["SUP-1042", "SUP-2318", "SUP-3155", "SUP-4077"]
AWARD = "SUP-1042"
RUNNER_UP = "SUP-4077"
NON_CANDIDATE = "SUP-9001"

# The FY2026 contract year the four offers cover is 1 April 2026 - 31 March
# 2027 (term-sheet header block; finance policy section 6). The planning cube
# dump is a rolling fifteen-month horizon carrying two S&OP cycles, so the
# requirement has to be cut out of it: the frozen November cycle read over the
# contract year is 493,000 pieces, read as calendar 2026 it is 512,000 and read
# whole it is 623,600.
GOOD_UNITS = 493000
CALENDAR_UNITS = 512000
HORIZON_UNITS = 623600

COSTS_HEADER = ["supplier_code", "supplier_name", "quoted_price_usd_per_unit",
                "units_to_purchase", "total_fy2026_cost_usd",
                "cost_per_good_unit_usd", "rank"]
DEFECTS_HEADER = ["supplier_code", "lots_inspected", "units_inspected",
                  "units_rejected", "reject_rate_pct"]
BUILDUP_HEADER = ["supplier_code", "cost_element", "amount_usd"]
ELEMENT_OK = re.compile(r"^[a-z0-9_]{1,32}$")

REQUIRED_SECTIONS = ["## Recommendation", "## Cost Comparison",
                     "## Basis of Decision", "## Data Quality and Exclusions",
                     "## Risks and Sensitivities"]

# The legal names as the supplier master spells them.
GOLD_NAME = {"SUP-1042": "Meridian Precision Works, LLC",
             "SUP-2318": "Rheinwerk Feinmechanik GmbH",
             "SUP-3155": "Talleres Nortenos, S.A. de C.V.",
             "SUP-4077": "Brackenridge Tooling Ltd"}

# Reference figures UNROUNDED, ahead of the rounding instruction.md asks for,
# as solution/_provenance/verify_design.py re-derives them from the shipped
# files. The checks below compare against these to half a unit in the last
# reported place, so the reported value is accepted only where it is this
# figure written to the required precision.
GOLD_PRICE = {"SUP-1042": 1.9450, "SUP-2318": 1.8662,
              "SUP-3155": 1.828475, "SUP-4077": 1.7904672}
GOLD_UNITS = {"SUP-1042": 494936, "SUP-2318": 498500,
              "SUP-3155": 517815, "SUP-4077": 504431}
GOLD_TOTAL = {"SUP-1042": 950828.5671013698, "SUP-2318": 962729.479,
              "SUP-3155": 970826.7189421575, "SUP-4077": 953203.2644085682}
GOLD_PER_GOOD = {"SUP-1042": 1.9286583511183972,
                 "SUP-2318": 1.9527981318458418,
                 "SUP-3155": 1.9692225536352080,
                 "SUP-4077": 1.9334751813561220}
GOLD_RANK = {"SUP-1042": 1, "SUP-4077": 2, "SUP-2318": 3, "SUP-3155": 4}

# `rejected` is every piece failed at incoming inspection - what
# defect_rates.csv reports. `scrapped` is the part of it Cadence disposed of;
# the rest went back to the seller on a return authorisation and was replaced
# free of charge inside the contract year (clause 5.4 of every term sheet), so
# it is not a loss the purchase quantity has to carry.
GOLD_DEFECTS = {
    "SUP-1042": dict(lots=60, units=180000, rejected=3276, scrapped=704,
                     returned=2572, rate=1.820),
    "SUP-2318": dict(lots=58, units=176000, rejected=2200, scrapped=1936,
                     returned=264, rate=1.250),
    "SUP-3155": dict(lots=63, units=190000, rejected=11590, scrapped=9105,
                     returned=2485, rate=6.100),
    "SUP-4077": dict(lots=61, units=182000, rejected=4368, scrapped=4124,
                     returned=244, rate=2.400),
}
REJECTED_TOTAL = sum(d["rejected"] for d in GOLD_DEFECTS.values())    # 21434
SCRAPPED_TOTAL = sum(d["scrapped"] for d in GOLD_DEFECTS.values())    # 15869
RETURNED_TOTAL = sum(d["returned"] for d in GOLD_DEFECTS.values())    #  5565

GOLD_MARGIN = GOLD_TOTAL[RUNNER_UP] - GOLD_TOTAL[AWARD]   # 2374.70
REBATE_THRESHOLD_4077 = 520000
BOX_2318 = 100

# Individual elements of the cost build-up, at the 2 dp the file reports. Each
# is reachable only through the analysis that produces it: the disposal base is
# the pieces Cadence actually scraps, the freight lanes are the two FCA offers,
# the rebate is banded and the shortfall is owed because the buy misses the
# 520,000-piece commitment.
GOLD_MATERIAL = {"SUP-1042": 962650.52, "SUP-2318": 930300.70,
                 "SUP-3155": 946811.78, "SUP-4077": 903167.16}
GOLD_DISPOSAL = {"SUP-1042": 2420.00, "SUP-2318": 6875.00,
                 "SUP-3155": 31018.75, "SUP-4077": 14288.75}
GOLD_FREIGHT = {"SUP-2318": 36667.00, "SUP-4077": 35497.00}
GOLD_TERMS = {"SUP-1042": -14241.95, "SUP-3155": -7003.81,
              "SUP-4077": -6680.96}
GOLD_REBATE_2318 = -11113.22
GOLD_SHORTFALL_4077 = 6931.32

# The figures that stand behind each supplier's place in the ranking: its own
# cost build-up and its own quality. `## Basis of Decision` has to say why the
# suppliers that lost lose, so naming one is not enough - the statement that
# names it has to carry one of that supplier's numbers.
GOLD_DRIVERS = {
    "SUP-1042": [950828.57, 1.9287, 494936, 1.820, 1.9450, 2420.00, 14241.95,
                 0.391],
    "SUP-2318": [962729.48, 1.9528, 498500, 1.250, 1.8662, 36667.00, 11113.22,
                 27909.02, 6875.00, 1.100],
    "SUP-3155": [970826.72, 1.9692, 517815, 6.100, 1.8285, 31018.75, 7003.81,
                 4.792],
    "SUP-4077": [953203.26, 1.9335, 504431, 2.400, 1.7905, 35497.00, 6931.32,
                 14288.75, 6680.96, 520000, 2.266],
}

# The populations a data-quality section can report having set aside, each with
# the spellings an attempt might use. The prompt asks what was excluded and
# why, so naming the non-candidate supplier alone does not answer it.
EXCLUSION_TOPICS = {
    "source inspections": r"source[\s-]*inspect|\bSOURCE\b|at the (?:supplier|seller)'?s? plant",
    "the ERP renumbering": r"\bERP\b|go-?live|cut-?over|CHG-2025|po_reference|reporting number",
    "the superseded plan cycle": r"october|plan[_\s-]*cycle|s&op cycle|superseded|frozen",
    "the other part": r"SP-22",
    "the cube subtotal rows": r"\bTOTAL\b|sub-?total",
    "double-keyed lots": r"duplicat|dedup|same lot",
    "cancelled orders": r"cancel",
    "the daily FX export": r"daily|planning rate|fx_daily|exchange rate",
}
MIN_EXCLUSION_TOPICS = 3
MIN_SECTION_WORDS = 30          # instruction.md sets this floor per section

# Awarding language. instruction.md asks `## Recommendation` for exactly one
# awarded supplier, so a statement that awards a different one is a second
# award however the memo words it.
AWARD_WORDS = r"award|recommend|select|choose|consolidat|go with|place the (?:volume|contract)"

# Conditional language. instruction.md asks `## Risks and Sensitivities` to say
# what would have to change to overturn the recommendation, as a quantity, so
# the section needs a figure inside a condition rather than a figure anywhere.
CONDITION_WORDS = (r"\bif\b|\bonce\b|\bwere\b|\bwould\b|above|below|beyond|"
                   r"exceed|reach|rise|fall|drift|past|over |under |up to|"
                   r"break-?even|breakeven|threshold|unless|overturn|reverse|flip")

# Where the requirement came from, for `## Cost Comparison`: instruction.md
# asks for the demand data it was taken from, and the demand extract is a
# planning-cube dump of monthly rows by part and S&OP cycle.
DEMAND_SOURCE_WORDS = (r"cycle|s&op|sop\b|november|monthly|month|plan\b|"
                       r"planning|forecast|cube|extract|sp-40|frozen|"
                       r"forecast_2026|demand file|demand data")

# Reason language, for `## Data Quality and Exclusions`: the prompt asks what
# was excluded AND why, so a bare list of populations does not answer it.
REASON_WORDS = (r"because|since|therefore|so that|so it|so they|as they|as it|"
                r"rather than|instead|not a candidate|out of scope|superseded|"
                r"replaced|never|do(?:es)? not|is not|are not|would|which is|"
                r"reason|due to|leaving|counted|set aside|excluded|dropped")

# The build-up instruction.md requires in `## Cost Comparison`: every element
# charged, labelled, as a US-dollar amount. These two are the elements a
# hurried cost model leaves out entirely, and they decide the award.
# Sections 3 and 5 of the shipped finance policy put a working-capital value
# on payment terms and a disposal cost on every rejected piece, so any correct
# build-up charges both. The labels are the attempt's own, so these are matched
# as amounts: an attempt that never modelled them has no row carrying the
# figure. Zero-valued elements are not required.
GOLD_BUILDUP = {
    "SUP-1042": {"payment terms": GOLD_TERMS["SUP-1042"]},
    "SUP-3155": {"payment terms": GOLD_TERMS["SUP-3155"]},
    "SUP-4077": {"payment terms": GOLD_TERMS["SUP-4077"]},
}

# Where in the demand data the requirement came from, for the second half of
# what `## Cost Comparison` is asked to state: the period it covers. The
# contract year is in the header block of all four term sheets and in section
# 6 of the finance policy.
CONTRACT_WINDOW_FROM = r"april\s*2026|apr\.?\s*2026|2026-04|04/2026|1[\s./-]*4[\s./-]*2026"
CONTRACT_WINDOW_TO = r"march\s*2027|mar\.?\s*2027|2027-03|03/2027|31[\s./-]*3[\s./-]*2027"

# The two dispositions an incoming reject can take. `## Data Quality and
# Exclusions` is asked which records were counted towards the reject rates and
# which were set aside; an attempt that never separated the two has no figure
# for the pieces that went back to the seller.
DISPOSITION_WORDS = (r"return|rtv|rma|replac|sent back|back to the (?:seller|"
                     r"supplier|vendor)|scrap")

# What separates the four offers. A statement that names a supplier that lost
# and reaches for one of these is giving a reason, whatever words it uses; a
# statement that names it and reaches for none of them is a list entry.
DRIVER_WORDS = (r"freight|duty|brokerage|incoterm|deliver|rebate|shortfall|"
                r"commitment|threshold|volume|reject|quality|defect|scrap|"
                r"price|quote|terms|discount|payment|yield|box|currency|"
                r"exchange|lead time")

NUMERIC_OK = re.compile(r"^-?\d+(\.\d+)?$")

# Decimal places instruction.md fixes for each reported field.
DP_PRICE, DP_TOTAL, DP_PER_GOOD, DP_RATE = 4, 2, 4, 3

# A dollar figure quoted in the memo passes to the cent or rounded to the whole
# dollar, which is what instruction.md allows there. Half a dollar of slack on
# a six-figure total is the same number written differently; a total that is
# actually different misses by thousands.
MONEY_SLACK = 0.50


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


def buildup_rows():
    """cost_buildup.csv as (supplier_code, element, amount) triples."""
    if not BUILDUP.is_file():
        return []
    text = BUILDUP.read_text(encoding="utf-8", errors="replace")
    rows = [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]
    if not rows:
        return []
    body = rows[1:] if [c.strip() for c in rows[0]] == BUILDUP_HEADER else rows
    return [tuple(c.strip() for c in r) for r in body if len(r) == 3]


def buildup_by_supplier():
    out = {}
    for code, element, amount in buildup_rows():
        out.setdefault(code, []).append((element, as_float(amount)))
    return out


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
    """Relative agreement, used only by the contradiction penalty, where a wide
    band is the conservative direction: the penalty must not fire on a figure
    the memo merely rounds differently."""
    return abs(a - b) <= abs(b) * rel


def at_precision(got, gold, dp):
    """True when `got` is `gold` reported to `dp` decimal places.

    Half a unit in the last place, so a correct figure passes whichever way the
    attempt breaks a rounding tie and the unrounded figure passes too, while a
    value that differs analytically - by even one unit in that last place -
    does not.
    """
    return abs(got - gold) <= 0.5 * 10 ** -dp + 1e-9


def is_whole(value):
    return abs(value - round(value)) <= 1e-9


# A dollar marker directly before or after a figure: `USD 963017.63`,
# `$963,017.63`, `963,017.63 USD`, `963,018 US dollars`.
DOLLAR_BEFORE = r"(?:USD|US\$|\$|US dollars?)\s*"
DOLLAR_AFTER = r"\s*(?:USD|US dollars?|dollars?)\b"
NUMBER = r"-?\d[\d,]*(?:\.\d+)?"


def dollar_figures(text):
    """Every figure the text explicitly states in US dollars."""
    out = []
    for pat in (DOLLAR_BEFORE + "(" + NUMBER + ")", "(" + NUMBER + ")" + DOLLAR_AFTER):
        for tok in re.findall(pat, text):
            try:
                out.append(float(tok.replace(",", "")))
            except ValueError:
                pass
    return out


def states_dollars(text, target):
    """The text states `target` as a US-dollar amount, to the cent or dollar."""
    return any(abs(v - target) <= MONEY_SLACK + 1e-9 for v in dollar_figures(text))


def states_money(text, target):
    """The text quotes `target` US dollars, to the cent or to the dollar."""
    return any(abs(v - target) <= MONEY_SLACK + 1e-9 for v in numbers_in(text))


def states_count(text, target):
    """The text quotes the whole number `target`, not one near it."""
    return any(abs(v - target) < 0.5 for v in numbers_in(text))


def statements(text):
    """The units a figure can be tied to: each table row on its own, and each
    sentence of running prose (with soft line-wraps joined first)."""
    out = []
    for block in re.split(r"\n\s*\n", text):
        for line in block.splitlines():
            if line.lstrip().startswith("|"):
                out.append(line)
        prose = " ".join(l for l in block.splitlines() if not l.lstrip().startswith("|"))
        out.extend(s for s in re.split(r"(?<=[.!?])\s+", prose) if s.strip())
    return out


def name_key(text):
    """Letters and digits only, casefolded.

    Punctuation and spacing inside a legal name vary freely - `Talleres
    Nortenos, S.A. de C.V.` and `Talleres Nortenos SA de CV` are the same name
    - but the name still has to be whole: a truncated or altered one does not
    match.
    """
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


def mentions(text, code):
    return code in text or name_key(GOLD_NAME[code]) in name_key(text)


def carries_a_figure_of(text, code):
    """`text` states one of `code`'s own figures.

    Money and quantities are matched to the whole unit, rates and per-piece
    figures to the last place the prompt asks for, so any rounding an attempt
    writes its memo in still counts.
    """
    for value in numbers_in(text):
        for target in GOLD_DRIVERS[code]:
            slack = MONEY_SLACK if abs(target) >= 1000 else 0.005
            if abs(value - target) <= slack + 1e-9:
                return True
    return False


def as_float(text, default=None):
    try:
        return float(text)
    except (TypeError, ValueError):
        return default


def decimals(value):
    return len(value.split(".")[1]) if "." in value else 0


def rank_one_row():
    """The attempt's own rank-1 row of supplier_costs.csv, or None."""
    rows, _ = costs_rows()
    top = [r for r in rows.values() if r[6].strip() in ("1", "1.0")]
    return top[0] if len(top) == 1 else None


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
    ranks = [as_float(r[6]) for r in body if len(r) == len(COSTS_HEADER)]
    assert all(r is not None and is_whole(r) for r in ranks), (
        "every rank must be an integer, got %s" % [r[6] for r in body])
    assert [int(r) for r in ranks] == [1, 2, 3, 4], (
        "rows must be sorted by rank ascending, got %s" % [int(r) for r in ranks])


def test_supplier_names_match_master():
    """The whole legal name, not a fragment of it: punctuation and spacing may
    vary, a dropped legal suffix or an altered name may not."""
    rows, _ = costs_rows()
    assert rows, "no parsable rows in supplier_costs.csv"
    for code, gold in GOLD_NAME.items():
        assert code in rows, "row for %s missing" % code
        assert name_key(rows[code][1]) == name_key(gold), (
            "%s supplier_name is %r, expected the supplier master's legal name "
            "%r in full" % (code, rows[code][1], gold))


# ---------------------------------------------------------------------------
# defect_rates.csv - shape
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


# ---------------------------------------------------------------------------
# recommendation.md - structure
# ---------------------------------------------------------------------------
def test_memo_has_required_sections_in_order():
    """The five required sections, in order, each carrying the content the
    prompt asks that section for - a heading over an empty or filler body is
    not a delivered section."""
    text = memo_text()
    assert text.strip(), "recommendation.md missing or empty"
    found = re.findall(r"^##\s+.+$", text, re.MULTILINE)
    found = [h.strip() for h in found]
    missing = [s for s in REQUIRED_SECTIONS if s not in found]
    assert not missing, "missing required level-2 headings: %s" % missing
    idx = [found.index(s) for s in REQUIRED_SECTIONS]
    assert idx == sorted(idx), "required headings are out of order: %s" % found

    thin = [(s, len(section(s).split())) for s in REQUIRED_SECTIONS
            if len(section(s).split()) < MIN_SECTION_WORDS]
    assert not thin, (
        "instruction.md sets a floor of %d words per section; short: %s"
        % (MIN_SECTION_WORDS, ", ".join("%s (%d)" % t for t in thin)))

    # the two sections whose substance nothing else here grades: why the
    # suppliers that were not picked lose, and what would overturn the award
    basis = section("Basis of Decision")
    silent = [c for c in CANDIDATES if c != AWARD and not mentions(basis, c)]
    assert not silent, (
        "## Basis of Decision never names %s" % ", ".join(silent))
    # a list of the three losers is not a reason any of them loses: the
    # statement that names one has to carry one of that supplier's own figures
    def explained(code):
        for unit in statements(basis):
            if not mentions(unit, code):
                continue
            if carries_a_figure_of(unit, code):
                return True
            if re.search(DRIVER_WORDS, unit, re.IGNORECASE):
                return True
        return False

    unexplained = [c for c in CANDIDATES if c != AWARD and not explained(c)]
    assert not unexplained, (
        "## Basis of Decision names %s without a figure of its own or anything "
        "that separates the offers beside it, so it lists them rather than "
        "saying why they lose" % ", ".join(unexplained))

    risks = section("Risks and Sensitivities")
    assert mentions(risks, AWARD), (
        "## Risks and Sensitivities does not tie the risks to the awarded "
        "supplier")
    # what would overturn the award is graded by the rubric against the figure
    # it has to be: this check keeps to what it can settle from the file, that
    # the section is about the supplier being awarded.


# ---------------------------------------------------------------------------
# the decision: supplier, contract quantity, contract-year cost
# ---------------------------------------------------------------------------
def test_award_is_correct_supplier():
    rows, _ = costs_rows()
    assert rows, "no parsable rows in supplier_costs.csv"
    top = [c for c, r in rows.items() if r[6].strip() in ("1", "1.0")]
    assert len(top) == 1, "expected exactly one rank-1 row, found %s" % top
    assert top[0] == AWARD, (
        "supplier_costs.csv ranks %s first; the FY2026 award goes to %s"
        % (top[0], AWARD))


def test_award_quantity_is_correct():
    """The quantity the committee contracts: the rank-1 row's units_to_purchase.

    Reachable only with the right supplier, the frozen plan cycle, the
    incoming-only reject rate on every attributed lot and the gross-up.
    """
    top = rank_one_row()
    assert top is not None, "no single rank-1 row in supplier_costs.csv"
    got = as_float(top[3])
    assert got is not None, "rank-1 units_to_purchase is not numeric"
    assert is_whole(got) and int(round(got)) == GOLD_UNITS[AWARD], (
        "the rank-1 row (%s) contracts %s pieces; the award is %d pieces of %s"
        % (top[0], top[3], GOLD_UNITS[AWARD], AWARD))


def test_award_total_is_correct():
    """The contract-year cost the committee signs: the rank-1 row's total."""
    top = rank_one_row()
    assert top is not None, "no single rank-1 row in supplier_costs.csv"
    got = as_float(top[4])
    assert got is not None, "rank-1 total_fy2026_cost_usd is not numeric"
    assert at_precision(got, GOLD_TOTAL[AWARD], DP_TOTAL), (
        "the rank-1 row (%s) costs USD %s; the award costs USD %.2f"
        % (top[0], top[4], round(GOLD_TOTAL[AWARD], DP_TOTAL)))


def test_recommendation_names_correct_supplier():
    """The memo awards the supplier its own costs file ranks first, and that
    supplier is SUP-1042, named by code and full legal name.

    A memo that mentions SUP-1042 only as the runner-up it beat has not
    awarded it; the rank-1 row of supplier_costs.csv says who was awarded,
    so that row has to be SUP-1042 for the mention to count.
    """
    body = section("Recommendation")
    assert body.strip(), "## Recommendation section missing or empty"
    top = rank_one_row()
    assert top is not None, "no single rank-1 row in supplier_costs.csv"
    assert top[0] == AWARD, (
        "supplier_costs.csv ranks %s first, so that is the supplier this memo "
        "awards; the award goes to %s" % (top[0], AWARD))
    assert AWARD in body, (
        "## Recommendation does not name the awarded supplier by its code, %s"
        % AWARD)
    assert name_key(GOLD_NAME[AWARD]) in name_key(body), (
        "## Recommendation does not name the awarded supplier's legal name in "
        "full, %r" % GOLD_NAME[AWARD])
    # the section has to put this supplier forward, not merely name it
    put_forward = [u for u in statements(body)
                   if mentions(u, AWARD) and re.search(AWARD_WORDS, u, re.IGNORECASE)]
    assert put_forward, (
        "## Recommendation names %s but never puts it forward for the award; "
        "the prompt asks the section to name the awarded supplier" % AWARD)
    # exactly one: no statement may award a supplier other than the awardee
    also_awarded = sorted({
        c for c in CANDIDATES if c != AWARD
        for unit in statements(body)
        if mentions(unit, c) and not mentions(unit, AWARD)
        and re.search(AWARD_WORDS, unit, re.IGNORECASE)})
    assert not also_awarded, (
        "## Recommendation puts %s forward for the award as well; the prompt "
        "asks for exactly one awarded supplier" % ", ".join(also_awarded))


def test_recommendation_states_quantity_total_and_margin():
    """The prompt asks the Recommendation section for the contract quantity,
    the total cost in US dollars and the US-dollar margin over the runner-up."""
    body = section("Recommendation")
    assert body.strip(), "## Recommendation section missing or empty"
    assert states_count(body, GOLD_UNITS[AWARD]), (
        "## Recommendation does not state the FY2026 purchase quantity of "
        "%d pieces" % GOLD_UNITS[AWARD])
    assert states_dollars(body, GOLD_TOTAL[AWARD]), (
        "## Recommendation does not state the awarded supplier's FY2026 total "
        "cost, USD %.2f, as a US-dollar amount" % round(GOLD_TOTAL[AWARD], 2))
    assert states_dollars(body, GOLD_MARGIN), (
        "## Recommendation does not state the US-dollar amount by which the "
        "award beats the second-ranked supplier over FY2026, USD %.2f"
        % round(GOLD_MARGIN, 2))


def test_full_ranking_correct():
    rows, _ = costs_rows()
    assert rows, "no parsable rows in supplier_costs.csv"
    raw = {c: as_float(r[6]) for c, r in rows.items()}
    assert all(v is not None and is_whole(v) for v in raw.values()), (
        "every rank must be an integer, got %s" % {c: r[6] for c, r in rows.items()})
    got = {c: int(round(v)) for c, v in raw.items()}
    assert got == GOLD_RANK, "ranking is %s, expected %s" % (got, GOLD_RANK)


def test_runner_up_identified():
    rows, _ = costs_rows()
    assert rows, "no parsable rows in supplier_costs.csv"
    second = [c for c, r in rows.items() if r[6].strip() in ("2", "2.0")]
    assert second == [RUNNER_UP], (
        "supplier_costs.csv ranks %s second; expected %s" % (second, RUNNER_UP))


# ---------------------------------------------------------------------------
# defect_rates.csv - figures
# ---------------------------------------------------------------------------
def test_defect_rates_lot_counts_correct():
    rows, _ = defects_rows()
    assert rows, "no parsable rows in defect_rates.csv"
    for code, gold in GOLD_DEFECTS.items():
        assert code in rows, "row for %s missing" % code
        raw = as_float(rows[code][1])
        assert raw is not None and is_whole(raw), (
            "%s lots_inspected is %r, expected a whole number of lots"
            % (code, rows[code][1]))
        got = int(round(raw))
        assert got == gold["lots"], (
            "%s lots_inspected is %d, expected %d distinct inspected lots"
            % (code, got, gold["lots"]))


def test_defect_rates_volumes_correct():
    rows, _ = defects_rows()
    assert rows, "no parsable rows in defect_rates.csv"
    for code, gold in GOLD_DEFECTS.items():
        assert code in rows, "row for %s missing" % code
        units = as_float(rows[code][2])
        rejected = as_float(rows[code][3])
        assert units is not None and rejected is not None, (
            "%s inspection volumes are not numeric" % code)
        assert is_whole(units) and int(round(units)) == gold["units"], (
            "%s units_inspected is %s, expected exactly %d pieces inspected"
            % (code, rows[code][2], gold["units"]))
        assert is_whole(rejected) and int(round(rejected)) == gold["rejected"], (
            "%s units_rejected is %s, expected exactly %d pieces rejected"
            % (code, rows[code][3], gold["rejected"]))


def test_defect_rates_values_correct():
    rows, _ = defects_rows()
    assert rows, "no parsable rows in defect_rates.csv"
    for code, gold in GOLD_DEFECTS.items():
        assert code in rows, "row for %s missing" % code
        got = as_float(rows[code][4])
        assert got is not None, "%s reject_rate_pct is not numeric" % code
        assert at_precision(got, gold["rate"], DP_RATE), (
            "%s reject_rate_pct is %s, expected %.3f - rejected pieces over "
            "inspected pieces, as a percentage"
            % (code, rows[code][4], gold["rate"]))


# ---------------------------------------------------------------------------
# supplier_costs.csv - figures
# ---------------------------------------------------------------------------
def test_quoted_prices_normalized():
    rows, _ = costs_rows()
    assert rows, "no parsable rows in supplier_costs.csv"
    for code, gold in GOLD_PRICE.items():
        assert code in rows, "row for %s missing" % code
        got = as_float(rows[code][2])
        assert got is not None, "%s quoted_price_usd_per_unit is not numeric" % code
        assert at_precision(got, gold, DP_PRICE), (
            "%s quoted_price_usd_per_unit is %s, expected %.4f USD per single "
            "piece" % (code, rows[code][2], round(gold, DP_PRICE)))


def test_units_to_purchase_correct():
    rows, _ = costs_rows()
    assert rows, "no parsable rows in supplier_costs.csv"
    for code, gold in GOLD_UNITS.items():
        assert code in rows, "row for %s missing" % code
        got = as_float(rows[code][3])
        assert got is not None, "%s units_to_purchase is not numeric" % code
        assert got > GOOD_UNITS, (
            "%s units_to_purchase is %s, which is not above the FY2026 good-unit "
            "requirement" % (code, rows[code][3]))
        assert is_whole(got) and int(round(got)) == gold, (
            "%s units_to_purchase is %s, expected exactly %d: the good-unit "
            "requirement grossed up for that supplier's own reject rate, "
            "rounded up to the next whole piece (or whole pack where the "
            "supplier sells only in packs)" % (code, rows[code][3], gold))


def test_total_costs_correct():
    rows, _ = costs_rows()
    assert rows, "no parsable rows in supplier_costs.csv"
    for code, gold in GOLD_TOTAL.items():
        assert code in rows, "row for %s missing" % code
        got = as_float(rows[code][4])
        assert got is not None, "%s total_fy2026_cost_usd is not numeric" % code
        assert at_precision(got, gold, DP_TOTAL), (
            "%s total_fy2026_cost_usd is %s, expected %.2f"
            % (code, rows[code][4], round(gold, DP_TOTAL)))


def test_cost_per_good_unit_correct():
    rows, _ = costs_rows()
    assert rows, "no parsable rows in supplier_costs.csv"
    for code, gold in GOLD_PER_GOOD.items():
        assert code in rows, "row for %s missing" % code
        got = as_float(rows[code][5])
        assert got is not None, "%s cost_per_good_unit_usd is not numeric" % code
        assert at_precision(got, gold, DP_PER_GOOD), (
            "%s cost_per_good_unit_usd is %s, expected %.4f"
            % (code, rows[code][5], round(gold, DP_PER_GOOD)))


def test_cost_per_good_unit_uses_the_contract_year_requirement():
    """cost_per_good_unit_usd divides a supplier's own filed total by the
    good-unit requirement it worked to, so it says which requirement that was.
    The four offers run 1 April 2026 - 31 March 2027; the frozen November cycle
    read over that window is 493,000 pieces, read as calendar 2026 it is
    512,000 and read over the whole fifteen-month cube horizon 623,600."""
    rows, _ = costs_rows()
    assert rows, "no parsable rows in supplier_costs.csv"
    for code, r in rows.items():
        total, per = as_float(r[4]), as_float(r[5])
        assert total is not None and per is not None, (
            "%s total_fy2026_cost_usd / cost_per_good_unit_usd are not numeric"
            % code)
        expect = total / GOOD_UNITS
        assert at_precision(per, expect, DP_PER_GOOD), (
            "%s cost_per_good_unit_usd is %s; its own total_fy2026_cost_usd %s "
            "divided by the %d good units required is %.4f"
            % (code, r[5], r[4], GOOD_UNITS, round(expect, DP_PER_GOOD)))


# ---------------------------------------------------------------------------
# sentinels - each is earned only by the population correction it names
# ---------------------------------------------------------------------------
def test_reject_rates_count_incoming_inspections_only():
    """The inspection log pools pre-shipment SOURCE inspections with the
    INCOMING ones. Pieces failed at the seller's own plant are scrapped there
    and never ship; counting them lifts the share of SUP-1042's inspected
    pieces that Cadence scrapped from 0.391% to about 2.54% and hands the award
    to SUP-4077. Only an attempt that restricted the rate to INCOMING records
    reports 180,000 pieces inspected and 3,276 rejected."""
    rows, _ = defects_rows()
    assert rows and AWARD in rows, "no %s row in defect_rates.csv" % AWARD
    units, rejected = as_float(rows[AWARD][2]), as_float(rows[AWARD][3])
    assert units is not None and rejected is not None, "%s volumes not numeric" % AWARD
    gold = GOLD_DEFECTS[AWARD]
    assert int(round(units)) == gold["units"] and int(round(rejected)) == gold["rejected"], (
        "%s is reported at %s rejected of %s inspected; the incoming record is "
        "%d of %d - pre-shipment source inspections are not incoming rejects"
        % (AWARD, rows[AWARD][3], rows[AWARD][2], gold["rejected"], gold["units"]))


def test_reject_rates_carry_every_attributed_lot():
    """SUP-3155's worst lots are the ones a careless attribution loses: the
    post-cutover receipts that only the ERP number reference resolves, and the
    lots whose free-text supplier field is blank. Both routes cut the share
    Cadence scrapped from 4.792% to about 1.5% and hand it the award. Only an
    attempt that attributed every lot reports 63 lots and 11,590 rejected
    pieces."""
    rows, _ = defects_rows()
    assert rows and "SUP-3155" in rows, "no SUP-3155 row in defect_rates.csv"
    lots, rejected = as_float(rows["SUP-3155"][1]), as_float(rows["SUP-3155"][3])
    assert lots is not None and rejected is not None, "SUP-3155 figures not numeric"
    gold = GOLD_DEFECTS["SUP-3155"]
    assert int(round(lots)) == gold["lots"] and int(round(rejected)) == gold["rejected"], (
        "SUP-3155 is reported on %s lots with %s rejects; every attributed lot "
        "gives %d lots and %d rejects" % (rows["SUP-3155"][1], rows["SUP-3155"][3],
                                          gold["lots"], gold["rejected"]))


def test_buy_quantity_carries_only_the_scrapped_share():
    """A rejected piece costs Cadence a piece only where Cadence scraps it.
    Pieces returned to the seller against an authorisation are replaced at the
    seller's cost inside the contract year and are not invoiced again (clause
    5.4 of every term sheet), so the buy is grossed up for the scrapped share,
    not for every reject. SUP-1042 returned 2,572 of its 3,276 rejected pieces
    and SUP-4077 only 244 of 4,368, so the two readings are 494,936 against
    502,139 pieces for SUP-1042 and 504,431 against 505,124 for SUP-4077 - and
    the award turns on the difference."""
    rows, _ = costs_rows()
    assert rows, "no parsable rows in supplier_costs.csv"
    for code in (AWARD, RUNNER_UP):
        assert code in rows, "row for %s missing" % code
        got = as_float(rows[code][3])
        assert got is not None and is_whole(got), (
            "%s units_to_purchase is %r, expected a whole number of pieces"
            % (code, rows[code][3]))
        gold = GOLD_UNITS[code]
        assert int(round(got)) == gold, (
            "%s units_to_purchase is %s, expected %d: %d good units grossed up "
            "for the %.3f%% of inspected pieces Cadence scrapped, not for the "
            "%.3f%% it rejected"
            % (code, rows[code][3], gold, GOOD_UNITS,
               100.0 * GOLD_DEFECTS[code]["scrapped"] / GOLD_DEFECTS[code]["units"],
               GOLD_DEFECTS[code]["rate"]))


def test_disposal_charged_on_the_scrapped_pieces_only():
    """Section 5 of the finance policy charges USD 1.25 per piece scrapped at
    incoming inspection, and says pieces that leave on a return authorisation
    carry no disposal charge. The four disposal amounts therefore fall out of
    the contract-year requirement and the scrapped share together, and no other
    reading of either produces them."""
    by = buildup_by_supplier()
    assert by, "no parsable rows in cost_buildup.csv"
    missing = []
    for code, value in sorted(GOLD_DISPOSAL.items()):
        amounts = [a for _, a in by.get(code, []) if a is not None]
        if not any(abs(a - value) <= 0.005 + 1e-9 for a in amounts):
            missing.append("%s (USD %.2f)" % (code, value))
    assert not missing, (
        "cost_buildup.csv charges no disposal element of the amount the "
        "scrapped pieces come to, for: %s. Disposal is USD 1.25 on the pieces "
        "Cadence scraps, not on every rejected piece" % "; ".join(missing))


def test_sup4077_volume_terms_applied_at_contract_year_demand():
    """Over the contract year SUP-4077's buy sits below its 520,000-piece
    threshold, so its rebate is not earned and its shortfall charge is owed.
    The calendar-2026 window, the untrimmed fifteen-month horizon, the
    subtotal rows and the October plan cycle each push the buy past the
    threshold, and the total then drops by about USD 43,000."""
    rows, _ = costs_rows()
    assert rows and RUNNER_UP in rows, "no %s row in supplier_costs.csv" % RUNNER_UP
    units, total = as_float(rows[RUNNER_UP][3]), as_float(rows[RUNNER_UP][4])
    assert units is not None and total is not None, "%s figures not numeric" % RUNNER_UP
    assert GOOD_UNITS < units < REBATE_THRESHOLD_4077, (
        "%s units_to_purchase is %s; over the contract year the buy is "
        "%d pieces, below the %d-piece rebate threshold"
        % (RUNNER_UP, rows[RUNNER_UP][3], GOLD_UNITS[RUNNER_UP], REBATE_THRESHOLD_4077))
    assert at_precision(total, GOLD_TOTAL[RUNNER_UP], DP_TOTAL), (
        "%s total_fy2026_cost_usd is %s, expected %.2f with no rebate earned, "
        "the shortfall charge owed and the standard Net 60 date planned on"
        % (RUNNER_UP, rows[RUNNER_UP][4], round(GOLD_TOTAL[RUNNER_UP], DP_TOTAL)))


def test_sup2318_bought_in_whole_boxes():
    """SUP-2318 tenders whole 100-piece boxes only (clause 1), so its
    purchase quantity is the grossed-up requirement rounded up to a box."""
    rows, _ = costs_rows()
    assert rows and "SUP-2318" in rows, "no SUP-2318 row in supplier_costs.csv"
    units = as_float(rows["SUP-2318"][3])
    assert units is not None and is_whole(units), "SUP-2318 units_to_purchase not a whole number"
    units = int(round(units))
    assert units % BOX_2318 == 0, (
        "SUP-2318 units_to_purchase is %d, not a whole number of %d-piece boxes"
        % (units, BOX_2318))
    assert units == GOLD_UNITS["SUP-2318"], (
        "SUP-2318 units_to_purchase is %d, expected %d" % (units, GOLD_UNITS["SUP-2318"]))


# ---------------------------------------------------------------------------
# recommendation.md - required content
# ---------------------------------------------------------------------------
def test_memo_states_good_unit_requirement():
    body = section("Cost Comparison")
    assert body.strip(), "## Cost Comparison section missing or empty"
    tied = [u for u in statements(body) if states_count(u, GOOD_UNITS)
            and re.search(r"good[\s-]*units?|requirement|required|demand",
                          u, re.IGNORECASE)]
    assert tied, (
        "## Cost Comparison does not state %d as the FY2026 good-unit "
        "requirement worked to" % GOOD_UNITS)
    # instruction.md also asks where in the demand data it was taken from
    sourced = [u for u in tied if re.search(DEMAND_SOURCE_WORDS, u, re.IGNORECASE)]
    assert sourced, (
        "## Cost Comparison states the %d-piece requirement but not where in "
        "the demand data it was taken from" % GOOD_UNITS)


def test_memo_cost_comparison_covers_all_four():
    """All four suppliers, each with the figure behind the ranking: its FY2026
    total cost, as filed in supplier_costs.csv."""
    body = section("Cost Comparison")
    assert body.strip(), "## Cost Comparison section missing or empty"
    rows, _ = costs_rows()
    units = statements(body)
    for code in CANDIDATES:
        assert mentions(body, code), "## Cost Comparison does not cover %s" % code
        row = rows.get(code, [])
        # the attempt's own filed total where it is usable, so this checks that
        # the memo carries the figures rather than charging a second time for a
        # total the costs-file checks have already scored
        total = (as_float(row[4], GOLD_TOTAL[code])
                 if len(row) == len(COSTS_HEADER) else GOLD_TOTAL[code])
        assert any(mentions(u, code) and states_dollars(u, total) for u in units), (
            "## Cost Comparison never ties %s to its own FY2026 total cost of "
            "USD %.2f, marked as a US-dollar amount, in one row or sentence"
            % (code, total))


def test_cost_buildup_file_exists():
    assert BUILDUP.is_file(), "missing /workspace/output/cost_buildup.csv"


def test_cost_buildup_header_and_shape():
    assert BUILDUP.is_file(), "cost_buildup.csv not produced"
    first = next(csv.reader(io.StringIO(
        BUILDUP.read_text(encoding="utf-8", errors="replace"))), [])
    assert [c.strip() for c in first] == BUILDUP_HEADER, (
        "header is %r, expected %r" % (first, BUILDUP_HEADER))
    rows = buildup_rows()
    assert rows, "no parsable rows in cost_buildup.csv"
    by = buildup_by_supplier()
    missing = [c for c in CANDIDATES if c not in by]
    assert not missing, "cost_buildup.csv carries no rows for %s" % ", ".join(missing)
    stray = sorted(set(by) - set(CANDIDATES))
    assert not stray, "cost_buildup.csv carries rows for %s" % ", ".join(stray)
    for code, element, amount in rows:
        assert ELEMENT_OK.match(element), (
            "%s cost_element %r is not a short lower-case label" % (code, element))
        assert NUMERIC_OK.match(amount), (
            "%s %s amount_usd is %r" % (code, element, amount))
        assert decimals(amount) == 2, (
            "%s %s amount_usd needs 2 dp" % (code, element))
    for code, items in by.items():
        labels = [e for e, _ in items]
        assert len(labels) == len(set(labels)), (
            "%s repeats a cost_element; each element charged gets one row" % code)
    ordered = [(c, e) for c, e, _ in rows]
    assert ordered == sorted(ordered), (
        "rows must be sorted by supplier_code then cost_element")


def test_cost_buildup_sums_to_the_filed_total():
    """instruction.md binds the decomposition only by its sum."""
    costs, _ = costs_rows()
    by = buildup_by_supplier()
    assert by, "no parsable rows in cost_buildup.csv"
    for code in CANDIDATES:
        items = by.get(code)
        assert items, "cost_buildup.csv carries no rows for %s" % code
        assert all(a is not None for _, a in items), (
            "%s has a non-numeric amount_usd" % code)
        filed = as_float(costs.get(code, [""] * 7)[4]) if code in costs else None
        assert filed is not None, (
            "supplier_costs.csv has no numeric total for %s to reconcile against" % code)
        total = sum(a for _, a in items)
        slack = 0.005 * len(items) + 1e-9
        assert abs(total - filed) <= slack, (
            "%s build-up sums to %.2f against a filed total of %.2f"
            % (code, total, filed))


def test_cost_buildup_material_correct():
    """The material line is the purchase quantity at the offered price restated
    in US dollars per single piece at the mandated planning rates."""
    by = buildup_by_supplier()
    assert by, "no parsable rows in cost_buildup.csv"
    missing = []
    for code, value in sorted(GOLD_MATERIAL.items()):
        amounts = [a for _, a in by.get(code, []) if a is not None]
        if not any(abs(a - value) <= 0.005 + 1e-9 for a in amounts):
            missing.append("%s (USD %.2f)" % (code, value))
    assert not missing, (
        "cost_buildup.csv charges no element of the material amount for: %s"
        % "; ".join(missing))


def test_cost_buildup_freight_rebate_and_shortfall_correct():
    """Two offers are FCA and carry the lane tariff plus brokerage on twelve
    shipments; two are DDP and carry none. SUP-2318's rebate is rated band by
    band rather than re-rating the year at 3.0%, and SUP-4077 owes the clause
    4.1 shortfall charge because the buy misses its 520,000-piece commitment.
    The labels are the attempt's own, so only the amounts are matched."""
    by = buildup_by_supplier()
    assert by, "no parsable rows in cost_buildup.csv"
    wanted = {code: [("inbound freight", v)] for code, v in GOLD_FREIGHT.items()}
    wanted.setdefault("SUP-2318", []).append(("banded volume rebate", GOLD_REBATE_2318))
    wanted.setdefault("SUP-4077", []).append(("volume shortfall charge", GOLD_SHORTFALL_4077))
    missing = []
    for code, items in sorted(wanted.items()):
        amounts = [a for _, a in by.get(code, []) if a is not None]
        for label, value in items:
            if not any(abs(a - value) <= 0.005 + 1e-9 for a in amounts):
                missing.append("%s %s (USD %.2f)" % (code, label, value))
    assert not missing, (
        "cost_buildup.csv charges no element of that amount for: %s"
        % "; ".join(missing))


def test_cost_buildup_charges_the_working_capital_value():
    """Section 3 of the shipped finance policy values payment terms against a
    Net 30 baseline at the cost of capital. Any correct build-up carries that
    amount for the three suppliers whose terms are not Net 30; the labels are
    the attempt's own, so only the amounts are matched. An attempt that never
    modelled working capital has no row of that size."""
    by = buildup_by_supplier()
    assert by, "no parsable rows in cost_buildup.csv"
    missing = []
    for code, wanted in sorted(GOLD_BUILDUP.items()):
        amounts = [a for _, a in by.get(code, []) if a is not None]
        for label, value in sorted(wanted.items()):
            if not any(abs(a - value) <= 0.005 + 1e-9 for a in amounts):
                missing.append("%s %s (USD %.2f)" % (code, label, value))
    assert not missing, (
        "cost_buildup.csv charges no element of that amount for: %s"
        % "; ".join(missing))


def test_memo_states_the_contract_year_window():
    """instruction.md asks `## Cost Comparison` for the requirement, which part
    of the demand data it came from and what period it covers. The offers run
    1 April 2026 to 31 March 2027 and the cube dump is a rolling fifteen-month
    horizon, so the period is a statement the memo has to make."""
    body = section("Cost Comparison")
    assert body.strip(), "## Cost Comparison section missing or empty"
    assert re.search(CONTRACT_WINDOW_FROM, body, re.IGNORECASE), (
        "## Cost Comparison does not say the FY2026 requirement covers a "
        "period starting April 2026")
    assert re.search(CONTRACT_WINDOW_TO, body, re.IGNORECASE), (
        "## Cost Comparison does not say the FY2026 requirement covers a "
        "period ending March 2027")


def test_memo_reports_the_reject_disposition_split():
    """instruction.md asks `## Data Quality and Exclusions` which inspection
    records were counted towards the reject rates and which were set aside,
    with the reason. The pieces returned to the seller and replaced free of
    charge are rejects that are not a loss, and only an attempt that separated
    them has the figure: 5,565 of the 21,434 rejected pieces went back, leaving
    15,869 scrapped."""
    body = section("Data Quality and Exclusions")
    assert body.strip(), "## Data Quality and Exclusions section missing or empty"
    tied = [u for u in statements(body)
            if re.search(DISPOSITION_WORDS, u, re.IGNORECASE)
            and (states_count(u, RETURNED_TOTAL) or states_count(u, SCRAPPED_TOTAL))]
    assert tied, (
        "## Data Quality and Exclusions never reports how the rejected pieces "
        "were dispositioned: of %d pieces rejected at incoming inspection %d "
        "went back to the seller on a return authorisation and %d were "
        "scrapped, and only the scrapped pieces are a loss the purchase "
        "quantity carries" % (REJECTED_TOTAL, RETURNED_TOTAL, SCRAPPED_TOTAL))


def test_memo_flags_non_candidate_supplier():
    """The prompt asks this section for what was excluded and why, and for
    every supplier in the source data that is not a candidate."""
    body = section("Data Quality and Exclusions")
    assert body.strip(), "## Data Quality and Exclusions section missing or empty"
    assert (NON_CANDIDATE in body or "old harbor" in body.casefold()), (
        "## Data Quality and Exclusions does not identify %s, the supplier that "
        "appears in the source data but is not a candidate" % NON_CANDIDATE)
    # each population has to be reported WITH a reason, per instruction.md
    reported = []
    for name, pattern in EXCLUSION_TOPICS.items():
        for unit in statements(body):
            if re.search(pattern, unit, re.IGNORECASE) and re.search(
                    REASON_WORDS, unit, re.IGNORECASE):
                reported.append(name)
                break
    # instruction.md names one of these explicitly: which inspection records
    # were counted towards the reject rates and which were set aside, and why
    assert "source inspections" in reported, (
        "## Data Quality and Exclusions does not say, with a reason, which "
        "inspection records were counted towards the reject rates and which "
        "were set aside")
    assert len(reported) >= MIN_EXCLUSION_TOPICS, (
        "## Data Quality and Exclusions names %s but gives a reason for only "
        "%d of the populations it set aside (%s); the prompt asks what else "
        "was excluded from the source data and why"
        % (NON_CANDIDATE, len(reported), ", ".join(reported) or "none"))


def test_memo_totals_agree_with_costs_file():
    rows, _ = costs_rows()
    body = section("Cost Comparison")
    assert rows, "no parsable rows in supplier_costs.csv"
    assert body.strip(), "## Cost Comparison section missing or empty"
    assert AWARD in rows, "row for %s missing from supplier_costs.csv" % AWARD
    filed = as_float(rows[AWARD][4])
    assert filed is not None, "%s total_fy2026_cost_usd is not numeric" % AWARD
    assert states_money(body, filed), (
        "## Cost Comparison does not carry the awarded supplier's total from "
        "supplier_costs.csv, USD %.2f" % filed)


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
