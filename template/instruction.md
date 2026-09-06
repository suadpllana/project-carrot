# Working title — replace

<!-- This file is the prompt the model receives. Keep it AMBIGUOUS on
     purpose: state the situation and the decision that is needed — never the
     method, the metric, or the answer. If a competent analyst could complete
     the task without deciding for themselves what to measure, the prompt is
     too prescriptive. -->

You are a data analyst at <describe the organization neutrally — replace>.

<Two to four sentences of business context: what happened, what leadership is
worried about, and the decision on the table — replace.>

Using the data provided in the environment:

1. Investigate <the open-ended question — replace>. Decide for yourself which
   of the provided sources matter, how to reconcile them, and what to measure.
2. Take a clear, written position on <the decision — replace>, supported by
   figures you derived from the data.

Write your final deliverables to `/workspace/output/`:

- `recommendation.md` — the recommendation memo: position, key evidence,
  quantified impact, risks.
- Any supporting artifacts (tables, charts, cleaned datasets) a reviewer
  would need to retrace your reasoning.

<!-- Authoring bar (delete this comment before submitting):
     - 5+ input files across 3+ distinct formats, realistically messy.
     - The ground-truth recommendation must be DETERMINISTIC — reproducible
       from the inputs alone.
     - The prompt stays silent about which analyses to run; the rubric, not
       the prompt, encodes what a strong answer contains.

     Archive capture files

     ## rubrics.json

     This archive-root file is OPTIONAL at upload. If omitted, intake shows a
     warning and you write the rubric in the platform editor before grading.
     If included, it seeds that editor. Invalid JSON or any unknown object key
     REJECTS the archive.

     The file is a bare JSON array. Every criterion object requires:
     - item: a unique, 1-based integer.
     - weight: a nonzero integer with absolute value at most 100. A negative
       weight is a penalty that subtracts from the numerator only.
     - criterion: a concrete, checkable claim.
     - category: one of explore, hypothesize, analyze, synthesize, recommend,
       instruction_following.
     - verification_type: one of text, multimodal, code_execution,
       file_structure.

     Optional keys are:
     - is_recommendation_criterion: a boolean.
     - grades_output_files: an array of globs over the task's expected output
       files.

     Reward is calculated as:

       final_reward = sum(earned weights) / sum(positive weights)

     Before grading, a complete rubric has 10-25 criteria; the criteria
     flagged is_recommendation_criterion — pooled with any tests flagged
     "decision": true in tests/test_weights.json — together carrying 30-50%
     of total positive weight; and
     at least one output-file glob on EVERY criterion. Grading sees only
     the final output files, so each criterion must declare which files it
     grades.

     If is_recommendation_criterion is omitted everywhere, the platform
     infers the decision criteria when the choice is unambiguous and asks
     you to confirm the selection in the editor.

     ## task_card.md

     This archive-root file is OPTIONAL at upload. If omitted, intake shows a
     warning and you complete it in the platform editor. It must contain:
     - the task description;
     - a complexity justification explaining why the task is hard;
     - taxonomy tags;
     - the expected difficulty range;
     - the ground-truth recommendation and its rationale; and
     - when no golden solution is included, a summary of the expected
       reasoning trajectory.

     The example file's six headings are a convention that helps the platform
     pre-fill its form. Validity is judged on CONTENT: an automated reviewer
     checks that the required items are present and substantive. Formatting
     deviations do not reject the file, but missing substance fails
     validation. The card must pass validation before grading can run.

     Delete this entire authoring comment before submitting. -->
