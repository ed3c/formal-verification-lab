#!/usr/bin/env bash
set -euo pipefail

toolchain="${FVL_TOOLCHAIN:-}"
evidence_dir="${FVL_EVIDENCE_DIR:-.p3-evidence}"
if [[ -z "$toolchain" ]]; then
  echo 'MODEL_CHECK=NOT_RUN: set FVL_TOOLCHAIN to the pinned toolchain directory' >&2
  exit 3
fi

exec python3 scripts/p3/run.py \
  --toolchain "$toolchain" \
  --evidence-dir "$evidence_dir" \
  "$@"
