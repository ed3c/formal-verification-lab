# Lab and Soodles decoupling boundary

Separate repositories make ownership and release boundaries visible. Repository count alone does not prove decoupling. The behavior below defines the boundary.

| Boundary | Required evidence | Current candidate observation |
| --- | --- | --- |
| Soodles does not depend on the Lab | Soodles source, dependencies, Hooks, CI, CLI and startup do not acquire a Lab runtime dependency. | This candidate changes only the independent Lab worktree. It adds no Soodles integration. |
| The Lab runs independently | Public Quint, Apalache, Python, and pure contract inputs run without a Soodles checkout, login, or Native Host. | Python, parity, source readback, typecheck, and P4 use repository files plus caller-supplied verifier tools. Fresh external P3 execution passed bounded safety, the real unsafe ITF canary, both reachability witnesses and three typed-induction obligations. The earlier restricted worker port refusal is historical. |
| Evidence is an explicit input | Private Owner and Provider material stays outside the repository. | Generated evidence is caller-directed to an external directory. The public core contains only synthetic fixtures and generic pins. |
| Missing inputs do not become success | Missing provenance, ordering, completeness, effect readback, or tool capability produces `UNKNOWN`, `NOT_RUN`, or `NOT_VERIFIED`. | P3 records `LOCAL_PORT_UNAVAILABLE` and does not use a fixed-port fallback. P4 distinguishes unavailable pins from failed validation. |
| Findings add no authority | The Lab cannot authorize admission, retry, terminal state, merge, or Provider effects. | No write credential, Provider client, dispatch path, or production admission path exists. |
| Development carrier stays external | Noodle is a development carrier, not a product dependency. | `.worktrees/`, `.noodle/`, and `.noodle.toml` are ignored. No Noodle runtime code is added. |
| The Lab is removable | Soodles keeps its existing entry points if the Lab fails or is removed. | No Soodles file or runtime dependency changed in this candidate. This Lab candidate adds no target runtime dependency, and standalone execution uses public Lab inputs; it is not a claim that all Soodles behavior was rerun. |

## Provenance and current verification

`scripts/p3/source-manifest.json` preserves the historical 188-file import at its fixed ref. The current source verifier reports that record as `HISTORICAL_NOT_REVERIFIED`. It does not compare every evolving public file with the old import.

Each P3 invocation freezes the current model, harness, runner, validator, source verifier, entry script, historical manifest, and toolchain digests. The validator compares current source readback with that same invocation manifest. It also checks that duplicate models are absent as files and symlinks, and that the two P3 harnesses import the repository operation spec.

Historical source custody, the independent Lab import commit, and earlier checker receipts remain historical facts. They are not fresh acceptance for changed candidate bytes.

## Evidence-dependent claims

The Session may discover, select and evaluate available evidence now. Source mappings, authentic provenance, ordering, truncation and effect completeness are recorded per claim, not imposed as a whole-task qualification gate. No original Session or external Owner mapping approval is required by the public core.

Full Native refinement, a complete external effect history, and blind behavioral or monetary gain need their corresponding observations. Partial readback findings and known costs can still be reported without those broader claims. Unobserved totals remain unknown, not zero.

The Lab proves only the declared formal model under stated bounds. A digest proves byte consistency, not producer authenticity or a trustworthy timestamp. A completed process or successful CI job alone does not establish external effect reconciliation.

Session source engineering is separate from evaluator execution. The current user authorization permits Soodles, Noodle and Lab source/tests and Draft PRs, while preserving the active runtime and forbidding merge or changes to #448, #450 and escrow. These authorized source tasks do not give the evaluator target-write or dispatch capabilities.
