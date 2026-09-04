"""Programmatic checks over the model's FINAL OUTPUT FILES only.

Grade what the run produced, never how it was produced: no trajectory access,
no implementation details. Keep each discrete check its own test so the CTRF
report names exactly which ones failed.
"""

from pathlib import Path

OUTPUT_DIR = Path("/workspace/output")


def test_recommendation_file_exists() -> None:
    assert (OUTPUT_DIR / "recommendation.md").is_file(), "replace with the real deliverable paths"


def test_expected_analysis_outputs() -> None:
    raise NotImplementedError("replace with checks over the declared output files")
