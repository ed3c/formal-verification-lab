# Phase 2: explicit-state preflight (not Quint / Apalache)

## Purpose and measurement

The `model_explore.py` enumerator hand-translates `specs/operation.qnt` into an
isolated Python finite-state model and checks the three existing safety
predicates. It is an **engineering preflight** for non-vacuity and counterexample
presentation, **not a proof of the Quint specification**, not a CrossHair result,
and not a proof of any Soodles production behavior. The translation itself is
an unverified assumption; it must be reviewed against the Quint source.

Command (no additional third-party packages):

```sh
PYTHONPATH=src python3 -m formal_verification_lab.model_explore --max-depth 12
```

## Observed on 2026-10-24

- `status=BOUNDED_PASS` for the Python finite-state abstraction: 14 unique states,
  31 explored edges, 12-action upper bound, and no remaining unvisited states at
  that bound (`bound_reached=false`). These values depend on this translation.
- Terminal non-vacuity witness: `authorize → bindEvidence → advance → publish →
  observeEffect → terminal`.
- Deliberately unsafe canary counterexample: `init → publishUnchecked` produces
  an effect with no authorization **in the Python canary translation**.
- Incomplete liveness modelling: `markUnknown → reconcileNoEffect → retry`
  reaches `RECONCILING`, for which the abstract model has no advancing transition.
  This is a **model coverage gap**, not evidence that the real runtime is stuck.
- Quint, Apalache, CrossHair, Hypothesis: `NOT_RUN` here; no extra proof claim.

The actual execution report is in the separate generated file
`fvl-explicit-state-report.json` and can be regenerated. The report is not
customer evidence, native observation or signed attestation.

## Exact requirements for formal verification

Before reporting `FVL-MODEL=BOUNDED_PASS` from Quint/Apalache, run the actual
checker with a pinned version, command, max steps and captured stdout/stderr,
assert that the intentionally unsafe canary produces a real counterexample, and
produce a reachable publish/terminal witness. A nonzero exit code from the
canary without counterexample evidence is **UNKNOWN**.

Before claiming a `PROVED` invariant, separately verify an inductive step for
specified invariants with documented state assumptions. Bounded traversal and
Python enumeration do not meet this requirement. The Session reviews source mappings and relevant external readback facts for each runtime claim; they are not a blanket prerequisite for partial evaluation.

## Historical Poteto follow-up (superseded by P2)

The abstract `RECONCILING` dead-end now has a *proposed* `resumeReconciled`
transition in both the hand-translated Python model and Quint source. It is
conditional on already-bound authority/evidence. This is an abstract
owner-confirmed continuation assumption, not evidence that Soodles implements
it. Re-run and source-check before any runtime claim. Current Python preflight:
14 states, 32 transitions, 37 tests passed, 1 optional skipped. Liveness is
still NOT_ESTABLISHED because fairness and real owner behavior are unverified.
See `docs/POTETO-2026-10-24.md` for remaining requirements and gates.

## Current source correction

P2 removed the unsupported same-operation continuation. The current graph has 14 states and 31 edges; fresh Quint parity passed 183 checks over 13 named actions. Terminal and RECONCILING are reachable, but the latter has no supported phase-changing continuation. The no-effect EXECUTING branch also lacks completion. Liveness remains NOT_ESTABLISHED. These restrictions do not demonstrate an improvement in Soodles production safety.
