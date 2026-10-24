# Property / Verification / Acceptance Matrix

| ID | Property | Planted positive | Planted negative | Oracle | Phase 1 claim |
|---|---|---|---|---|---|
| FVL-AUTH | Operation and Session match a valid owner grant | publish_valid | foreign_session | Owner export, later independent Authority readback | Offline conformance |
| FVL-BIND | Evidence operation/session/head match | publish_valid | wrong_binding | SHA-pinned source and originating owner | Offline conformance |
| FVL-FRESH | Pre-effect head+owner epoch agree, in order | publish_valid | stale_head, wrong_epoch | Provider preflight readback | Offline conformance |
| FVL-LEGAL | Transition in frozen allowed relation | advance_valid | illegal_transition | Source-versioned model mapping reviewed by the engineering Session | Offline conformance |
| FVL-IDEMPOTENCY | Stable operation key, at most one observed effect | publish_valid | duplicate_publish, incomplete_ledger, wrong_provider_key | Complete owner/provider ledger | Offline conformance |
| FVL-CHECKPOINT | Resume digest agrees | resume_checkpoint | resume_wrong_checkpoint | Original checkpoint owner | Offline conformance |
| FVL-RETRY | Prior outcome reconciled **before** retry (ordered after prior attempt) | retry_reconciled | retry_unknown_effect, retry_reconciliation_too_late, retry_reconciliation_too_early | Provider readback | Offline conformance / UNKNOWN |
| FVL-TERMINAL | Receipt has observed provider effect | terminal_valid | terminal_false_receipt | Independent receipt/provider readback | Offline conformance |
| FVL-NO-FALSE-SUCCESS | Missing evidence cannot support success | publish_valid | absent_provider, unsupported_success, success_without_effect, effect_receipt_missing | Independent observer | Offline conformance |
| FVL-MODEL | No duplicate and no unsafe effect | TBD | UnsafeCanary | Quint + Apalache | BOUNDED_PASS at the recorded bound; typed induction separately |
| FVL-CONFORMANCE | Runtime events refine abstract transitions | TBD | TBD | Selected runtime evidence with an explicit source mapping | Scoped findings / UNKNOWN; no full Native refinement claim |
| FVL-EVAL | Blind gain above paired baseline | TBD | TBD | Frozen separate observer | Evidence-dependent comparison; no unmeasured gain |

## Claim vocabulary
- COUNTEREXAMPLE: concrete scoped test/model trace contradicts a claimed invariant, or a complete case claims success without its required support. Omitting evidence from a partial selection is not such a counterexample.
- BOUNDED_PASS: available synthetic/offline observations satisfy implemented checks; no general proof.
- UNKNOWN: incomplete or non-comparable observation, not a passing property.
- NOT_RUN: required tool/procedure has not executed.
- PROVED: reserved for successfully checked inductive invariant with documented assumptions and independent proof-checker evidence. The current CLI never emits PROVED.

Acceptance Phase 1: all named synthetic cases and manifest integrity controls pass. This only validates the local implementation's planted examples. These synthetic controls do not establish Native Soodles, Provider effects or a real comparison; those observations are reported separately at their actual scope.

Acceptance Phase 2: record actual Quint version, command, exit, invariant result, traces and bounds, successful deliberate canary counterexample (not merely nonzero process exit), and at least one non-vacuity / reachability witness. Submit inductive invariant separately. If backend unavailable, NOT_RUN.

Acceptance Phase 3: the Session reviews a source-versioned mapping from selected producer/provider data to the normalized fields. Record semantics, ordering assumptions, provenance, deduplication scope, loss/truncation and omitted effects for each claim. There is no external Owner approval, original Session identity or complete-bundle qualification gate. Discovery and supported partial checks proceed with available data. Missing facts keep dependent properties UNKNOWN. The Lab has no write credentials.

Acceptance Phase 4: independent frozen baseline and treatment; random/blind assignment; same admitted task/head/runtime/necessary control set; known planted controls for wrong identity, stale head, false resolution; report false acceptance, true verified tasks, unknowns, latency/token/verification/recovery cost. No fabricated sample or fixed gain threshold.

Warning: independent readback ≠ independent attacker-resistant attestation. Authenticity-dependent claims need their actual channel or attestation evidence; a self-hash alone cannot establish them. This does not prevent inspecting or evaluating other supplied facts.

## Partial evidence and selected properties

`discover` lists workspace candidates within explicit depth, total-entry and match bounds. It does not infer a join, approval or complete lifecycle from the files it finds. `evaluate --select ROLE=PATH` loads only named parts and records their actual byte digests. No manifest or complete bundle is required for this route.

`evaluate --property ID` reports only requested properties. Each property checks its own dependencies: legal transition endpoints can be checked without a grant; grant acceptance still needs its actual identity/scope/order; retry and at-most-once claims need their own matching readback. Missing dependencies and non-applicable properties are UNKNOWN, not vacuous passes. An unbound raw count is an observation, not a per-operation duplicate proof.

Unselected evidence is not evidence that the original execution lacked support. Partial selection therefore does not turn an omitted part into a false-success counterexample. An observed contradiction is still reported at its scoped property. The legacy complete v1 synthetic case protocol and its 23 independent expected verdicts remain unchanged.
