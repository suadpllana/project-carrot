#!/usr/bin/env python3
"""Build the upload archive for a task package.

    python3 scripts/package_task.py cadence-supplier-award

Writes `dist/<task>.zip` containing a single top-level directory named after
the task, laid out exactly as the Harbor package how-to specifies. Refuses to
build if a file that is required in the upload is missing, so a broken archive
is never handed over by accident.

Before zipping it PURGES build caches from the task tree rather than merely
skipping them, so no other packaging route can pick them up either: intake once
refused an archive over a stray `.pyc` under `tests/__pycache__`. After zipping
it re-opens its own output and audits every member against an extension
allowlist, then prints the SHA-256 so the archive that was uploaded can be
matched against the archive that was built.

It also refuses to build when the grading definition is out of bounds: the
rubric outside the documented criterion count, weight cap or decision band, or
a weights file that names a check `test_outputs.py` does not define (or misses
one it does, which would score it at the silent default of 1), or a check that
asserts on a bare string the attempt was never shown - which is what the
platform's format step refuses over.

This does NOT run the local checks. Run them first - the nop agent must score
0.000 and the oracle 1.000 against the same tree this zips.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]

# required in the upload: intake rejects the archive without them
REQUIRED_FILES = ["task.toml", "instruction.md"]
REQUIRED_DIRS = ["environment", "solution", "tests"]
# optional at upload, required before grading: intake only warns
EXPECTED_FILES = ["rubrics.json", "task_card.md"]

SKIP_DIRS = {"__pycache__", ".pytest_cache", ".git", ".ruff_cache", ".mypy_cache"}
SKIP_NAMES = {".DS_Store"}
SKIP_SUFFIXES = {".pyc", ".pyo"}

# Everything a task package legitimately ships. A file type outside this set is
# either a build artefact or something that was never meant to be uploaded, and
# either way the archive should not be handed over until it is explained.
ALLOWED_SUFFIXES = {".md", ".csv", ".jsonl", ".json", ".py", ".sh", ".toml",
                    ".xlsx", ".patch"}
ALLOWED_NAMES = {"Dockerfile"}

# docs/harbor-package-howto.md, "rubrics.json schema and weight rules"
MIN_CRITERIA, MAX_CRITERIA = 25, 50
MIN_RECOMMENDATION_CRITERIA = 3
DECISION_BAND = (0.30, 0.50)      # pooled: rubric criteria + tests marked decision
MAX_SINGLE_CRITERION = 0.20       # of the rubric's positive weight
MAX_ABS_WEIGHT = 100


def validate_grading(task_dir: Path):
    """The grading rules the how-to states, checked before the zip is written.

    Two failure modes this exists to stop: a rubric that has drifted outside a
    documented limit, and a weights file that names a check the test module no
    longer defines (or misses one it does). The second silently deflates every
    reward, the reference solution included.
    """
    problems = []
    rubric_path, weights_path = task_dir / "rubrics.json", task_dir / "tests" / "test_weights.json"
    module_path = task_dir / "tests" / "test_outputs.py"
    if not (rubric_path.is_file() and weights_path.is_file() and module_path.is_file()):
        return ["cannot validate grading: rubrics.json, test_weights.json or "
                "test_outputs.py is missing"]

    rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
    weights = json.loads(weights_path.read_text(encoding="utf-8"))

    # every check that exists is weighted, and every weight has a check
    defined = {n.name for n in ast.walk(ast.parse(module_path.read_text(encoding="utf-8")))
               if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")}
    weighted = {w["test_name"] for w in weights}
    for name in sorted(weighted - defined):
        problems.append("test_weights.json weights %s, which test_outputs.py does "
                        "not define" % name)
    for name in sorted(defined - weighted):
        problems.append("test_outputs.py defines %s, which test_weights.json does "
                        "not weight (it would score at the default weight 1)" % name)

    if not MIN_CRITERIA <= len(rubric) <= MAX_CRITERIA:
        problems.append("rubrics.json has %d criteria; the how-to requires %d-%d"
                        % (len(rubric), MIN_CRITERIA, MAX_CRITERIA))
    for c in rubric:
        for key in ("item", "weight", "criterion", "grades_output_files"):
            if key not in c:
                problems.append("rubric item %s has no %r" % (c.get("item", "?"), key))
        if c.get("weight", 0) == 0 or abs(c.get("weight", 0)) > MAX_ABS_WEIGHT:
            problems.append("rubric item %s has weight %s; must be nonzero and "
                            "|weight| <= %d" % (c.get("item"), c.get("weight"), MAX_ABS_WEIGHT))
        if not c.get("grades_output_files"):
            problems.append("rubric item %s names no output file; grading sees only "
                            "the final files" % c.get("item"))

    rub_pos = sum(c["weight"] for c in rubric if c["weight"] > 0)
    rub_dec = sum(c["weight"] for c in rubric if c.get("is_recommendation_criterion"))
    n_dec = sum(1 for c in rubric if c.get("is_recommendation_criterion"))
    if n_dec < MIN_RECOMMENDATION_CRITERIA:
        problems.append("rubrics.json flags %d recommendation criteria; at least %d "
                        "are required" % (n_dec, MIN_RECOMMENDATION_CRITERIA))
    top = max((c["weight"] for c in rubric), default=0)
    if rub_pos and top > MAX_SINGLE_CRITERION * rub_pos:
        problems.append("largest rubric criterion is %.1f%% of the rubric's positive "
                        "weight; the cap is %.0f%%" % (100 * top / rub_pos,
                                                       100 * MAX_SINGLE_CRITERION))

    test_pos = sum(w["weight"] for w in weights if w["weight"] > 0)
    test_dec = sum(w["weight"] for w in weights if w.get("decision"))
    pooled = test_pos + rub_pos
    share = (test_dec + rub_dec) / pooled if pooled else 0.0
    if not DECISION_BAND[0] <= share <= DECISION_BAND[1]:
        problems.append("pooled decision weight is %.1f%% of total positive weight; "
                        "the band is %.0f-%.0f%%" % (100 * share, 100 * DECISION_BAND[0],
                                                     100 * DECISION_BAND[1]))
    else:
        print("  grading: %d criteria, %d checks, pooled decision %.1f%% of %d "
              "positive weight" % (len(rubric), len(weights), 100 * share, pooled))
    return problems


def undisclosed_literals(task_dir: Path):
    """String literals a check asserts on that appear nowhere the agent can read.

    The platform's format check refuses a package whose verifier grades against
    a value the attempt was never told about. It reads that off the test module
    as bare string literals inside `assert` statements - a literal carrying a
    format placeholder is a diagnostic, not a graded value, and is exempt.

    So a diagnostic must name its artefact, field or section through a
    placeholder or a module constant rather than repeating the text inline.
    That is better failure output anyway: the message names the real path.
    """
    module_path = task_dir / "tests" / "test_outputs.py"
    if not module_path.is_file():
        return []
    readable = []
    prompt = task_dir / "instruction.md"
    if prompt.is_file():
        readable.append(prompt.read_text(encoding="utf-8", errors="replace"))
    env = task_dir / "environment"
    if env.is_dir():
        for path in env.rglob("*"):
            if path.is_file():
                try:
                    readable.append(path.read_text(encoding="utf-8", errors="replace"))
                except (OSError, UnicodeError):
                    pass
    readable = "\n".join(readable)

    out, seen = [], set()
    for node in ast.walk(ast.parse(module_path.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Assert):
            continue
        for sub in ast.walk(node):
            if not (isinstance(sub, ast.Constant) and isinstance(sub.value, str)):
                continue
            text = sub.value.strip()
            if not text or re.search(r"%[srdfi%]|\{\}", text):
                continue
            if text in readable or text in seen:
                continue
            seen.add(text)
            out.append("tests/test_outputs.py:%d asserts on %r, which appears "
                       "nowhere the agent can read" % (sub.lineno, text[:60]))
    return out


def purge_caches(task_dir: Path):
    """Delete build caches from the task tree itself, not just from the zip."""
    removed = []
    for path in sorted(task_dir.rglob("*"), reverse=True):
        rel = path.relative_to(task_dir)
        if path.is_dir() and path.name in SKIP_DIRS:
            shutil.rmtree(path, ignore_errors=True)
            removed.append("%s/" % rel)
        elif path.is_file() and (path.suffix in SKIP_SUFFIXES
                                 or path.name in SKIP_NAMES):
            path.unlink()
            removed.append(str(rel))
    return removed


def collect(task_dir: Path):
    for path in sorted(task_dir.rglob("*")):
        if any(part in SKIP_DIRS for part in path.relative_to(task_dir).parts):
            continue
        if path.name in SKIP_NAMES or path.suffix in SKIP_SUFFIXES:
            continue
        if path.is_file():
            yield path


def audit(archive: Path, task: str):
    """Every member is under one top-level dir and is a file type we ship."""
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
    bad = []
    for name in names:
        parts = PurePosixPath(name)
        if parts.parts[0] != task:
            bad.append("%s (not under %s/)" % (name, task))
        elif any(part in SKIP_DIRS for part in parts.parts):
            bad.append("%s (build cache)" % name)
        elif parts.suffix not in ALLOWED_SUFFIXES and parts.name not in ALLOWED_NAMES:
            bad.append("%s (unexpected file type)" % name)
    return names, bad


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    task = argv[1].rstrip("/")
    task_dir = ROOT / task
    if not task_dir.is_dir():
        print("no such task directory: %s" % task_dir, file=sys.stderr)
        return 2

    missing = [n for n in REQUIRED_FILES if not (task_dir / n).is_file()]
    missing += ["%s/" % n for n in REQUIRED_DIRS
                if not (task_dir / n).is_dir() or not any((task_dir / n).rglob("*"))]
    if missing:
        print("refusing to build: %s is missing %s"
              % (task, ", ".join(missing)), file=sys.stderr)
        return 1
    for name in EXPECTED_FILES:
        if not (task_dir / name).is_file():
            print("warning: %s has no %s; it is required before grading" % (task, name))

    problems = validate_grading(task_dir) + undisclosed_literals(task_dir)
    if problems:
        print("refusing to build: the grading definition is out of bounds",
              file=sys.stderr)
        for line in problems:
            print("  %s" % line, file=sys.stderr)
        return 1

    purged = purge_caches(task_dir)
    for rel in purged:
        print("purged %s" % rel)

    files = list(collect(task_dir))
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    archive = dist / ("%s.zip" % task)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, Path(task) / path.relative_to(task_dir))

    names, bad = audit(archive, task)
    if bad:
        archive.unlink()
        print("refusing to hand over the archive; it contains:", file=sys.stderr)
        for line in bad:
            print("  %s" % line, file=sys.stderr)
        return 1

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    print("wrote %s" % archive.relative_to(ROOT))
    print("  %d files, %.1f KiB" % (len(names), archive.stat().st_size / 1024))
    print("  sha256 %s" % digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
