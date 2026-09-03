#!/usr/bin/env python3
"""Regenerate solution/gold.patch: the unified diff from the fresh workspace
(no output/ directory) to the solved state, exactly as solve.sh produces it.

Runs solve.py against environment/data/ into a scratch directory and formats
the three deliverables as new-file hunks. Do not hand-edit gold.patch.

Run from anywhere:  python solution/_provenance/make_gold_patch.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FILES = ["supplier_costs.csv", "defect_rates.csv", "recommendation.md"]

HEADER = """\
Gold patch for cadence-supplier-award.

Unified diff from the fresh workspace to the solved state, exactly as
solution/solve.sh produces it. Regenerate with
solution/_provenance/make_gold_patch.py; do not hand-edit.

"""


def main():
    out = Path(tempfile.mkdtemp(prefix="cadence-gold-"))
    env = dict(os.environ, CADENCE_DATA=str(ROOT / "environment" / "data"), CADENCE_OUT=str(out))
    subprocess.run([sys.executable, str(ROOT / "solution" / "solve.py")], env=env, check=True,
                   capture_output=True)
    parts = [HEADER]
    for name in FILES:
        lines = (out / name).read_text(encoding="utf-8").split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        parts.append("diff --git a/output/%s b/output/%s\n" % (name, name))
        parts.append("new file mode 100644\n--- /dev/null\n+++ b/output/%s\n" % name)
        parts.append("@@ -0,0 +1,%d @@\n" % len(lines))
        parts.extend("+%s\n" % line for line in lines)
    (ROOT / "solution" / "gold.patch").write_text("".join(parts), encoding="utf-8", newline="\n")
    shutil.rmtree(out, ignore_errors=True)
    print("wrote solution/gold.patch")


if __name__ == "__main__":
    main()
