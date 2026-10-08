from __future__ import annotations

from pathlib import Path
from typing import Any

from .feature_engineering import build_features
from .predictor import FEATURE_COLUMNS
from sklearn.linear_model import LogisticRegression


DATASET_PATH = Path("data/experiments/environment_failures.csv")


def _prototype_vector(features: dict[str, Any]) -> list[int]:
    """Map repository-level compatibility features to the V1 benchmark schema.

    This adapter is intentionally explicit: the current ML model is trained on
    the controlled benchmark, so repository predictions are prototype signals,
    not calibrated real-world probabilities.
    """

    runtime_mismatch = int(
        any(
            value == 0
            for key, value in features.items()
            if key.endswith("_version_match")
        )
        or any(
            value > 0
            for key, value in features.items()
            if key.endswith("_major_difference")
            and isinstance(value, (int, float))
        )
    )

    dependency_mismatch = int(
        features.get("dependency_environment_conflict", 0) == 1
    )

    os_mismatch = int(
        features.get("os_match") == 0
    )

    config_mismatch = int(
        features.get("required_env_missing", 0) == 1
    )

    resource_mismatch = int(
        features.get("resource_constraint_detected", 0) == 1
    )

    runtime_compatible = int(
        not any(
            value == 1
            for key, value in features.items()
            if key.endswith("_requirement_violation")
        )
    )

    dependency_compatible = int(
        features.get("dependency_environment_conflict", 0) != 1
    )

    os_compatible = int(features.get("os_match", 1) != 0)
    config_compatible = int(
        features.get("required_env_missing", 0) != 1
    )
    resource_sufficient = int(
        features.get("resource_constraint_detected", 0) != 1
    )

    values = {
        "runtime_mismatch": runtime_mismatch,
        "dependency_mismatch": dependency_mismatch,
        "os_mismatch": os_mismatch,
        "config_mismatch": config_mismatch,
        "resource_mismatch": resource_mismatch,
        "runtime_compatible": runtime_compatible,
        "dependency_compatible": dependency_compatible,
        "os_compatible": os_compatible,
        "config_compatible": config_compatible,
        "resource_sufficient": resource_sufficient,
    }

    return [values[column] for column in FEATURE_COLUMNS]


def predict_repository(features: dict[str, Any]) -> dict[str, Any]:
    """Return a prototype ML risk signal for a repository.

    The model is trained only on the controlled benchmark. It must not be
    interpreted as a validated real-world probability.
    """

    rows = build_features(DATASET_PATH)

    X = [
        [row[column] for column in FEATURE_COLUMNS]
        for row in rows
    ]
    y = [row["environment_failure"] for row in rows]

    model = LogisticRegression(random_state=42)
    model.fit(X, y)

    vector = _prototype_vector(features)
    risk = float(model.predict_proba([vector])[0][1])
    prediction = int(risk >= 0.5)

    return {
        "prediction": prediction,
        "risk_score": round(risk, 3),
        "threshold": 0.5,
        "model": "logistic_regression",
        "status": "prototype_benchmark_model",
        "warning": (
            "Risk score is not calibrated for real-world repositories; "
            "the current model is trained on the controlled benchmark."
        ),
        "features": dict(zip(FEATURE_COLUMNS, vector)),
    }
