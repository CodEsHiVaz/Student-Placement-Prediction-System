"""
Train the placement prediction model.

Flow:
    CSV -> load -> validate -> clean -> preprocess -> train/test split ->
    train 4 models -> evaluate -> select best -> save pipeline + metadata

Run from the project root:
    python ml/train_model.py

The saved artefact is a full scikit-learn Pipeline (preprocessing + model),
so the web app never has to repeat preprocessing.
"""

import os
import sys
import json
from datetime import datetime

# Allow running directly.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
import joblib

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)

from config import (
    Config,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    ALL_FEATURES,
    TARGET,
    TARGET_MAP,
)
from ml.data_validation import validate_dataframe, print_report, DataValidationError


def load_dataset(path):
    """Load the CSV, with a friendly error if it is missing."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Dataset not found at '{path}'.\n"
            "Place your CSV at data/student_placement.csv and try again."
        )
    return pd.read_csv(path)


def clean_dataframe(df):
    """Basic cleaning: drop exact duplicate rows and coerce numeric types.

    Missing values are handled inside the pipeline (SimpleImputer), so we do
    not drop thousands of rows here.
    """
    df = df.drop_duplicates().copy()
    for col in NUMERIC_FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # Strip whitespace on categorical / target text columns.
    for col in CATEGORICAL_FEATURES + [TARGET]:
        df[col] = df[col].astype(str).str.strip()
    return df


def build_preprocessor():
    """ColumnTransformer: scale numerics, one-hot encode categoricals."""
    numeric_pipe = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    categorical_pipe = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    return ColumnTransformer(transformers=[
        ("num", numeric_pipe, NUMERIC_FEATURES),
        ("cat", categorical_pipe, CATEGORICAL_FEATURES),
    ])


def get_models():
    """The candidate models to compare.

    Tree-based models use a capped depth. This is standard regularisation to
    avoid overfitting, and it also keeps predicted probabilities graded (a
    fully grown tree only ever outputs 0.0 or 1.0, which would make the
    High/Medium/Low category meaningless).
    """
    return {
        "Logistic Regression": LogisticRegression(max_iter=1000),
        "Decision Tree": DecisionTreeClassifier(max_depth=8, random_state=42),
        "Random Forest": RandomForestClassifier(
            n_estimators=200, max_depth=8, random_state=42, n_jobs=-1
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            subsample=0.8, random_state=42
        ),
    }


def evaluate(model, X_test, y_test):
    """Return a metrics dict for a fitted pipeline."""
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    return {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1": f1_score(y_test, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_test, y_proba),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        # How many distinct probabilities the model produces: a proxy for how
        # graded (well-calibrated) its probabilities are.
        "n_unique_proba": int(np.unique(np.round(y_proba, 2)).size),
    }


def print_comparison(results):
    """Print a clear comparison table across all models."""
    header = f"{'Model':<22}{'Accuracy':<11}{'Precision':<11}{'Recall':<10}{'F1':<9}{'ROC-AUC':<9}"
    print("\n" + "=" * len(header))
    print("MODEL COMPARISON")
    print("=" * len(header))
    print(header)
    print("-" * len(header))
    for name, m in results.items():
        print(f"{name:<22}{m['accuracy']:<11.4f}{m['precision']:<11.4f}"
              f"{m['recall']:<10.4f}{m['f1']:<9.4f}{m['roc_auc']:<9.4f}")
    print("=" * len(header))


def main():
    dataset_path = Config.DATASET_PATH
    model_path = Config.MODEL_PATH
    metadata_path = Config.MODEL_METADATA_PATH

    print(f"Loading dataset from: {dataset_path}")
    try:
        df = load_dataset(dataset_path)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    # Validate then clean.
    try:
        report = validate_dataframe(df, strict_labels=True)
    except DataValidationError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    print_report(report)

    df = clean_dataframe(df)

    # Build X / y.
    X = df[ALL_FEATURES]
    y = df[TARGET].map(TARGET_MAP)

    # Drop rows whose target could not be mapped (safety net).
    valid = y.notna()
    X, y = X[valid], y[valid].astype(int)

    if y.nunique() < 2:
        print("ERROR: Target has only one class after cleaning; cannot train.")
        sys.exit(1)

    # Stratified 80/20 split.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"\nTraining rows: {len(X_train)}   Testing rows: {len(X_test)}")

    preprocessor = build_preprocessor()
    models = get_models()

    results = {}
    fitted = {}
    for name, estimator in models.items():
        print(f"Training: {name} ...")
        pipe = Pipeline(steps=[("preprocessor", preprocessor), ("model", estimator)])
        pipe.fit(X_train, y_train)
        results[name] = evaluate(pipe, X_test, y_test)
        fitted[name] = pipe

    print_comparison(results)

    # Select the best model primarily by F1 and ROC-AUC. Metrics are rounded to
    # 2 decimals so statistically near-identical models count as tied; among
    # tied models we prefer the one with more graded probabilities, so the
    # High/Medium/Low category stays meaningful.
    def selection_key(name):
        m = results[name]
        return (round(m["f1"], 2), round(m["roc_auc"], 2), m["n_unique_proba"])

    best_name = max(results, key=selection_key)
    best_pipe = fitted[best_name]
    best_metrics = results[best_name]

    print(f"\nBest model: {best_name} "
          f"(F1={best_metrics['f1']:.4f}, ROC-AUC={best_metrics['roc_auc']:.4f})")
    print("Confusion matrix [[TN, FP], [FN, TP]]:")
    print(np.array(best_metrics["confusion_matrix"]))

    # Save the pipeline and metadata.
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(best_pipe, model_path)

    model_version = datetime.now().strftime("%Y%m%d%H%M%S")
    metadata = {
        "best_model": best_name,
        "model_version": model_version,
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "metrics": {n: {k: (v if k == "confusion_matrix" else round(v, 4))
                        for k, v in m.items()} for n, m in results.items()},
        "best_metrics": {k: (v if k == "confusion_matrix" else round(v, 4))
                         for k, v in best_metrics.items()},
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
    }
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nSaved model to:    {model_path}")
    print(f"Saved metadata to: {metadata_path}")
    print("Done.")


if __name__ == "__main__":
    main()
