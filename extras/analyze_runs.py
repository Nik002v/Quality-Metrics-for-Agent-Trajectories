#!/usr/bin/env python3
# /// script
# dependencies = ["pandas", "matplotlib", "seaborn"]
# ///
"""
analyze_runs.py

Visualize data/top5_runs.csv with:
  - Boxplots for each model (system, user, assistant, tool, total) -> charts/boxplot/
  - Histograms for each model (system, user, assistant, tool, total) -> charts/histogram/
  - Grouped histograms for total count by resolved status -> charts/grouped/
  - Barchart for resolved status by model -> charts/grouped/
  - Resolve rate chart -> charts/grouped/

Output: PNG files with charts organized in subdirectories
"""

import sys
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Use Agg backend (no GUI)
import matplotlib.pyplot as plt
import seaborn as sns

DEFAULT_INPUT = "data/top5_runs.csv"
CHARTS_BASE = "charts"


def load_data(csv_path: str) -> pd.DataFrame:
    """Load CSV file."""
    path = Path(csv_path)
    if not path.exists():
        sys.exit(f"ERROR: '{csv_path}' not found.")
    
    df = pd.read_csv(path)
    print(f"✅ Loaded: {csv_path}")
    print(f"   Rows: {len(df)}")
    print(f"   Columns: {', '.join(df.columns)}")
    return df


def create_boxplot_per_model(df: pd.DataFrame, output_dir: Path) -> None:
    """Create figures with boxplots — one per model."""
    models = df["model"].unique()
    numeric_cols = ["system", "user", "assistant", "tool", "total"]
    
    for model in models:
        model_data = df[df["model"] == model][numeric_cols]
        
        fig, axes = plt.subplots(2, 3, figsize=(14, 8))
        fig.suptitle(f"Message distribution (Boxplot) — {model}", fontsize=14, fontweight="bold")
        axes = axes.flatten()
        
        for idx, col in enumerate(numeric_cols):
            ax = axes[idx]
            data = model_data[col]
            
            bp = ax.boxplot(
                data,
                patch_artist=True,
                widths=0.5,
                showmeans=True,
                meanline=True,
            )
            
            for patch in bp["boxes"]:
                patch.set_facecolor("lightblue")
                patch.set_alpha(0.7)
            
            ax.set_ylabel(col.capitalize(), fontweight="bold")
            ax.set_title(col.capitalize())
            ax.grid(True, alpha=0.3, axis="y")
            
            stats_text = (
                f"Mean: {data.mean():.1f}\n"
                f"Median: {data.median():.1f}\n"
                f"Min: {data.min():.0f}\n"
                f"Max: {data.max():.0f}"
            )
            ax.text(
                1.35, data.median(),
                stats_text,
                fontsize=9,
                verticalalignment="center",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
            )
        
        axes[5].remove()
        plt.tight_layout()
        
        safe_model_name = model.replace(" ", "_").replace("(", "").replace(")", "")
        filepath = output_dir / f"boxplot_{safe_model_name}.png"
        plt.savefig(filepath, dpi=300, bbox_inches="tight")
        print(f"✅ Saved: {filepath}")
        plt.close()


def create_histogram_per_model(df: pd.DataFrame, output_dir: Path) -> None:
    """Create figures with histograms — one per model."""
    models = df["model"].unique()
    numeric_cols = ["system", "user", "assistant", "tool", "total"]
    
    for model in models:
        model_data = df[df["model"] == model][numeric_cols]
        
        fig, axes = plt.subplots(2, 3, figsize=(14, 8))
        fig.suptitle(f"Message distribution (Histogram) — {model}", fontsize=14, fontweight="bold")
        axes = axes.flatten()
        
        for idx, col in enumerate(numeric_cols):
            ax = axes[idx]
            data = model_data[col]
            
            ax.hist(data, bins=20, color="skyblue", edgecolor="black", alpha=0.7)
            
            ax.set_xlabel("Count")
            ax.set_ylabel("Frequency", fontweight="bold")
            ax.set_title(col.capitalize())
            ax.grid(True, alpha=0.3, axis="y")
        
        axes[5].remove()
        plt.tight_layout()
        
        safe_model_name = model.replace(" ", "_").replace("(", "").replace(")", "")
        filepath = output_dir / f"histogram_{safe_model_name}.png"
        plt.savefig(filepath, dpi=300, bbox_inches="tight")
        print(f"✅ Saved: {filepath}")
        plt.close()


def create_grouped_histogram_per_model(df: pd.DataFrame, output_dir: Path) -> None:
    """Create a histogram for 'total' grouped by 'resolved' status — one per model."""
    models = df["model"].unique()
    
    for model in models:
        model_data = df[df["model"] == model]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.suptitle(f"Total count distribution by resolved status — {model}", fontsize=14, fontweight="bold")
        
        passed = model_data[model_data["resolved"] == 1]["total"]
        failed = model_data[model_data["resolved"] == 0]["total"]
        unknown = model_data[model_data["resolved"] == -1]["total"]
        
        # Prikazujemo preklopljene histograme
        if not passed.empty:
            ax.hist(passed, bins=20, alpha=0.6, color="#2ecc71", label="Passed (1)", edgecolor="black")
        if not failed.empty:
            ax.hist(failed, bins=20, alpha=0.6, color="#e74c3c", label="Failed (0)", edgecolor="black")
        if not unknown.empty:
            ax.hist(unknown, bins=20, alpha=0.6, color="#95a5a6", label="Unknown (-1)", edgecolor="black")
            
        ax.set_xlabel("Total messages", fontsize=11)
        ax.set_ylabel("Frequency", fontweight="bold", fontsize=11)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        safe_model_name = model.replace(" ", "_").replace("(", "").replace(")", "")
        filepath = output_dir / f"grouped_hist_total_{safe_model_name}.png"
        plt.savefig(filepath, dpi=300, bbox_inches="tight")
        print(f"✅ Saved: {filepath}")
        plt.close()


def create_resolved_barchart(df: pd.DataFrame, output_dir: Path) -> None:
    """Create barchart for resolved status by model."""
    models = df["model"].unique()
    
    data = []
    for model in models:
        model_data = df[df["model"] == model]
        resolved_1 = len(model_data[model_data["resolved"] == 1])
        resolved_0 = len(model_data[model_data["resolved"] == 0])
        resolved_neg1 = len(model_data[model_data["resolved"] == -1])
        
        data.append({
            "model": model,
            "Passed (1)": resolved_1,
            "Failed (0)": resolved_0,
            "Unknown (-1)": resolved_neg1,
        })
    
    summary_df = pd.DataFrame(data)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    x = range(len(summary_df))
    width = 0.25
    
    bars1 = ax.bar([i - width for i in x], summary_df["Passed (1)"], width, label="Passed (1)", color="#2ecc71", alpha=0.8)
    bars2 = ax.bar([i for i in x], summary_df["Failed (0)"], width, label="Failed (0)", color="#e74c3c", alpha=0.8)
    bars3 = ax.bar([i + width for i in x], summary_df["Unknown (-1)"], width, label="Unknown (-1)", color="#95a5a6", alpha=0.8)
    
    ax.set_xlabel("Model", fontweight="bold", fontsize=11)
    ax.set_ylabel("Number of runs", fontweight="bold", fontsize=11)
    ax.set_title("Resolved Status by Model", fontweight="bold", fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(summary_df["model"], rotation=45, ha="right")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis="y")
    
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, height, f"{int(height)}", ha="center", va="bottom", fontsize=9)
    
    plt.tight_layout()
    
    filepath = output_dir / "resolved_status_barchart.png"
    plt.savefig(filepath, dpi=300, bbox_inches="tight")
    print(f"✅ Saved: {filepath}")
    plt.close()


def create_resolve_rate_chart(df: pd.DataFrame, output_dir: Path) -> None:
    """Create barchart showing resolve rate (percentage) by model."""
    models = df["model"].unique()
    
    rates = []
    for model in models:
        model_data = df[df["model"] == model]
        resolve_rate = len(model_data[model_data["resolved"] == 1]) / len(model_data) * 100
        rates.append({"model": model, "resolve_rate": resolve_rate})
    
    rates_df = pd.DataFrame(rates)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(rates_df["model"], rates_df["resolve_rate"], color="#3498db", alpha=0.8, edgecolor="navy", linewidth=1.5)
    
    ax.set_xlabel("Model", fontweight="bold", fontsize=12)
    ax.set_ylabel("Resolve Rate (%)", fontweight="bold", fontsize=12)
    ax.set_title("Resolve Rate by Model", fontweight="bold", fontsize=14)
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3, axis="y")
    plt.xticks(rotation=45, ha="right")
    
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height + 1, f"{height:.1f}%", ha="center", va="bottom", fontsize=11, fontweight="bold")
    
    plt.tight_layout()
    
    filepath = output_dir / "resolve_rate_chart.png"
    plt.savefig(filepath, dpi=300, bbox_inches="tight")
    print(f"✅ Saved: {filepath}")
    plt.close()


def print_summary_stats(df: pd.DataFrame) -> None:
    """Print detailed statistics by model."""
    print("\n" + "=" * 80)
    print("DETAILED STATISTICS BY MODEL")
    print("=" * 80)
    
    models = df["model"].unique()
    numeric_cols = ["system", "user", "assistant", "tool", "total"]
    
    for model in models:
        model_data = df[df["model"] == model]
        resolve_rate = len(model_data[model_data["resolved"] == 1]) / len(model_data) * 100
        
        print(f"\n📊 {model}")
        print(f"   Runs: {len(model_data)}")
        print(f"   Resolve rate: {resolve_rate:.1f}%")
        print(f"\n   {'Column':<15} {'Mean':>8} {'Median':>8} {'Min':>6} {'Max':>6} {'Std':>8}")
        print(f"   {'-' * 60}")
        
        for col in numeric_cols:
            data = model_data[col]
            print(f"   {col:<15} {data.mean():>8.1f} {data.median():>8.1f} {data.min():>6.0f} {data.max():>6.0f} {data.std():>8.2f}")


def main() -> None:
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Visualize data/top5_runs.csv",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT,
        help=f"Input CSV file (default: {DEFAULT_INPUT})",
    )
    args = parser.parse_args()
    
    # Create output directories
    boxplot_dir = Path(CHARTS_BASE) / "boxplot"
    histogram_dir = Path(CHARTS_BASE) / "histogram"
    grouped_dir = Path(CHARTS_BASE) / "grouped"
    
    boxplot_dir.mkdir(parents=True, exist_ok=True)
    histogram_dir.mkdir(parents=True, exist_ok=True)
    grouped_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📂 Output directories:")
    print(f"   Boxplots:  {boxplot_dir.resolve()}")
    print(f"   Histograms: {histogram_dir.resolve()}")
    print(f"   Grouped:    {grouped_dir.resolve()}")
    
    df = load_data(args.input)
    
    print("\n📈 Creating boxplots by model...")
    create_boxplot_per_model(df, boxplot_dir)

    print("\n📈 Creating standard histograms by model...")
    create_histogram_per_model(df, histogram_dir)

    print("\n📈 Creating grouped 'total' histograms by resolved status per model...")
    create_grouped_histogram_per_model(df, grouped_dir)
    
    print("\n📊 Creating barchart for resolved status...")
    create_resolved_barchart(df, grouped_dir)
    
    print("\n📈 Creating resolve rate chart...")
    create_resolve_rate_chart(df, grouped_dir)
    
    print_summary_stats(df)
    
    print(f"\n✅ All charts created in '{CHARTS_BASE}' subdirectories!")


if __name__ == "__main__":
    main()
