#!/usr/bin/env python3
# /// script
# dependencies = ["docent-python", "python-dotenv"]
# ///
"""
export_runs_csv.py

Convert data/top5_enriched.json to CSV file where each row is one run with:
  - model name
  - message counts (system, user, assistant, tool, total)
  - resolved status (1 = resolved/passed, 0 = failed, -1 = unknown)

Output: data/top5_runs.csv

Usage
-----
    uv run extras/export_runs_csv.py                    # default (data/top5_enriched.json -> data/top5_runs.csv)
    uv run extras/export_runs_csv.py --input data/top5_enriched.json --output data/top5_runs.csv
"""

import argparse
import csv
import json
import sys
from pathlib import Path

DEFAULT_INPUT  = "data/top5_enriched.json"
DEFAULT_OUTPUT = "data/top5_runs.csv"


def resolved_to_int(resolved: bool | None) -> int:
    """Convert resolved status to int: 1 (True), 0 (False), -1 (None)."""
    if resolved is True:
        return 1
    elif resolved is False:
        return 0
    else:
        return -1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert data/top5_enriched.json to CSV with one row = one run.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT,
        help=f"Input JSON file (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output CSV file (default: {DEFAULT_OUTPUT})",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Load JSON
    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"ERROR: '{args.input}' not found.")

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    models = data.get("models", [])
    if not models:
        sys.exit("ERROR: No 'models' list in JSON file.")

    print(f"Loaded: {args.input}  ({len(models)} models)")

    # Collect all runs
    all_runs = []
    total_runs = 0

    for model in models:
        model_name = model["model_name"]
        runs = model.get("runs", [])
        total_runs += len(runs)

        for run in runs:
            run_id = run.get("run_id", "")
            
            # Message counts
            system_count = run.get("system", 0)
            user_count = run.get("user", 0)
            assistant_count = run.get("assistant", 0)
            tool_count = run.get("tool", 0)
            total_count = run.get("total", 0)

            # Resolved status
            resolved = run.get("resolved")
            resolved_int = resolved_to_int(resolved)

            all_runs.append({
                "model": model_name,
                "run_id": run_id,
                "system": system_count,
                "user": user_count,
                "assistant": assistant_count,
                "tool": tool_count,
                "total": total_count,
                "resolved": resolved_int,
            })

    print(f"Total runs: {total_runs}\n")

    # Write CSV
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    fieldnames = ["model", "run_id", "system", "user", "assistant", "tool", "total", "resolved"]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_runs)

    print(f"Saved to: {output_path.resolve()}")
    print(f"   {len(all_runs)} rows (runs)")
    print(f"\nColumns: {', '.join(fieldnames)}")
    print(f"Resolved encoding: 1=passed, 0=failed, -1=unknown")


if __name__ == "__main__":
    main()
