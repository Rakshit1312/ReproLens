from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

from .feature_engineering import build_features
from .predictor import FEATURE_COLUMNS

DATASET_PATH = Path("data/experiments/environment_failures.csv")


def compare_models() -> dict[str, Any]:
    rows = build_features(DATASET_PATH)
    X = np.array([[row[column] for column in FEATURE_COLUMNS] for row in rows])
    y = np.array([row["environment_failure"] for row in rows])

    models = {
        "Logistic Regression": make_pipeline(
            StandardScaler(),
            LogisticRegression(random_state=42, max_iter=1000),
        ),
        "Decision Tree": DecisionTreeClassifier(
            max_depth=4, random_state=42
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=100, max_depth=4, random_state=42
        ),
        "SVM": make_pipeline(
            StandardScaler(),
            SVC(kernel="linear"),
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            random_state=42,
        ),
    }

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    results = []

    for name, model in models.items():
        scores = cross_validate(
            model,
            X,
            y,
            cv=cv,
            scoring=("accuracy", "precision", "recall", "f1"),
        )
        results.append(
            {
                "model": name,
                "accuracy": round(float(scores["test_accuracy"].mean()), 3),
                "precision": round(float(scores["test_precision"].mean()), 3),
                "recall": round(float(scores["test_recall"].mean()), 3),
                "f1": round(float(scores["test_f1"].mean()), 3),
            }
        )

    best = max(results, key=lambda item: item["f1"])
    return {
        "dataset": str(DATASET_PATH),
        "rows": len(rows),
        "features": FEATURE_COLUMNS,
        "validation": "5-fold stratified cross-validation",
        "results": results,
        "best_by_f1": best["model"],
        "warning": (
            "Preliminary controlled-benchmark comparison; "
            "20 rows are insufficient for real-world generalization."
        ),
    }
