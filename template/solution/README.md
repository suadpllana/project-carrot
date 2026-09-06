# Gold solution (placeholder)

Replace this directory's contents with the complete gold solution:

- `gold.patch` — unified diff (git diff format) from the fresh workspace to
  the solved state. This is the artifact reviewers read; keep it exactly in
  sync with what `solve.sh` produces.
- `solve.sh` — deterministic script that materializes the gold outputs in a
  fresh environment. The oracle run executes it and must earn the full
  reward; the nop run (no action taken) must earn exactly 0.

Requirements:

- The final recommendation is DETERMINISTIC: anyone re-running the analysis
  on the input data reaches the same figures and the same position.
- Produce every output file the instruction asks for, at the exact paths the
  verifier and rubric grade.
- Nothing under `solution/` may be visible to the model: never COPY this
  directory into the environment image.
