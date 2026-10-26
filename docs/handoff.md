# Formal verification / test value — conversation handoff

As of 2026-10-26. This is the entry for a new conversation, not an acceptance gate,
an execution request or a claim that the whole Parent Goal is complete.
Q70 selects this Lab document as the committed main handoff; Q71 selects a new
conversation that first reads back and reconstructs the task. No automatic Native
resume, deployment or merge follows.

## Task definition and intended outcome

The Parent Goal is to lower Soodles Test Manager's **Cost per Verified Change**:
remove unnecessary selection and repeated verification while retaining behavioral
contracts, system invariants, independent oracles and necessary exact-head acceptance.
The question is whether AI-generated tests protect requirements or merely endorse the
current implementation. This is not a ban on unit tests or a test-framework rewrite.

The complete workstream also includes:

- An independent, decoupled formal-verification Lab: P1–P8, declared model assumptions,
  canary counterexamples, reachability, bounded and inductive checking, partial evidence,
  actual implementation-to-model mapping and honest cost reporting.
- Session-owned engineering judgment across Soodles, Noodle and Lab. New Sessions can
  discover and select continuation from a repository/workspace without an original
  Owner/Session qualification, external mapping approval or complete private bundle.
- Real Native/recovery and blind-reader experiments, retained failures and corrections;
  model proofs, source tests, runtime observations and comparative benefit stay separate.
- A universal formal-route in Lab, a thin Soodles entry and actual original-tool wiring;
  test-value adjudication, classification, finite source mapping and route behavior eval.
- Local source/test improvements, versioned evidence and handoff. Remote delivery and
  active-runtime acceptance are distinct from these local results.

The next conversation's first turn is **readback and task reconstruction only**.
After that, the primary unfinished engineering line is specific high-cost selection /
fixture duplication and sufficient-oracle evidence for the same required outcome.
Full retry refinement and whole CPVC gain remain unestablished; neither is a new gate
for independent work or a reason to repeat an unchanged experiment.

## Settled decisions and boundaries — do not re-ask

- Q44–Q50 retain original Test Manager, P-class/CLI owners and the #443 cost-work line;
  no new Manager, scheduler or global gate. Impact candidates are not automatically
  proof of necessity. Explicit diagnostics do not clear unrelated canonical refusals.
- Q51–Q52 allow evidence-backed rewriting/merging/deletion and include proven external
  compatibility dependencies as contracts. Internal structure is not automatically a
  contract. Preserve unique faults and verified alternatives; time/count alone is not
  deletion evidence. An expected-result change needs independent contract evidence.
- Q53–Q56: Lab is the universal method/interaction source; Soodles is a thin caller.
  Other repositories can connect through the same `.md` contracts and their own tools.
  Required route eval checks necessary behavior; no comparative improvement is claimed
  without a separate valid baseline/treatment. The initial retention pilot uses CLI controls.
- Q57–Q59: every original required/on-demand control received a final decision; UNKNOWN
  alone was not completion. Historical-only research requirements/evidence stay historical
  when their conditions are met; current consumer guards remain. The old #157 six-real-run
  no-waiver obligation was not retroactively replaced by synthetic controls.
- Q63–Q69: the named factory-route means FactoryWeaver's **original** unified
  `skills/factoryweaver/SKILL.md` and existing route, not a new skill. The caller reference
  is `contracts/factoryweaver-route-reference.md`, pinned to revision
  `bc8d7815ed4b3446bb3eacb6e3b50675f24b6f32`. FactoryWeaver/NeoWeaver are read-only.
  Full relevant route/Manager definitions live in `.md` plus original mechanical code;
  P-class entries retain reasoning methods. Hook/Cron/Native are conditional, not a chain.
- Precision **and** recall must each be strictly >99% for one frozen, independently
  checked named population. UNKNOWN/missing rows reduce recall. The historical finite
  location/registration result does not prove all inputs, test value, dynamic coverage,
  Native correctness or accuracy at a new HEAD.
- Session owns judgment. Retain data consistency, explicit selection, mutual exclusion,
  deduplication, exact source/effect subjects, real permission and unknown-effect readback.
  Identity fields describe facts/responsibility; they do not require finding a former actor.
- Local first. No automatic remote CI, source push, active-version switch or merge;
  do not change #448, #450 or escrow. Do not weaken tests, bypass hooks or invent evidence.
  Necessary Native validation was authorized only through normal original resource
  governance; zero credit does not allow another Host, carrier or ordinary subprocess.
  The two latest contexts are migration-detached: retain pending work, never auto-resume.

## Current source and evidence entry

The new conversation receives a **private RESUME.json locator** separately. It contains
actual local paths, source refs and the commit/readback receipt for this document.
Do not commit that locator, raw traces, credentials, private caller code or local identity
metadata into this public Lab. `FVL_EVIDENCE_ROOT` below is a locator placeholder, not
an assumed environment variable or an installed service.

| Source | Selected snapshot before this document's commit | Meaning |
| --- | --- | --- |
| Soodles | `aa87f279db0367a132e7cdbe059138e61a709694` | Latest local caller source; 298 scoped unit observations bind the checked bytes |
| Lab | `ab74317d23086079d372d9ea54ee3ba36839981d` | Latest core/route source before this handoff-only commit; read actual Git HEAD |
| Noodle | `b9f1a3c9ff15a9e9fdfad9e91159ae34eb578521` | Historical Session-discovery source delivery, not the active Host version |

Current local workspaces are isolated Git worktrees; keep primary trees on main and do
not switch them. Inspect actual status before writing. A later handoff commit does not
make an older test receipt fresh exact-head acceptance, even when tested bytes agree.

The historical three-repo Session delivery (#451 / #123 / Lab #1) and its provider
checks belong to their own frozen heads. The Test Manager cost line is #443. Do not
mix those PRs, assume a current Draft/CI state from an old report, or claim that a local
commit is already in a remote PR. Read the provider only when a concrete delivery
question requires it. This handoff performs no remote update.

## Completed work and proof ceilings

Read the linked source definitions and private case reports; do not reproduce their raw
results or silently replace their historical status.

| Area | Current conclusion | Primary reference |
| --- | --- | --- |
| Session discovery/recovery | Three source/test/Draft deliveries; no original-actor qualification, with original consistency guards | Private `session-engineering/REPORT.md`; [decoupling](DECOUPLING.md) |
| P1–P4 | Finite parity, corrected operation model, bounded safety / typed induction, pure-contract controls with counterexamples | [P1–P8](P1-P8-STATUS.md), [P3](C0-P3.md), [P4](P4-CONTRACTS.md) |
| P5–P8 | Partial evidence, explicit mappings/readers, scoped conformance and independent source delivery; not full Native refinement or economic gain | [reader](READER-HANDOFF.md), [partial evidence](PARTIAL-EVIDENCE.md), [retry](RETRY-CONFORMANCE.md) |
| Blind/recovery trials | Old 8/8 timeouts and four method leaks retained; corrected A/B/C batches kept separately, final C eight valid deliveries and four fixed pairs | Private `native-verification/REPORT.md`, `native-round2/REPORT.md`; [protocol](NATIVE-READBACK.md) |
| CAS model | Eight-step safety, two canaries, three reachability witnesses; 14-record invariant proves Init→I, I∧Step→I′, I→safety under fixed assumptions | [bounded](LOCAL-REF-CAS-FORMAL.md), [induction](LOCAL-REF-CAS-INDUCTION.md) |
| Actual CAS acquisition | First collector lost raw bytes and remains UNKNOWN; successor's two distinct fixtures support scoped mismatch/no-ref-update and matching A→B observations | [actual acquisition](LOCAL-REF-CAS-NATIVE.md); private `native-effect-continuation-20261026` |
| Full test-value adjudication | Original 2309 unit IDs: 2100 keep /181 rewrite /9 merge /19 remove; 7 physical families retained on demand | Caller `docs/test-retention/final-controls-20261025.jsonl`; private `test-retention-final` |
| Current caller population | 2281 methods /116 source modules plus7 physical families; four reviewed method updates now yield2096 unit keep /185 with rewrites | Caller `docs/test-retention/catalog.md` and `catalog-map.json`; private `selection-scope-continuation-20261026` |
| Universal formal-route | Lab SSOT, Soodles thin entry and original tools; finite replacement/retention interface and required behavior eval | [method](FORMAL-ROUTE.md), [retention](TEST-RETENTION-INTERACTION.md), [interaction](ROUTE-INTERACTION.md) |
| Classification / source mapping | Method/environment/module/demand dimensions separated; fixed finite mapping result, not necessity or new-head correctness | [catalog](TEST-CATALOG.md), [mapping](SOURCE-MAPPING.md); private `test-taxonomy-20261025` |
| Local cost work | Evidence-backed high-cost fixture simplifications and a historical ABBA comparison; no whole-CPVC causal result | Private `test-retention-next`, `local-cost-continuation-20261025` |
| Latest caller correction | Exact catalog observation path registered; unknown neighbor still refuses. Local source-derived17/17 then accumulated298/298,2039 source bytes unchanged | [latest source handoff](HANDOFF-TEST-CATALOG.md); private `selection-scope-continuation-20261026` |

P2 liveness/progress, fairness, full Git correctness and full implementation refinement
were not established by these model results. A completed Native turn is not task
acceptance. Final blind C's four-pair observation is conditional on its actual supplied
inputs; B and C interventions differ and their denominators must not be pooled.
Route eval's matched reported fields are consumer-report scope, not complete internal
or Provider action capture, global accuracy or a new mandatory eval on every change.

**Status precedence:** old proof/reader documents contain design-time NOT_RUN snapshots.
For actual acquisition, use the later acquisition report and frozen raw receipts. Do not
rewrite old UNKNOWN/failures or rerun experiments merely to make prose agree. The current
source classification query is CATALOG_ONLY / retention_decision=NOT_EVALUATED; labels
and valid schema do not independently prove value or necessity.

## Evidence map and costs

Private case paths below are under `FVL_EVIDENCE_ROOT/outputs/`. Select only the records
needed for the current claim; complete private bundles are not a discovery prerequisite.

- `session-engineering`: three-repo source/Draft/provider snapshot and original guards.
- `native-verification`, `native-round2`, `reader-submission`: actual recovery, failed
  blinded designs, corrected protocols, source-reader delivery and known/unknown costs.
- `retry-conformance`, `effect-retry-evidence`, `effect-operation`: real-source event
  mapping, missing facts, bounded searches and the original CAS acquisition design.
- `p3`, `fvl-execution`, `cas-formal`, `cas-induction`: fixed tools, exact commands,
  bounds/timeouts, exits, canary ITFs, reachability and inductive obligations.
- `test-retention`, `test-retention-next`, `test-retention-all`, `test-retention-final`:
  independent oracles, final ledger, alternatives, actual source changes and failures.
- `test-taxonomy-20261025`: FactoryWeaver reference, route/Manager definitions, finite
  precision/recall populations, behavior eval and exporter/query evidence.
- `local-cost-continuation-20261025`: actual fixed-source diagnostics and ABBA observations.
- `native-effect-continuation-20261026`: raw-capture root cause/fix, actual two-case CAS,
  scoped offline audit, original capture/readback correction and migration-detach receipts.
- `selection-scope-continuation-20261026`: latest 298-method original receipt, source
  snapshot, exact observation-only registration, negative control, audit errors and costs.

Each sealed case's EVIDENCE/manifest describes its own payload scope. Keep originals,
commands, exits, failures and costs. No hash authenticates a hostile producer. Full raw
Native contexts stay at their private custody locations; exported command projections
are not a complete Native transcript. Never overwrite sealed packages or rerun their
packaging scripts into the same destination.

The latest scope phase records316 execution events for298 distinct controls, including
one pre-fix failure and a17-control small step; unit-owner time111.153564s. Its cumulative
298-control run records99.352785s. Cached input /reasoning output are subsets of their
reported totals, not additional tokens. Outer/worker/case/helper durations overlap; do
not sum them blindly. Missing billing, complete engineering/model/tool cost and whole
CPVC stay UNKNOWN. A smaller pool, CI PASS or faster unmatched run proves no economic gain.

## Remaining work and next legal continuation

1. Read this entry, the selected source statuses and latest private report/receipt first.
   Return a concise reconstruction: Parent Goal, sources, completed/remaining claims,
   actual legal continuation and genuinely new material questions. Do not execute or
   restore a Native task in this initial handoff turn.
2. Continue the Test Manager cost line from actual current source/cost data. Recheck
   applicability of the historical999 surplus candidates; they are not a deletion list.
   Preserve known fault/legal-neighbor discrimination and verified replacement coverage.
   Prioritize observed costly/repeated selection or fixture work over a new full audit.
   Do not reopen settled all-control decisions without new contract/consumer evidence.
3. Follow original `prepare → execute → inspect` and exact selected source/demand when
   verification is necessary. Reuse still-applicable evidence; cross-HEAD PASS reuse needs
   reviewed complete input/oracle/environment applicability and worthwhile marginal cost.
   Otherwise execute the justified scope. No unchanged full suite, solver or remote CI
   merely to obtain timing or a handoff number.
4. Full retry/binding/refinement is a separate dependent claim. The two helper cases have
   no retry or native normalized key/grant/phase; labels, OIDs and observer ordinals cannot
   supply them. Seek real producer semantics/evidence only for a concrete required claim.
   Unknown operations are not replayed. No new identity protocol, Manager or CLI state
   condition is introduced to manufacture conformance.
5. Current Native task/reviews remain pending despite migration-detach. Original intents,
   ACKs, work and evidence stay. Any later effect requires legitimate current admission
   and an authorized operation; an old request, local source PASS or this handoff is not
   permission to bypass governance. Do not recreate another Host or clear failure state.
6. Remote Draft updates/publication and exact-head delivery are not performed here.
   Future delivery must use the actual then-current source/provider readback and original
   acceptance owner; never carry a different head's CI or local PASS forward.

Known audit traps: original success status is `completed` with receipt exit0, not a
`passed` request enum; expected negative exit128 alone is not a counterexample; mixed
Selection includes whole modules as well as test_cases; use original projection, not
an Agent-rebuilt global list. Raw pre-decoding bytes cannot be recovered by re-encoding
text. Missing events, persisted active state, endpoint equality or cleanup labels do
not prove zero effects, live residency, task completion or an authenticated history.

## Suggested skills

Use a native Skill tool when this carrier actually provides one; otherwise read the
selected SKILL.md and follow it. Do not fabricate invocation, isolation or behavior-eval
receipts. Resolve caller paths in the selected Soodles workspace and Lab paths here.
Load only the skill needed for the current uncertainty/continuation.

- Lab [formal-route](../.agents/skills/formal-route/SKILL.md), caller
  `.agents/skills/formal-route/SKILL.md`: independent oracle/value and cross-repo method.
- Caller `thinking-router` and, when material, `ambitious-route`: one Session-owned
  source-bound delta; same-Session adversarial views, not a fixed Agent loop. New major
  semantic uncertainty can require questions; established facts/valid next can be NOOP.
- Caller `test-manager` and `code-intel`: current demand, original selection and complete
  registrations. Read `contracts/formal-route-flow.md`, `test-manager-process.md` and
  `factoryweaver-route-reference.md`; do not invent a factory-route skill or new flags.
- Caller `review-writing`: preserve source/claim limits and original Schema feedback.
  Use installed `evals-start`, `eval-audit`, `error-discovery` for new route behavior
  claims; data generation or a semantic judge/validation only when needed. Another
  uncalibrated Agent is not an independent oracle. Unchanged methods need no fresh eval.
- Caller `verify-soodles` / `verify-noodle` only for selected real runtime/effect claims;
  Noodle's actual selected Poteto entry remains inside normal original admission.
- Caller `handoff` when preparing the next handoff. Its temporary-output default is
  overridden here by the user's explicit Q70 instruction to commit `docs/handoff.md`.

This document guides continuation. It grants no production effect, merge, remote CI,
new identity qualification or automatic task completion.
