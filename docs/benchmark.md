# Benchmark Guide and Results

This document shows how to benchmark the project on known sample binaries and compares those measurements with one reference run from this repository.

## Important note

Your numbers will vary by CPU, storage, OS scheduling, Python version, and background load. The goal is reproducibility of the method, not identical absolute timings.

## Reproduce the benchmark

From the project root:

```bash
/home/t/PycharmProjects/graphisomorphism/.venv/bin/python benchmark.py \
  --json-output out/benchmark.json
```

What this runs:
- Builds example binaries in `examples/bin`
- Benchmarks `partial` scenario (`prog_a` vs `prog_b`)
- Benchmarks `multi` scenario (`prog_multi_a` vs `prog_multi_b`)
- Measures three stages per scenario:
  - `extract_pair`
  - `compare_best`
  - `compare_all_sizes`

## Optional benchmark controls

```bash
# More stable numbers
/home/t/PycharmProjects/graphisomorphism/.venv/bin/python benchmark.py --iterations 100 --warmup 5

# Benchmark only one scenario
/home/t/PycharmProjects/graphisomorphism/.venv/bin/python benchmark.py --scenario partial

# Skip rebuilding binaries between runs
/home/t/PycharmProjects/graphisomorphism/.venv/bin/python benchmark.py --skip-build
```

## Reference run (20 Feb 2026)

Command used:

```bash
/home/t/PycharmProjects/graphisomorphism/.venv/bin/python benchmark.py --json-output out/benchmark.json
```

### Scenario: partial (`prog_a` vs `prog_b`)

- Iterations: `10` (warmup `1`)
- Nodes: left `21`, right `22`
- Best compare result: `best_match_size=14`, `fit_ratio_against_min_nodes=66.67%`, `matches=1`
- All-sizes result: `best_match_size=14`, `fit_ratio_against_min_nodes=66.67%`, `matches=70`

| Metric | Mean (ms) | P50 (ms) | P95 (ms) | Min (ms) | Max (ms) | Ops/s |
|---|---:|---:|---:|---:|---:|---:|
| extract_pair | 11.58 | 10.92 | 13.83 | 9.53 | 13.83 | 86.38 |
| compare_best | 2.65 | 2.51 | 3.84 | 1.97 | 3.84 | 377.58 |
| compare_all_sizes | 8.18 | 7.53 | 10.47 | 6.73 | 10.47 | 122.18 |

### Scenario: multi (`prog_multi_a` vs `prog_multi_b`)

- Iterations: `10` (warmup `1`)
- Nodes: left `19`, right `21`
- Best compare result: `best_match_size=15`, `fit_ratio_against_min_nodes=78.95%`, `matches=1`
- All-sizes result: `best_match_size=15`, `fit_ratio_against_min_nodes=78.95%`, `matches=82`

| Metric | Mean (ms) | P50 (ms) | P95 (ms) | Min (ms) | Max (ms) | Ops/s |
|---|---:|---:|---:|---:|---:|---:|
| extract_pair | 11.67 | 10.14 | 15.30 | 9.77 | 15.30 | 85.67 |
| compare_best | 1.51 | 1.50 | 2.06 | 1.08 | 2.06 | 662.46 |
| compare_all_sizes | 7.38 | 6.80 | 9.52 | 5.65 | 9.52 | 135.50 |

## Interpreting performance

- `extract_pair` is usually dominated by `objdump` + parsing.
- `compare_best` is fastest because it stops at first largest overlap.
- `compare_all_sizes` is slower by design because it continues collecting plural matches.
