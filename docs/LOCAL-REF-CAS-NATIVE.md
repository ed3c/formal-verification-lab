# Local ref CAS acquisition report

The isolated Lab now has actual observations for the two cases in the
[frozen acquisition design](LOCAL-REF-CAS.md). These observations support the
selected CAS slice under declared assumptions. They do not establish full Soodles
Native acceptance, effect-retry conformance or runtime refinement of the model.
Raw caller records remain in the private evidence store, outside this repository.

## Actual results

The first normal admission initially encountered a client/Host binary mismatch.
A fresh request used the already-active immutable Host client without installing
or switching a runtime. Its first Native collector observed an actual expected-old
CAS rejection but failed to retain original pipe bytes before decoding. It stopped:
the selected finding remains UNKNOWN, and its positive case remains NOT_RUN.
The lost bytes were not reconstructed from decoded text or a later execution.

A readonly child-process probe reproduced the observer defect. On the selected
Python 3.14 implementation, the old return-point observer captured no byte pair;
an observer at the pre-translation call captured the exact literal CRLF/UTF-8
stdout and stderr. The successor collector and probe share that observer module.
Source comparison left the collector's intent, case preparation, reconciliation,
UNKNOWN and stop behavior unchanged.

The successor ran through normal Native resource admission in two new independent
fixtures. It invoked the selected helper once per case; neither case retries the
first trial or the other case.

| Case | Helper exit | Independent selected-ref observation |
|---|---:|---|
| Mismatched expected-old | 128 | Exact ref and reflog unchanged; matching known CAS-mismatch receipt and original pipe bytes retained |
| Matching expected-old | 0 | Exact A→B ref update and one matching reflog append; successful receipt and original pipe bytes retained |

An offline Session audit verified 195 copied files, 154 contiguous observer journal
entries and 142 journal file references. Intent preceded callbacks; each case had
one started/terminal callback pair and one raw stdout/stderr pair. Exact command,
cwd, OIDs, terminal receipt, helper return and readback agreed. Configuration,
objects, other inventoried files, empty remotes and empty fixture hooks were
cross-checked. The first trial's 116 manifest payloads were also reverified.

These are byte-consistency and bounded-observation checks, not authentication of
a hostile producer or exclusion of every outside writer. The declared single
writer and trusted Git CAS contract remain assumptions. Endpoint lock inventory
does not prove no transient lock, and selected-ref equality does not prove no
global side effects or intermediate ABA. Fixture preparation and capture wrote
objects, configuration, refs, reflogs and observer files.

## Relation to the abstract model

| Real evidence | Model relationship and limitation |
|---|---|
| Persisted pre-invocation intent and started callback | Supports an offered invocation; `offer` is an abstraction, not a runtime phase or proof that spawn succeeded |
| Terminal known mismatch or success, with exact original output | Supports the selected `completeGit` outcome under the trusted atomic CAS contract; the internal atomic step was not directly traced |
| Matching saved terminal callback and helper return | Observational counterpart of `recordCompletion`; no receipt-loss behavior was exercised |
| Exact post-readback and bounded effect evidence | Supports mismatch/no-selected-ref-update or matching/A→B; it is not reconciliation before retry |

No literal `OperationProtocol` phase, producer operation ID, idempotency key,
grant or global event order was supplied by these helper records. Observer
ordinals and case labels must not fill those fields. The model's separate
`otherRef` sentinel was not instantiated as a second live ref. Therefore these
checks establish selected observational compatibility only, not complete model
trace conformance. Dependent retry/binding claims remain UNKNOWN. The existing
bounded and inductive proofs keep their original model assumptions and were not
rerun for these observations.

## Cost and continuation

The first Native attempt recorded 433 seconds and 910,257 total tokens. The
successor attempt elapsed 166.422033 seconds and recorded 673,393 total tokens.
Token totals include input and output; cached input and reasoning output are
subsets, not additional tokens to sum. Dollar cost is UNKNOWN. Collector/helper
timings and local diagnostic costs remain separately recorded; they are not
added to attempt wall time. This is not a matched cost comparison or whole CPVC
improvement claim.

After acquisition, both this chat's contexts were paused, stop-acknowledged and
migration-detached through the original client under confirmed human maintenance
authorization. Work, pending reviews and evidence remain; no automatic resume or
effect replay is authorized. This chat did not stop other contexts or replace the
Host. Later maintenance by another authorized chat does not alter acquisition
provenance.

The caller's local readback correction preserves a candidate/review refusal and
its continuation while permitting an explicitly requested independent evidence
capture. A known SDK metadata kind is recognized without weakening private or
unknown-record handling. The 107 affected original local controls passed and an
actual completed-task capture returned observed while preserving its inactive-host
refusal. No new mandatory test, solver, CI job, Manager or acceptance gate was added.
Local source delivery does not switch the installed version, update remote PR
acceptance or authorize merge. Further acquisition needs a specific missing claim,
new legitimate evidence and normal governance, not another run to erase UNKNOWN.
