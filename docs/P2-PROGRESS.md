# P2 source fidelity and progress limits

P2 removes the unsupported same-operation `resumeReconciled` action from both abstract models. The source review did not find an original Owner transition that supports `RECONCILING -> CLAIMED` for the same operation. Restricting the model does not change Production behavior and does not establish a safety improvement.

## Current finite observations

The current Python graph saturates at depth 12 with 14 states and 31 named edges. `bound_reached` is false. The current Quint to Python parity run parsed 13 actions and passed 183 generated tests. The deliberate wrong `publish` target exited 1 with `QNT508: Expect condition does not hold true`.

The terminal witness remains:

```text
authorize -> bindEvidence -> advance -> publish -> observeEffect -> terminal
```

The observed reconciliation witness is:

```text
authorize -> bindEvidence -> advance -> markUnknown -> reconcileNoEffect -> retry
```

The last transition reaches `RECONCILING`. The explorer does not append a fabricated continuation.

## Named controls

`P2-positive-terminal-witness` is the positive control. It proves that the current finite graph still reaches a supported terminal state with one observed effect.

`P2-negative-unsupported-resume` is the negative control. Neither model declares `resumeReconciled`. A focused test also rejects any phase-changing successor from a `RECONCILING` state. The parity negative control independently proves that a false expected target produces the required Quint diagnostic.

`P2-unknown-progress` is the unknown control. Two paths lack a source-supported progress rule:

- `UNKNOWN -> reconcileNoEffect -> retry` reaches `RECONCILING`. No declared action changes its phase.
- `advanceToExecute` can reach `EXECUTING` with `effectCount == 0`. No declared action then observes an effect or changes the phase.

These are model coverage and liveness gaps. They do not prove that a real runtime is stuck. They also do not authorize a retry, resume, advance, or terminal transition.

## Reproduce the observations

```sh
PYTHONPATH=src python3 -m formal_verification_lab.model_explore --max-depth 12
PYTHONPATH=src python3 -m pytest -q tests/test_model_explore.py tests/test_parity.py
python3 scripts/parity.py --toolchain <quint-toolchain> --evidence-dir <new-external-evidence-dir>
```

The result is finite and source-specific. Liveness remains `NOT_ESTABLISHED`. Native refinement, external authorization, Provider effect truth, and Production acceptance remain `NOT_RUN`.
