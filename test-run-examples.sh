#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="${ROOT_DIR}/examples/src"
BIN_DIR="${ROOT_DIR}/examples/bin"
OUT_DIR="${ROOT_DIR}/out-examples"

mkdir -p "${BIN_DIR}" "${OUT_DIR}"

echo "[1/4] Building example binaries"
gcc -O0 -fno-inline -fno-omit-frame-pointer "${SRC_DIR}/prog_a.c" -o "${BIN_DIR}/prog_a"
gcc -O0 -fno-inline -fno-omit-frame-pointer "${SRC_DIR}/prog_b.c" -o "${BIN_DIR}/prog_b"

echo "[2/4] Extracting graph from prog_a"
python3 "${ROOT_DIR}/graph_iso.py" extract \
  --binary "${BIN_DIR}/prog_a" \
  --output "${OUT_DIR}/graph_a.json"

echo "[3/4] Comparing prog_b against prog_a graph"
python3 "${ROOT_DIR}/graph_iso.py" compare \
  --binary "${BIN_DIR}/prog_b" \
  --prior-graph "${OUT_DIR}/graph_a.json" \
  --output "${OUT_DIR}/comparison.json" \
  --extracted-output "${OUT_DIR}/graph_b.json"

echo "[4/4] Summary"
python3 - <<'PY'
import json
from pathlib import Path

report = json.loads(Path("out-examples/comparison.json").read_text(encoding="utf-8"))
cmp = report["comparison"]
print("best_match_size:", cmp["best_match_size"])
print("fit_ratio_against_min_nodes:", f"{cmp['fit_ratio_against_min_nodes']:.2%}")
print("match_count_reported:", cmp["match_count_reported"])
if cmp["matches"]:
    print("first_match:", cmp["matches"][0])
PY

echo "Done. Binaries in ${BIN_DIR}, reports in ${OUT_DIR}"
