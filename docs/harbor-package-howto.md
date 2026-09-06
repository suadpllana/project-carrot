# Harbor package how-to

Source: <https://carrot-instructions.edgeone.dev/>

Every submission is a single archive with a fixed layout, built and tested
locally with the Harbor CLI before it is uploaded. The platform rebuilds and
re-checks everything server-side: **a package that does not pass on your own
machine will not pass theirs.**

## Layout

```
my-task/
├── task.toml            Task metadata, timeouts, resource caps         (required)
├── instruction.md       The prompt, exactly what the agent reads       (required)
├── rubrics.json         Rubric-editor seed                             (optional)
├── task_card.md         Task-card editor seed                          (optional)
├── environment/         Container + input data, as the attempt sees it (required)
├── solution/            Reference solution (never shown to the agent)  (required)
└── tests/               Verifier that grades the final output files    (required)
```

"Required" and "optional" both refer to the ZIP you upload. `rubrics.json` and
`task_card.md` are the only files you may omit at upload, and both stop being
optional before grading:

| File | In the upload | Before grading |
| --- | --- | --- |
| `task.toml` | required | required |
| `instruction.md` | required | required |
| `environment/` (≥1 file) | required | required |
| `solution/` (≥1 file) | required | required |
| `tests/` (≥1 file) | required | required |
| `rubrics.json` | optional (intake warns) | required, finalized in the rubric editor with the decision criteria confirmed |
| `task_card.md` | optional (intake warns) | required, after passing the task-card content-validity check |

## `task.toml`

Only allowlisted keys are honored at ingest. Anything else is dropped and
reported; executable keys (`docker_image`, `mcp_servers`, `env` tables) are
refused outright — the platform re-derives runtime facts server-side. Task
category, reasoning phases, licensing and fail-to-pass / pass-to-pass test tags
are declared on the **submission form**, not in this file.

`[agent] max_turns` caps at 600; `timeout_sec` is the per-trial wall clock
(5400 is the long-horizon default). `[verifier] timeout` is server-owned and
ignored here. `[environment] allow_internet` must be absent or `false` — solver
egress is admin-controlled and default-deny, and the archive cannot enable it.

## `environment/`

The build context is this directory. **Pin the base image by digest** — a
floating tag fails the build check:

```
docker pull python:3.12-slim
docker inspect --format '{{index .RepoDigests 0}}' python:3.12-slim
```

Stage only the input files. Never `COPY tests/` or `solution/` into the image:
the attempt must not be able to see either. Preinstall only what the task's
*start* state requires — discovering and installing analysis dependencies is
legitimate work for the model.

## `rubrics.json`

A bare JSON array. Invalid JSON or any unknown object key **rejects** the
archive. Every criterion object requires:

- `item` — unique, 1-based integer
- `weight` — nonzero integer, `|weight| ≤ 100`; a negative weight is a penalty
  that subtracts from the numerator only
- `criterion` — a concrete, checkable claim
- `category` — one of `explore`, `hypothesize`, `analyze`, `synthesize`,
  `recommend`, `instruction_following`
- `verification_type` — one of `text`, `multimodal`, `code_execution`,
  `file_structure`

Optional keys: `is_recommendation_criterion` (boolean) and
`grades_output_files` (array of globs over the task's expected output files).

```
final_reward = sum(earned weights) / sum(positive weights)
```

Before grading, a complete rubric has **25–50 criteria**; at least three
criteria flagged `is_recommendation_criterion` — pooled with any tests flagged
`"decision": true` in `tests/test_weights.json` — carrying **30–50%** of total
positive weight; **no single criterion above 20%** of the rubric's weight; and
an output-file glob on **every** criterion, because grading sees only the final
output files. Every explicit instruction in the prompt (file names, formats,
required fields, precision, prohibitions) must be graded by a criterion or a
test.

If `is_recommendation_criterion` is omitted everywhere, the platform infers the
decision criteria when the choice is unambiguous and asks you to confirm the
selection in the editor.

## `task_card.md`

Must contain: the task description; a complexity justification explaining why
the task is hard; taxonomy tags; the expected difficulty range; the ground-truth
recommendation and its rationale; and, when no golden solution is included, a
summary of the expected reasoning trajectory. The six headings are a convention
that helps the platform pre-fill its form — validity is judged on **content**.
Formatting deviations do not reject the file; missing substance fails
validation, and the card must pass before grading can run.

## `tests/`

The reward contract:

- write the trial's reward as a **float** to `/logs/verifier/reward.json`
  (`{"reward": <float>}`) — partial credit is real signal, never round a
  fraction to 0 or 1;
- emit per-check results in CTRF to `/logs/verifier/ctrf.json` so reviewers see
  *which* checks failed, not just the score;
- grade **final output files only** — the verifier never reads how the model
  worked.

Before submitting, run the verifier yourself with the built-in nop and oracle
agents: **nop must earn exactly 0, oracle the full reward.**

## `solution/`

`gold.patch` is the unified diff from the fresh workspace to the solved state,
and it is the artifact reviewers read — keep it exactly in sync with what
`solve.sh` produces. `solve.sh` must be deterministic and safe to run once in a
fresh environment. Nothing under `solution/` may be visible to the model.
