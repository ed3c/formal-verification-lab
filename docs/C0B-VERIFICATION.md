# C0b verification

This document records the exact-file-scope repair. It does not replace the original C0 record and does not close P1 through P8.

## Source custody

The retained source contained 199 files. Every retained file matched the custody SHA-256 list. The pinned source manifest contains 188 files at ref `b58b14a021ed58c12fa374397aacba2e74e424bd`.

The source verifier accepted the recorded C0 integration for `scripts/check_models.sh` and the two-name `fail` to `markFailed` parser repair. C0b removed `scripts/p3/models/canary.qnt` and `scripts/p3/models/operation.qnt`. The remaining P3 harnesses import `specs/operation.qnt` directly.

## Local verification

The following checks passed.

```text
python3 -m py_compile scripts/p3/run.py scripts/p3/validate.py scripts/p3/verify_sources.py tests/test_p3_runner.py
PYTHONPATH=src pytest -q
43 passed
PYTHONPATH=src pytest -q tests/test_p3_runner.py
4 passed
PYTHONPATH=src python3 -m formal_verification_lab.cli controls fixtures/cases
23 of 23 synthetic controls matched
quint typecheck specs/operation.qnt
exit 0
quint typecheck specs/canary.qnt
exit 0
```

The prior runner evidence was executed with `bash scripts/check_models.sh` and the pinned toolchain. Both repository typecheck processes exited 0 and reported unchanged inputs. The first checker query could not bind a fresh ephemeral local port. The runner wrote a `fvl.p3-capability.v1` receipt with `status` `NOT_RUN`, `reason` `LOCAL_PORT_UNAVAILABLE`, and `fixed_port_fallback` `false`. The command exited 2. No checker result, canary violation trace, terminal witness, or induction receipt was claimed. That evidence predates the current input-manifest validator repair and is not reused as acceptance for this changed candidate.

The repaired runner records one common input manifest and the model, harness, runner, validator, repository specs, manifest, and toolchain input digests. The validator independently checks every command's before and after maps against that manifest. Raw host-specific evidence stays outside tracked source.

## Remaining status

C0b is not outer checker acceptance. The authorized outer Session must run bounded12, canary2 with a real ITF violation, terminal reachability, separate reconciliation, and independent induction on this exact candidate. P1, P2, P4, P5, P6, P7, and P8 remain `NOT_RUN`. The original C0 non-delivery remains explicit.
