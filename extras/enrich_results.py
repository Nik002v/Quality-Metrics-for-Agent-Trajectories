# /// script
# dependencies = ["docent-python", "python-dotenv"]
# ///

#!/usr/bin/env python3
"""
enrich_results.py

Takes existing data/top5_results.json (created by process_top5.py),
fetches result/score for each run_id from Docent metadata via DQL,
and creates new data/top5_enriched.json file combining:
  - message count (from existing file)
  - resolved (True/False) and other score metadata

Usage
-----
    uv run extras/enrich_results.py                              # default input/output
    uv run extras/enrich_results.py --input data/top5_results.json --output data/top5_enriched.json
    uv run extras/enrich_results.py --limit 5                   # test mode
    uv run extras/enrich_results.py --schema                    # print available DQL columns and exit
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

try:
    from docent import Docent
except ImportError:
    sys.exit("ERROR: docent-python is not installed.")

DEFAULT_INPUT  = "data/top5_results.json"
DEFAULT_OUTPUT = "data/top5_enriched.json"


# ---------------------------------------------------------------------------
# DQL helpers
# ---------------------------------------------------------------------------
def fetch_schema(client: Docent, collection_id: str) -> None:
    """Print available DQL columns for a collection."""
    try:
        schema = client.get_dql_schema(collection_id)
        print(json.dumps(schema, indent=2))
    except Exception as e:
        print(f"ERROR reading schema: {e}")


def fetch_scores_via_dql(
    client: Docent,
    collection_id: str,
) -> dict[str, dict]:
    """
    Fetch all run_id + metadata with single DQL query instead of N individual requests.
    Returns dict: run_id -> metadata dict.
    """
    # First try with scores column, if not found fallback to metadata_json
    queries_to_try = [
        "SELECT agent_runs.id, agent_runs.metadata_json FROM agent_runs",
        "SELECT id, metadata_json FROM agent_runs",
    ]

    result = None
    for q in queries_to_try:
        try:
            result = client.execute_dql(collection_id, q)
            if result.get("rows"):
                break
        except Exception:
            continue

    if result is None or not result.get("rows"):
        return {}

    rows = client.dql_result_to_dicts(result)
    scores_map: dict[str, dict] = {}
    for row in rows:
        run_id = row.get("id") or row.get("agent_runs.id", "")
        metadata_raw = row.get("metadata_json") or row.get("agent_runs.metadata_json", {})

        # metadata_json can be string or dict
        if isinstance(metadata_raw, str):
            try:
                metadata = json.loads(metadata_raw)
            except Exception:
                metadata = {}
        elif isinstance(metadata_raw, dict):
            metadata = metadata_raw
        else:
            metadata = {}

        scores_map[str(run_id)] = metadata

    return scores_map


def extract_resolved(metadata: dict) -> bool | None:
    """
    Try to extract resolved/score field from metadata.
    SWE-bench trajectories store result under different keys.
    """
    # Try different keys where SWE-bench stores result
    for key in ["resolved", "score", "passed", "success", "result"]:
        val = metadata.get(key)
        if val is not None:
            if isinstance(val, bool):
                return val
            if isinstance(val, (int, float)):
                return bool(val)
            if isinstance(val, str):
                return val.lower() in ("true", "1", "yes", "passed", "resolved")

    # Try nested under "scores"
    scores = metadata.get("scores", {})
    if isinstance(scores, dict):
        for key in ["resolved", "score", "passed"]:
            val = scores.get(key)
            if val is not None:
                if isinstance(val, bool):
                    return val
                if isinstance(val, (int, float)):
                    return bool(val)

    return None  # not found


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
def enrich_model(
    client: Docent,
    model_data: dict,
    limit: int | None,
) -> dict:
    collection_id = model_data["collection_id"]
    model_name    = model_data["model_name"]
    runs          = model_data["runs"]

    if limit:
        runs = runs[:limit]

    print(f"\n{'=' * 55}")
    print(f"Model:      {model_name}")
    print(f"Collection: {collection_id}")
    print(f"Runs:       {len(runs)}")
    print(f"{'=' * 55}")

    # Single DQL query for all runs — much faster than N individual requests
    print("  Fetching metadata with single DQL query ...", flush=True)
    try:
        scores_map = fetch_scores_via_dql(client, collection_id)
        print(f"  Got metadata for {len(scores_map)} runs.")
    except Exception as e:
        print(f"  WARNING: DQL failed ({e}), using empty metadata.")
        scores_map = {}

    enriched_runs = []
    resolved_count = 0
    unknown_count  = 0

    for run in runs:
        run_id   = run["run_id"]
        metadata = scores_map.get(run_id, {})
        resolved = extract_resolved(metadata)

        if resolved is True:
            resolved_count += 1
        elif resolved is None:
            unknown_count += 1

        enriched_run = {
            **run,                          # everything from existing file (messages)
            "resolved": resolved,           # True / False / None
            "metadata": metadata,           # full metadata dict
        }
        enriched_runs.append(enriched_run)

        status = (
            "RESOLVED" if resolved is True
            else "FAILED " if resolved is False
            else "UNKNOWN"
        )
        print(f"  {run_id[:40]}  {status}  total_msgs={run['total']}")

    n = len(enriched_runs)
    resolve_rate = (resolved_count / n * 100) if n > 0 else 0.0

    print(f"\n  Resolve rate: {resolved_count}/{n} = {resolve_rate:.1f}%")
    if unknown_count:
        print(f"  Note: {unknown_count} runs have no resolved field in metadata.")

    # Update aggregate to include resolve_rate
    enriched_model = {
        **model_data,
        "runs": enriched_runs,
        "n_runs": n,
        "resolve_rate_pct": round(resolve_rate, 2),
        "resolved_count": resolved_count,
        "failed_count": n - resolved_count - unknown_count,
        "unknown_count": unknown_count,
    }
    return enriched_model


def print_final_summary(all_enriched: list[dict]) -> None:
    print(f"\n{'=' * 75}")
    print("FINAL SUMMARY — messages + resolve rate")
    print(f"{'=' * 75}")
    print(
        f"{'Model':<35} {'Runs':>5} {'Resolved%':>10}"
        f" {'Avg Total':>10} {'Avg Ast':>8} {'Avg Tool':>9}"
    )
    print(f"{'-' * 75}")
    for r in all_enriched:
        avg_total = r["aggregate"]["total"]["avg"] if r.get("aggregate") else 0
        avg_ast   = r["aggregate"]["assistant"]["avg"] if r.get("aggregate") else 0
        avg_tool  = r["aggregate"]["tool"]["avg"] if r.get("aggregate") else 0
        print(
            f"{r['model_name']:<35}"
            f"{r['n_runs']:>5}"
            f"{r['resolve_rate_pct']:>9.1f}%"
            f"{avg_total:>10.1f}"
            f"{avg_ast:>8.1f}"
            f"{avg_tool:>9.1f}"
        )
    print(f"{'=' * 75}")


# ---------------------------------------------------------------------------
# Command Line Interface
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Enrich top5_results.json with resolved/score metadata.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--api-key", default=os.getenv("DOCENT_API_KEY"))
    parser.add_argument("--input",  default=DEFAULT_INPUT,
                        help=f"Input JSON file (default: {DEFAULT_INPUT})")
    parser.add_argument("--output", default=DEFAULT_OUTPUT,
                        help=f"Output JSON file (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--limit",  type=int, default=None,
                        help="Max runs per model (test mode)")
    parser.add_argument("--schema", action="store_true",
                        help="Print DQL schema for first collection and exit")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.api_key:
        sys.exit("ERROR: No API key found. Add DOCENT_API_KEY to .env file.")

    # Load existing file
    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(
            f"ERROR: '{args.input}' not found.\n"
            f"       First run: uv run process_top5.py"
        )

    with open(input_path, encoding="utf-8") as f:
        existing = json.load(f)

    models = existing.get("models", [])
    if not models:
        sys.exit("ERROR: Input file has no 'models' list.")

    client = Docent(api_key=args.api_key)

    # --schema mode
    if args.schema:
        print(f"DQL schema for first collection ({models[0]['collection_id']}):\n")
        fetch_schema(client, models[0]["collection_id"])
        return

    print(f"Loaded: {args.input}  ({len(models)} models)")
    if args.limit:
        print(f"Limit:  {args.limit} runs per model (test mode)\n")

    all_enriched: list[dict] = []
    for model_data in models:
        enriched = enrich_model(client, model_data, args.limit)
        all_enriched.append(enriched)

    print_final_summary(all_enriched)

    # Save new file
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    output = {
        "generated_at": datetime.now().isoformat(),
        "source_file": str(input_path.resolve()),
        "models": all_enriched,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
