# Abstract local ref CAS checks

The new CAS specification has an eight-step **BOUNDED_PASS**, two planted counterexamples and three reachability witnesses. These are actual Quint/Apalache results for an abstract model. The real fixture cases in [the acquisition design](LOCAL-REF-CAS.md) remain NOT_RUN, and effect-retry conformance remains UNKNOWN.

The same unchanged model now also has [inductive invariant checks](LOCAL-REF-CAS-INDUCTION.md). Initialization, preservation and safety implication passed; stage-specific negative controls verify all three obligations. The bounded results below retain their original scope and evidence.

## Scope and assumptions

`specs/local_ref_cas.qnt` models one fixed ref and a separate unchanged ref. OIDs 0, 1 and 2 are abstract symbols. The initial expected-old is either 0 (matching) or 2 (mismatched). The model allows one offer, one trusted atomic Git CAS, completion receipt delivery or loss, and one readback. It has no retry, native operation key, authorization grant or full Soodles lifecycle.

An offered `STARTED` record precedes the hidden Git action. It does not mean that a child process started. A hidden update may finish while the receipt remains unknown. Readback supports no-effect reconciliation only for a known mismatch with zero target-ref effects. The other ref stays unchanged under the single-writer assumption.

The model assumes trusted CAS semantics, truthful-or-lost receipts, truthful readback, prebuilt valid objects, no hooks and no outside writer. It excludes forged receipts, pre-spawn errors, in-flight timeouts, arbitrary hooks, object-store writes and global effects. At-most-one offer is part of this model, not a native deduplication proof. No `OperationProtocol` phase or missing key is manufactured.

## Actual checks

The fixed tools are Quint 0.32.0, Apalache 0.56.1 build 70cdaf4, OpenJDK 21.0.2 and Node 22.17.1. Queries run serially with a 180-second process timeout and `JVM_ARGS=-Xmx512m`. The heap limit is not a total RSS limit.

| Query | Bound | Exit | Structured result | Checked evidence |
|---|---:|---:|---|---|
| `LocalRefCAS.safety` | 8 | 0 | ok, backend NoError | Eight safety predicates hold within the bound |
| Expected-old bypass canary | 2 | 1 | violation | Two transitions update the ref despite a mismatched expected-old |
| False-reconciliation canary | 4 | 1 | violation | Four transitions mark UNKNOWN with effectCount=1 as reconciled no-effect |
| Rejection reachable | 8 | 1 | violation of the negated query | Four transitions reach a reconciled mismatch with effectCount=0 |
| Positive reachable | 8 | 1 | violation of the negated query | Four transitions reach a confirmed matching update with effectCount=1 |
| UNKNOWN with effect reachable | 8 | 1 | violation of the negated query | Three transitions reach UNKNOWN with effectCount=1 and noEffectReconciled=false |

Both model files passed type/effect checking. All six verification results were checked against process exit, structured status, backend version and unchanged model bytes. Concrete ITF fields were checked for each witness. A nonzero exit alone was never accepted as a counterexample. The reachability queries deliberately assert that the target cannot be reached; their violations are witnesses, not safety defects.

The [portable evidence](evidence/local-ref-cas.json) contains the exact model hashes and symbolic states from those checker traces. It excludes private paths, process metadata and Native records. It is a public derived model artifact, not authenticated producer evidence. Raw commands, logs, SMT/ITF files, errors and costs remain in the external evidence store.

The first wrapper incorrectly supplied `--main` to `typecheck`; the CLI rejected that argument before checking the model. A later wrapper expected a PID on stdout even though `--out` suppresses console output. Both failures and runner versions are retained. The successful typechecks and safety result were validated and reused without rerunning them. Cleanup readbacks found each chosen endpoint bindable and no Apalache server command matching its port. Backend PIDs were unavailable in the suppressed output and were not invented.

The queries recorded above are bounded model checks. Their separate inductive extension is linked above. Neither establishes liveness/fairness, verification of Git's implementation or runtime refinement. The existing operation protocol was unchanged and was not rerun.

## Reproduce with the fixed tools

Use a new evidence directory and a fresh available localhost endpoint for each query. Keep output and errors even when a command exits nonzero. The existing P3 runner provides the receipt format and command timeout; do not change its original query list to overwrite historical runs.

```sh
QUINT_HOME="$FVL_TOOLCHAIN/quint-home" "$FVL_TOOLCHAIN/node_modules/.bin/quint" typecheck specs/local_ref_cas.qnt
QUINT_HOME="$FVL_TOOLCHAIN/quint-home" "$FVL_TOOLCHAIN/node_modules/.bin/quint" typecheck specs/local_ref_cas_checks.qnt
```

The verify query selections are below. Each command also needs `--backend=apalache --apalache-version=0.56.1`, its own `--server-endpoint`, `--out` and `--out-itf` destinations. Preserve `JVM_ARGS=-Xmx512m` and the 180-second process timeout when reproducing this run; the backend wrapper otherwise defaults to a larger heap.

| File | Main | Invariant | Step | Max steps |
|---|---|---|---|---:|
| `specs/local_ref_cas.qnt` | `LocalRefCAS` | `safety` | `step` | 8 |
| `specs/local_ref_cas_checks.qnt` | `LocalRefCASCanary` | `updateRequiresMatch` | `unsafeStep` | 2 |
| `specs/local_ref_cas_checks.qnt` | `LocalRefCASFalseReconciliationCanary` | `unknownIsNotNoEffect` | `unsafeStep` | 4 |
| `specs/local_ref_cas_checks.qnt` | `LocalRefCASReachability` | `rejectionUnreachable` | `step` | 8 |
| `specs/local_ref_cas_checks.qnt` | `LocalRefCASReachability` | `positiveUnreachable` | `step` | 8 |
| `specs/local_ref_cas_checks.qnt` | `LocalRefCASReachability` | `unknownEffectUnreachable` | `step` | 8 |

Native acquisition still requires its original admission. Do not execute Git or use another carrier to replace the deferred trace. After this source update, read back the old prepared request and its frozen sources before using it; a previous preparation does not establish freshness for a newer head.
