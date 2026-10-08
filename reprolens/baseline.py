from reprolens.feature_engineering import build_features


MISMATCH_FEATURES = [
    "runtime_mismatch",
    "dependency_mismatch",
    "os_mismatch",
    "config_mismatch",
    "resource_mismatch",
]

COMPATIBILITY_FEATURES = [
    "runtime_compatible",
    "dependency_compatible",
    "os_compatible",
    "config_compatible",
]

RESOURCE_FEATURE = "resource_sufficient"


def predict_baseline(row: dict) -> int:
    """
    Rule-based ReproLens baseline.

    Predict environment-induced failure when:
    1. a development/CI environment mismatch exists, OR
    2. an explicit compatibility problem exists, OR
    3. required resources are insufficient.
    """

    mismatch_detected = any(
        row[column] == 1
        for column in MISMATCH_FEATURES
    )

    compatibility_problem = any(
        row[column] == 0
        for column in COMPATIBILITY_FEATURES
    )

    insufficient_resources = (
        row[RESOURCE_FEATURE] == 0
    )

    return int(
        mismatch_detected
        or compatibility_problem
        or insufficient_resources
    )


def evaluate_baseline(rows: list[dict]) -> dict:
    """
    Evaluate baseline predictions against known labels.
    """

    true_positive = 0
    true_negative = 0
    false_positive = 0
    false_negative = 0

    for row in rows:
        prediction = predict_baseline(row)
        actual = row["environment_failure"]

        if prediction == 1 and actual == 1:
            true_positive += 1

        elif prediction == 0 and actual == 0:
            true_negative += 1

        elif prediction == 1 and actual == 0:
            false_positive += 1

        elif prediction == 0 and actual == 1:
            false_negative += 1

    return {
        "true_positive": true_positive,
        "true_negative": true_negative,
        "false_positive": false_positive,
        "false_negative": false_negative,
    }


if __name__ == "__main__":
    rows = build_features(
        "data/experiments/environment_failures.csv"
    )

    results = evaluate_baseline(rows)

    print("ReproLens Compatibility Baseline")
    print("-" * 40)

    for key, value in results.items():
        print(f"{key}: {value}")