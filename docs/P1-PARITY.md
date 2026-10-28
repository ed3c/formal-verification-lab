# P1 finite reachable named-action parity

P1 compares the saturated reachable graph from `State()` with the actions parsed from `specs/operation.qnt`. The result applies only to the recorded source bytes, Quint 0.32.0, and the finite deterministic state domain below.

## What the check does

`scripts/parity.py` performs these checks in one invocation:

1. It enumerates `successors` until no new `State` exists. A 1,000-state cap fails the invocation instead of accepting a partial graph. The saved graph contains every state field and every named edge, including self loops.
2. It runs `quint parse` on `specs/operation.qnt`. It requires `step` to be an `actionAny` registry of unique action names. It accepts only the observed deterministic AST forms for `init` and those actions. The only Python-to-Quint name alias is `fail` to `markFailed`.
3. It generates one exact `init` check. It also generates one check for every parsed action at every reachable Python state. An enabled action must produce the full expected record. A disabled action must fail.
4. It runs the generated tests with Quint's TypeScript backend, one sample, and seed `20261024`. It checks the exact passed test names and count.
5. It generates a separate negative control. The control gives `publish` the wrong expected `effectCount`. Acceptance requires exit 1, the exact test name, and Quint diagnostic `QNT508: Expect condition does not hold true`. An action-disabled, runtime, or tool error cannot satisfy the control.
6. It records SHA-256 digests before and after the invocation for the Python model, the Quint spec, the generator, and the Quint package. Any drift fails the invocation.

The parser AST, graph, generated Quint modules, commands, raw stdout and stderr, exits, diagnostic record, results, and digest manifest are written to the caller's external evidence directory. The script rejects an evidence directory inside the repository and does not overwrite an existing directory.

## Reproduce the check

Use an empty path outside the repository:

```sh
python3 scripts/parity.py \
  --toolchain <quint-toolchain> \
  --evidence-dir <new-external-evidence-dir>
```

The pinned invocation ran Quint 0.32.0 with these test flags:

```text
--backend=typescript --max-samples=1 --seed=20261024
```

## Observed result

The fresh Session invocation exited 0 and recorded `BOUNDED_PASS` for `FINITE_REACHABLE_NAMED_ACTION_PARITY`.

| Observation | Result |
|---|---:|
| Reachable states | 14 |
| Python named edges | 31 |
| Self-loop edges | 16 |
| Parsed `step` actions | 13 |
| State-action checks | 182 |
| Exact initial-state checks | 1 |
| Quint positive tests | 183 passed, 0 failed, 0 ignored |
| Deliberate publish mismatch | exit 1; `deliberatePublishMismatchTest`; `QNT508: Expect condition does not hold true` |
| Input digests | unchanged before and after |
| Repository Python suite | 58 passed |

The observed input SHA-256 values were:

| Input | SHA-256 |
|---|---|
| `src/formal_verification_lab/model_explore.py` | `92875cd7d1a77632a19146fa34b8eb4dca05e827ee4b11f458bb03163818af12` |
| `specs/operation.qnt` | `75b0e841556577ca911a1a8fdea363041a5f29531c0942d33faca28399c39a59` |
| `scripts/parity.py` | `e93f8c9b6a239bf8404bb6ecff3fa843c6f2062b18c75d42aa5e2ea939675ebd` |
| Quint `package.json` | `08355263da6adb7d5578c2cddb9b0e9634d79cfb2f73e4679888031067c332a4` |

## Controls and claim boundary

`P1-positive-reachable-matrix` is the positive control. All 183 generated Quint tests pass.

`P1-negative-publish-target` is the negative control. The generated expectation changes only `effectCount` from 1 to 0 after an enabled `publish`. Quint reports `QNT508: Expect condition does not hold true`. The external evidence retains the complete diagnostic in `runs/negative/stdout.txt`, the command and exit in `runs/negative/result.json`, and the validated fields in `negative-diagnostic.json`.

`P1-unknown-incomplete-input` is the unknown control. A graph cap, unsupported AST form, parser failure, test tool failure, count mismatch, or input drift produces `NOT_VERIFIED`. None of those conditions can produce `BOUNDED_PASS`.

This result does not establish all-state equivalence. It does not establish liveness, an inductive safety proof, Native Soodles refinement, external authorization, provider effects, or production acceptance. The current model removes unsupported `resumeReconciled`; the fresh Session parity run applies to that changed model. The earlier C1 run of 197 tests on 14 actions is historical.
