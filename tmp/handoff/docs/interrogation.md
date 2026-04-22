Inspect the latest pipeline run end to end and answer the following questions with code-level evidence.

Use the current canonical docs as the contract:
- project_spec.md
- question_generation_algorithm_spec.md

Focus on the contradiction that:
- source_run_summary.yaml reports 146 answered, 0 rejected, 0 errored
- but entry_question_count is 0
- and generated beginner-definition questions like “What is R?” / “What is a factor in R?” exist in artifacts
- while their source_refs/source_evidence are empty
- and the inspection bundle export appears filtered to 4 of 5 courses

For each answer:
1. name the exact function(s) and file(s)
2. show the exact data field(s) involved
3. explain whether this is a bug, a metric bug, a wiring gap, or expected behavior
4. propose the minimal patch
5. say what regression test should be added

Questions:

1. Why does source_run_summary.yaml report entry_question_count: 0 even though the run clearly generated beginner “what is” questions such as “What is R?” and “What is a factor in R?”?

2. Where in the codebase is entry_question_count computed, and what exact predicate determines whether a question counts as an entry question?

3. Are “what_is” questions being mapped to the Stage 11 family tag `entry`, or are they remaining only as raw/question_family labels without being promoted into the canonical family taxonomy?

4. Where exactly are question families assigned in the latest operational path for this run: semantic stage, normalization, V4/V4.1 policy, ledger build, or summary rendering?

5. For course 7630, do any generated questions get marked `required_entry=true` anywhere in the pipeline? If not, where is that decision failing?

6. Is foundational anchor detection running at all for these non-time-series courses, or is it effectively scoped only to the earlier R time-series logic? Show the actual anchors detected for each of the 5 courses in this run.

7. If foundational anchor detection does run, why did it not recognize obvious beginner anchors like R, vector, matrix, factor, data frame, or list?

8. Is the `foundational_entry_questions.py` helper actually invoked on the current path for this run? If yes, where; if no, why not?

9. Does the current pipeline path skip V4.1 protected-entry promotion entirely and go straight from semantic outputs to answer generation / final rows? Trace the real executed path, not the intended spec path.

10. Where do `source_refs` first become empty for generated semantic questions? Are they absent at generation time, dropped during normalization, or stripped during ledger/final export?

11. For a concrete example like course 7630 / question “What is a factor in R?”, trace the fields end to end:
    - semantic topic/question artifact
    - question_context_frame
    - cache/train row
    - answer row
    - final all_rows row
    Show exactly where provenance is lost.

12. The question_context_frame appears to retain `support_refs` like summary/overview. Why are those not carried into `source_refs` on question rows or `source_evidence` on answer/final rows?

13. Is there a schema mismatch between `support_refs`, `source_refs`, and `source_evidence` that causes provenance to be silently dropped? If so, where?

14. Which code path is responsible for rendering `answers.jsonl` / `all_rows.jsonl`, and why does it emit `source_evidence: []` for surfaced answered questions?

15. Is the empty-provenance issue a rendering/export bug only, or are the authoritative in-memory / DB records also missing provenance before export?

16. The spec says the ledger row should include source refs and inspection bundles should show what course content the questions were derived from. Which invariant is currently being violated in code, and by which module?

17. Why did the run not fail in strict mode if entry_question_count is 0? Was strict mode disabled, never reached, scoped only to foundational anchors that were never detected, or is the fail condition broken?

18. Where is strict coverage failure enforced in code, and what exact data structure does it inspect before deciding whether to fail the run?

19. Does the coverage audit operate on all generated questions, only validated/policy-classified questions, or only ledger rows? Could that explain why visible beginner definitions exist but coverage still reports zero?

20. The inspection bundle log shows a filtered export with selected_course_ids = ['24372', '24373', '24374', '7630'] while the run summary includes 5 courses including 24370. Why was 24370 excluded from the bundle?

21. Is the filtered inspection bundle expected behavior, or is it masking problems by making a partial export look like the full latest inspection surface?

22. Which command / config / default selected only 4 courses and 98 of 146 rows for the bundle? Show the entrypoint and selection logic.

23. Are there any discrepancies between the authoritative full-run artifacts and the filtered inspection bundle that could mislead a reviewer about coverage or provenance?

24. For the latest run, what is the true authoritative artifact for debugging:
    - semantic outputs
    - answers.jsonl
    - all_rows.jsonl
    - a ledger artifact
    - inspection bundle
    Explain the precedence order with code references.

25. Is the repo currently running the canonical spec path:
    normalized course -> V3 -> V4/V4.1 policy -> V6 ledger -> derived views,
    or has the runtime drifted into a different path? Show the real call graph.

26. If the runtime has drifted from the spec, what is the smallest change that would restore spec-compliant behavior for:
    a) entry-family tagging
    b) protected entry promotion
    c) strict coverage failure
    d) provenance propagation

27. What regression fixtures should be added immediately so that a future run cannot succeed when:
    - entry_question_count is zero despite generated beginner definitions
    - surfaced questions have empty provenance
    - a filtered bundle is mistaken for a full-run inspection artifact

28. After inspecting everything, what is the single root cause?
    Choose one:
    - family/coverage metric bug
    - foundational-anchor detection bug
    - provenance wiring bug
    - pipeline path drift / spec mismatch
    - bundle/export selection bug
    - multiple independent bugs
    Then justify that conclusion with code evidence.
