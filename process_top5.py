# /// script
# dependencies = ["docent-python", "python-dotenv"]
# ///

#!/usr/bin/env python3
"""
process_top5.py — Process top 5 models using trajectory_metrics.py

Imports process_collection() and count_messages() from trajectory_metrics.py,
processes all 5 collections and saves results to top5_results.json.

Usage
-----
    uv run process_top5.py                   # all models, all runs
    uv run process_top5.py --limit 5         # test: only first 5 runs per model
    uv run process_top5.py --model claude45_opus_high   # single model only
    uv run process_top5.py --output my_results.json
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# Import core logic from trajectory_metrics.py
# Both files must be in the same folder
try:
    from trajectory_metrics import (
        process_collection,
        MessageCounts,
        print_aggregate,
    )
except ImportError:
    sys.exit(
        "ERROR: Cannot import trajectory_metrics.py\n"
        "       Both files must be in the same folder."
    )

try:
    from docent import Docent
except ImportError:
    sys.exit("ERROR: docent-python is not installed.")


# ---------------------------------------------------------------------------
# Collections — top 5 models from mini-SWE-agent-v2 leaderboard
# ---------------------------------------------------------------------------
COLLECTIONS = {
    "claude45_opus_high": "b038912e-0133-4594-b093-92806f8ffb17",
    "gemini3_flash_high": "1ebbdd7a-55b3-4015-9b83-5978cc7fb618",
    "minimax_m25_high":   "5b77e003-7328-4003-879e-9b55dd3a0b6f",
    "claude_opus_46":     "9243cc78-d399-402f-be97-e366ff63282c",
    "gpt52_codex":        "fb22a2e4-0a41-4d41-8e1e-388d4cb50d80",
}

MODEL_NAMES = {
    "claude45_opus_high": "Claude 4.5 Opus (high reasoning)",
    "gemini3_flash_high": "Gemini 3 Flash (high reasoning)",
    "minimax_m25_high":   "MiniMax M2.5 (high reasoning)",
    "claude_opus_46":     "Claude Opus 4.6",
    "gpt52_codex":        "GPT-5.2 Codex",
}

OUTPUT_FILE = "data/top5_results.json"


# ---------------------------------------------------------------------------
# Helper functions for aggregation
# ---------------------------------------------------------------------------
def agg(counts: list[MessageCounts], field: str) -> dict:
    vals = [getattr(c, field) for c in counts]
    if not vals:
        return {"min": 0, "max": 0, "avg": 0.0}
    return {"min": min(vals), "max": max(vals), "avg": round(sum(vals) / len(vals), 2)}


def build_model_result(
    model_key: str,
    collection_id: str,
    runs: list[tuple[str, MessageCounts]],
) -> dict:
    counts = [c for _, c in runs]
    return {
        "model_key": model_key,
        "model_name": MODEL_NAMES[model_key],
        "collection_id": collection_id,
        "n_runs": len(counts),
        "aggregate": {
            field: agg(counts, field)
            for field in ["system", "user", "assistant", "tool", "total"]
        },
        "runs": [
            {
                "run_id": run_id,
                "system": c.system,
                "user": c.user,
                "assistant": c.assistant,
                "tool": c.tool,
                "total": c.total,
            }
            for run_id, c in runs
        ],
    }


def save_results(all_model_results: list[dict], output_file: str) -> None:
    # Ensure parent directory exists
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "generated_at": datetime.now().isoformat(),
        "models": all_model_results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {output_path.resolve()}")


def print_summary(all_model_results: list[dict]) -> None:
    print(f"\n{'=' * 72}")
    print("SUMMARY — Top 5 models (mini-SWE-agent-v2)")
    print(f"{'=' * 72}")
    print(f"{'Model':<35} {'Runs':>5} {'Avg Total':>10} {'Avg Ast':>8} {'Avg Tool':>9}")
    print(f"{'-' * 72}")
    for r in all_model_results:
        if r["n_runs"] == 0:
            print(f"{r['model_name']:<35}  {'N/A':>5}")
            continue
        print(
            f"{r['model_name']:<35}"
            f"{r['n_runs']:>5}"
            f"{r['aggregate']['total']['avg']:>10.1f}"
            f"{r['aggregate']['assistant']['avg']:>8.1f}"
            f"{r['aggregate']['tool']['avg']:>9.1f}"
        )
    print(f"{'=' * 72}")


# ---------------------------------------------------------------------------
# Command Line Interface
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Process trajectories for top 5 mini-SWE-agent-v2 models.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("DOCENT_API_KEY"),
        help="Docent API key (env: DOCENT_API_KEY)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of runs per model (for testing, e.g. --limit 5)",
    )
    parser.add_argument(
        "--model",
        choices=list(COLLECTIONS.keys()),
        default=None,
        help="Process single model only",
    )
    parser.add_argument(
        "--output",
        default=OUTPUT_FILE,
        help=f"Output JSON file (default: {OUTPUT_FILE})",
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Data directory for output files (default: data/)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.api_key:
        sys.exit("ERROR: No API key found. Add DOCENT_API_KEY to .env file.")

    client = Docent(api_key=args.api_key)

    models_to_process = (
        {args.model: COLLECTIONS[args.model]}
        if args.model
        else COLLECTIONS
    )

    print(f"Processing {len(models_to_process)} model(s)...")
    if args.limit:
        print(f"Limit: {args.limit} runs per model (test mode)\n")

    all_model_results: list[dict] = []

    for model_key, collection_id in models_to_process.items():
        print(f"\n{'=' * 55}")
        print(f"Model:      {MODEL_NAMES[model_key]}")
        print(f"Collection: {collection_id}")
        print(f"{'=' * 55}")

        # Call core function from trajectory_metrics.py
        runs = process_collection(
            client=client,
            collection_id=collection_id,
            limit=args.limit,
            verbose=True,
        )

        # Print aggregate for this model
        if runs:
            print_aggregate(runs)

        result = build_model_result(model_key, collection_id, runs)
        all_model_results.append(result)

    print_summary(all_model_results)
    save_results(all_model_results, args.output)


if __name__ == "__main__":
    main()
