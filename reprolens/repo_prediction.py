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
    not calibrated real-world probabilities. Unknown inputs use the legacy
    binary defaults only to preserve that model's input schema.
    """

    runtime_matches = [
        value
        for key, value in features.items()
        if key.endswith("_version_match") and value in (0, 1)
    ]
    runtime_differences = [
        value
        for key, value in features.items()
        if key.endswith("_major_difference")
        and isinstance(value, (int, float))
    ]
    runtime_mismatch = (
        1
        if any(value == 0 for value in runtime_matches)
        or any(value > 0 for value in runtime_differences)
        else 0
        if runtime_matches or runtime_differences
        else None
    )

    requirement_violations = [
        value
        for key, value in features.items()
        if key.endswith("_requirement_violation") and value in (0, 1)
    ]
    runtime_compatible = (
        0
        if 1 in requirement_violations
        else 1
        if requirement_violations
        else None
    )

    dependency_conflict = features.get("dependency_environment_conflict")
    dependency_mismatch = (
        int(dependency_conflict == 1)
        if dependency_conflict in (0, 1)
        else None
    )
    dependency_compatible = (
        int(dependency_conflict == 0)
        if dependency_conflict in (0, 1)
        else None
    )

    os_match = features.get("os_match")
    os_mismatch = 1 - os_match if os_match in (0, 1) else None
    os_compatible = os_match if os_match in (0, 1) else None

    missing_required_env = features.get("required_env_missing")
    config_mismatch = (
        missing_required_env
        if missing_required_env in (0, 1)
        else None
    )
    config_compatible = (
        1 - missing_required_env
        if missing_required_env in (0, 1)
        else None
    )

    resource_constraint = features.get("resource_constraint_detected")
    resource_mismatch = (
        resource_constraint
        if resource_constraint in (0, 1)
        else None
    )
    resource_sufficient = (
        1 - resource_constraint
        if resource_constraint in (0, 1)
        else None
    )

    values: dict[str, int | None] = {
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

    legacy_unknown_defaults = {
        "runtime_mismatch": 0,
        "dependency_mismatch": 0,
        "os_mismatch": 0,
        "config_mismatch": 0,
        "resource_mismatch": 0,
        "runtime_compatible": 1,
        "dependency_compatible": 1,
        "os_compatible": 1,
        "config_compatible": 1,
        "resource_sufficient": 1,
    }
    return [
        values[column]
        if values[column] is not None
        else legacy_unknown_defaults[column]
        for column in FEATURE_COLUMNS
    ]


def _unknown_prototype_features(features: dict[str, Any]) -> list[str]:
    known_runtime_matches = any(
        value in (0, 1)
        for key, value in features.items()
        if key.endswith("_version_match")
    ) or any(
        isinstance(value, (int, float))
        for key, value in features.items()
        if key.endswith("_major_difference")
    )
    known_requirement = any(
        value in (0, 1)
        for key, value in features.items()
        if key.endswith("_requirement_violation")
    )
    known = {
        "runtime_mismatch": known_runtime_matches,
        "runtime_compatible": known_requirement,
        "dependency_mismatch": features.get("dependency_environment_conflict") in (0, 1),
        "dependency_compatible": features.get("dependency_environment_conflict") in (0, 1),
        "os_mismatch": features.get("os_match") in (0, 1),
        "os_compatible": features.get("os_match") in (0, 1),
        "config_mismatch": features.get("required_env_missing") in (0, 1),
        "config_compatible": features.get("required_env_missing") in (0, 1),
        "resource_mismatch": features.get("resource_constraint_detected") in (0, 1),
        "resource_sufficient": features.get("resource_constraint_detected") in (0, 1),
    }
    return [column for column in FEATURE_COLUMNS if not known[column]]


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
    unknown_inputs = _unknown_prototype_features(features)
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
            "the current model is trained on the controlled benchmark. "
            "Unknown repository checks use legacy binary defaults for model "
            "input only and do not imply compatibility. Retraining or revising "
            "the benchmark is required before modeling unknown states directly."
        ),
        "features": dict(zip(FEATURE_COLUMNS, vector)),
        "unknown_input_features": unknown_inputs,
        "unknown_input_projection": "legacy_v1_defaults",
    }
