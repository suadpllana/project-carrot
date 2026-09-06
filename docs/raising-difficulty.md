# Raising the difficulty of a Carrot task — field notes

Working notes from three tasks that each took several revisions to land inside
the sweep band, plus what was learned calibrating against a strong model rather
than a weak one. Diagnosis first and prescription second: what made a task too
easy, what made it genuinely hard, and how the verifier has to be built so that
"hard" shows up in the score. `docs/task-authoring-guide.md` has the platform
rules; this file has the judgement.

Throughout, **task01** is the pharmacovigilance signal-escalation task,
**task03** the supply-point sizing task, and **cadence** the FY2026 sourcing
award in this repo.

---

## Diagnosing why it's too easy

**Ask "can this be solved by following the instructions?" before you ask
anything else.** Task01 v1 shipped a procedure (SOP-PV-004) that specified
every step: version resolution, product mapping, the duplicate key, term scope,
role definition, exclusion criteria, exposure rule. The weak model scored 0.888
because the task rewarded implementing a written spec, not analysing data.
Task03 repeated the mistake with DPS-07, which spelled out quality codes,
duplicates, the N-1 rule, the restatement duty, the block-load filter, the
sizing integral and the selection rule: 0.573. If a competent reader can reach
your answer without forming one judgement of their own, you don't have a task.

**Distinguish "hard to execute" from "hard to figure out."** The task01 dedup
rule was a six-part key over 24,000 cases. Laborious, and worthless as
difficulty. Task03 shipped an 841,000-row interval file. Also worthless on its
own. Volume is not difficulty. Models are tireless.

**Filtering traps are checklist items.** This was the task01 v3–v5 mistake and
the more expensive lesson. Two genuine data-integrity findings were added and
the strong model still scored 0.92. A capable attempt that has decided to be
careful will find rows contradicting a reference table; it treats "check the
reference data" as a list and works down it. Task03's first four traps were all
of this kind — quality codes, duplicates, a CT ratio error, a retired
transformer — and a fifth would have changed nothing.

**Count your signposts, don't just check each one.** This is the task03 lesson
that task01 never surfaced. My second revision hid the crux properly but
pointed at it in four places: the register note named the metering point id
outright, the standard said the analyst must establish which metering points
make up each supply point, the data dictionary repeated it, and the prompt
asked the attempt to explain how it had done so. Every one was individually
defensible. Together they were an instruction, and the weak model scored 0.471.
Grep the whole package for the mechanism before you decide it is hidden — and
count *distinct statements*, not files: cadence's clause 5.4 appears in four
term sheets but is one signpost, deliberately identical so no supplier is
advantaged by a hidden term.

**Test the spec-only path explicitly.** The task01 blind spot was only ever
mutating the reference solution, never asking whether the shipped documents
alone were sufficient. Mutation testing cannot catch that, because the mutation
assumes you are already doing the analysis. Write the attempt that does
everything a document instructs and forms none of the judgements no document
makes for it, and score it through the real verifier. Make it *generous* — give
it every reconciliation a document states as a fact — so the number is an upper
bound. Cadence's spec-only path scores **0.079**.

**Then extend it: score every partial-correction path.** Task03 needed more
than the spec-only path. I built the attempt that finds crux A but not B, the
one that finds B but not A, and the one that finds neither, each correct in
every other respect, and scored all of them on the real verifier. The middle
case is the one that decides the band. Spec-only was 0.31; the best partial was
0.36. Without that table I would have been guessing.

**Your simulation of a wrong attempt can flatter itself.** I built a wrong-site
attempt by changing the recommendation but leaving the golden ranking in the
JSON. That handed it 50 decision points it could never earn in practice, and
made the partial path look 5 points worse than it was. A simulated wrong
attempt must be internally consistent: it ranks the site it recommends first,
and it sizes the site it recommends. **The memo counts too.** Cadence's harness
originally computed the exclusion statistics once from the correct pipeline and
handed them to every mutated run, so a variant that pooled the source
inspections still filed a memo saying it had excluded them, and collected three
memo checks no real attempt on that path could earn. Recomputing per variant
and branching the prose on the run's actual choices moved the measured wrong
paths down 1 to 2 points each.

## The traps that actually worked

**Make the answer invisible, not mis-ranked.** This is the single biggest
lever. In task01, pooling the solicited reports drove the correct combination to
PRR 0.18, below every threshold and absent from the candidate list entirely. In
task03, the correct supply point reads 83.0 per cent on its busbar metering and
sits sixth of seven, while the decoy is the only site over its limit. In
cadence the winner is third of four on the default reading of the inspection
log and fourth with the source inspections pooled. There is no wrong-but-close
result to notice and correct. Compare that to a decoy that merely outranks the
answer: the answer is still on screen, and a second look finds it.

**Attack the analysis population, not the data quality.** The 5,200 solicited
reports in task01 are not erroneous. Every field is valid. They are simply not
spontaneous reports, and a disproportionality ratio is defined over spontaneous
reporting. Task03 used the same move twice: a feeder metered separately since a
2022 reconfiguration is exported under its own metering point, and the readings
are correct, but a metering point is not a supply point; three weeks of load
transferred onto a substation during a cable replacement is real demand
correctly recorded, but it is not that substation's own demand. Cadence's
source inspections are the same shape — real inspections of real lots, but not
pieces Cadence ever bought. All of these require knowing what the measure is
defined over, not spotting a bad row. That is a different cognitive act and it
is the one that holds.

**Prefer silent drops to loud errors.** Task01's retired term spellings sit in
the coding dictionary with an empty `seg_code` and a `superseded_by_term`
pointer; a plain join drops them without raising anything. Task03's separately
metered feeder has no row in the substation register, so a join from demand to
the register drops it and nothing warns. Cadence's post-cutover receipts carry
the ERP's purchase-order number, so a join to the purchasing extract matches
every pre-cutover receipt and silently matches nothing after go-live. Errors
that announce themselves get fixed. Silent ones do not.

**Two jointly necessary cruxes beat one hidden crux.** This is the change that
moved task03 from 0.471 to a measured partial ceiling around 0.33. Finding the
feeder is not sufficient, because leaving the transferred load in still puts the
decoy on top. Excluding the transferred load is not sufficient, because without
the feeder the decoy is the only site over its limit. Only both together
produce the answer, so an attempt that solves one crux perfectly scores like an
attempt that solved neither.

**Ground the mechanism in real literature.** Task01 found Drug Safety 2019 on
precautionary reporting bias, which documents that pooling patient-support-
programme reports both manufactures false positives and masks true signals. One
planted feature doing two jobs, and it survives reviewer scrutiny because it is
a documented phenomenon rather than a puzzle. Task03's equivalents are ordinary
utility practice: separately metered feeders after a reconfiguration, abnormal
running arrangements during outages, CT ratio misconfiguration. Cadence's are
ordinary procurement practice: return-to-vendor authorisations, an ERP cutover
mid-year, a rolling planning cube.

**Make every wrong answer survive all your documented exclusion criteria.**
Each task01 decoy passes E1, E2 and E3 cleanly. In task03, an attempt that
misses the feeder produces a table in which exactly one supply point is over
its limit, which is exactly what a plausible answer looks like. Nothing
downstream contradicts it, so the attempt commits with full confidence and
never gets a nudge.

**Never let the correct answer be the top-ranked candidate on any uncorrected
view.** Task01's answer is 3.52 against decoys at 4.82 and 3.97. Task03's is
sixth of seven on busbar-only utilisation, third on real power, and least
loaded of all if the retired transformer is counted. "Pick the strongest
signal" is always wrong.

**Kill the coarse-fact shortcuts deliberately.** Task01 gave every product at
least one labelled grouping so that "the one with no labelled reaction" dies.
Task03's answer is not the newest supply point, not the largest, and not the
only one missing from the screen — a second unscreened supply point is included
and is genuinely healthy, so "the one they forgot" is not a shortcut either.
Cadence's winner holds the *highest* quoted price of the four and does not have
the lowest reject rate.

**Make each trap independently decisive.** Six separate omissions in task01
each flip the decision and cost all 124 test-side decision points. Task03 has
seven, each landing on a different named supply point. Getting five of six
right scores like getting none right. That is what converts "hard" into
"reliably missed."

**Accept a dead end as a legitimate outcome.** If task01's retired terms go
unresolved, nothing in the class survives the screen. That prompts
self-correction in a model that notices "zero signals is implausible" and
re-examines. That model has earned the credit; one that reports "no signal"
scores zero on the decision. It is fair either way.

## Against strong models

**The asymmetry that matters.** A strong model, once it decides to be careful,
exhausts any checklist you can enumerate. So difficulty cannot come from adding
items to a list — it has to come from work that isn't list-shaped. Design the
crux out of what a strong attempt reliably misses:

- **the frame** — which rows constitute the analysis population at all
- **silent loss** — a join that drops rows without raising anything
- **definitional knowledge** — what the metric is defined over, versus what the
  procedure says to do
- **second-order effects** — something moving the denominator, not the numerator
- **absence** — noticing that something which should be there isn't

**Four archetypes that survived.**

*Population contamination.* Plant a large block of rows that are valid,
well-formed, and from a different data-generating process — 5,200 of 30,181
cases from a patient support programme with scheduled blood counts. Pooled, it
manufactures a false positive and masks the true signal: two effects, one
planted feature. It survives because nothing is wrong with any row, so there is
no contradiction to detect.

*Silent join loss.* Retired term spellings with an empty `seg_code` and a
`superseded_by_term` pointer. Concentrate the loss on the answer: 6 of 11
target cases legacy against about 7% of the database, so the background barely
moves while the answer's PRR collapses 3.52 → 1.71.

*Background corruption.* Most traps hit cell *a*, and strong models watch *a*.
Put the trap on *c* and *d*, so the comparator is wrong while every number
about the product of interest looks clean.

*Defensible-method divergence.* Design so that all defensible methods agree and
only the lazy default diverges. If two defensible methods give different
answers you have a broken task, not a hard one.

**The calibration arithmetic.** This is the part worth internalising. With `q`
the probability a strong attempt clears one non-checklist layer, `k` the number
of independently decisive layers, and `f` the score cap when the decision is
wrong:

```
mean ≈ q**k + (1 - q**k) · f
```

Task01 measured `f ≈ 0.27`, so `mean ≤ 0.6` needs `q**k ≤ 0.45`: at `q = 0.85`
that is `k ≥ 5`, at `q = 0.75` it is `k ≥ 3`. Six shipped. That is the concrete
answer to "how many traps is enough."

**Measure `f`, don't assume it,** and measure it over internally consistent
wrong attempts. Cadence's harness prints it: max 0.416 and mean 0.225 over 27
wrong-decision paths, which puts the strong ceiling at `q**k ≤ 0.484` and the
weak ceiling at `q**k ≤ 0.161` — `q ≤ 0.886` and `q ≤ 0.737` respectively at
`k = 6`. Note what that says: the strong ceiling is comfortable and **the weak
ceiling is the binding one**, because it demands that a weak attempt fail
roughly one layer in four. Reweighting barely moves `f`; only more
independently decisive layers move `q**k`. If a sweep comes back over the weak
ceiling, add a layer — do not re-tune the rubric and hope.

**Three rules that make each layer count.** Invisible beats mis-ranked (drive
the answer below threshold, not just below a decoy). Every decoy must survive
all documented exclusions, or you hand out a free correction signal. Layers
must be independently decisive, so that five of six right scores like none.

**What measurably did not work:** more filtering traps (task01 v3–v5 added two;
the strong model scored 0.92), data volume, format messiness, arithmetic
complexity, and long complete procedures — that last one actively helps a
strong model.

## Verifier design

**Cut free credit aggressively.** Task01 moved structural checks from 32 points
to 18 of 789. Task03 moved them from 25.7% of the test weight to 5.5%. Rubric
criteria that a well-written memo earns regardless of correctness get capped
low. These are the points a wrong attempt harvests.

**But do not cut by reweighting alone. Merge.** Task03 got flagged by the audit
for uneven weight distribution after I pushed contract checks down to 1 point
each against a decision test at 74 — a 74:1 spread. The fix was not more
reweighting, it was merging 28 thinly spread contract checks into 10 that cover
the same ground. That removes free items and evens the spread at the same time.
The sweep wants concentration on the decision; the audit wants even
distribution. Merging satisfies both; reweighting satisfies one at the expense
of the other. Cadence had the same shape — fourteen checks at weight 1 against
a decision test at 52 — and merging eleven of them into three took the spread
to 57:2 over 40 checks. Keep the merged assertions individually named, so a
reviewer reading `ctrf.json` still sees which clause failed.

**Push the decision share to the top of the permitted band, and split it across
many items.** Task01 ran 44.9% against a 30–50% band; task03 ran 47% across 17
items rather than four; cadence now runs 47.0%. The wider the decision share,
the more a wrong conclusion costs. Splitting it across many items keeps any
single item small enough to survive the per-criterion cap.

**Add sentinel checks on the artefact rows.** Named tests asserting a specific
corrected value, earnable only by an attempt that made the corresponding
correction, and independent of whether the final decision was right. Task03 has
six. Each also asserts the value is *not* the uncorrected one, so a near-miss
cannot pass.

**Verify the whole table, not the winning row.** Task01 compared all 49
contingency tables against a reference artefact. Task03 checks every supply
point's peak, utilisation, first exceedance year and forecast, because every
correction shifts the whole table. The table is where the work shows.

**Tolerances cover rounding, nothing else — and you should measure that rather
than guess.** Task01's first audit failure was generous bands that let
analytically wrong answers pass. Task03 ran several defensible implementations
against each other, varying rounding of intermediates and day-grouping
convention, and measured the widest legitimate divergence at 0.044; tolerances
were then set 4 to 20 times that. **Publish them in the prompt as a table** —
that turns an "unstated tolerance" finding into a stated contract. Cadence
pins every convention in the shipped finance policy (the `/365` basis, the
spend base, the Incoterm rule) so the only legitimate divergence is rounding,
and the prompt now states the accepted band for every field.

**Read declared integers strictly.** `int(num(x))` silently truncates 11.9 into
a pass. Write an `as_int()` that accepts 11, 11.0 and "11" but rejects anything
fractional. Task01's audit caught four instances of this.

**Check that your ground truth does not depend on an arbitrary convention.**
Task03's peak-day integral originally crossed UTC midnight, so grouping by UTC
day and by local day gave answers 15% apart — two correct implementations would
have disagreed. Fixed by shifting the load shape so the exceedance window sits
inside one day under either convention. Verify this explicitly rather than
assuming it.

**Do not let a computed answer land on a rule of thumb.** Task03's energy
rating initially came out within 1.5% of six hours times the power rating,
which meant a heuristic would pass the test. I tuned the load shape until the
answer was more than 6% from every round-hour multiple, then confirmed that a
four-hour and a six-hour rule both fail.

**Grade what the attempt charged, not how it wrote it down.** Cadence's
build-up checks matched each cost element against a single filed row, while the
prompt invited the attempt to itemise freely. An analytically perfect answer
that split inbound freight into the lane tariff and the brokerage — which the
prompt's own "give each element its own row" rule encourages — lost 16 points
and scored 0.959. Matching an amount against any subset of the rows fixed it,
and changed no mutation score. A check that grades presentation instead of
substance costs you correct attempts and buys nothing.

## Rubric and prompt

**Every rubric criterion must grade something the prompt requires.** An audit
flagged 17 of mine as "expecting something a correct solution would not
produce", because the prompt never asked for that content. The fix is not to
delete the criteria. It is to make the prompt require the topic and let the
rubric grade the correct answer on that topic. The prompt now says the report
must state how firm capacity was derived, which block loads were included and
why, and whether the screen result stands; the rubric grades whether those
answers are right.

**Enumerate every prompt instruction and check coverage in both directions.**
Doing this found a straight contradiction in task03's: the prompt said "exactly
these eleven keys" and then listed ten, so an attempt trusting the prose would
have invented a key and failed the test. The same sweep over cadence found two
stale counts — "Both files are RFC 4180" and "the two CSVs" — in a prompt that
by then shipped three.

**Signpost the duty, refuse to enumerate the checks.** Task01's SOP §5.4 says
unassessable reports do not enter the analysis set and explicitly declines to
list what to check. Task03's standard says the analyst is responsible for
satisfying themselves the record is complete and correctly scaled, and states
in terms that it does not enumerate the checks. That keeps it fair, because the
information is all present, while leaving the work undone.

**Watch the criterion cap fight your rubric quality.** Task01 merged three
Limitations criteria to get under 50 and immediately triggered a "may bundle
multiple facts" suggestion. Task03 hit the same wall from the other side: to
add a criterion the audit demanded, I had to merge two others, which drew the
same suggestion. Splitting and staying under 50 are in direct tension. Budget
criterion slots early.

## Process

**Build the mutation harness first, not last.** Mutate the reference solution
one step at a time and score each result against the real verifier. This is the
whole game. Task01 built it late and it cost two cycles.

**Build the spec-only harness beside it, before the data is final.** See above:
mutation cannot answer the question it answers.

**Add negative mutations as well as positive ones.** As well as "does this
mutation get caught", ask "does a correct output that has been reformatted
still pass". Task03's harness re-wraps the report at 34 columns and requires
every test to still pass; that caught a test that failed on a line wrap because
"Harbour Transit" was split across two lines and the check matched the literal
string. Cadence's runs six reformats — re-wrapping, `$1,234.56` money, whole-
dollar rounding, CRLF endings, another house style for the legal names, and a
finer build-up decomposition — and the last of those found a live 16-point bug
in a correct answer. Reformats must respect what the prompt actually permits:
"Ltd" → "Limited" is a different name, not a house style, so it belongs in a
positive mutation.

**Keep the ground truth deterministic under reordering.** Task01 made the
exclusion sets disjoint by construction, so applying dedup before or after
assessability gives identical counts. Task03 kept the duplicate week, the
absent-interval run and the flagged intervals non-overlapping for the same
reason. Otherwise the right answer depends on the order an attempt happens to
choose.

**Re-derive the answer from the shipped files only.** A script that reads
`environment/data` and reproduces the ground truth without touching generator
state proves solvability rather than asserting it.

**Check the sibling tasks before you choose a domain.** I built a complete
task03 package in pharmacovigilance before noticing that task01 and task02 were
both pharmacovigilance signal-escalation tasks with the same "escalate exactly
one candidate" shape, the same three-table ICSR export and the same six-heading
memo. The whole build was thrown away. Look at what is already in the project
first.

**Ship a standard-library-only golden solution.** One audit could not execute
mine at all because its sandbox had no numpy, and every finding came back with
"the attempted golden-solution execution was blocked". Rewriting `solve.py` in
pure stdlib, with no pandas and no numpy, removed a whole class of unverifiable
findings. It costs little: an 841,000-row CSV is fine with the `csv` module,
and an `.xlsx` is a zip of XML that `zipfile` plus `xml.etree` reads in about
forty lines. Keep the *image* preinstalling whatever an analyst would expect —
the constraint is on the reference solution and the provenance tooling, not on
the attempt.

**Do not write test files through shell heredocs.** Mine silently turned a
regex word boundary into a literal backspace character, so the pattern could
never match and the check was dead. It only surfaced because the reference
dropped from 49 of 49. Write test files with a file-writing tool, and scan the
result for control characters before trusting it.

## The review loop

**Confirm the audit read the version you shipped.** One audit came back word
for word identical to the previous one, naming a test function I had renamed,
reporting 58 tests when I had 61, and quoting a prompt sentence I had already
split in two. It had run against the stale archive. Check the fingerprints —
test count, function names, quoted text — before you spend a cycle fixing
findings that are already fixed.

**Confirm the archive that was uploaded is the archive you built.** Intake once
refused mine over a `.pyc` file under `tests/__pycache__`, reporting a digest
and file count that were not mine. My packaging step already skipped caches;
the zip that got uploaded had been built some other way. Purge caches at the
source so no packaging method can pick them up, and make the packaging script
verify its own output against an extension allowlist and print the digest.

**Confirm the platform rubric matches the archive rubric.** After one
submission the editor was showing an older rubric than the archive contained:
different weights, eight decision criteria instead of ten, and one criterion
missing entirely. Both had the same criterion count, so it looked fine at a
glance. Annotating the wrong copy wastes the work.

**Once a task is review ready, change nothing in the package.** Task card and
rubric edits belong in the platform editors, which do not require a resubmit.
Resubmitting re-runs the sweeps, and a warning can become a failure.

**Write the zero-reward notes from evidence, not assertion.** For every
criterion, point at the reference deliverable that satisfies it and say why the
criterion is independent of, or dependent on, the decision. And say plainly
when the pattern looks wrong: if no trial earned a criterion that is simply
"the report is 1500 words or fewer", that is worth raising with the reviewer
rather than explaining away.
