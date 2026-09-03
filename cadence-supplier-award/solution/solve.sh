#!/usr/bin/env bash
set -euo pipefail

# Apply the complete gold solution: read the shipped inputs under
# /workspace/data and materialize the three graded deliverables under
# /workspace/output. Deterministic and safe to run once in a fresh
# environment. Keep gold.patch beside this script in sync - it is the
# reviewable statement of this change.

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Write where the verifier grades: the runner's output directory if it names
# one, else the platform default. solve.py reads CADENCE_OUT.
OUT="${CADENCE_OUT:-${OUTPUT_DIR:-/workspace/output}}"
export CADENCE_OUT="$OUT"

mkdir -p "$OUT"
python3 "${HERE}/solve.py"

ls -l "$OUT"
