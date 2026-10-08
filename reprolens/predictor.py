from reprolens.feature_engineering import build_features
from reprolens.baseline import predict_baseline

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split


FEATURE_COLUMNS = [
    "runtime_mismatch",
    "dependency_mismatch",
    "os_mismatch",
    "config_mismatch",
    "resource_mismatch",
    "runtime_compatible",
    "dependency_compatible",
    "os_compatible",
    "config_compatible",
    "resource_sufficient",
]


def load_dataset():
    """Load structured ReproLens features."""

    return build_features(
        "data/experiments/environment_failures.csv"
    )


def calculate_metrics(actual, predictions):
    """Calculate standard binary classification metrics."""

    return {
        "accuracy": accuracy_score(
            actual,
            predictions,
        ),
        "precision": precision_score(
            actual,
            predictions,
            zero_division=0,
        ),
        "recall": recall_score(
            actual,
            predictions,
            zero_division=0,
        ),
        "f1": f1_score(
            actual,
            predictions,
            zero_division=0,
        ),
        "confusion_matrix": confusion_matrix(
            actual,
            predictions,
        ),
    }


def run_experiment():
    rows = load_dataset()

    X = [
        [row[column] for column in FEATURE_COLUMNS]
        for row in rows
    ]

    y = [
        row["environment_failure"]
        for row in rows
    ]

    # Keep the exact same unseen test set for both approaches.
    (
        X_train,
        X_test,
        y_train,
        y_test,
        rows_train,
        rows_test,
    ) = train_test_split(
        X,
        y,
        rows,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )

    # -----------------------------
    # ML MODEL
    # -----------------------------

    model = LogisticRegression(
        random_state=42
    )

    model.fit(
        X_train,
        y_train,
    )

    ml_predictions = model.predict(
        X_test
    )

    ml_probabilities = model.predict_proba(
        X_test
    )[:, 1]

    # -----------------------------
    # RULE BASELINE
    # -----------------------------

    baseline_predictions = [
        predict_baseline(row)
        for row in rows_test
    ]

    # -----------------------------
    # METRICS
    # -----------------------------

    ml_metrics = calculate_metrics(
        y_test,
        ml_predictions,
    )

    baseline_metrics = calculate_metrics(
        y_test,
        baseline_predictions,
    )

    return (
        model,
        ml_metrics,
        baseline_metrics,
        y_test,
        ml_predictions,
        baseline_predictions,
        ml_probabilities,
    )


if __name__ == "__main__":

    (
        model,
        ml_metrics,
        baseline_metrics,
        actual,
        ml_predictions,
        baseline_predictions,
        probabilities,
    ) = run_experiment()

    print(
        "ReproLens Baseline vs ML Evaluation"
    )
    print("=" * 50)

    print("\nDataset")
    print("-" * 50)
    print("Training examples: 15")
    print("Unseen test examples: 5")

    print("\nRule-Based Baseline")
    print("-" * 50)

    print(
        f"Accuracy:  "
        f"{baseline_metrics['accuracy']:.3f}"
    )
    print(
        f"Precision: "
        f"{baseline_metrics['precision']:.3f}"
    )
    print(
        f"Recall:    "
        f"{baseline_metrics['recall']:.3f}"
    )
    print(
        f"F1 Score:  "
        f"{baseline_metrics['f1']:.3f}"
    )

    print("\nBaseline Confusion Matrix:")
    print(
        baseline_metrics["confusion_matrix"]
    )

    print("\nLogistic Regression")
    print("-" * 50)

    print(
        f"Accuracy:  "
        f"{ml_metrics['accuracy']:.3f}"
    )
    print(
        f"Precision: "
        f"{ml_metrics['precision']:.3f}"
    )
    print(
        f"Recall:    "
        f"{ml_metrics['recall']:.3f}"
    )
    print(
        f"F1 Score:  "
        f"{ml_metrics['f1']:.3f}"
    )

    print("\nML Confusion Matrix:")
    print(
        ml_metrics["confusion_matrix"]
    )

    print("\nSame Unseen Test Cases")
    print("-" * 50)

    for index, (
        actual_value,
        baseline_prediction,
        ml_prediction,
        probability,
    ) in enumerate(
        zip(
            actual,
            baseline_predictions,
            ml_predictions,
            probabilities,
        ),
        start=1,
    ):
        print(
            f"Example {index}: "
            f"actual={actual_value}, "
            f"baseline={baseline_prediction}, "
            f"ML={ml_prediction}, "
            f"risk={probability:.3f}"
        )