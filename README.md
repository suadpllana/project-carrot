# project-carrot

Carrot (Harbor) task packages and the reference material for authoring them.

| Path | What it is |
| --- | --- |
| `cadence-supplier-award/` | FY2026 valve-seat sourcing award — a hard, multi-format procurement analysis task |
| `docs/` | Platform rules, the authoring guide, and field notes on difficulty |
| `template/` | The official starter template, unmodified |

Start with [`CLAUDE.md`](CLAUDE.md) for the working rules, then
[`docs/task-authoring-guide.md`](docs/task-authoring-guide.md).

## cadence-supplier-award

The attempt is a sourcing analyst who must award a full contract year of a
stainless valve seat to one of four suppliers, from seventeen unreconciled
input files across four formats, and file three CSVs and a committee memo.

Six independent judgements gate the answer and each one lands on a different
supplier when it is missed: which rejected pieces are actually a loss, which
months of a rolling planning cube the contract covers, which inspection records
belong in a reject rate, how a lot is attributed across an ERP renumbering,
whether the free-text supplier field is usable, and which S&OP cycle is the
plan of record. On every uncorrected view the right supplier is third or fourth
of four.

Ground truth, verifier design and the measured mutation sweep are in
[`cadence-supplier-award/task_card.md`](cadence-supplier-award/task_card.md).
