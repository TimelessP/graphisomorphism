#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${ROOT_DIR}/out-miss"

BIN_A="${1:-/bin/true}"
BIN_B="${2:-/bin/ls}"

mkdir -p "${OUT_DIR}"

echo "[1/3] Extracting graph from ${BIN_A}"
python3 "${ROOT_DIR}/graph_iso.py" extract \
  --binary "${BIN_A}" \
  --output "${OUT_DIR}/graph_a.json"

echo "[2/3] Extracting + comparing graph from ${BIN_B}"
python3 "${ROOT_DIR}/graph_iso.py" compare \
  --binary "${BIN_B}" \
  --prior-graph "${OUT_DIR}/graph_a.json" \
  --output "${OUT_DIR}/comparison.json" \
  --extracted-output "${OUT_DIR}/graph_b.json"

echo "[3/3] Summary from comparison report"
python3 - <<'PY'
import json
from pathlib import Path

report = json.loads(Path("out-miss/comparison.json").read_text(encoding="utf-8"))
cmp = report["comparison"]
print("best_match_size:", cmp["best_match_size"])
print("fit_ratio_against_min_nodes:", f"{cmp['fit_ratio_against_min_nodes']:.2%}")
print("match_count_reported:", cmp["match_count_reported"])
PY

echo "Done. Outputs written to ${OUT_DIR}"
