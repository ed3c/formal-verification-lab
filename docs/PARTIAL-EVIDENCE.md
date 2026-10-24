# Discover and evaluate selected evidence

The current Session chooses the engineering question, source mapping and evidence scope. Local discovery and supported checks do not require a complete private bundle, original Session identity or external Owner mapping approval. Grant, identity, ordering and effect-completeness facts remain necessary for the particular conclusions that use them.

## Find candidates

```sh
PYTHONPATH=src python3 -m formal_verification_lab.cli discover <workspace> \
  --pattern '*.json' --max-depth 4 --max-files 200 --max-entries 10000
```

The root may be a repository or a non-Git workspace. Discovery reports paths, sizes and filename-based role hints. It does not read record contents, join candidates, derive operation identities, or evaluate them. It skips symlinks and common source-control/dependency directories. Depth limits, match truncation, the total entry budget and scan errors are explicit. A bounded scan that found no record is not proof that no evidence exists elsewhere. A truncated result is a filesystem prefix, not a ranked sample.

## Select available parts

```sh
PYTHONPATH=src python3 -m formal_verification_lab.cli evaluate <workspace> \
  --select operation=selected/operation.json \
  --select provider=selected/readback.json \
  --property FVL-LEGAL --property FVL-NO-DUPLICATE
```

Roles are `operation`, `authority`, `evidence`, `preflight` and `provider`. Every path is relative to the selected root. Traversal, symlinks, unknown roles and duplicate role assignments are rejected. The same five-part v1 bundle command remains available when an existing frozen bundle is useful; it is not the prerequisite for this selection route.

Selection records each successfully parsed file's actual SHA-256 and source path. Missing, unreadable or malformed selected parts produce named `selection_errors`; independent valid parts remain usable. No exception is silently discarded. Path-boundary and role-ambiguity errors still reject the invalid selection. Nothing fabricates a missing identity, grant, sequence, epoch or effect receipt.

Raw native documents are not automatically normalized. The Session reviews the meaning of their fields. Supplying a document without the operation schema leaves unavailable properties UNKNOWN rather than labelling the underlying runtime unsafe.

## Read scoped findings

A legal transition can be checked from its operation kind and endpoints without first establishing a grant. `FVL-AUTH` still checks the actual operation/session, grant scope, authorization value and sequence order. `FVL-RETRY` independently checks the operation/key binding, prior-attempt order, no-effect reconciliation and complete relevant scope. `FVL-NO-DUPLICATE` can pass only for a bound operation and complete relevant effect scope; a known duplicate within that bound subject is a counterexample even if the rest of the ledger is incomplete.

A provider-only record saying `effect_count=2` is preserved as an observation. It is not by itself a duplicate proof about an unbound operation. Freshness, checkpoint, receipt, terminal and idempotency checks similarly carry their own subject dependencies when selected alone. A non-applicable property is UNKNOWN and cannot pass vacuously.

Unselected evidence is not proof that the original execution lacked that evidence. Partial selection therefore does not turn omission into a false-success counterexample. A known contradiction still produces its scoped finding. The legacy complete synthetic cases keep their independent expected verdicts.

A `BOUNDED_PASS` applies only to the selected property and supplied facts. It does not authorize an effect or establish a complete lifecycle, production correctness, authenticity, liveness or a blind behavioral gain. Private records and generated outputs stay outside Git.
