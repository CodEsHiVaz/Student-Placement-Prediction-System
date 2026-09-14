"""
Standalone Exploratory Data Analysis.

Prints dataset statistics and saves a few charts to ml/eda_output/.
This is NOT part of the web request flow - run it manually:

    python ml/eda.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd

import matplotlib
matplotlib.use("Agg")  # no GUI needed; save charts to files
import matplotlib.pyplot as plt

from config import Config, NUMERIC_FEATURES, CATEGORICAL_FEATURES, TARGET, ID_COL

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "eda_output")


def main():
    path = Config.DATASET_PATH
    if not os.path.exists(path):
        print(f"ERROR: Dataset not found at '{path}'.")
        print("Place your CSV at data/student_placement.csv and try again.")
        sys.exit(1)

    df = pd.read_csv(path)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("EXPLORATORY DATA ANALYSIS")
    print("=" * 60)
    print(f"Records : {len(df)}")
    print(f"Columns : {df.shape[1]}")

    print("\n--- Missing values ---")
    missing = df.isna().sum()
    print(missing[missing > 0] if missing.sum() else "None")

    print("\n--- Duplicate rows ---")
    print(f"Exact duplicate rows : {int(df.duplicated().sum())}")
    if ID_COL in df.columns:
        print(f"Duplicate {ID_COL}      : {int(df[ID_COL].duplicated().sum())}")

    if TARGET in df.columns:
        print("\n--- Placement distribution ---")
        counts = df[TARGET].value_counts()
        print(counts)
        placed = counts.get("Placed", 0)
        pct = 100 * placed / len(df) if len(df) else 0
        print(f"Placement percentage : {pct:.2f}%")

    print("\n--- Numerical statistics ---")
    present_numeric = [c for c in NUMERIC_FEATURES if c in df.columns]
    print(df[present_numeric].describe().round(2))

    print("\n--- Categorical value counts ---")
    for col in CATEGORICAL_FEATURES:
        if col in df.columns:
            print(f"\n{col}:")
            print(df[col].value_counts())

    print("\n--- Correlation (numeric features) ---")
    corr = df[present_numeric].corr().round(2)
    print(corr)

    _save_charts(df, present_numeric, corr)

    print(f"\nCharts saved to: {OUTPUT_DIR}")
    print("Done.")


def _save_charts(df, present_numeric, corr):
    """Save a handful of useful charts as PNG files."""
    # 1. Placement distribution.
    if TARGET in df.columns:
        ax = df[TARGET].value_counts().plot(kind="bar", color=["#198754", "#dc3545"])
        ax.set_title("Placement Distribution")
        ax.set_ylabel("Students")
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "placement_distribution.png"))
        plt.close()

    # 2. CGPA histogram.
    if "CGPA" in df.columns:
        df["CGPA"].plot(kind="hist", bins=20, color="#0d6efd")
        plt.title("CGPA Distribution")
        plt.xlabel("CGPA")
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "cgpa_distribution.png"))
        plt.close()

    # 3. Correlation heatmap.
    if len(present_numeric) > 1:
        fig, ax = plt.subplots(figsize=(9, 7))
        im = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
        ax.set_xticks(range(len(present_numeric)))
        ax.set_yticks(range(len(present_numeric)))
        ax.set_xticklabels(present_numeric, rotation=90, fontsize=7)
        ax.set_yticklabels(present_numeric, fontsize=7)
        fig.colorbar(im)
        ax.set_title("Numeric Feature Correlation")
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "correlation_heatmap.png"))
        plt.close()


if __name__ == "__main__":
    main()
