# formal-verification-lab

`formal-verification-lab` is a standalone, read-only evaluator for Agent Harness state-transition safety contracts. The public core uses synthetic data. It has no Soodles runtime dependency, Provider credentials, network adapter, dispatch path, production admission path, or merge authority.

## Current verification status

The repository separates observations by checker and source bytes.

| Check | Current result | Limit |
| --- | --- | --- |
| Synthetic offline controls | `BOUNDED_PASS` | Synthetic fixtures do not establish Native behavior. |
| Finite Quint to Python named-action parity | `BOUNDED_PASS` | 14 reachable states, 31 Python edges, 13 actions, and 183 Quint tests on the current model. This is not all-state equivalence. |
| Python model exploration | `BOUNDED_PASS` | The terminal and `RECONCILING` witnesses are reachable. Liveness is `NOT_ESTABLISHED`. |
| P3 Quint and Apalache model checking | `BOUNDED_PASS`; separate typed induction `PASS` | Fresh external execution: safety bound 12; unsafe canary bound 2 with a one-transition ITF counterexample; terminal and RECONCILING witnesses of 6 transitions; three induction obligations. |
| P4 pure Python contracts | `BOUNDED_PASS` | CrossHair checked only `formal_contracts.py`. Hypothesis and literal controls do not establish authorization authenticity. |
| Selected evidence analysis | Supported | Repository/workspace discovery and per-property partial evaluation do not require a complete bundle or external mapping approval. |
| Full Native refinement and blind gain | `NOT_ESTABLISHED` | Limited observations do not establish unobserved effects, complete histories, or a comparable gain. |

The historical 188-file source manifest remains in `scripts/p3/source-manifest.json`. P3 records it as historical provenance. Current model checking does not require byte equality with that historical import.

## Run the public core

Run the synthetic controls and the complete Python suite without installing the package:

```sh
PYTHONPATH=src python3 -m formal_verification_lab.cli controls fixtures/cases
PYTHONPATH=src python3 -m pytest -q
PYTHONPATH=src python3 -m formal_verification_lab.model_explore --max-depth 12
```

Find evidence in a repository or workspace, then explicitly choose the available parts and properties:

```sh
PYTHONPATH=src python3 -m formal_verification_lab.cli discover <workspace> --max-depth 4 --max-entries 10000 --max-files 200
PYTHONPATH=src python3 -m formal_verification_lab.cli evaluate <workspace> --select operation=relative/operation.json --property FVL-LEGAL
```

Discovery lists file metadata and reports depth limits, entry/match truncation, symlinks and scan errors. It does not read and join all candidate records. Selection records the actual bytes' digests; omitted parts stay omitted. Missing operation identity does not prevent checking available transition endpoints, and a missing grant remains UNKNOWN for grant-dependent checks. See [partial evidence](docs/PARTIAL-EVIDENCE.md).

Run finite named-action parity with Quint 0.32.0. Use a new evidence directory outside the repository:

```sh
python3 scripts/parity.py \
  --toolchain <quint-toolchain> \
  --evidence-dir <new-external-evidence-dir>
```

Run P3 with the pinned Quint 0.32.0 and Apalache 0.56.1 toolchain:

```sh
python3 scripts/p3/run.py \
  --toolchain <quint-toolchain> \
  --evidence-dir <external-evidence-parent> \
  --tag p3
```

If the process cannot bind a fresh local port, P3 writes a diagnostic `NOT_RUN` receipt and exits 2. It never falls back to port 8822.

Run P4 from a Python environment installed from `requirements-verification.lock.txt`:

```sh
<verification-python> scripts/p4.py \
  --evidence-dir <new-external-evidence-dir>
```

The runner uses its own `sys.executable`. It saves package versions, commands, limits, stdout, stderr, exits, and before and after input digests. A missing or mismatched pinned environment returns `NOT_RUN`.

## Read selected source data and prepare blind packets

`python3 tools/read_bundle.py BUNDLE.json` reads only explicitly declared local files and JSON pointers. It preserves MISSING, UNREADABLE and DRIFT while retaining unrelated values. Its UTF-8 stdout limit is 1..65536 bytes, including the final newline. Source reads have no input-memory cap. The implementation uses POSIX descriptor APIs.

`PYTHONPATH=src python3 -m formal_verification_lab.blind_outcome --help` describes the closed eight-question format and neutral packet CLI. Schema validity does not score truth. The pure helpers in `blind_protocol.py` isolate profile data, provide task-local zsh overrides and prepare exact typed stdin. None starts a model or grants runtime effects.

`PYTHONPATH=src python3 -m formal_verification_lab.retry_conformance --help` describes selected lifecycle, resume and explicit operation-state checks. Native requeue is a conditional action candidate; missing operation/effect facts stay UNKNOWN. See [retry mapping](docs/RETRY-CONFORMANCE.md). The [effect evidence contract](docs/EFFECT-RETRY-EVIDENCE.md) explains how to collect missing operation, reconciliation and coverage facts without deriving them from worker records.

See the [verification protocol](docs/NATIVE-READBACK.md) and [reader handoff](docs/READER-HANDOFF.md). Public tests use synthetic data. Private experiment sources, independent answers, failures and costs stay outside Git.

The [local ref CAS design](docs/LOCAL-REF-CAS.md) selects the next real effect observation in isolated fixtures. Its rejection and positive cases remain NOT_RUN until normal Native admission and capture; they do not establish retry conformance.

The separate [abstract CAS checks](docs/LOCAL-REF-CAS-FORMAL.md) have an eight-step bounded safety result, two planted counterexamples and three reachability witnesses, including UNKNOWN with an effect. These model results do not supply a Native trace.

## Claim boundary

The model checks only the declared formal specification and bounds. `BOUNDED_PASS` is not production acceptance. Missing facts remain `UNKNOWN`; observed contradictions produce scoped findings. The current Session makes engineering judgments within the user-authorized scope. The Lab does not mutate the producer or Provider.

Keep private Owner records, Provider records, raw Native traces, credentials, and generated evidence outside this repository. A self-contained digest proves byte consistency only. It does not prove producer authorization, authenticity, or a trustworthy timestamp.

## Main files

- `specs/operation.qnt` contains the abstract protocol.
- `src/formal_verification_lab/model_explore.py` contains the finite Python translation.
- `scripts/parity.py` compares reachable named actions through the Quint parser and TypeScript backend.
- `scripts/p3/` contains standalone Quint and Apalache execution and validation.
- `scripts/p4.py` runs pure CrossHair, Hypothesis, and literal anti-vacuity controls.
- `docs/P2-PROGRESS.md` records the changed retry and progress assumptions.
- `docs/P4-CONTRACTS.md` records the portable P4 contract and current observation.
- `docs/DECOUPLING.md` defines the Lab and Soodles boundary.

## Source and license

The public core uses the MIT license. Dependencies keep their own licenses. `LICENSE` applies only to this project's original code.
