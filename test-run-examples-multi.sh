#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="${ROOT_DIR}/examples/src"
BIN_DIR="${ROOT_DIR}/examples/bin"
OUT_DIR="${ROOT_DIR}/out-examples-multi"
SIZE_FILTER="${1:-}"

mkdir -p "${BIN_DIR}" "${OUT_DIR}"

echo "[1/4] Building multi-match example binaries"
gcc -O0 -fno-inline -fno-omit-frame-pointer "${SRC_DIR}/prog_multi_a.c" -o "${BIN_DIR}/prog_multi_a"
gcc -O0 -fno-inline -fno-omit-frame-pointer "${SRC_DIR}/prog_multi_b.c" -o "${BIN_DIR}/prog_multi_b"

echo "[2/4] Extracting graph from prog_multi_a"
python3 "${ROOT_DIR}/graph_iso.py" extract \
  --binary "${BIN_DIR}/prog_multi_a" \
  --output "${OUT_DIR}/graph_a.json"

echo "[3/4] Comparing prog_multi_b against prog_multi_a graph"
COMPARE_CMD=(
  python3 "${ROOT_DIR}/graph_iso.py" compare
  --binary "${BIN_DIR}/prog_multi_b"
  --prior-graph "${OUT_DIR}/graph_a.json"
  --output "${OUT_DIR}/comparison.json"
  --extracted-output "${OUT_DIR}/graph_b.json"
  --collect-all-sizes
  --min-size 4
  --max-report 50
)

if [[ -n "${SIZE_FILTER}" ]]; then
  COMPARE_CMD+=(--size-filter "${SIZE_FILTER}")
fi

"${COMPARE_CMD[@]}"

echo "[4/4] Summary"
python3 - <<'PY'
import json
from pathlib import Path

report = json.loads(Path("out-examples-multi/comparison.json").read_text(encoding="utf-8"))
cmp = report["comparison"]
print("best_match_size:", cmp["best_match_size"])
print("fit_ratio_against_min_nodes:", f"{cmp['fit_ratio_against_min_nodes']:.2%}")
print("match_count_reported:", cmp["match_count_reported"])
print("sample_matches:")
for item in cmp["matches"][:5]:
    print("  ", item)
PY

echo "Done. Binaries in ${BIN_DIR}, reports in ${OUT_DIR}"
