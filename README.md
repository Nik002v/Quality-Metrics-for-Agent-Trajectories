# SWE-bench Trajectory Metrics

This repository contains a small command-line workflow for counting messages in
mini-SWE-agent-v2 trajectories from SWE-bench leaderboard runs.

The main metric is the number of messages per trajectory, split by role:

- system
- user
- assistant
- tool
- total

The repository also includes scripts for processing the top five model
collections, exporting the results, and generating charts for a short analysis
report.

## Repository Structure

```text
.
|-- trajectory_metrics.py      # Core message-counting CLI and reusable functions
|-- process_top5.py            # Processes the top five model collections
|-- data/
|   |-- top5_results.json      # Raw count results for all processed runs
|   `-- top5_runs.csv          # Flat CSV used for analysis and charts
|-- extras/
|   |-- enrich_results.py      # Adds resolved/unresolved labels via Docent metadata
|   |-- export_runs_csv.py     # Converts enriched JSON into CSV
|   `-- analyze_runs.py        # Generates charts from the CSV file
`-- charts/                    # Generated visualizations
```

## Requirements

The scripts are written in Python and use inline `uv` dependency metadata.
Recommended usage is with `uv`.

Core dependencies:

- `docent-python`
- `python-dotenv`

Analysis/chart dependencies:

- `pandas`
- `matplotlib`
- `seaborn`

The Docent API key should be placed in a local `.env` file:

```text
DOCENT_API_KEY=your_api_key_here
DOCENT_COLLECTION_ID=optional_default_collection_id
```

The `.env` file is local configuration and should not be committed with real
credentials.

## Count Messages for One Collection

`trajectory_metrics.py` lists all runs in a Docent collection, fetches each
agent trajectory, and counts messages by role.

```bash
uv run trajectory_metrics.py --collection-id <collection_id> --all
```

Print only aggregate statistics:

```bash
uv run trajectory_metrics.py --collection-id <collection_id> --all --aggregate
```

Process only a small sample for testing:

```bash
uv run trajectory_metrics.py --collection-id <collection_id> --all --limit 5
```

Example output:

```text
System messages:        1
User messages:          1
Assistant messages:    32
Tool messages:         32
==============================
Total messages:        66
```

## Process the Top Five Models

`process_top5.py` processes the top five mini-SWE-agent-v2 model collections
used in the analysis:

- Claude 4.5 Opus (high reasoning)
- Gemini 3 Flash (high reasoning)
- MiniMax M2.5 (high reasoning)
- Claude Opus 4.6
- GPT-5.2 Codex

Run the full processing workflow:

```bash
uv run process_top5.py
```

Run a quick sample:

```bash
uv run process_top5.py --limit 5
```

Process a single model:

```bash
uv run process_top5.py --model gpt52_codex
```

The default output is:

```text
data/top5_results.json
```

## Enrich, Export, and Analyze Results

After generating `data/top5_results.json`, resolved/unresolved labels can be
added from Docent metadata:

```bash
uv run extras/enrich_results.py
```

Note: `data/top5_enriched.json` was removed from the repository because it is a
large generated file. Nothing else in the workflow was changed; the file can be
recreated at any time with the command above.

Convert the enriched JSON file into a flat CSV:

```bash
uv run extras/export_runs_csv.py
```

Generate charts:

```bash
uv run extras/analyze_runs.py
```

Generated charts are saved under:

```text
charts/boxplot/
charts/histogram/
charts/grouped/
```

### Chart Overview

The generated charts provide a visual summary of the message-count data:

- `charts/boxplot/` shows the distribution of system, user, assistant, tool,
  and total messages for each model. These charts make it easy to compare
  median behavior, spread, and outliers.
- `charts/histogram/` shows how often different message-count ranges appear for
  each model. These charts highlight whether a model usually produces short,
  medium, or long trajectories.
- `charts/grouped/` compares total message counts together with resolved status.
  These charts are useful for seeing whether successful and unsuccessful runs
  have different trajectory lengths, and for comparing resolve rates across
  models.

## Existing Results

The checked-in result files contain 500 trajectories per model, for 2,500 total
runs. The main aggregate findings are:

| Model | Runs | Avg total messages | Min | Max | Resolve rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Claude 4.5 Opus (high reasoning) | 500 | 72.41 | 14 | 222 | 76.8% |
| Gemini 3 Flash (high reasoning) | 500 | 113.24 | 2 | 319 | 75.8% |
| MiniMax M2.5 (high reasoning) | 500 | 121.89 | 23 | 502 | 75.8% |
| Claude Opus 4.6 | 500 | 60.84 | 11 | 288 | 74.0% |
| GPT-5.2 Codex | 500 | 72.88 | 17 | 251 | 72.8% |

## Notes

Message counts are useful as an activity, cost, and efficiency signal, but they
do not measure solution quality by themselves. The enriched analysis therefore
adds resolved labels separately, so trajectory length can be interpreted
together with task outcome.
