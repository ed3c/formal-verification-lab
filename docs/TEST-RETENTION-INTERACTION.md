# Portable test-retention interaction

Any repository can supply a bounded study without importing Soodles or starting a runtime. The original repository keeps its test runner, Test Manager and acceptance authority. The Session reviews independent contract meaning and chooses the question. The Lab reads selected local JSON and returns findings; it never runs supplied commands, edits tests, selects a suite or approves deletion.

Use the existing Lab CLI:

```sh
PYTHONPATH=<lab>/src python3 -m formal_verification_lab.cli retention <evidence-root> \
  --study study.json --fail-on-counterexample
```

The caller saves stdout/stderr, exit, duration, source revision and tool version outside public Git. Exit2 with the optional flag means a reported counterexample; exit3 means invalid input/read failure. Exit0 alone is not PASS: consume the report's verdict and findings. Ordinary Repo tests do not depend on this command or Lab availability.

## A finite study

The JSON object has `schema="fvl.retention.v1"`, a nonempty `scope`, and these fields:

| Field | Meaning |
|---|---|
| contracts | Rows `{id, ref}`. Each selected JSON object states `basis` as requirement, compatibility or bug; a nonempty `statement` and original `source` citation. These labels do not establish independence or authenticity. Session must read the actual source and verify that it supports this behavior. |
| tests | Rows `{id, source, context}`. Source is a JSON snapshot of the selected test's provenance. Context requires nonempty string `entrypoint` and `input_recipe`, describing the same selected input recipe/entrypoint/domain. Empty, different or unreadable context cannot establish replacement equivalence. |
| scenarios | Rows `{id, kind, input}` with kind valid or fault. A fault also names its `contract`. Inputs are selected JSON objects. The supplied universe is finite and must have a valid positive case and a fault for each selected contract. No global exhaustiveness is inferred. |
| observations | Rows `{test, scenario, ref}`. The referenced trace contains matching `test`, `scenario`, `test_source_sha256`, `input_sha256`, `context_sha256`, `outcome` and `phase`. The source digest binds the selected source snapshot at capture; rebinding a source requires fresh observations. |
| baseline, candidate | Unique lists of declared test IDs before and after the proposed change. Empty candidate coverage loses any supported required fault. |

Every `ref`, `source`, `context` or `input` above is `{path, sha256}` relative to the selected evidence root. Use the original producer's file references or a deterministic capture; do not invent digests, identities or execution receipts. The existing bundle reader checks selected paths and bytes. Parent traversal and symlinks are rejected. Missing or changed parts remain named errors; there is no complete-private-bundle or original Owner/Session requirement.

`passed` with phase `complete` is a positive or surviving-fault observation. `assertion_failed` with phase `body` detects a fault only when the same control passes all selected valid cases. Setup, cleanup, environment errors, timeouts, missing traces and unexecuted cases do not count as detecting the intended fault. A control that rejects a selected valid case is a counterexample to that positive calibration, not useful universal coverage.

## What the check establishes

For each selected fault, find a valid baseline detector and a valid remaining detector in the comparable supplied context. If both exist, that finite coverage obligation is BOUNDED_PASS. A supported baseline detector followed by an empty candidate, or known candidate survivors for that same fault, yields a named COUNTEREXAMPLE. Otherwise the obligation is UNKNOWN. Known contradictions remain visible beside missing facts. Missing valid/fault populations cannot pass vacuously.

This is exhaustive comparison of the supplied finite relation. It does not invoke a model checker merely to restate a finite subset, and reports `model_checker=NOT_RUN`. It does not prove arbitrary Python equivalence, independent oracle meaning, completeness of the real fault space, authenticity, current production behavior or Native conformance. AST similarity or a self-hash alone is insufficient. Session still decides keep, rewrite, merge or delete from the original product requirements and alternative coverage evidence.

The output separates source refs, selection errors, per-fault findings, assumptions and observed evaluator cost. `oracle_review` and `retention_decision` remain SESSION_REQUIRED. No value score, mandatory solver job or new CI gate exists.

## Original repository adapter

Use original Test Manager prepare/execute/inspect to obtain actual selected identities, source bindings, result and registered obligations. Preserve valid results and failures. Export only selected public/redacted facts to a private study directory. A separate assertion-calibration adapter may inject literal faulty responses; label those as planted calibration, not real product defects or Native execution. Bind the actual assertion failure phase and preserve the correct positive neighbor.

For a duplicate public CLI control, compare the original and remaining assertions under the same selected fixture/entrypoint. Preserve the caller's registered IDs, effects/state obligations and source triggers when changing test references. Keep additional compatibility discriminators in the remaining control. Verify the real current CLI through the original runner, then use labelled finite calibration for the limited coverage question. A deliberately weakened guard must expose a witness, and a changed root/entrypoint must stay non-comparable. Caller-specific source, identifiers and raw traces stay in that repository or private evidence store. See [formal-route method](FORMAL-ROUTE.md).
