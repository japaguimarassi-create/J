#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
TARGET="${1:-16820000}"
CHUNK="${2:-1000}"
OUT="${3:-checkpoints/continuous-16820x1000}"
INIT="${4:-checkpoints/mesh-smoke-final.pt}"
mkdir -p "$OUT"
if [[ ! "$TARGET" =~ ^[0-9]+$ ]] || [[ "$TARGET" -lt 1 ]]; then
  printf '%s\n' 'TARGET must be a positive integer.' >&2
  exit 2
fi
if [[ ! "$CHUNK" =~ ^[0-9]+$ ]] || [[ "$CHUNK" -lt 1 ]]; then
  printf '%s\n' 'CHUNK must be a positive integer.' >&2
  exit 2
fi
while true; do
  if [[ -s "$OUT/latest.pt" ]]; then
    STEP="$(python - "$OUT/latest.pt" <<'PY'
import sys
import torch
checkpoint = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
print(int(checkpoint.get("global_step", checkpoint.get("step", 0))))
PY
)"
    if [[ "$STEP" -ge "$TARGET" ]]; then
      printf 'Target reached: %s / %s cycles\n' "$STEP" "$TARGET"
      break
    fi
    python -u -m ai.continuous_refine --total-cycles "$TARGET" --max-updates-this-run "$CHUNK" --checkpoint-every "$CHUNK" --eval-every "$CHUNK" --resume "$OUT/latest.pt" --output-dir "$OUT" 2>&1 | tee -a "$OUT/runner.log"
  else
    python -u -m ai.continuous_refine --total-cycles "$TARGET" --max-updates-this-run "$CHUNK" --checkpoint-every "$CHUNK" --eval-every "$CHUNK" --init-checkpoint "$INIT" --output-dir "$OUT" 2>&1 | tee -a "$OUT/runner.log"
  fi
done
