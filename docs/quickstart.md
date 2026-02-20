# Analyst Quickstart (10 Commands)

Use this page when you want fast triage on ELF binaries with graph-structure matching.

## 0) Enter project folder

```bash
cd graphisomorphism
```

## 1) Extract graph from known/baseline sample

```bash
python3 graph_iso.py extract \
  --binary /path/to/baseline.elf \
  --output out/baseline.graph.json
```

## 2) Compare unknown sample to baseline (best-size mode)

```bash
python3 graph_iso.py compare \
  --binary /path/to/suspect.elf \
  --prior-graph out/baseline.graph.json \
  --output out/compare.best.json \
  --extracted-output out/suspect.graph.json
```

## 3) Compare and collect plural matches (all sizes)

```bash
python3 graph_iso.py compare \
  --binary /path/to/suspect.elf \
  --prior-graph out/baseline.graph.json \
  --output out/compare.all.json \
  --collect-all-sizes \
  --min-size 4 \
  --max-report 200
```

## 4) Focus on one exact subgraph size

```bash
python3 graph_iso.py compare \
  --binary /path/to/suspect.elf \
  --prior-graph out/baseline.graph.json \
  --output out/compare.size12.json \
  --collect-all-sizes \
  --min-size 4 \
  --size-filter 12 \
  --max-report 200
```

## 5) Print quick summary from a report

```bash
python3 - <<'PY'
import json
from pathlib import Path

path = Path('out/compare.all.json')
d = json.loads(path.read_text(encoding='utf-8'))
c = d['comparison']
print('best_match_size:', c['best_match_size'])
print('fit_ratio_against_min_nodes:', f"{c['fit_ratio_against_min_nodes']:.2%}")
print('match_count_reported:', c['match_count_reported'])
print('first_5_matches:', c['matches'][:5])
PY
```

## 6) Run included demos

```bash
./test-run.sh
./test-run-miss.sh
./test-run-examples.sh
./test-run-examples-multi.sh
./test-run-examples-multi.sh 14
```

## How to read results quickly

- `best_match_size`: Largest shared subgraph window between samples.
- `fit_ratio_against_min_nodes`: Best-size normalized by the smaller graph size.
- `match_count_reported`: How many windows were reported (can be plural in all-sizes mode).
- `matches[]`: Start offsets and size for each overlapping subgraph candidate.

## Triage hints

- High ratio + many matches: strong family-level similarity.
- High ratio + few matches: one large shared routine.
- Low ratio + non-zero match: partial reuse, still worth deeper RE.
- Use `--size-filter` to isolate repeated motifs of one size.
