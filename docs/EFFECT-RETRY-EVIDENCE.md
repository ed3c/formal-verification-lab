# Collect evidence for an effect-retry claim

A worker requeue and an effect retry are different claims. A missing effect-domain operation cannot be repaired by filling similarly named phase, key or count fields from another task. The current Session chooses and reviews the mapping. Original Owner approval, original Session identity and a complete private bundle are not qualification gates.

## Identify the operation before collecting more fields

Record the actual action, target, payload/version and producer operation/key when available. Distinguish those runtime facts from an analysis label or file digest. Never turn an order/stage pair or hash into a producer idempotency key.

Keep the selected source revision, actual producer binary/version evidence, record family and ordering domain separate. A source audit explains implementation semantics. It does not prove which source produced an old record. A current endpoint readback does not reconstruct an unrecorded historical interval.

A worker snapshot can expose order, stage and attempt state while having no operation-model phase. In that case, report an unbound effect domain and preserve UNKNOWN for the dependent effect-retry claim. Continue independent workflow and lineage checks.

## Three proof obligations

| Obligation | Evidence needed for that claim | Observations that do not supply it |
|---|---|---|
| Operation phase | Source-reviewed abstraction of the actual operation's program state before and after the action | Worker running/failed/completed labels, a control ACK, or a phase from a different action |
| No-effect reconciliation | An operation/key/target-bound negative result or authoritative readback, ordered after the prior attempt and before retry | `effects=[]` in an incomplete capture, zero declarative ledger attempts, process exit0 or endpoint equality alone |
| Relevant complete effect scope | A declared boundary, observation interval and matching subject/key with source-supported coverage of that boundary | A bare `complete=true`, one local counter, a best-effort log, missing tool inventory or global absence inferred from a bounded search |

The existing normalized evaluator checks supplied operation/key/order and completeness facts. Its offline result remains conditional on the source mapping and evidence quality. It does not authenticate a hostile producer or prove coverage from the word `complete`.

Explicitly state the abstraction function. For example, treating an offered communication attempt as CLAIMED rather than EXECUTING is an assumption about the model's meaning, not an observed literal phase. The original operation model has no EXECUTING-to-FAILED `markFailed` edge. Preserve a mapping or specification gap instead of inserting hidden steps or changing the model to obtain PASS.

## Use the actual producer's readback route

For a publication action, collect the existing publication journal, exact command and target, complete process receipt, action-specific readback and any scope/ordering records. A complete single-ref porcelain rejection can support a bounded no-ref-update conclusion for that invocation under the reviewed source contract. A stderr phrase, timeout, unknown offered request or unchanged endpoint alone cannot establish it. Do not replay an unknown offered action to create a cleaner receipt.

Landing actions have their own checkpoint phases, delivery intents and provider readbacks. They are not interchangeable with a publication or worker retry. A prohibition on merge remains in force during evidence collection. Read existing records; do not execute a forbidden action to fill a proof gap.

A declarative dispatch ledger may remain pending even though process activity is observed. Preserve the ledger and actual process records separately. Do not rewrite pending as done, or pending/attempts0 as proof of zero effects. Positive observations can refute an effect-free interpretation within the same established domain. They cannot be reassigned to a different operation.

## Inspect partial evidence without inventing values

Use the existing CLI to select named available JSON parts and dependent properties:

```sh
PYTHONPATH=src python3 -m formal_verification_lab.cli evaluate SELECTED_DIRECTORY \
  --select operation=selected-operation.json \
  --select provider=selected-readback.json \
  --property FVL-LEGAL --property FVL-RETRY --property FVL-POST-BIND --property FVL-NO-DUPLICATE
```

The CLI preserves unavailable or oversized selected parts in `selection_errors`. A zero process exit does not mean every requested part was loaded. Inspect `selected_parts`, `source_refs` and errors before claiming that a file supplied a fact. Preserve the original file and diagnostic; do not widen the existing read bound just to remove an error.

A raw native record that lacks normalized operation semantics remains unsupported for that projection. Selecting the file does not manufacture an operation or assert a complete bundle. Report the source digest and normalization gap. A legal transition can still be checked independently when its endpoints are actually supplied, while missing readback facts keep retry-dependent findings UNKNOWN.

The public controls include an explicit synthetic valid case, contradictions and incomplete evidence. They prevent an all-PASS or all-UNKNOWN implementation from satisfying the suite. Native lookalike records with pending effects, empty UNKNOWN captures, null inventories, successful ACKs and non-porcelain rejection text do not acquire invented no-effect facts.

## Decide whether historical evidence can be completed

Search the named case and the producer's documented journal locations within declared bounds. Retain searched roots, errors, source digests and missing locations. No match means not found in those roots, not global absence.

If the matching original records were not captured, record the retrospective limit. Unrelated operations or later endpoints cannot fill it. A future authorized real operation can capture the missing observation at its source; that is a new case with its own provenance. Do not start a new Provider action merely to make the old case pass. Necessary source-delivery operations are also separate from the target retry.

For the current source workflow, preserve normal resource admission. A prepared Noodle request is not a started worker. Zero start credit does not authorize another carrier or changes to the governor. Keep engineering, test, historical observation and fresh Native costs separate, with unknown amounts left unknown.
