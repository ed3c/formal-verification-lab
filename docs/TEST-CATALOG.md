# Test catalog: independent dimensions

Use this reference when formal-route classifies controls or answers how many are
retained, necessary, on demand, in CI, or protecting a behavior module. The
catalog describes existing controls; it does not select or execute them. The
caller keeps its own catalog and evidence. Other repositories need neither
Soodles nor its identifiers.

## Classification and counting

| Dimension | Meaning | Counting rule |
| --- | --- | --- |
| `granularity` | `unit_method`, `physical_family`, `property`, `proof_obligation`, `query`, `agent_case` | Count unique IDs separately by granularity. A family is not one method; a query may check several properties. |
| `methods` | `unit`, `contract`, `integration`, `e2e`, `property`, `model_check`, `induction`, `trace_conformance`, `agent_eval`, `source_check` | Multiple labels may describe one control. State the caller's meaning of unit; a unittest method can exercise a real CLI. |
| `environments` | `local`, `ci`, `native` | Supported execution surfaces, not results or independent oracles. CI is not a method. Native requires the actual carrier, not a filename. |
| `modules` | Caller-defined protected behavior/contract responsibilities | Multiple memberships allowed. Source paths are locators, not the reason for protection. Read the behavior and contract before assigning. |
| `retention` | Existing `keep` or `rewrite` decision and its evidence | A retained control is not necessarily needed for this change. Historical merge/remove donors stay in the original decision ledger. |
| `demand` | `on_demand` with the concrete condition and its source | Affected contracts/invariants/acceptance obligations can make it necessary for a particular request. Research/performance/exploration requires its stated demand. No unconditional full-suite baseline follows. |
| `ci_bindings` | Workflow identity, event, source and dynamic or explicit selection | Count workflows separately. Explicit member IDs are a subset of controls; dynamic membership has no fixed control count. Neither is an execution receipt. |

An ID has one granularity. Tag and module totals overlap; do not add them to the
unique-control denominator. Compare counts only at the same source revision and
granularity. Report missing classification, absent request context and unmeasured
cost explicitly. Zero matching labels does not prove zero protection or authorize
skipping a control. A new/changed control requires updating the caller's mapping,
not guessing from a directory or keyword.

"Necessary now" requires a named change/request, independently justified
protection, the applicable trigger and original selection/evidence. This catalog
does not evaluate that relation. Without it, the necessary count is unknown,
not zero and not the whole on-demand pool. The original Test Manager continues
to select and execute. Missing catalog metadata never changes its admission,
fallback, runtime or CI behavior.

## Portable input

`schema` is `fvl.test-catalog.v1`. `scope` and `revision` describe the caller's
actual source scope; `method_notes` explains any caller-specific method labels.
`modules` is an array of `{id, statement, basis}`; `basis` cites the protected
contract/behavior source, not merely its directory. `controls` contains:

```json
{
  "id": "parser.reject_truncated_input",
  "granularity": "unit_method",
  "methods": ["unit", "contract"],
  "environments": ["local", "ci"],
  "modules": ["input-integrity"],
  "source": "tests/test_parser.py:12",
  "retention": {"decision": "keep", "ref": "review.jsonl#parser.reject_truncated_input"},
  "demand": {"mode": "on_demand", "condition": "Parser input contract or its consumer changes, or this regression is explicitly requested.", "ref": "requirements.md:8"},
  "protection": {"behavior": "Reject truncated input before any durable write.", "oracle_ref": "requirements.md:8", "discriminator_ref": "review.jsonl#parser.reject_truncated_input"}
}
```

Large caller inventories may keep `controls: []` in the manifest and supply
`control_parts: [{"path": "controls-001.json", "sha256": "<actual digest>"}]`.
Each selected part is an object with a `controls` array. The existing selected
file reader enforces its 256,000-byte per-part bound, path and symlink policy;
duplicates across parts are errors. All source digests appear in the report.

Empty method/environment/module lists or missing protection/condition expose
per-control gaps; they do not prove low value. Invalid types, duplicate IDs,
unknown labels/modules and dangling CI members are input errors. The reader
checks the supplied structure and counts only; it cannot authenticate citations,
prove oracle independence, re-adjudicate retention or establish completeness.
Caller source/AST/runner readback must reconcile the supplied denominator.

`ci_bindings` rows have `{id, event, source, selection, controls}`. `selection`
is `explicit` with distinct declared member IDs, or `dynamic` with an empty
list and a nonempty `condition` explaining the original selector. A workflow
with no fixed list must not be reported as zero executed checks. Store actual
run/job/head/results in their original receipts, outside these descriptive rows.

## Read-only query

```sh
PYTHONPATH=<lab>/src python3 -m formal_verification_lab.cli catalog <catalog-root> \
  --catalog catalog.json
PYTHONPATH=<lab>/src python3 -m formal_verification_lab.cli catalog <catalog-root> \
  --catalog catalog.json --module input-integrity --environment ci --list
```

Repeat a filter for union within that dimension; different dimensions intersect.
Supported filters: `--module`, `--method`, `--environment`, `--granularity`.
The report preserves the whole denominator, filtered counts, overlap rules, CI
bindings, gaps and the exact catalog byte digest. An unknown filter is a diagnostic
error, not a successful empty result. Exit 0 means the query ran, not validation
PASS. Exit 3 means invalid/unreadable input. It runs no tests, model checker,
provider, Native or CI, and grants no authority. Reuse existing source evidence;
do not launch all controls to fill a catalog.

## Retention and formal-route

Apply [the independent-oracle/value method](FORMAL-ROUTE.md) to necessary and
on-demand controls alike: independent requirement/invariant/proven compatibility
or real-defect basis; valid positive and named faulty/legal neighbor; unique
protection or verified replacement; concrete consumer/trigger; source and cost
boundaries. Field presence and classification do not satisfy these obligations.
Use [finite replacement evidence](TEST-RETENTION-INTERACTION.md) when relevant;
formal checks are selected only when they resolve the actual uncertainty.

Classify a formal query, its properties and induction obligations at their own
granularities, with assumptions/canaries/reachability and actual result references.
Do not sum them as distinct protections or turn model success into implementation
conformance. Do not infer a full formal inventory from an acceptance table.
Existing tools may supply only a scoped catalog; state omissions explicitly.

Return to the caller's thinking route only for a new material semantic conflict
(for example an externally relied-on behavior contradicting a proposed oracle).
Deterministic source lookup or a missing tag calls for readback, not a new
interview, Owner identity binding or global gate. New route behavior claims need
the existing [behavior eval](FORMAL-ROUTE.md#required-route-behavior-evaluation).
