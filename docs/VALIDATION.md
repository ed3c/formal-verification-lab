# Local execution receipt — 2026-10-24

## Source-only / synthetic controls
- Environment: CPython 3.13.5; Pytest 9.0.2.
- Command: `PYTHONPATH=src python3 -m pytest -q tests`
- Result: 29 passed, 1 skipped (optional Hypothesis dependency unavailable).
- Command: `PYTHONPATH=src python3 -m formal_verification_lab.cli controls fixtures/cases`
- Result: PASS, 23 of 23 synthetic cases matched frozen expectations.
- `python3 -m compileall -q src`: success.

## NOT_RUN and blockers
- CrossHair: NOT_RUN, package unavailable and package-index network unavailable.
- icontract: NOT_RUN, package unavailable.
- Hypothesis randomized tests: NOT_RUN, dependency unavailable; no randomized sample evidence.
- Quint parser/typechecker: NOT_RUN, no `quint` command installed.
- Apalache bounded checks: NOT_RUN, requires Quint and checker backend.
- Inductive invariants: NOT_RUN.
- Native Soodles readback / real provider conformance: NOT_RUN, deliberately not accessed by Phase 1.
- Blind baseline/treatment and Formal Verification RL: NOT_RUN.
- GitHub independent remote repo and PR: NOT_CREATED; connected GitHub interface does not expose a repository-creation action.

## Evidentiary scope
Hash pins inside synthetic manifests prove byte consistency relative to their own manifest, not origin authentication. The synthetic expected outputs were authored as planted controls, not independently collected native outcomes. No production state or source was changed.

## 2026-10-24 explicit-state preflight (Python translation)

- `PYTHONPATH=src python3 -m pytest -q`: **35 passed, 1 skipped** (Hypothesis unavailable).
- `PYTHONPATH=src python3 -m formal_verification_lab.model_explore --max-depth 12`: **14 states / 31 explored edges**, no safety violations in the translated model, a terminal reachability witness and deliberately unsafe canary counterexample.
- `UNKNOWN → RECONCILING` abstract liveness gap remains; no real Soodles runtime defect inferred.
- `npm view @informalsystems/quint version`: DNS `EAI_AGAIN`; Quint/Apalache unavailable. CrossHair/icontract/Hypothesis not installed. All native/checker claims are `NOT_RUN`.
- Private Soodles provider data were NOT ingested, replayed or published.
