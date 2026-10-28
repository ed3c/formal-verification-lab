---
name: verify-p4-contracts
description: Read or maintain the Lab P4 pure-predicate evidence when its source, Oracle, or verification environment changes; reuse applicable historical observations and verify actual source faults without widening to Native or CAS.
---

# Verify P4 contracts

Use the [formal-route integration](../../../docs/PSTACK-FORMAL-INTEGRATION.md) before creating or maintaining verification. This skill packages the existing P4 runner; it adds no new model or test scheduler. Read [P4's scope](../../../docs/P4-CONTRACTS.md) and [acceptance](../../../docs/ACCEPTANCE.md).

## Property and coverage

`eligible_effect` must not accept a missing authorization, freshness, legality or identity condition, or an observed duplicate. `receipt_supported` must not accept a count other than one or a missing provider/authorization confirmation. Accepting these inputs would let a pure predicate endorse an unsupported effect or receipt. The predicates do not establish that their Boolean inputs are true in a real system.

Coverage: `src/formal_verification_lab/contracts.py` contains both functions; `formal_contracts.py` contains their CrossHair postconditions; `tests/test_properties.py` contains sampling properties. `scripts/p4.py` supplies the fixed literal accepted tuples, 32 effect cases, 24 receipt cases, and an always-False control. `scripts/p4_canary.py` supplies the unsafe postcondition control. The pinned lock and download record are verification inputs.

The reviewed source sync commit is `72646cf797fa2a4f82f7b88f57dd7c5d0b309119`. It records source correspondence, not a new run at that commit. `scripts/p4_readback.py` uses this same reference for Oracle protection. Move it only after reviewing the actual code, independent contract evidence and affected check results. An implementation change, test change or commit message alone cannot approve a different property. Keep the original source/receipt and report an unresolved change instead of moving the reference.

## Read existing evidence first

Select an existing P4 evidence directory from the caller's evidence index, with its original custody and source receipt. It must contain `input-manifest.json`, `versions.json`, `summary.json`, and `runs/{crosshair,canary,hypothesis,controls}`. Run from the Lab root with the selected pinned Python environment:

```sh
"$P4_PYTHON" scripts/p4_readback.py --evidence "$P4_EVIDENCE"
```

`P4_PYTHON` is the actual Python executable named by the selected environment; `P4_EVIDENCE` is the actual selected evidence directory. Resolve both from the caller's records, not an assumed installation. The readback runs no checker and does not import candidate predicate code. Its `--source` option reads a distinct source fixture during controlled verification; the default is this checkout.

- `REUSE`: the seven recorded input bytes, original process results and recorded environment fields agree. Review the original scope, custody and any unrecorded dependency changes, including package initialization and pytest configuration. If they remain applicable, consume the historical result and stop; do not invoke maintain merely to obtain another PASS. This does not certify a current execution environment or canonical acceptance.
- `SOURCE_CHANGED`: retain the old result as historical. Inspect the actual diff and select the affected original checks through the caller's existing verification owner.
- `ORACLE_REVIEW_REQUIRED`: the accepted contract, postcondition, property test or original runner changed. Review the independent requirement before running or changing expected results. A weakened expectation is not a fix. This conservative readback also sends harmless edits in those files to review.
- `ENVIRONMENT_REVIEW_REQUIRED` or `EVIDENCE_REVIEW_REQUIRED`: read the named missing or changed facts. Do not fill a missing observation or automatically run the whole suite.

## Execute only a justified P4 demand

When a new P4 observation is required, use the original runner with a new directory outside the repository:

```sh
"$P4_PYTHON" scripts/p4.py --evidence-dir "$P4_NEW_EVIDENCE"
```

Resolve `P4_NEW_EVIDENCE` to a fresh external directory. The runner checks pinned package versions, two CrossHair postconditions, the unsafe canary, two sampling properties and literal controls. CrossHair uses 10-second condition and 5-second path bounds; sampling uses seed 20261024. Preserve stdout, stderr, process exits, source digests and failures. A nonzero process exit alone is not a counterexample. This entry is Lab's original runner; Soodles software changes still use its original Test Manager prepare/execute/inspect flow.

For a newly generated or changed verify skill, follow it on a disposable copy of the selected pure sources. Remove `authorized` from `eligible_effect` while leaving the Oracle fixed. The original checker must expose an unauthorized accepted input. Restore the exact source bytes and confirm the prior applicable result or justified fresh result. Never mutate the shared checkout for this control. Record the actions and the original outputs; a modeled canary alone does not demonstrate sensitivity to a real source change.

If maintaining after a skipped verification change, read the installed `maintain-formal-verification-skill` and apply the integration contract. Keep model/harness drift separate from a product bug. This P4 example has no TLA+ model, so `/statechart` is not applicable. Preserve pending Native work, old failures and UNKNOWN claims. Cleanup removes only disposable source copies; evidence survives.
