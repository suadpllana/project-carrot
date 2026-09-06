# Raising the difficulty of a Carrot task — field notes

Working notes kept from a task that took six revisions to land inside the
sweep band. They are diagnosis first and prescription second: what made a task
too easy, what made it genuinely hard, and how the verifier has to be built so
that "hard" shows up in the score. `docs/task-authoring-guide.md` has the
platform rules; this file has the judgement.

---

Diagnosing why it's too easy
Ask "can this be solved by following the instructions?" before you ask anything else. My v1 shipped a procedure (SOP-PV-004) that specified every step: version resolution, product mapping, the duplicate key, term scope, role definition, exclusion criteria, exposure rule. The weak model scored 0.888 because the task rewarded implementing a written spec, not analysing data. If a competent reader can reach your answer without forming one judgement of their own, you don't have a task.

Distinguish "hard to execute" from "hard to figure out." My dedup rule was a six-part key over 24,000 cases — laborious, and completely worthless as difficulty. Volume is not difficulty. Models are tireless.

Filtering traps are checklist items. This was my v3–v5 mistake and the more expensive lesson. I added two genuine data-integrity findings (reports predating a product's authorisation; a case series cited 288 times that describes 28 patients). Strong model: 0.92. A capable attempt that has decided to be careful will find rows contradicting a reference table — it treats "check the reference data" as a list and works down it. Adding a third such trap would have changed nothing.

Test the spec-only path explicitly. My blind spot was that I only ever mutated my reference solution. I never asked whether the shipped documents alone were sufficient. Mutation testing can't catch that, because the mutation assumes you're already doing the analysis.

The traps that actually worked
Make the answer invisible, not mis-ranked. This is the single biggest lever. Pooling the solicited reports drove the correct combination to PRR 0.18 — below every threshold, absent from the candidate list entirely. There is no wrong-but-close result to notice and correct. Compare that to a decoy that merely outranks the answer: the answer is still on screen, and a second look finds it.

Attack the analysis population, not the data quality. The 5,200 solicited reports aren't erroneous. Every field is valid. They're simply not spontaneous reports, and a disproportionality ratio is defined over spontaneous reporting. Excluding them requires knowing what the measure is, not spotting a bad row. That's a different cognitive act, and it's the one that held.

Prefer silent drops to loud errors. The retired term spellings (Neutropaenia, Pancytopaenia) sit in the coding dictionary with an empty seg_code and a superseded_by_term pointer. A plain join drops them without raising anything. Nothing fails, nothing warns — six of eleven target cases just aren't there, in a series whose true size you don't know in advance. Errors that announce themselves get fixed; silent ones don't.

Ground the mechanism in real literature. I searched before designing and found Drug Safety 2019 on precautionary reporting bias, which documents that pooling patient-support-programme reports simultaneously manufactures false positives and masks true signals. That gave me one planted feature doing two jobs, and it survives reviewer scrutiny because it's a documented real-world phenomenon rather than a puzzle.

Make every wrong answer survive all your documented exclusion criteria. Each decoy — Merizanib/SEG_INF, Norvacitib/SEG_HEP, Ferozanib/SEG_INF — passes E1, E2 and E3 cleanly. Nothing downstream contradicts them. An attempt escalates its decoy with full confidence and never gets a nudge that something is off.

Never let the correct answer be the top-ranked candidate on any uncorrected view. Tesparinib/SEG_HAE is 3.52 against decoys at 4.82 and 3.97. "Pick the strongest signal" is always wrong.

Kill the coarse-fact shortcuts deliberately. Tesparinib is not the newest product (Norvacitib is), and it is not the only product without a labelled reaction — I gave every product at least one labelled grouping specifically so that heuristic dies.

Make each trap independently decisive. Six separate omissions each flip the decision and cost all 124 test-side decision points. Getting five of six right scores like getting none right. That's what converts "hard" into "reliably missed."

Accept a dead end as a legitimate outcome. If retired terms go unresolved, nothing in the class survives the screen. I worried that prompts self-correction — then kept it. A model that notices "zero signals is implausible" and re-examines has earned the credit; one that reports "no signal" scores zero on the decision. It's fair either way.

Verifier design
Cut free credit aggressively. Structural checks (file existence, headers, sort order, tokens) went from 32 points to 18 of 789. Rubric criteria that a well-written memo earns regardless of correctness — "states that NARROW scope was used," "states the thresholds applied" — got capped at 4 each. These are the points a wrong attempt harvests.

Push the decision share to the top of the permitted band. 44.9% against a 30–50% band. The wider the decision share, the more a wrong conclusion costs.

Add sentinel checks on the artefact rows. Named tests asserting Norvacitib/SEG_HEP has a=18 and flag false, Merizanib/SEG_INF a=22 and false. These are only earnable by an attempt that made the corresponding correction, and they're independent of whether the final decision was right.

Verify the whole table, not the winning row. All 49 contingency tables and statistics compared against a reference artifact — because every correction shifts the entire screen, so the table is where the work shows.

Tolerances cover rounding, nothing else. My first audit failure was generous bands (±8 on counts, ±250 on exposure) that let analytically wrong answers pass. I tightened to exact integers and ±0.011 on 2 dp fields — after confirming the exposure sums to exactly 41000.0 in any summation order, so tightening couldn't fail a correct solution.

Read declared integers strictly. int(num(x)) silently truncated 11.9 into a pass. I wrote an as_int() that accepts 11, 11.0 and "11" but rejects anything fractional. The audit caught four instances of this.

Process
Build the mutation harness first, not last. Mutate the reference solution one step at a time and score each result against the real verifier. This is the whole game. It gave me the table that made the task card credible and that justified the nine zero-reward notes. I built it late; building it first would have saved two cycles.

Keep the ground truth deterministic under reordering. I made the exclusion sets disjoint by construction — literature cases are never duplicated — so applying dedup before or after assessability gives identical counts. Otherwise the "right" answer depends on the order an attempt happens to choose.

Re-derive the answer from the shipped files only. verify_design.py reads environment/data/ and reproduces the ground truth without touching generator state. It proves solvability rather than asserting it.

Signpost the duty, refuse to enumerate the checks. SOP §5.4 says unassessable reports don't enter the analysis set and explicitly declines to list what to check. That keeps it fair — the information is all present — while leaving the work undone. The solicited block gets no mention beyond a factual report_source column description.

Watch the criterion cap fight your rubric quality. I merged three Limitations criteria to get under 50, which immediately triggered a "may bundle multiple facts" suggestion. Splitting and staying under 50 are in direct tension; budget criteria slots early.

