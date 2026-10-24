# Thinking V2 / conditional V3 × Ambitious — decision record

## Decisions from the task owner
FVL-01 C: independent repository; independently validate contracts before proposing changes to another system.
FVL-02 A: shadow only. No production gate.
FVL-03 B: Publish, Resume, Advance, Retry, Terminal.
FVL-04 B: local contracts + inductive invariant attempts + model ↔ trace conformance.
FVL-05 B: use relevant producer/provider readback facts for claims that depend on them; missing readback does not block unrelated engineering or partial evaluation.
FVL-06 C: independent controls + blind baseline/treatment + cost per verified task.
FVL-07 C: frozen bundles first, later strictly read-only provider adapter.
FVL-08 C: public MIT core, PRIVATE evidence store. No private evidence in Git history.

## Final adversarial review
- First causal breakpoint: a producer-supplied Boolean is not the underlying authorization fact.
- Concurrency: local idempotency does not imply external at-most-once effects.
- Proof weakness: trivial/vacuous invariants and weakened specifications can pass. Canary and liveness/reachability review required.
- Independence: hash-matching a self-contained bundle detects accidental drift but does not authenticate a hostile producer.
- Read-only is both capability restriction and source review. Phase 1 deliberately has no network/provider connector.
- Models and observations are versioned separately; do not reinterpret historical results as fresh.

## Unique source-bound minimal Prompt Delta
Preserve Goal/Measurement/Effort and the explicitly authorized write boundaries.
Consume only versioned, read-only evidence. Missing facts remain UNKNOWN. Preserve contradictory records and report only the conclusions their scoped comparisons support.
Model the five named operations; retain counterexamples, exact scope and assumptions.
Never equate model check PASS, local tests PASS and original native acceptance.
Use frozen independent positive/negative controls and paired cost-aware comparisons before claiming gain.
Keep all private Soodles data, credentials, runs and raw traces outside the public repository.
Stop only dependent operation when evidence/permission is missing; continue independent verification.

## Original source anchors (read 2026-10-24)
- Soodles-private://main/AGENTS.md
- Soodles-private://main/.agents/skills/thinking-router/SKILL.md
- Soodles-private://main/.agents/skills/ambitious-route/SKILL.md
- Soodles-private://main/.agents/skills/verify-soodles/SKILL.md
- Soodles-private://main/.agents/skills/test-manager/SKILL.md
- Soodles-private://main/contracts/state-machine-change.md
- Soodles-private://main/contracts/test-manager-tools.md

Historical prototype scope: no production source/effect mutation was requested in that original run. The current authorized engineering scope below supersedes that scope statement.

## Current Session engineering clarification

The Session is the engineering judgment subject. Source-producer identity and record ownership describe facts, not a requirement to return to an original Session or obtain an external mapping approval. The Session may locate repositories/workspaces, choose readable evidence, review source mappings, evaluate supported properties, and implement authorized source/test changes and prepare Draft PRs.

Requirements for a particular conclusion remain concrete. A grant check needs actual grant subject/scope/order data. A per-operation at-most-once pass needs the matching operation/key/readback order and complete relevant effect scope. A missing fact remains UNKNOWN; a mismatched fact is retained rather than repaired by invented values. These conditions do not require a complete private bundle before lookup or independent checks.

The current user-authorized engineering scope includes Soodles, Noodle and Lab source/tests and Draft PRs. It forbids switching the active runtime, merging, or modifying #448, #450 or escrow. The Lab evaluator component itself remains read-only: it does not mutate target repositories, dispatch tasks or grant production effects. The Session engineering role and the evaluator capability boundary are distinct.
