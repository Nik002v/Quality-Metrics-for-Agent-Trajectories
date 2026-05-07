# /// script
# dependencies = ["docent-python", "python-dotenv"]
# ///

#!/usr/bin/env python3
"""
trajectory_metrics.py  —  CLI tool for metrics from a single collection

Usage
-----
    uv run trajectory_metrics.py --input path/to/trajectory.json
    uv run trajectory_metrics.py --collection-id <collection_id> --all
    uv run trajectory_metrics.py --collection-id <collection_id> --all --aggregate
    uv run trajectory_metrics.py --collection-id <collection_id> --all --limit 5

.env
----
    DOCENT_API_KEY=...
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

try:
    from docent import Docent
    from docent.data_models import AgentRun
    from docent.data_models.chat.message import (
        SystemMessage, UserMessage, AssistantMessage, ToolMessage,
    )
except ImportError:
    Docent = None
    AgentRun = object
    SystemMessage = UserMessage = AssistantMessage = ToolMessage = ()


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class MessageCounts:
    system: int = 0
    user: int = 0
    assistant: int = 0
    tool: int = 0

    @property
    def total(self) -> int:
        return self.system + self.user + self.assistant + self.tool


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------
def count_messages(agent_run: AgentRun) -> MessageCounts:
    """Count messages by role across all transcripts in an AgentRun."""
    counts = MessageCounts()
    for transcript in agent_run.transcripts:
        for msg in transcript.messages:
            if isinstance(msg, SystemMessage):
                counts.system += 1
            elif isinstance(msg, UserMessage):
                counts.user += 1
            elif isinstance(msg, AssistantMessage):
                counts.assistant += 1
            elif isinstance(msg, ToolMessage):
                counts.tool += 1
    return counts


def count_messages_json(path: str) -> MessageCounts:
    """Count messages by role in a local trajectory JSON file."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "transcripts" in data:
        messages = [m for t in data["transcripts"] for m in t.get("messages", [])]
    elif isinstance(data, dict):
        messages = data.get("messages") or data.get("trajectory") or []
    else:
        messages = data

    counts = MessageCounts()
    for msg in messages:
        role = str(msg.get("role", "")).lower()
        if role == "system":
            counts.system += 1
        elif role == "user":
            counts.user += 1
        elif role == "assistant":
            counts.assistant += 1
        elif role == "tool":
            counts.tool += 1
    return counts


def process_collection(
    client: Docent,
    collection_id: str,
    limit: int | None = None,
    verbose: bool = True,
) -> list[tuple[str, MessageCounts]]:
    """
    Fetch all runs from collection and return list of (run_id, MessageCounts).
    This is the main function used by process_top5.py.
    """
    run_ids = client.list_agent_run_ids(collection_id)
    if limit:
        run_ids = run_ids[:limit]

    results: list[tuple[str, MessageCounts]] = []
    for i, run_id in enumerate(run_ids, 1):
        if verbose:
            print(f"  [{i:>3}/{len(run_ids)}] {run_id}", end=" ... ", flush=True)
        try:
            run = client.get_agent_run(collection_id, run_id)
            if run is None:
                if verbose:
                    print("NOT FOUND — skipped")
                continue
            counts = count_messages(run)
            results.append((run_id, counts))
            if verbose:
                print(
                    f"total={counts.total:>3} "
                    f"(sys={counts.system} usr={counts.user} "
                    f"ast={counts.assistant} tool={counts.tool})"
                )
        except Exception as e:
            if verbose:
                print(f"ERROR — {e}")
    return results


# ---------------------------------------------------------------------------
# Pretty print helpers
# ---------------------------------------------------------------------------
def print_counts(counts: MessageCounts, label: Optional[str] = None) -> None:
    sep = "=" * 30
    if label:
        print(f"\n{'—' * 30}")
        print(f"Run: {label}")
        print(f"{'—' * 30}")
    print(f"{'System messages:':<22} {counts.system:>4}")
    print(f"{'User messages:':<22} {counts.user:>4}")
    print(f"{'Assistant messages:':<22} {counts.assistant:>4}")
    print(f"{'Tool messages:':<22} {counts.tool:>4}")
    print(sep)
    print(f"{'Total messages:':<22} {counts.total:>4}")


def print_aggregate(all_counts: list[tuple[str, MessageCounts]]) -> None:
    if not all_counts:
        print("No runs to aggregate.")
        return
    n = len(all_counts)
    roles = {
        "System":    [c.system    for _, c in all_counts],
        "User":      [c.user      for _, c in all_counts],
        "Assistant": [c.assistant for _, c in all_counts],
        "Tool":      [c.tool      for _, c in all_counts],
        "Total":     [c.total     for _, c in all_counts],
    }
    print(f"\n{'=' * 50}")
    print(f"AGGREGATE STATISTICS  ({n} runs)")
    print(f"{'=' * 50}")
    print(f"{'Role':<22} {'Min':>6} {'Max':>6} {'Avg':>8}")
    print(f"{'-' * 46}")
    for label, vals in roles.items():
        print(
            f"{label + ' messages:':<22}"
            f"{min(vals):>6} {max(vals):>6} {sum(vals)/n:>8.1f}"
        )
    print(f"{'=' * 50}")


# ---------------------------------------------------------------------------
# Command Line Interface
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Metrics for trajectories from a single Docent collection.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input",
        help="Local trajectory JSON file to process.",
    )
    parser.add_argument(
        "--collection-id",
        help="Docent collection ID to process.",
    )
    parser.add_argument("--all", action="store_true", help="All runs in collection.")
    parser.add_argument("--aggregate", action="store_true", help="Print aggregate at end.")
    parser.add_argument("--api-key", default=os.getenv("DOCENT_API_KEY"))
    parser.add_argument("--limit", type=int, default=None)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.input:
        print_counts(count_messages_json(args.input), label=args.input)
        return
    if not args.collection_id:
        sys.exit("ERROR: Provide --input trajectory.json or --collection-id <collection_id>.")
    if Docent is None:
        sys.exit("ERROR: docent-python is not installed.\n       Run: uv run trajectory_metrics.py")
    if not args.api_key:
        sys.exit("ERROR: No API key found. Add DOCENT_API_KEY to .env")
    if not args.all:
        sys.exit("ERROR: Use --all flag to process all runs.")

    client = Docent(api_key=args.api_key)

    # All runs
    print(f"Listing runs in collection {args.collection_id} ...", flush=True)
    run_ids = client.list_agent_run_ids(args.collection_id)
    if not run_ids:
        sys.exit("No runs in this collection.")
    if args.limit:
        run_ids = run_ids[:args.limit]
    print(f"Found {len(run_ids)} run(s). Processing ...\n", flush=True)

    all_counts: list[tuple[str, MessageCounts]] = []
    for i, run_id in enumerate(run_ids, 1):
        print(f"[{i}/{len(run_ids)}] {run_id}", end=" ... ", flush=True)
        run = client.get_agent_run(args.collection_id, run_id)
        if run is None:
            print("NOT FOUND — skipped.")
            continue
        counts = count_messages(run)
        all_counts.append((run_id, counts))
        print(f"total={counts.total} (sys={counts.system} usr={counts.user} ast={counts.assistant} tool={counts.tool})")
        if not args.aggregate:
            print_counts(counts, label=run_id)

    if args.aggregate:
        print_aggregate(all_counts)


if __name__ == "__main__":
    main()
