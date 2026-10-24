# Execution plan

1. **Phase 1 — Synthetic/offline read-only core**: isolated Python package; pure kernel, pinned JSON parts, no provider integration, 23 planted controls, manifest hardening, tests. Independent observer status separate from provider acceptance.
2. **Phase 2 — Quint / Apalache**: manually check syntax and invariant model with recorded installed toolchain, max steps and bounded limitations; add inductive invariant and non-vacuity witness. Deliberate unsafe canary must produce an explicit counterexample trace. Source of model truth is original Soodles CLI contract, not a duplicated enforcement authority.
3. **Phase 3 — Native readback bridge**: locate and explicitly select available producer/provider evidence; pin Soodles ref and source bytes; align operation ID, owner_epoch, monotonic order, checkpoint and provider head. Replay actual Soodles trace through a separate source-bound conformance mapper; maintain private evidence outside repository.
4. **Phase 4 — Blind Evals**: freeze corpus, independent oracle, matched baseline and treatment; score per observed verified task, scoped findings and observed verified-task costs. The Session may implement authorized engineering corrections; the Lab does not mutate external targets.
5. **Research branch**: Lean4/RLVR reward shaping only after real eval gain; never required by Phase 1 runtime.

## Explicit deferments
- No installation of Soodles production tool/daemon/CI gate.
- No real provider connector or GitHub write scope.
- The evaluator does not modify target source. Separate Session engineering changes follow the current authorized scope in DECISIONS.md.
- No claims of formal verification or native acceptance without verifier run receipts.
- No new Test Manager, scheduler or state authority.

Current execution uses the Session as engineering principal. Missing complete private exports or external mapping approval does not block lookup, source work or evaluable subsets. Complete ordering/effect scope is required only for conclusions that actually depend on it. See `ACCEPTANCE.md` and `PARTIAL-EVIDENCE.md` for current interfaces.
