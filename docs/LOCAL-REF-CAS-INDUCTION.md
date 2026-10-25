# CAS inductive invariant checks

The unchanged CAS model now has a machine-checked inductive invariant. The checker verified initialization, preservation by the original step, and implication of all eight safety predicates. This extends the earlier eight-step bounded result to arbitrary-length executions of this fixed abstract model, including terminal stutter. It is not Native conformance or a proof of Git's implementation.

## Candidate invariant

`specs/local_ref_cas_induction.qnt` imports `LocalRefCAS` without replacing its `init`, `step` or `safety`. It defines `IndInv = s.in(consistentStates)`. The set has 14 complete records: expected-old 0 or 2, each with seven phase-consistent shapes. The slot is a pure constructor parameter, not a new protocol state variable.

| Slot | Shape | Receipt | Git finished | Readback |
|---:|---|---|---|---|
| 0 | Initial | NONE | false | absent |
| 1 | Pre-spawn offer | STARTED | false | absent |
| 2 | Hidden CAS completed | STARTED | true | absent |
| 3 | Known completion | COMPLETED_OK or COMPLETED_REJECTED | true | absent |
| 4 | Lost completion | UNKNOWN | true | absent |
| 5 | Known completion read back | Same known receipt | true | present |
| 6 | Unknown completion read back | UNKNOWN | true | present |

The constructor independently specifies all 14 fields. It does not call the transition relation, a reachability search or safety to generate candidates. Before=0, target=1 and otherRef=2 retain their existing symbolic meaning. Matching completion has ref=1 and effectCount=1; mismatch has ref=0 and effectCount=0. UNKNOWN with an effect remains in the invariant, before and after readback, without supporting no-effect reconciliation.

`IndInv` does not conjoin `safety`. The target is separately defined as `proofTarget = safety and candidateCountIs14`. The third obligation therefore checks the original safety predicates and the cardinality assertion, rather than eliminating safety from a conjunction already assumed in I.

The candidate may exclude unreachable, well-typed valuations. It must still include every original initial state and be closed under every original step from any candidate state. No checker state constraint, sampled prefix, restricted step or changed initialization supplies this closure.

## Actual proof obligations

Fixed Quint 0.32.0 implements the inductive flag using three Apalache 0.56.1 build 70cdaf4 configurations. The actual backend log confirms the following results.

| Obligation | Initialization predicate | Step | Target | Depth | Result |
|---|---|---|---|---:|---|
| Init implies I | Original `q::init` | Original `q::step` | `q::inductiveInv` | 0 | NoError |
| I and Step imply I-prime | `q::inductiveInv` | Original `q::step` | `q::inductiveInv` | 1 | NoError |
| I implies safety and cardinality | `q::inductiveInv` | Original `q::step` | `q::inv` | 0 | NoError |

Depth one in the middle row starts from any state admitted by I. It is not a one-step run from the original initial states. These three obligations support an inductive claim without the previous eight-step execution-depth limit. The initial OID symbols, single offer and all model assumptions remain fixed.

## Controls for each obligation

The harness provides three deliberately wrong candidate predicates. They all use the unchanged original relation.

| Candidate | Deliberate defect | Observed backend outcomes | Concrete counterexample |
|---|---|---|---|
| `MissingInitialInv` | Omits the expected=2 initial state | Error at initialization | Zero transitions, original initial state with expected=2 |
| `WeakInv` | Adds a safety-satisfying offered state with effectCount=1 but gitDone=false | NoError, then Error at preservation | One transition of normal completeGit increments count from 1 to 2 |
| `BadProjectionInv` | Adds a terminal UNKNOWN state with effectCount=1 and noEffectReconciled=true | NoError, NoError, then Error at implication | Zero transitions, the added unsafe candidate valuation |

The weak and bad-projection prestates are deliberately admitted by those candidate invariants. They are not claimed reachable from the original Init. They demonstrate failed proof obligations, not production defects. BadProjectionInv's extra state can only stutter, which is why closure can pass while safety implication fails.

Every nonzero result was checked against structured violation status, its expected failing obligation, and concrete ITF fields. The [portable abstract evidence](evidence/local-ref-cas-induction.json) contains source hashes, configuration summaries and negative-control states. It has no Native records, private paths or runtime identities.

## Reproduce and preserve

Use the existing fixed toolchain and a fresh evidence directory. Typecheck accepts the input file without `--main`. For verification, preserve the following selection and use a fresh available endpoint for each candidate.

```text
quint verify specs/local_ref_cas_induction.qnt
  --main=LocalRefCASInduction --init=init --step=step
  --inductive-invariant=IndInv --invariant=proofTarget
  --backend=apalache --apalache-version=0.56.1
  --server-endpoint=<fresh endpoint> --out=<result> --out-itf=<trace>
```

Retain `QUINT_HOME` for the pinned backend, `JVM_ARGS=-Xmx512m` and the 180-second process timeout. The heap bound is not total RSS. Replace only the inductive candidate with the three names above for the negative controls. Do not rerun unchanged bounded queries just to repair a result reader.

The first result reader sorted individual log lines. Configuration lines with identical millisecond timestamps then appeared out of physical order, causing a parser assertion after the successful proof. The raw result and runner version were preserved. The corrected reader retains log-file line order, verifies all three configurations, and reuses the successful proof; only the outstanding negative controls were executed afterward. The harness, invariants and model bytes did not change to obtain PASS.

Selected endpoint cleanup readbacks showed bindable ports and no matching Apalache server `--port` command. Console suppression left backend PID unobserved; no original-PID custody or global process-absence claim is made.

## Trust and continuation limits

This claim trusts the fixed Quint translation, Apalache, Z3 and the declared model semantics. No independent proof certificate was produced. The model still assumes trusted atomic CAS, truthful-or-lost completion receipts, truthful readback, one writer, no hooks and one offer. It excludes forged receipts, in-flight timeouts, arbitrary failures, concurrent writers and global effects. Liveness and fairness are not established.

The real fixture cases remain NOT_RUN and effect-retry conformance remains UNKNOWN. Worker credit was zero when proof work began. The proof used authorized foreground offline checking, without a new Host or real CAS. Any subsequent admitted Noodle source review has its own receipts and does not establish effect conformance.

The original bounded evidence stays historical. Prepared Native requests retain their original source freezes and must be read back before continuation after a source update. Follow the [reader handoff](READER-HANDOFF.md); no original Owner, original Session or complete private bundle is required for Session engineering judgment.
