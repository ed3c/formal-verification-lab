# P4 portable pure-contract verification

P4 checks two pure necessary-condition predicates. CrossHair analyzes only `src/formal_verification_lab/formal_contracts.py`. The runner does not import a Provider adapter or execute Production handlers.

## Portable runner contract

Install the exact packages in `requirements-verification.lock.txt`. `verification-downloads.json` records the hashes of the macOS arm64 artifacts used for the observed run. Other platforms must resolve their own artifacts and retain their download hashes.

Run the checker with a new evidence directory outside the repository:

```sh
<verification-python> scripts/p4.py --evidence-dir <new-external-evidence-dir>
```

The runner uses `sys.executable` for every child process. It records the Python and package versions, actual arguments, working directory, wall timeout, CrossHair bounds, Hypothesis seed, stdout, stderr, exits, and input digests before and after each process.

The runner accepts a result only when all conditions hold:

- CrossHair exits 0 and reports exactly two `Confirmed over all paths.` results.
- The unsafe canary exits 1 and reports that `unchecked_effect(False)` returns `True` and violates its postcondition.
- Hypothesis runs both properties with seed `20261024`, reports two passes, and reports no skipped or expected-failure result.
- The literal oracle checks all 32 effect combinations and all 24 receipt combinations.
- The literal always-False canary misses the one accepted effect case and produces a concrete counterexample.
- Every input digest remains unchanged.

The runner uses explicit exceptions and exit handling for acceptance. Python optimization cannot remove the checks. Missing packages or version differences produce diagnostic `NOT_RUN`. Process errors, malformed output, wrong counts, timeouts, or changed inputs produce `NOT_VERIFIED`.

## Current candidate observation

The current run used Python 3.13.1, CrossHair 0.0.112, icontract 2.7.3, Hypothesis 6.170.9, and pytest 9.1.1. All 21 locked packages matched.

| Run | Exit | Validated observation |
| --- | ---: | --- |
| CrossHair pure contracts | 0 | Two confirmed postconditions. The per-condition limit was 10 seconds and the per-path limit was 5 seconds. |
| Unsafe CrossHair canary | 1 | A real `unchecked_effect(False) -> True` postcondition counterexample. |
| Hypothesis sampling | 0 | Two properties passed with seed `20261024`; no skip. |
| Literal controls | 0 | 32 effect cases, 24 receipt cases, and one always-False counterexample. |

The four processes reported unchanged inputs. The result is `BOUNDED_PASS` for these pure predicates. It does not prove authorization authenticity, a complete Provider ledger, Native refinement, or Production acceptance.

The earlier standalone P4 report is a historical receipt for different source custody. This candidate reran the portable entry point and did not reuse that report as acceptance.
