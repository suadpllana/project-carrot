#!/usr/bin/env python3
"""Build the upload archive for a task package.

    python3 scripts/package_task.py cadence-supplier-award

Writes `dist/<task>.zip` containing a single top-level directory named after
the task, laid out exactly as the Harbor package how-to specifies. Refuses to
build if a file that is required in the upload is missing, so a broken archive
is never handed over by accident.

This does NOT run the local checks. Run them first — the nop agent must score
0.000 and the oracle 1.000 against the same tree this zips.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# required in the upload: intake rejects the archive without them
REQUIRED_FILES = ["task.toml", "instruction.md"]
REQUIRED_DIRS = ["environment", "solution", "tests"]
# optional at upload, required before grading: intake only warns
EXPECTED_FILES = ["rubrics.json", "task_card.md"]

SKIP_DIRS = {"__pycache__", ".pytest_cache", ".git", ".ruff_cache", ".mypy_cache"}
SKIP_NAMES = {".DS_Store"}


def collect(task_dir: Path):
    for path in sorted(task_dir.rglob("*")):
        if any(part in SKIP_DIRS for part in path.relative_to(task_dir).parts):
            continue
        if path.name in SKIP_NAMES or not path.is_file():
            continue
        yield path


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
                if not any((task_dir / n).rglob("*")) or not (task_dir / n).is_dir()]
    if missing:
        print("refusing to build: %s is missing %s"
              % (task, ", ".join(missing)), file=sys.stderr)
        return 1
    for name in EXPECTED_FILES:
        if not (task_dir / name).is_file():
            print("warning: %s has no %s; it is required before grading" % (task, name))

    files = list(collect(task_dir))
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    archive = dist / ("%s.zip" % task)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, Path(task) / path.relative_to(task_dir))

    print("wrote %s" % archive.relative_to(ROOT))
    print("  %d files, %.1f KiB" % (len(files), archive.stat().st_size / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
