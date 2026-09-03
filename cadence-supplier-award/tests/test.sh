#!/usr/bin/env bash
set -uo pipefail

# Verifier entry point.
#
#   /logs/verifier/ctrf.json   per-check results, so a reviewer sees WHICH
#                              checks failed rather than only the score
#   /logs/verifier/reward.json {"reward": <float>} - weighted, never rounded
#                              to 0 or 1
#
# Grades the attempt's final output files under /workspace/output and nothing
# else. Deterministic: no network calls of its own, no clock, no randomness.
#
# Runs on the task image exactly as built: CPython standard library only. No
# package installs and no PyPI fetch at verify time - the image carries no uv
# and the verifier has no egress, so an install step here cannot resolve and
# would score every run, the reference solution included, exactly 0.
# test_outputs.py stays plain pytest-compatible (bare `def test_*` + `assert`)
# so an author can still run `pytest tests/test_outputs.py` locally.

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CADENCE_TESTS="${CADENCE_TESTS:-$HERE}"
export CADENCE_LOGS="${CADENCE_LOGS:-/logs/verifier}"

mkdir -p "$CADENCE_LOGS"

python3 - <<'PY'
"""Run every check in test_outputs.py, then score it.

Exits non-zero only when the VERIFIER itself is broken (checks unloadable,
weights unreadable, logs unwritable). An attempt that earns nothing is a
legitimate 0 and exits clean; a broken verifier must never again pass itself
off as one.
"""
import importlib.util
import json
import os
import sys
import traceback
from pathlib import Path

TESTS = Path(os.environ.get("CADENCE_TESTS", "/tests"))
LOGS = Path(os.environ.get("CADENCE_LOGS", "/logs/verifier"))
MODULE = TESTS / "test_outputs.py"
WEIGHTS = TESTS / "test_weights.json"


def die(msg):
    print("VERIFIER ERROR: %s" % msg, file=sys.stderr)
    sys.exit(2)


# ---------------------------------------------------------------------------
# load the checks and their weights
# ---------------------------------------------------------------------------
if not MODULE.is_file():
    die("no check module at %s" % MODULE)

spec = importlib.util.spec_from_file_location("test_outputs", MODULE)
module = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(module)
except Exception:
    traceback.print_exc()
    die("%s did not import" % MODULE)

# source order, so the printed table reads like the file
checks = [(n, f) for n, f in vars(module).items()
          if n.startswith("test_") and callable(f)]
checks.sort(key=lambda kv: kv[1].__code__.co_firstlineno)
if not checks:
    die("%s defines no test_* checks" % MODULE)

try:
    rows = json.loads(WEIGHTS.read_text(encoding="utf-8"))
except Exception:
    traceback.print_exc()
    die("%s is unreadable" % WEIGHTS)

weights, decision = {}, set()
for row in rows:
    weights[row["test_name"]] = int(row["weight"])
    if row.get("decision"):
        decision.add(row["test_name"])

# ---------------------------------------------------------------------------
# run them
# ---------------------------------------------------------------------------
seen, tests, errored = {}, [], []
for name, fn in checks:
    try:
        fn()
        status, message = "passed", ""
    except AssertionError as exc:
        status, message = "failed", str(exc).strip() or "assertion failed"
    except Exception:
        # a check that blew up on the attempt's output has not passed, but say
        # so distinctly: an exception is a defect in the check or in the file
        # it parsed, not a graded judgement
        status, message = "failed", traceback.format_exc().strip()
        errored.append(name)
    seen[name] = status == "passed"
    entry = {"name": "test_outputs.py::%s" % name, "status": status,
             "duration": 0}
    if message:
        entry["message"] = message
    tests.append(entry)

passed = sum(1 for t in tests if t["status"] == "passed")
ctrf = {
    "reportFormat": "CTRF",
    "specVersion": "0.0.0",
    "results": {
        "tool": {"name": "cadence-checks"},
        "summary": {"tests": len(tests), "passed": passed,
                    "failed": len(tests) - passed, "pending": 0, "skipped": 0,
                    "other": 0, "start": 0, "stop": 0},
        "tests": tests,
    },
}
try:
    (LOGS / "ctrf.json").write_text(json.dumps(ctrf, indent=2) + "\n",
                                    encoding="utf-8")
except Exception:
    traceback.print_exc()
    die("cannot write %s" % (LOGS / "ctrf.json"))

# ---------------------------------------------------------------------------
# score
# ---------------------------------------------------------------------------
# A check absent from the weights file counts as weight 1 (platform default).
for name in seen:
    weights.setdefault(name, 1)

# A weighted name with no check behind it earns nothing and would quietly
# deflate every reward, so name it rather than swallowing it.
orphans = sorted(n for n in weights if n not in seen)

positive = sum(w for w in weights.values() if w > 0)
earned = 0
for name, w in weights.items():
    if not seen.get(name, False):
        continue
    if w > 0:
        earned += w
    elif w < 0:
        # penalty tests pass only when their defect is present
        earned += w

reward = (earned / positive) if positive else 0.0
reward = max(0.0, min(1.0, reward))

try:
    (LOGS / "reward.json").write_text(
        json.dumps({"reward": round(reward, 6)}), encoding="utf-8")
except Exception:
    traceback.print_exc()
    die("cannot write %s" % (LOGS / "reward.json"))

# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
print("output graded : %s" % module.OUTPUT_DIR)
print()
print("%-52s %6s  %s" % ("check", "weight", "result"))
for t in tests:
    name = t["name"].split("::")[-1]
    print("%-52s %6d  %s" % (name, weights.get(name, 1),
                             "PASS" if t["status"] == "passed" else "FAIL"))
print()
for t in tests:
    if t["status"] != "passed" and t.get("message"):
        head = t["message"].splitlines()[0]
        print("FAIL %s: %s" % (t["name"].split("::")[-1], head))
if errored:
    print()
    print("VERIFIER WARNING: %d check(s) raised instead of asserting: %s"
          % (len(errored), ", ".join(errored)))
if orphans:
    print("VERIFIER WARNING: weighted but not defined in %s: %s"
          % (MODULE.name, ", ".join(orphans)))

dec_pos = sum(w for n, w in weights.items() if n in decision and w > 0)
print()
print("checks scored : %d" % len(weights))
print("positive pool : %d (decision tests %d)" % (positive, dec_pos))
print("earned        : %d" % earned)
print("reward        : %.6f" % reward)
PY
rc=$?

if [ "$rc" -ne 0 ]; then
  echo "verifier did not complete (exit $rc); reward is not trustworthy" >&2
fi
exit "$rc"
