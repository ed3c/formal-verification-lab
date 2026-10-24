# Native readback verification protocol

This protocol documents a read-only experiment. The public repository contains code and synthetic controls. Selected private records, independent answers, allocation keys, Native transcripts, process receipts and costs stay in a separate evidence directory. The Lab does not start a model, Noodle task, Provider client or runtime admission.

## Select and read sources

Run `python3 tools/read_bundle.py BUNDLE.json` with a caller-selected bundle. Its schema is `schema=1`, an absolute normalized `root`, `files` of `id/path/sha256`, `selectors` of `id/file/pointer`, and `max_output_bytes` in 1..65536. Each declared file stays under the root. IDs must be unique, pointers follow RFC6901, and file digests use lowercase SHA256.

The tool reports each actual file's digest, byte count and byte-split line count. MISSING, UNREADABLE and DRIFT remain explicit. A missing field is different from JSON null. Matching files with invalid JSON remain INVALID_JSON for selectors. One unavailable file does not erase unrelated values. Digest consistency does not authenticate a producer or prove current liveness.

The output limit includes the final UTF-8 newline. Exceeding it exits 2 with no partial stdout. Invalid input also exits 2. The reader has no source-input byte or memory cap, reads complete selected files and uses POSIX descriptor APIs. Use it for selected local data under a separate execution policy. It is not a hostile-file resource sandbox and is not promised to run unchanged on Windows. The CLI accepts a bundle position, not `--help`.

## Freeze the comparison

Choose the question shape before observing candidate answers. The current public closed-output tool supports exactly eight questions Q1..Q8 and common evidence groups G1..G8, with eight neutral labels R01..R08 per packet. This is a fixed experiment format, not a general evaluator or a new FVL property. Freeze per-case value types, source selections, independent literal answers, exposure mode, deadline, allocation seed and judge criteria before dispatch. Keep the independent answers out of candidate inputs.

Supply the same questions, common data and reader to both sides. Identify whether extra observations are merely available as a file or actually supplied in stdin. Saved availability cannot establish exposure. `prepare_trial_input` appends closed observations as data and returns exact stdin bytes and their SHA256. That digest binds prepared bytes, not successful process delivery or model use. An external carrier must record the bytes it really sends and compare the digest. Do not add a dispatch path to this Lab to make that observation.

`clone_profile` deep-copies a template before extending denies. It never removes an existing deny or changes original write/metadata grants. It rejects required input paths under a blocked root. This lexical check does not validate an operating system sandbox. Compare each actual consumer profile with the tested profile and compare actual source readback inside and outside the profile before inference.

`prepare_trial_input` accepts unique checks C1..C8 with only check/value fields. Values are booleans, integers 0..512, or MATCH, DRIFT, MISSING, UNKNOWN, COMPLETE, INCOMPLETE, LIVE and NOT_ESTABLISHED. These labels define shape, not truth or authentication.

`consumer_environment` returns only task-local TMPDIR and TMPPREFIX overrides. zsh can use TMPPREFIX independently of TMPDIR; an allowed TMPDIR alone does not prove heredoc storage works. Keep the inherited login environment and write policy intact. Verify a real heredoc under the selected policy rather than widening permissions or altering HOME.

## Keep judgment blind to allocation

`python3 -m formal_verification_lab.blind_outcome validate --contract CONTRACT --case SYNTHETIC --input OUTCOME` validates shape. It does not score truth. Only `schema` and eight `answers` with `id/value/evidence` are accepted. Integers, booleans and closed enums are distinct. Additional method, path, narrative or arbitrary text fields are rejected. A wrong but legal value stays unchanged. UNKNOWN and INCOMPLETE must not be merged.

The `packet --contract CONTRACT --manifest MANIFEST --output NEW_DIRECTORY` command accepts eight explicit `label/case/path` selections. Paths are caller-selected local files; this packet command is not the reader's symlink-confinement interface. Store its output outside the public source tree. It preserves original bytes as mode-0600 files in raw/ and records a ledger. Keep the output directory under caller-managed private custody. Invalid output becomes only a fixed INVALID_OUTPUT envelope in primary.json. Its unseen semantic risk stays unassessed. Do not report invalid answers as zero false acceptance.

Give the judge only primary.json, the frozen independent facts and criteria. Do not give the allocation key, raw narrative, argv, runtime, paths, cost or ledger. Canonical formatting removes formatting variation, not wrong claims. Seal the actual judge artifact before joining the separate allocation key. Preserve timestamps, source hashes and all original errors externally.

Participants can see different observations. Same-family judging and related samples limit independence. A closed schema blocks direct method metadata, but cannot prove all statistical or semantic clues absent. Do not call this double-blind or cross-family validation without corresponding observations.

## Retain failures and costs

Keep every failed preparation, timeout, invalid output and valid wrong answer. A changed input, profile, exposure mode or protocol is a new named batch. Preserve the earlier batch, its amendments and costs. Do not pool incomparable batches or rerun until the selected result improves. Distinguish process exit, schema validity, semantic correctness, task completion and runtime acceptance.

Record actual tool/model versions, commands, source digests, bounds, exits, deadlines and process completion. Count each terminal usage once. Cached input and reasoning fields may be subsets; retain their original definitions instead of adding them twice. Keep shared preparation costs once and all failed batches. Unknown costs, internal decision costs and USD stay unknown. Process wall sums are not parallel elapsed time. Do not derive per-tool seconds from transcripts that do not contain them.

## Resume from a repository or workspace

The current Session can locate evidence and choose supported checks. No original Owner, Session identity, external mapping approval or complete private bundle is a blanket prerequisite. A source index is a locator, not a credential. Missing data limits only the claims that depend on it. Retain data consistency, mutual exclusion, deduplication and actual Provider permissions.

For source review, run `PYTHONPATH=src python3 -m pytest -q`. Read the selected independent evidence separately. Public synthetic tests do not certify Native behavior, production acceptance, a model benefit or a runtime rollout. The external experiment's sealed results remain historical observations on their own inputs and source hashes.
