# Retry event mapping and scoped conformance

The public checker inspects selected local records. It does not dispatch a task, retry an operation, contact a Provider or change a runtime. Public tests use synthetic data. Actual Native traces and their source/version receipts remain outside Git.

## Two meanings of retry

An implementation can requeue a worker stage after failure or review changes. That transition records scheduling and custody facts. The abstract `OperationProtocol.retry` requires an operation in FAILED or UNKNOWN, a reconciled no-effect observation, and effectCount zero. A worker requeue does not establish those facts.

The operation model also permits `markFailed` only from CLAIMED. If a proposed mapping turns native running into EXECUTING, the model has no corresponding EXECUTING-to-FAILED edge. Report that mapping gap. Do not erase running, insert an unobserved reconciliation, fill missing State fields or change the specification to produce a match.

## Native event mapping

This version reads the dot-named lifecycle stream `{seq,type,at,payload}`. It does not treat canonical ingest names such as `stage_failed` as synonyms. Keep their source families separate.

| Native event | Observed fact | Candidate abstract action | Missing interpretation |
|---|---|---|---|
| `stage.failed` | A named stage/Session failed according to the producer | `markFailed` | Operation phase and domain; failure may be review failure rather than Native process exit |
| `order.failed` | The order was marked failed | No direct operation action | Worker order state is not operation state |
| `order.requeued` | Requeue notification for the named order | `retry`, conditional | Prior operation state, ordered no-effect reconciliation and relevant complete effect scope |

A retained `stage.failed < order.failed < order.requeued` sequence supports an observed workflow prefix for that order. It does not prove an attempt has restarted. An ACK is a separate control observation. Never use a requeue or recovery label as `reconcileNoEffect`.

The source lifecycle writer is best-effort and retains at most 200 lines. It can omit events. Increasing or contiguous sequence numbers order the selected stream, not every runtime/Provider effect. Missing events, gaps, a bounded read or an empty selection cannot prove absence. Preserve unfamiliar events and source line/digest references rather than silently discarding them. Selected source revisions and actual producer/runtime versions are different provenance claims; leave an unavailable producer version UNKNOWN.

## Explicit operation projections

`check_model_step` checks one named transition against the existing finite Python translation. The Quint `markFailed` name has the explicit Python `fail` alias. The checker does not modify either model or run Quint/Apalache.

Supply operation before and after states explicitly in the existing State field names. Complete observations can support a local relation match or mismatch. Missing fields remain UNKNOWN. Worker lifecycle fields do not supply operation authorization, freshness, binding or effect counts. A match is conditional on the caller's operation-domain interpretation and source evidence. It is not global reachability, a whole-trace refinement proof, source authentication or production acceptance.

A missing or invalid domain mapping is not an implementation counterexample. A complete synthetic projection with a disabled model action is a named counterexample to that proposed local relation. The tests include valid retry, unreconciled retry, UNKNOWN-to-RECONCILING, missing fields and the EXECUTING-to-FAILED gap.

## Resume lineage and attempts

Use actual predecessor/current spawn records, raw Native bytes and an optional snapshot. The explicit resume predecessor, raw SHA and Native thread must agree. Shared Native thread identity is compatible with a documented resume; it is not a unique attempt identifier. Preserve the real attempt IDs and statuses from the snapshot, and never invent them by parsing a Session name.

The source spawn stage index may use a decimal string while lifecycle/snapshot stage indices use integers. Record both source encodings and the named conversion. Reject booleans, malformed strings and ambiguous joins. Do not silently compare arbitrary strings as stages.

A Native `turn.completed` record is not a process exit code or successful task acceptance. A failed task can have a completed Native turn. Keep null exits, pending dispatch effects and conflicting records unchanged. Matching resume lineage supplies no Provider no-effect proof.

## Run selected evidence

Run `PYTHONPATH=src python3 -m formal_verification_lab.retry_conformance --help` for the explicit file selections. The required lifecycle file is inspected independently when optional lineage or operation-state projections are missing. The CLI writes JSON to stdout and reads no implicit private store. Its input paths are caller-selected local reads, not a hostile-file confinement interface.

Save the command, model/mapping source digests, input bytes/digests, actual stdout/stderr/exit and independent expected observations outside the public repository. Freeze expected observations before reading checker output. Keep earlier partial captures and failed checks; a later complete retained record is a new selected observation, not permission to rewrite an old UNKNOWN result.

Run `PYTHONPATH=src python3 -m pytest -q` for public software controls. The controls and actual trace results answer different questions. Historical trace reuse starts no new Native worker, while replaying selected files is not a fresh runtime experiment. Missing operation reconciliation limits the corresponding model conclusion and does not block independent workflow/lineage inspection or Session engineering.
