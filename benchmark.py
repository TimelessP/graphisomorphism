#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import math
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any

from graph_iso import build_graph_from_binary, compare_graphs


ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "examples" / "src"
BIN_DIR = ROOT_DIR / "examples" / "bin"


SCENARIOS = {
    "partial": {
        "name": "partial",
        "left": BIN_DIR / "prog_a",
        "right": BIN_DIR / "prog_b",
        "min_size": 1,
    },
    "multi": {
        "name": "multi",
        "left": BIN_DIR / "prog_multi_a",
        "right": BIN_DIR / "prog_multi_b",
        "min_size": 4,
    },
}


def build_examples() -> None:
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    commands = [
        ["gcc", "-O0", "-fno-inline", "-fno-omit-frame-pointer", str(SRC_DIR / "prog_a.c"), "-o", str(BIN_DIR / "prog_a")],
        ["gcc", "-O0", "-fno-inline", "-fno-omit-frame-pointer", str(SRC_DIR / "prog_b.c"), "-o", str(BIN_DIR / "prog_b")],
        [
            "gcc",
            "-O0",
            "-fno-inline",
            "-fno-omit-frame-pointer",
            str(SRC_DIR / "prog_multi_a.c"),
            "-o",
            str(BIN_DIR / "prog_multi_a"),
        ],
        [
            "gcc",
            "-O0",
            "-fno-inline",
            "-fno-omit-frame-pointer",
            str(SRC_DIR / "prog_multi_b.c"),
            "-o",
            str(BIN_DIR / "prog_multi_b"),
        ],
    ]

    for command in commands:
        process = subprocess.run(command, capture_output=True, text=True, check=False)
        if process.returncode != 0:
            message = process.stderr.strip() or process.stdout.strip() or "unknown gcc failure"
            raise RuntimeError(f"Build failed: {' '.join(command)}\n{message}")


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, math.ceil((p / 100.0) * len(ordered)) - 1))
    return ordered[index]


def summarize(name: str, values: list[float]) -> dict[str, float | str]:
    return {
        "metric": name,
        "mean_ms": statistics.mean(values) * 1000.0,
        "p50_ms": percentile(values, 50) * 1000.0,
        "p95_ms": percentile(values, 95) * 1000.0,
        "min_ms": min(values) * 1000.0,
        "max_ms": max(values) * 1000.0,
        "ops_per_sec": (len(values) / sum(values)) if sum(values) > 0 else 0.0,
    }


def run_one_scenario(
    scenario: dict[str, Any],
    iterations: int,
    warmup: int,
    max_report: int,
    all_sizes_min: int,
) -> dict[str, Any]:
    left_bin = Path(scenario["left"])
    right_bin = Path(scenario["right"])
    min_size_default = int(scenario["min_size"])

    extract_times: list[float] = []
    compare_best_times: list[float] = []
    compare_all_times: list[float] = []

    left_nodes = None
    right_nodes = None
    best_report: dict[str, Any] | None = None
    all_report: dict[str, Any] | None = None

    total_runs = warmup + iterations
    for run in range(total_runs):
        t0 = time.perf_counter()
        left_graph = build_graph_from_binary(left_bin)
        right_graph = build_graph_from_binary(right_bin)
        t1 = time.perf_counter()

        best = compare_graphs(
            left=left_graph,
            right=right_graph,
            left_name="left",
            right_name="right",
            max_report=max_report,
            collect_all_sizes=False,
            min_size=min_size_default,
            size_filter=None,
        )
        t2 = time.perf_counter()

        all_sizes = compare_graphs(
            left=left_graph,
            right=right_graph,
            left_name="left",
            right_name="right",
            max_report=max_report,
            collect_all_sizes=True,
            min_size=max(min_size_default, all_sizes_min),
            size_filter=None,
        )
        t3 = time.perf_counter()

        if run >= warmup:
            extract_times.append(t1 - t0)
            compare_best_times.append(t2 - t1)
            compare_all_times.append(t3 - t2)

        left_nodes = left_graph["node_count"]
        right_nodes = right_graph["node_count"]
        best_report = best
        all_report = all_sizes

    return {
        "scenario": scenario["name"],
        "left_binary": str(left_bin),
        "right_binary": str(right_bin),
        "iterations": iterations,
        "warmup": warmup,
        "node_counts": {"left": left_nodes, "right": right_nodes},
        "last_best_compare": {
            "best_match_size": best_report["best_match_size"],
            "fit_ratio_against_min_nodes": best_report["fit_ratio_against_min_nodes"],
            "match_count_reported": best_report["match_count_reported"],
        },
        "last_all_sizes_compare": {
            "best_match_size": all_report["best_match_size"],
            "fit_ratio_against_min_nodes": all_report["fit_ratio_against_min_nodes"],
            "match_count_reported": all_report["match_count_reported"],
            "min_size_considered": all_report["min_size_considered"],
        },
        "timing": {
            "extract_pair": summarize("extract_pair", extract_times),
            "compare_best": summarize("compare_best", compare_best_times),
            "compare_all_sizes": summarize("compare_all_sizes", compare_all_times),
        },
    }


def print_summary(results: list[dict[str, Any]]) -> None:
    print("\nBenchmark summary (milliseconds)")
    print("=" * 88)
    for result in results:
        print(
            f"Scenario={result['scenario']} nodes(L/R)={result['node_counts']['left']}/{result['node_counts']['right']} "
            f"iter={result['iterations']}"
        )
        for key in ("extract_pair", "compare_best", "compare_all_sizes"):
            row = result["timing"][key]
            print(
                f"  {key:18} mean={row['mean_ms']:.2f} p50={row['p50_ms']:.2f} "
                f"p95={row['p95_ms']:.2f} min={row['min_ms']:.2f} max={row['max_ms']:.2f} ops/s={row['ops_per_sec']:.2f}"
            )
        print(
            "  compare(best): "
            f"best_size={result['last_best_compare']['best_match_size']} "
            f"ratio={result['last_best_compare']['fit_ratio_against_min_nodes']:.2%} "
            f"matches={result['last_best_compare']['match_count_reported']}"
        )
        print(
            "  compare(all):  "
            f"best_size={result['last_all_sizes_compare']['best_match_size']} "
            f"ratio={result['last_all_sizes_compare']['fit_ratio_against_min_nodes']:.2%} "
            f"matches={result['last_all_sizes_compare']['match_count_reported']}"
        )
        print("-" * 88)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark extract/compare performance on known sample binaries.")
    parser.add_argument("--iterations", type=int, default=10, help="Measured iterations per scenario")
    parser.add_argument("--warmup", type=int, default=1, help="Warmup iterations per scenario")
    parser.add_argument("--max-report", type=int, default=200, help="Max matches reported in compare calls")
    parser.add_argument("--all-sizes-min", type=int, default=4, help="Minimum size for all-sizes compare benchmark")
    parser.add_argument(
        "--scenario",
        choices=["all", "partial", "multi"],
        default="all",
        help="Which sample scenario to benchmark",
    )
    parser.add_argument("--skip-build", action="store_true", help="Skip rebuilding sample binaries")
    parser.add_argument("--json-output", type=str, help="Optional path to write benchmark JSON report")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.iterations < 1:
        parser.error("--iterations must be >= 1")
    if args.warmup < 0:
        parser.error("--warmup must be >= 0")
    if args.max_report < 1:
        parser.error("--max-report must be >= 1")
    if args.all_sizes_min < 1:
        parser.error("--all-sizes-min must be >= 1")

    if not args.skip_build:
        print("Building example binaries...")
        build_examples()

    selected = [SCENARIOS[args.scenario]] if args.scenario != "all" else [SCENARIOS["partial"], SCENARIOS["multi"]]

    results = []
    for scenario in selected:
        print(f"Running scenario: {scenario['name']}")
        result = run_one_scenario(
            scenario=scenario,
            iterations=args.iterations,
            warmup=args.warmup,
            max_report=args.max_report,
            all_sizes_min=args.all_sizes_min,
        )
        results.append(result)

    print_summary(results)

    if args.json_output:
        out_path = Path(args.json_output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({"results": results}, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote JSON benchmark report to {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
