# Finite source-mapping quality

Use this only to measure a named source-location/control-registration mapping,
not oracle quality, test-selection sufficiency, dynamic call-graph completeness,
retention value, Native behavior or a repository-wide reliability claim.

Freeze the expected population before obtaining the measured output. Each truth
row is `{id, path, line}` for one scoped identity. Cite its independent producer
and source review; do not derive expected rows from the same query under test,
filter the denominator to returned successes, or treat two Agents as independent
specification. A source ledger produced separately before this change can support
a finite location comparison; shared parsers and incomplete review remain limits.
Use literal positive/fault/unsupported controls to challenge the reader as needed.

Observed rows have matching fields and optional `status=resolved`, or
`{id, status=unknown}`. IDs must be unique within each side. Missing/UNKNOWN is a
recall miss. A wrong location contributes one FP and one FN; an extra resolved ID
is an FP. Precision is `TP/(TP+FP)`, recall `TP/(TP+FN)`, coverage is the fraction
of expected identities resolved (including wrong resolutions). Unknown and
missing populations are reported separately. Empty denominators produce null,
not a vacuous 100%. An unsupported dynamic fact is not relabelled as a location.

The selected target requires **both precision and recall strictly greater than
99%** on the same frozen population. Exactly 99% fails. This is a bounded
measurement, not statistical evidence for unseen inputs or a general guarantee.
Report population selection, source/tool versions, commands, exits, mismatches,
UNKNOWN, source drift and actual costs. Cost and P95 latency are different claims.

Input `schema=fvl.mapping.v1` has nonempty `scope`, `revision`, `expected_origin`,
and `expected`/`observed` FileRefs `{path, sha256}` relative to the selected root.
Either side may instead be a nonempty list of those refs, preserving one combined
population; duplicate IDs across parts are errors.
Each selected JSON object contains `rows`. The original selected-file reader
enforces bytes, path and symlink limits. Split a large study into named independent
populations without omitting failures; report their actual denominators.

```sh
PYTHONPATH=<lab>/src python3 -m formal_verification_lab.cli mapping <evidence-root> --study mapping.json
```

Exit 0 means measurement completed, **not that the target passed**. Read
`target_met_supplied_population`, nulls and error populations. Invalid/read
failure exits 3 with a diagnostic. The CLI does not authenticate truth sources,
execute target code, modify selection or grant effects. `ground_truth_review`
stays SESSION_REQUIRED. Do not install this metric as a universal CI/Native gate.
