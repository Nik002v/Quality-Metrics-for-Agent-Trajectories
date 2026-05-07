# SWE-bench Trajectory Metrics and Reports

This repository contains my solution for the trajectory-metrics task based on
mini-SWE-agent-v2 executions from the SWE-bench leaderboard. The core part of
the repository is a small Python command-line workflow that counts messages in
agent trajectories and then uses those counts to compare the top five model
collections.

The repository also includes the short written reports submitted with the
solution:

- `swe_agent_trajectory_analysis_report.pdf` — one-page report for Task #2,
  summarizing observations from raw message counts and from an additional
  resolved/unresolved analysis.
- `Towards_AI_Agent_Reliability_Summary.docx` — short summary of the paper
  *Towards a Science of AI Agent Reliability*.

## What the Required Tool Does

The required tool parses each provided mini-SWE-agent-v2 trajectory and counts
messages by role:

- `system`
- `user`
- `assistant`
- `tool`
- `total`

This directly addresses the required metric-computation part of the task. The
resolved/unresolved labels used later in the analysis are an additional step,
not part of the required Task #1 message-count extractor.

## Repository Structure

```text
.
|-- trajectory_metrics.py                 # Core message-counting CLI and reusable functions
|-- process_top5.py                       # Processes the top five model collections
|-- README.md                             # Project overview and usage instructions
|-- swe_agent_trajectory_analysis_report.pdf
|-- Towards_AI_Agent_Reliability_Summary.docx
|-- data/
|   |-- top5_results.json                 # Raw count results for all processed runs
|   `-- top5_runs.csv                     # Flat CSV used for analysis and charts
|-- extras/
|   |-- enrich_results.py                 # Adds resolved/unresolved labels via Docent metadata
|   |-- export_runs_csv.py                # Converts enriched JSON into CSV
|   `-- analyze_runs.py                   # Generates charts from the CSV file
`-- charts/                               # Generated visualizations
    |-- boxplot/
    |-- histogram/
    `-- grouped/
```

## Requirements

The scripts are written in Python and use inline `uv` dependency metadata.
Recommended usage is with `uv`.

Core dependencies:

- `docent-python`
- `python-dotenv`

Analysis and chart dependencies:

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

`process_top5.py` processes the five mini-SWE-agent-v2 model collections used in
the report:

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

## Optional Enrichment and Analysis

After `data/top5_results.json` is generated, the results can optionally be
joined with resolved/unresolved outcome labels from Docent metadata:

```bash
uv run extras/enrich_results.py
```

This enrichment is used for the report, but it is intentionally separate from
the required message-counting tool. It helps test whether patterns in raw
message counts correspond to successful or failed runs.

`data/top5_enriched.json` is not committed because it is a large generated file.
It can be recreated at any time with the command above.

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

## Chart Overview

The generated charts support two levels of analysis:

- `charts/histogram/` and `charts/boxplot/` describe raw message-count
  distributions without outcome labels. These plots show model tempo, spread,
  outliers, and stopping behavior.
- `charts/grouped/` splits message-count distributions by resolved status. These
  plots show how trajectory length differs between successful and unsuccessful
  runs.

This distinction is important: raw counts alone measure activity and cost, while
resolved labels make it possible to discuss efficiency and failure modes.

## Existing Results

The checked-in result files contain 500 trajectories per model, for 2,500 total
runs. The main aggregate results are:

| Model | Runs | Avg total messages | Min | Max | Resolve rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Claude 4.5 Opus (high reasoning) | 500 | 72.41 | 14 | 222 | 76.8% |
| Gemini 3 Flash (high reasoning) | 500 | 113.24 | 2 | 319 | 75.8% |
| MiniMax M2.5 (high reasoning) | 500 | 121.89 | 23 | 502 | 75.8% |
| Claude Opus 4.6 | 500 | 60.84 | 11 | 288 | 74.0% |
| GPT-5.2 Codex | 500 | 72.88 | 17 | 251 | 72.8% |

## Reports Included in This Repository

### SWE-bench trajectory report

The PDF report summarizes the trajectory analysis. It first discusses what can
be learned from raw message-count histograms and boxplots, then uses grouped
histograms with resolved labels to separate successful and unsuccessful runs.
The main conclusion is that message count is useful for cost, latency, stopping
behavior, and failure-mode analysis, but only when interpreted together with task
outcome.

### AI-agent reliability paper summary

The DOCX file summarizes *Towards a Science of AI Agent Reliability* based on
pages 1-21, excluding the appendix. The summary focuses on the paper's main
argument that agent reliability should be evaluated across multiple dimensions,
not only by average task success.

## Notes

Message counts should not be treated as a direct measure of reasoning quality. A
long trajectory may represent useful search, but it may also represent repeated
failed edits, redundant tool calls, or recovery from an early wrong assumption.
For this reason, the repository keeps the required raw-count extraction separate
from the optional resolved-label analysis.
