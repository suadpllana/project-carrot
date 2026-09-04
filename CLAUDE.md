# project-carrot

Carrot (Harbor) task packages. One directory per task; everything else is
reference material for authoring them.

```
cadence-supplier-award/   the task package
docs/                     platform rules and authoring judgement
template/                 the official starter template, unmodified
```

## Reference material

- `docs/harbor-package-howto.md` — archive layout, what is required at upload
  versus before grading, `task.toml` allowlist, `rubrics.json` schema and
  weight rules, the verifier reward contract.
- `docs/task-authoring-guide.md` — the four load-bearing parts of a task, the
  submission workflow, the ground rules, and the sweep ceilings.
- `docs/raising-difficulty.md` — field notes on what actually makes a task
  hard, and what only looks like it does. Read this before changing a task's
  difficulty.
- `template/` — the starter template as shipped. Never edit it in place; copy
  it to a new task directory.

## Sweep targets

Every model is run four times and the **mean** is judged:

| Sweep | Ceiling |
| --- | --- |
| strong model | **≤ 0.60** |
| weak model | **≤ 0.35** |

A task above either ceiling comes back. Both are checked before manual review,
so a local mutation sweep that predicts the profile is worth more than any
amount of reasoning about how hard a task feels.

## Working on a task package

The invariants below are enforced by the platform and by this repo's own
tooling. Break one and the submission comes back.

1. **The nop agent scores exactly 0.000 and the oracle scores 1.000**, against
   the exact archive you would upload. Check both before every commit that
   touches the data, the solution, the tests or the weights.
2. **The shipped documents describe their systems and decide nothing.** Any
   wording in `environment/data/` that tells the attempt what to exclude, which
   join to fix, or which rows to keep turns a judgement into a checklist item.
   That is the single failure mode that has cost this repo the most revisions.
3. **Grade final output files only.** The verifier never reads the trajectory.
4. **Regenerate, do not hand-edit.** Input data comes from
   `solution/_provenance/generate_data.py`, `gold.patch` from
   `make_gold_patch.py`. Both are deterministic and idempotent.
5. **Re-derive the ground truth independently.**
   `solution/_provenance/verify_design.py` reads only `environment/data/` with
   its own pipeline, proves `solve.py` agrees with it, then mutates the
   reference one analysis choice at a time and scores each variant through the
   real verifier. Its tables are what `task_card.md` quotes; refresh them
   whenever a figure moves.
6. **Keep the numbers in one place.** After a data or price change, re-read the
   constants at the top of `tests/test_outputs.py` from `verify_design.py`'s
   re-derivation, and refresh every figure quoted in `rubrics.json`,
   `task_card.md` and `solution/README.md`. A stale figure in the rubric is a
   silently unearnable criterion.

### Local checks

```
cd cadence-supplier-award
python3 solution/_provenance/generate_data.py     # needs openpyxl; idempotent
python3 solution/_provenance/verify_design.py     # re-derive + mutation sweep
python3 solution/_provenance/make_gold_patch.py

# oracle: must print reward 1.000000
CADENCE_DATA=environment/data CADENCE_OUT=/tmp/out python3 solution/solve.py
OUTPUT_DIR=/tmp/out CADENCE_LOGS=/tmp/logs CADENCE_TESTS=$PWD/tests bash tests/test.sh

# nop: must print reward 0.000000
mkdir -p /tmp/nop
OUTPUT_DIR=/tmp/nop CADENCE_LOGS=/tmp/noplogs CADENCE_TESTS=$PWD/tests bash tests/test.sh
```

`tests/test.sh` runs on the task image with the standard library only — no
`uv`, no package installs, no egress at verify time. Keep
`tests/test_outputs.py` plain pytest-compatible (bare `def test_*` +
`assert`) so it can also be run directly with pytest while authoring.

## Git

Work on `main` and push directly. No pull requests.
