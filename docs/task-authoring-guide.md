# Carrot task authoring guide

Source: <https://carrot-instructions.edgeone.dev/>. Package mechanics are in
`docs/harbor-package-howto.md`; hard-won judgement about difficulty is in
`docs/raising-difficulty.md`.

## 1. What you are building

Every task is an immutable, executable package with four load-bearing parts.

1. **An ambiguous prompt.** State the decision that is needed — never the
   analysis steps, the columns to use, or the expected shape of the answer.
2. **Messy, cross-referenced input data.** Several files across multiple
   formats (spreadsheets, exports, logs, documents) the way a real analyst
   would actually receive them. Noise and inconsistency are the point, not
   defects to clean away before packaging.
3. **One deterministic recommendation.** Decide, before anything ever runs, the
   single unambiguous conclusion the data supports, and write down why. Your
   reference solution has to reach it.
4. **A weighted binary rubric.** 25 to 50 criteria, each a concrete, checkable
   claim about the final output files, worth a signed weight. Positive weights
   reward; negative weights are penalties. The decision must dominate the
   reward: at least three criteria, together with any decision-scoring tests,
   score whether the attempt reached your conclusion, and together they carry
   30 to 50% of the total positive weight. No single criterion carries more
   than 20% of the rubric's weight. Every explicit instruction in the prompt
   (file names, formats, required fields, precision, prohibitions) is graded by
   a criterion or a test.

## 2. Workflow

1. **Build the package locally** from the starter template in `template/`.
   Author the prompt, assemble the dataset, write the reference solution and
   the verifier.
2. **Test it yourself.** Run both local checks before every submission: the nop
   agent must score 0 and the oracle agent must score full marks against the
   exact archive you upload.
3. **Submit the archive.** The platform re-validates everything server-side:
   format and quality checks, then a rebuild, then the same two agent checks
   you ran locally, then a task-quality audit of the prompt, rubric, tests and
   instruction coverage, then evaluation sweeps against the project's model
   set. Sweeps run each model four times and judge the mean:

   | Sweep | Ceiling |
   | --- | --- |
   | strong model mean reward | **≤ 0.60** |
   | weak model mean reward | **≤ 0.35** |

   A failed audit or sweep returns the task with the specific criteria, tests
   or trial outcomes that caused it.
4. **Manual review.** A human reviewer inspects the full package. Approval
   makes the version deliverable; a send-back returns it with written,
   actionable feedback.
5. **Revise when asked.** A returned task keeps its identity: upload the
   corrected archive and its version number increases. Nothing is silently
   discarded. If you edited the rubric in the platform editor, either carry
   those edits into the archive's `rubrics.json` or omit that file from the
   re-upload — an uploaded `rubrics.json` replaces the editor's copy.

## 3. Ground rules

- Everything in the package must be yours to submit. Attach a licensing note
  for any file you sourced rather than authored; you are responsible for its
  provenance.
- Model identities are never shown on this platform. Sweep results are reported
  with neutral labels only.
- Never include personal information, credentials, private URLs, or anything
  you would not hand to a stranger, in any file of the package.
- **Difficulty must come from the analysis itself.** Withholding information an
  analyst would obviously have, trick wording, a broken environment, or
  penalties designed to depress the score are grounds for a send-back, not
  difficulty.
- **Deliverables are files.** Every graded output must be written to the output
  directory; text in the conversation is not graded.

## 4. How to raise difficulty

Let the coding agent raise the difficulty and test itself locally. The short
version of `docs/raising-difficulty.md`:

- Ask first whether the task can be solved by *following the shipped
  documents*. If a competent reader can reach the answer without forming one
  judgement of their own, you do not have a task.
- Volume is not difficulty. Models are tireless. "Hard to figure out" beats
  "hard to execute" every time.
- Filtering traps are checklist items. A careful attempt works down the list of
  reference tables and finds them.
- **Make the answer invisible, not mis-ranked.** A decoy that merely outranks
  the answer leaves the answer on screen for a second look to find. Attack the
  analysis population instead, so the right answer is not on the podium at all
  on any uncorrected view.
- Prefer silent drops to loud errors. A join that quietly matches nothing gets
  fixed far less often than one that raises.
- Make every wrong answer survive all your documented exclusion criteria, so an
  attempt escalates its decoy with full confidence.
- Make each trap independently decisive. Getting five of six right should score
  like getting none right.
- Signpost the duty; refuse to enumerate the checks. That keeps it fair — the
  information is all present — while leaving the work undone.
- Cut free credit aggressively in the verifier, and put the weight on figures
  only the correct pipeline produces.
- Build the mutation harness first, not last: mutate the reference solution one
  step at a time and score each result against the real verifier.
