# Local ref CAS evidence design

This proposed trial observes a real, persistent Git ref operation in an isolated Lab fixture. It uses the existing Soodles `run_push` process-receipt helper and keeps the Lab evaluator read-only. The first trial has two independent cases. Neither case retries an operation.

At design time, the observed resource start credit and effective limit are zero. Both cases are **NOT_RUN**. No runtime OIDs, receipts, no-effect finding, or conformance PASS are supplied by this document.

## Source relationship

The reviewed Soodles source revision is `ea5420cdd88b3b75db08380ee358048111be1054`. These references describe source semantics, not the version of an active runtime.

- `issue_atom.py:2221-2308`, `acquire_revision_base`, persists a ref intent, uses expected-old CAS through `run_push`, and reads back the exact target.
- `issue_atom.py:2290-2298` checks the current ref against the intent and prohibits another invocation once `ref_process` exists. An observed target permits readback, not replay.
- `candidate_publication.py:537-570`, `run_push`, offers a `started` receipt to the callback before spawning the child and later offers a terminal process receipt.
- `candidate_publication.py:522-535`, `push_disposition`, classifies single-ref push porcelain. It does not classify `update-ref` failures.
- `tests/test_admission_revision.py:284-345` provides related local CAS, race, and unknown-readback test patterns. Reading these tests is not a new execution result.

The local Git readback at design time is `2.50.1 (Apple Git-155)`. Its installed manual and the [Git 2.50 update-ref documentation](https://git-scm.com/docs/git-update-ref/2.50.0) describe the expected-old condition. The three-argument operation updates the ref only when its current OID matches the supplied old OID. That contract supports the proposed control; it does not replace the future process and readback evidence.

## Two separate fresh cases

Each case creates its own repository and prebuilds valid commit objects before the observation interval. A, B, and C below are symbolic design names, not recorded OIDs. In each case, A differs from B, and C differs from A.

| Case | Ref before invocation | Fixed expected-old | Fixed target | Proposed observation |
|---|---|---|---|---|
| Rejection | A | C | B | One completed CAS refusal, followed by bounded readback and stop |
| Positive witness | A | A | B | One completed CAS, followed by exact target readback |

The rejection case deliberately exercises the lower-level Git primitive through the existing helper. The full `acquire_revision_base` precheck would reject its mismatched current value before calling Git. This case is therefore not a trace of that full lifecycle. The positive case also covers only the helper slice, not its surrounding authorization, Provider, ancestry, or custody checks.

The design has no lock injection or lock removal. It does not change expected-old, target, or payload after rejection. It does not reset a ref to enable a second attempt. The two cases cannot be joined into a retry trace or used to repair an earlier UNKNOWN operation.

## Evidence boundary

The effect under observation is the value transition of one named, non-symbolic, non-checked-out ref in one fresh local repository. The fixture uses the files refs backend, prebuilt objects, declared configuration, no remotes, no network, no credentials, and an empty fixture-specific hooks location. Existing repositories, user hooks, global configuration, tests, and resource controls remain untouched.

The admitted worker places scratch files only under its permitted private path, such as its own `.private/` directory. The actual execution envelope determines that path. A proposed pathname grants no filesystem permission. Raw records are copied to the external private evidence store before any worker cleanup; they never enter public fixtures or Git history.

The scope assumes a single writer for the fixture during the interval. Record that assumption and the actual repository path, refs backend, Git executable and version, source digests, configuration and hooks inventory, object identities, and other refs. Hashes identify selected bytes; they do not authenticate a hostile producer or exclude another process with write access.

Pre/post ref and reflog observations are cross-checks. Endpoint equality alone cannot exclude an intermediate change or establish complete history. A bounded no-ref-update conclusion additionally depends on the expected-old contract, a complete matching invocation receipt, the fixed fixture, and the declared writer boundary. Missing support leaves that conclusion UNKNOWN.

The claim does not cover zero writes to objects, reflogs, lockfiles, process files, observer journals, or the whole machine. Fixture preparation and observation themselves have effects and costs. Inventory other refs without treating an endpoint inventory as a global absence proof.

## Capture after normal admission

Only a normally admitted Noodle Native worker drives the proposed effects. Preparing a request does not start a worker or establish admission. Zero credit does not authorize a second Host, another carrier, or an ordinary engineering subprocess to obtain the deferred trace.

1. Freeze the selected source, helper, Git version, environment, and the case design. Confirm the actual execution envelope permits the private fixture and evidence destinations.
2. Prepare a fresh case and its objects. Freeze the actual ref, current OID, expected-old OID, target OID, and exact command before the invocation. An independent observer freezes that case's expected observations before inspecting checker output.
3. Save the pre-observation, configuration, hooks and refs inventories, and raw reflog state. Retain command exits and bytes, including an absent reflog where applicable.
4. Persist the case intent before mutation. Use an append-only observer journal whose callback saves and fsyncs each raw receipt version. Keep the pre-spawn `started` record even when a later record exists.
5. Invoke the selected helper once. Preserve complete stdout, stderr, exit status, process disposition, and duration without replacing earlier records. The helper's current subprocess timeout is 30 seconds.
6. Read back the selected ref, all refs, and reflog without another mutation. Preserve the command, bytes, digests, and observation order. Stop the rejection case here regardless of its result.
7. Run the separate positive case only after the first case has complete capture and no unresolved process or effect boundary. Preserve it by the same procedure. An independent Session observer reads the frozen raw evidence and reports only the bounded claims its sources support.
8. Capture the actual Native input, returned outcome, completion readback, usage, and recovery cost separately. Worker completion is not proof of the Git effect or full Soodles acceptance.

Journal append ordinals describe this observer's actual order. They are not producer-global sequence numbers or trusted timestamps. A case label, OID tuple, or digest is correlation data, not an existing producer operation ID or idempotency key.

## Phase and conformance limits

The raw helper exposes process observations, not model phases. Its `started` callback occurs before spawn, so it does not even prove the child started. A completed receipt and matching readback can support a bounded effect observation while leaving the operation-model interpretation unresolved.

Any abstraction must state its meaning and sources. Treating an offered invocation as CLAIMED until an observed ref update is a proposed interpretation, not a literal runtime phase. Mapping process start to EXECUTING encounters the existing model's missing EXECUTING-to-FAILED edge. Do not insert an unobserved step or change the model to obtain a match.

No-effect reconciliation in this trial means a supported, invocation-specific no-ref-update finding after the rejection. It is not a reconciliation-before-retry witness because no retry occurs. The full producer's no-replay contract remains intact.

Git and the selected helper supply no native operation ID or idempotency key for the normalized retry checks. Do not manufacture them from the case label or ref intent. Dependent `FVL-RETRY`, binding, at-most-once, and full-trace conformance claims remain UNKNOWN. Record any independently supported raw observation separately. See [the evidence obligations](EFFECT-RETRY-EVIDENCE.md) and [the retry mapping limits](RETRY-CONFORMANCE.md).

This design adds no evaluator write client, new producer identity protocol, manager, CLI state condition, or runtime gate. The current Session selects and reviews the evidence. Discovery and partial checks require no original Owner, original Session, or complete private bundle.

## Stop and retain uncertainty

Stop the affected effect path for resource refusal, missing permission, source or configuration drift, an unexpected writer, an unexpected ref, a journal failure, timeout, decode error, interruption, or a started-only receipt. Preserve the original result and use bounded readback. Do not replay an unknown operation or silently classify it as a known CAS refusal.

Retain failures, partial inputs, UNKNOWN findings, and measured costs. Unavailable usage or money remains unknown. No result here switches the active version, merges a branch, or changes #448, #450, or escrow. A later admitted run is new evidence under its recorded source and boundary; it does not overwrite historical failures.

The separate [abstract CAS model checks](LOCAL-REF-CAS-FORMAL.md) now have an eight-step bounded safety result, two planted counterexamples and three reachability witnesses. They do not change the NOT_RUN status of these real fixture cases or establish effect-retry conformance.
