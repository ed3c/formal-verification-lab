# Formal-route method and test value

The question is whether a test verifies a product requirement or merely endorses the current implementation. Unit/E2E labels, AI authorship, coverage, green CI and test count do not answer it. Different populations reporting5000tests/few bugs versus150tests/15bugs are not a controlled defect-yield comparison. Prioritize oracle quality and comparable verified-change cost.

## Establish the independent oracle first

For each control, locate the actual user outcome, stable external contract, system invariant, confirmed external compatibility dependency or required behavior from a real defect. Read its source. A registration, generic document citation, implementation output or another Agent reading the same code does not create an independent oracle. An unresolved oracle is not final approval to retain the test, nor proof that it can safely be removed. Resolve the evidence gap or explicitly leave that decision open.

Review three recurring failures:

- Implementation-Coupled Testing: internal call order, object identity, private layout, exact wording or constants may cause false red during a legal refactor. Determine whether each expectation protects an external contract or only one implementation. Preserve payload, input isolation, concurrency, durable-state and effect discriminators when rewriting it. A table-consistency relation or protocol constant may have a real consumer; do not delete it by shape alone.
- Self-Verification: implementation changes cannot silently redefine expected behavior. Record which independent contract changed before changing the oracle. Freeze the expected input population separately; a test generated from the implementation's own case list may shrink with the same bug. Use distinct review and positive/negative controls, while acknowledging that another Agent is not itself an independent specification or final acceptance authority.
- Oracle Problem: equal output from two paths, copied current values or model consistency may still validate the wrong behavior. Require concrete literal expected outcomes or independently sourced properties and discriminating faulty/legal-neighbor cases. Model premises and source-to-model mapping need the same scrutiny as test code.

For each negative scenario, verify the nominal baseline and change only the intended fault. Check the named refusal/effect boundary where the contract defines it. A different pre-existing failure can mask the intended discriminator. Conversely, a suspicious field is not necessarily authoritative; read the real contract and consumer before changing a test. Preserve disproved hypotheses and their correction.

## Evidence layers and known/unknown questions

Classify and count controls through [the test catalog](TEST-CATALOG.md). Keep
method, environment, protected behavior module, retention and conditional demand
separate; the catalog is not a selector, oracle or proof of necessity.
Use [the interaction contract](ROUTE-INTERACTION.md) for caller tools and Managers,
and [finite mapping quality](SOURCE-MAPPING.md) for source-location metrics.
Keep deterministic paths in their original code/contracts, not additional
probabilistic route choices or a prose state machine.

| Layer | What an actual result can establish | What it does not establish |
|---|---|---|
| Unit/property/contract test | Selected implementation behavior agrees with an independently justified expected result for its exercised inputs/properties. | All inputs, unmodeled user requirements, or correctness of an implementation-derived oracle. |
| CI | The stated commit/environment executed its original selected checks with recorded results and source bindings. It is an execution/delivery envelope, not a separate independent oracle. | A changed contract, another HEAD, full-system correctness, Native behavior or the Parent Goal. |
| Formal specification/checker | Declared transitions/properties under stated assumptions and bounds, including combinations not manually enumerated; induction has its own obligations. | The truth of those premises, unmodeled behavior, source-to-model conformance or unknown external effects. |
| Actual trace/conformance | Selected implementation events agree or disagree with an explicit model mapping at that observed scope. | Unobserved effects, complete histories or all Native executions. |
| Agent behavior eval | The actual consumer used the saved route correctly on selected tasks, with captured decisions/actions and independent expected conditions. | Product proof, global routing accuracy, or causal improvement over a baseline without a separate comparison. |

For an already established contract and sufficient current evidence, use the original deterministic continuation. For a named missing fact, read the available source/tool before creating another run or asking the user. Missing evidence is not a reason to rerun thinking route mechanically. A new semantic contradiction, unsupported premise or material product tradeoff returns to thinking route with the source, uncertainty and a falsifiable question. After it is resolved, return to the same task and original execution owner.

No layer closes unmodeled/unknown risks by declaration. Use targeted adversarial cases, property exploration, source-to-model comparison and error analysis to expose new hypotheses where justified. Report the unexamined scope. Do not infer that unknown unknowns are covered from a green suite or model PASS, and do not turn them into an automatic full-suite or solver requirement.

## Choose only the method that resolves the question

First fix the Goal, measurement, supported effort and first causal uncertainty, following the existing thinking-route design. Use one necessary method; expand to bounded adversarial perspectives only when they introduce a new falsifiable issue. Formal-route is a domain route, not a sixth cognitive method or a new CLI decision state. It adds no fixed decision/test budget.

| Question | Appropriate evidence/method |
|---|---|
| Does one current control duplicate another's finite contract guards? | Source/fixture/entrypoint mapping, correct positive control and finite failure discrimination. Use the [retention relation](TEST-RETENTION-INTERACTION.md); do not force a solver. |
| Does a pure algorithm/parser/permission rule satisfy a general property? | Stable contract plus property-based tests or suitable pure-function analysis. Use the existing [P4 scope](P4-CONTRACTS.md); do not run I/O handlers under a symbolic analyzer. |
| Can retry/concurrency/recovery violate an invariant? | Explicit state/actions, assumptions, safety and progress obligations. Use [Quint/Apalache architecture](C0-P3.md), [model exploration](MODEL-EXPLORATION.md), and [induction](LOCAL-REF-CAS-INDUCTION.md) when applicable. Keep canary counterexamples and non-vacuity/reachability evidence. |
| Does implementation behavior refine that model? | Explicit mapping and actual selected trace. Use [partial evidence](PARTIAL-EVIDENCE.md), [retry conformance](RETRY-CONFORMANCE.md) and [effect evidence](EFFECT-RETRY-EVIDENCE.md). Missing facts stay UNKNOWN for their dependent claim. |
| Is a retained control worth its execution cost? | Independent protection, verified replacement, actual trigger, true defect impact/yield when known, refactor stability and observed total verified-change cost. Formal coverage does not itself prove economic value. |

Retain contracts and distinct failure boundaries. Rewrite brittle expectations without losing their protection. Merge only with verified replacement and fixture isolation. Remove controls with no unique required discriminator once their preservation/replacement evidence is established. A valuable control can be on demand; a frequent control can be redundant. Assess necessary and on-demand tests by the same value criteria, then decide when this change needs them. Regression history, price and full cost that are not measured remain UNKNOWN.

## Boundary with original Managers and repositories

The Session owns engineering judgment. The original repository's Test Manager owns selection/execution and its original acceptance owner retains delivery authority. Schema/feedback tools, when present, carry the original evidence and continuation; they do not turn labels into semantic proof. Noodle or another carrier is optional and stays external. Hook/Cron work requires its own real event/request. Formal-route invokes none merely because a test was reviewed.

The Lab is a read-only evaluator and universal method source, not a replacement Test Manager, scheduler or value-policy service. Any Repo can use the portable contract. Soodles keeps only a thin entry and its own tool adapter. Lab absence does not disable ordinary Repo tests or create a new admission requirement. No original Owner, original Session, complete private bundle or credentials are eligibility gates.

## Honest verification and cost

For project-local verification skill creation and upkeep, use the [pstack integration](PSTACK-FORMAL-INTEGRATION.md). It defines applicability review before selecting upstream create/maintain, independent evidence for Oracle changes, and the existing caller execution boundaries. The [P4 skill](../.agents/skills/verify-p4-contracts/SKILL.md) packages an existing check rather than creating another model.

Prefer existing valid evidence. Run a new checker only when model/assumption/mapping changes invalidate the relevant result or a genuinely new question needs it. Preserve actual model/tool/source versions, command, bounds, exit, result, canary trace and observed costs. BOUNDED_PASS, induction under fixed assumptions, finite source checks, local test PASS and Native conformance are different claims. No Lab result authorizes writes, retry, merge or deletion.

Independent oracle quality comes before adding more tests, including formal tests. A new formal check must justify the unique behavior or assumption it protects and its execution demand. Avoid accumulating duplicate controls, universal solver jobs or fresh full-suite runs to collect missing timing. See [decoupling](DECOUPLING.md), [acceptance](ACCEPTANCE.md) and [security](SECURITY.md).

## Required route behavior evaluation

Before claiming that a new/changed route correctly separates these layers, interacts with thinking route or judges retention, use the actual installed eval skills and preserve their source/digests. `evals-start` selects a suitable method; `eval-audit` checks an existing pipeline; `generate-synthetic-data` prepares inputs when actual route traces do not yet exist; `error-discovery` analyzes the actual resulting traces. Synthetic inputs are not fabricated execution traces. Use objective source/receipt checks for structured conditions. A semantic LLM judge needs its own `write-judge-prompt`/`validate-evaluator` evidence if one is actually necessary; a second uncalibrated Agent score does not solve the Oracle Problem.

Freeze requirement-derived expected conditions separately from the consumer. Give fresh consumers the task, selected saved instructions and necessary raw inputs, without expected answers or intended fixes. Preserve their actual output and available action capture, errors/timeouts, source bindings and cost. Record transcript/capture limits. Use the original caller's behavior-feedback/Schema tools when available, and consume their actual returned continuation; never invent a Stage/session or substitute format validation for semantic criteria review.

Evaluate the distinct decisions needed by the change, not one run per file or per test. The initial acceptance covers supported retention, insufficient oracle, wrong-head CI evidence, model versus actual trace, and new semantic uncertainty versus deterministic lookup. It claims only observed necessary behavior correctness. Comparative benefit, global error rates and Native completeness remain unestablished. Existing valid behavior evidence may be reused for unchanged instructions; a changed instruction's claim needs its own binding. Missing eval capability leaves that behavior claim NOT_RUN/UNKNOWN, without blocking independent source or test work.
