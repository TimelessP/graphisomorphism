#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


CONDITIONAL_LOOP_PREFIXES = ("loop",)
UNCONDITIONAL_JUMPS = {"jmp", "jmpq", "ljmp"}


def is_elf(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(4) == b"\x7fELF"
    except OSError:
        return False


def is_conditional_jump(mnemonic: str) -> bool:
    name = mnemonic.lower().strip()
    if name.startswith("j") and name not in UNCONDITIONAL_JUMPS:
        return True
    return any(name.startswith(prefix) for prefix in CONDITIONAL_LOOP_PREFIXES)


def parse_instruction_line(line: str) -> tuple[int, str, str] | None:
    if ":" not in line:
        return None
    left, right = line.split(":", 1)
    left = left.strip()
    if not left or any(ch not in "0123456789abcdefABCDEF" for ch in left):
        return None

    address = int(left, 16)
    tokens = right.strip().split()
    if not tokens:
        return None

    index = 0
    while index < len(tokens) and re.fullmatch(r"[0-9a-fA-F]{2}", tokens[index]):
        index += 1

    if index >= len(tokens):
        return None

    mnemonic = tokens[index]
    operands = " ".join(tokens[index + 1 :])
    return address, mnemonic, operands


def parse_target_address(operands: str) -> int | None:
    if not operands:
        return None

    symbol_form = re.search(r"\b([0-9a-fA-F]+)\s*<", operands)
    if symbol_form:
        return int(symbol_form.group(1), 16)

    hex_form = re.search(r"\b0x([0-9a-fA-F]+)\b", operands)
    if hex_form:
        return int(hex_form.group(1), 16)

    plain_form = re.search(r"\b([0-9a-fA-F]{4,})\b", operands)
    if plain_form:
        return int(plain_form.group(1), 16)

    return None


def run_objdump(binary: Path) -> str:
    command = ["objdump", "-d", str(binary)]
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    if process.returncode != 0:
        raise RuntimeError(f"objdump failed: {process.stderr.strip() or process.stdout.strip()}")
    return process.stdout


def build_graph_from_binary(binary: Path) -> dict[str, Any]:
    if not binary.exists():
        raise FileNotFoundError(f"Binary not found: {binary}")
    if not is_elf(binary):
        raise ValueError(f"File is not an ELF executable: {binary}")

    disassembly = run_objdump(binary)
    nodes: list[dict[str, Any]] = []
    jump_targets: list[int | None] = []
    addr_to_node_id: dict[int, int] = {}

    for line in disassembly.splitlines():
        parsed = parse_instruction_line(line)
        if parsed is None:
            continue
        address, mnemonic, operands = parsed
        if not is_conditional_jump(mnemonic):
            continue

        node_id = len(nodes)
        addr_to_node_id[address] = node_id
        target = parse_target_address(operands)
        jump_targets.append(target)
        nodes.append(
            {
                "id": node_id,
                "address": f"0x{address:x}",
                "mnemonic": mnemonic.lower(),
                "target": f"0x{target:x}" if target is not None else None,
            }
        )

    edge_set: set[tuple[int, int, str]] = set()
    for index in range(len(nodes) - 1):
        edge_set.add((index, index + 1, "seq"))

    for src, target_addr in enumerate(jump_targets):
        if target_addr is None:
            continue
        dst = addr_to_node_id.get(target_addr)
        if dst is not None:
            edge_set.add((src, dst, "jmp"))

    edges = [
        {"src": src, "dst": dst, "type": edge_type}
        for src, dst, edge_type in sorted(edge_set, key=lambda item: (item[0], item[1], item[2]))
    ]

    return {
        "version": 1,
        "binary": str(binary),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }


def load_graph(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    required = {"nodes", "edges", "node_count", "edge_count"}
    missing = required - set(data)
    if missing:
        raise ValueError(f"Graph file missing required keys: {sorted(missing)}")
    return data


def window_fingerprint(graph: dict[str, Any], start: int, size: int) -> str:
    stop = start + size
    id_map = {old: new for new, old in enumerate(range(start, stop))}

    node_labels = tuple(graph["nodes"][old]["mnemonic"] for old in range(start, stop))
    edge_tuples: list[tuple[int, int, str]] = []
    for edge in graph["edges"]:
        src = edge["src"]
        dst = edge["dst"]
        if start <= src < stop and start <= dst < stop:
            edge_tuples.append((id_map[src], id_map[dst], edge["type"]))

    edge_tuples.sort()
    payload = {"labels": node_labels, "edges": edge_tuples}
    encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def collect_window_map(graph: dict[str, Any], size: int) -> dict[str, list[int]]:
    node_count = graph["node_count"]
    if size <= 0 or size > node_count:
        return {}

    result: dict[str, list[int]] = {}
    for start in range(0, node_count - size + 1):
        fp = window_fingerprint(graph, start, size)
        result.setdefault(fp, []).append(start)
    return result


def compare_graphs(
    left: dict[str, Any],
    right: dict[str, Any],
    left_name: str,
    right_name: str,
    max_report: int,
    collect_all_sizes: bool,
    min_size: int,
    size_filter: int | None,
) -> dict[str, Any]:
    max_size = min(left["node_count"], right["node_count"])
    best_matches: list[dict[str, int]] = []
    all_matches: list[dict[str, int]] = []
    best_size = 0

    for size in range(max_size, min_size - 1, -1):
        left_windows = collect_window_map(left, size)
        right_windows = collect_window_map(right, size)
        overlap = set(left_windows) & set(right_windows)
        if not overlap:
            continue

        for fingerprint in overlap:
            for left_start in left_windows[fingerprint]:
                for right_start in right_windows[fingerprint]:
                    match = {
                        f"{left_name}_start": left_start,
                        f"{right_name}_start": right_start,
                        "size": size,
                    }
                    passes_filter = (size_filter is None) or (size == size_filter)
                    if (size == best_size or best_size == 0) and passes_filter:
                        best_matches.append(match)
                    if collect_all_sizes and passes_filter:
                        all_matches.append(match)
                    reported_count = len(all_matches) if collect_all_sizes else len(best_matches)
                    if reported_count >= max_report:
                        break
                reported_count = len(all_matches) if collect_all_sizes else len(best_matches)
                if reported_count >= max_report:
                    break
            reported_count = len(all_matches) if collect_all_sizes else len(best_matches)
            if reported_count >= max_report:
                break

        if best_size == 0:
            best_size = size
            if not collect_all_sizes:
                break
        if collect_all_sizes and len(all_matches) >= max_report:
            break

    reported_matches = all_matches if collect_all_sizes else best_matches

    min_nodes = min(left["node_count"], right["node_count"])
    fit_ratio = (best_size / min_nodes) if min_nodes else 0.0
    return {
        "best_match_size": best_size,
        "fit_ratio_against_min_nodes": fit_ratio,
        "collect_all_sizes": collect_all_sizes,
        "min_size_considered": min_size,
        "size_filter": size_filter,
        "match_count_reported": len(reported_matches),
        "matches": reported_matches,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def cmd_extract(args: argparse.Namespace) -> int:
    graph = build_graph_from_binary(Path(args.binary))
    write_json(Path(args.output), graph)
    print(f"Wrote graph with {graph['node_count']} nodes and {graph['edge_count']} edges to {args.output}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    new_graph = build_graph_from_binary(Path(args.binary))
    prior_graph = load_graph(Path(args.prior_graph))

    if args.extracted_output:
        write_json(Path(args.extracted_output), new_graph)

    report = compare_graphs(
        left=prior_graph,
        right=new_graph,
        left_name="prior",
        right_name="new",
        max_report=args.max_report,
        collect_all_sizes=args.collect_all_sizes,
        min_size=args.min_size,
        size_filter=args.size_filter,
    )

    payload = {
        "mode": "compare",
        "prior_graph": str(args.prior_graph),
        "new_binary": str(args.binary),
        "prior_node_count": prior_graph["node_count"],
        "new_node_count": new_graph["node_count"],
        "comparison": report,
    }
    write_json(Path(args.output), payload)
    print(
        "Best fit size "
        f"{report['best_match_size']}"
        f" ({report['fit_ratio_against_min_nodes']:.2%} of min(node_count)), "
        f"reported matches: {report['match_count_reported']}"
    )
    print(f"Wrote comparison report to {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract conditional-jump fingerprint graphs from ELF binaries and compare shared subgraph structure."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    extract = sub.add_parser("extract", help="Extract conditional-jump graph from ELF binary")
    extract.add_argument("--binary", required=True, help="Path to target ELF binary")
    extract.add_argument("--output", required=True, help="Path to graph JSON output")
    extract.set_defaults(func=cmd_extract)

    compare = sub.add_parser("compare", help="Compare new binary graph against prior graph JSON")
    compare.add_argument("--binary", required=True, help="Path to new target ELF binary")
    compare.add_argument("--prior-graph", required=True, help="Path to previously extracted graph JSON")
    compare.add_argument("--output", required=True, help="Path to comparison JSON output")
    compare.add_argument(
        "--extracted-output",
        required=False,
        help="Optional path to also save the newly extracted graph JSON",
    )
    compare.add_argument(
        "--max-report",
        type=int,
        default=200,
        help="Maximum number of matching windows to report",
    )
    compare.add_argument(
        "--collect-all-sizes",
        action="store_true",
        help="Collect matching windows across all sizes down to --min-size (instead of only best size)",
    )
    compare.add_argument(
        "--min-size",
        type=int,
        default=1,
        help="Minimum subgraph window size to consider during compare",
    )
    compare.add_argument(
        "--size-filter",
        type=int,
        required=False,
        help="Only report matches with this exact window size",
    )
    compare.set_defaults(func=cmd_compare)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if getattr(args, "command", None) == "compare" and args.min_size < 1:
            parser.error("--min-size must be >= 1")
        if getattr(args, "command", None) == "compare" and args.size_filter is not None and args.size_filter < 1:
            parser.error("--size-filter must be >= 1")
        return args.func(args)
    except Exception as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
