from reprolens.feature_engineering import build_features
from reprolens.baseline import predict_baseline

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

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
    return build_features(
        "data/experiments/environment_failures.csv"
    )


def calculate_metrics(actual, predictions):
    matrix = confusion_matrix(
        actual,
        predictions,
    )

    return {
        "accuracy": round(
            accuracy_score(actual, predictions),
            3,
        ),
        "precision": round(
            precision_score(
                actual,
                predictions,
                zero_division=0,
            ),
            3,
        ),
        "recall": round(
            recall_score(
                actual,
                predictions,
                zero_division=0,
            ),
            3,
        ),
        "f1": round(
            f1_score(
                actual,
                predictions,
                zero_division=0,
            ),
            3,
        ),
        "confusion_matrix": matrix.tolist(),
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

    models = {
        "Logistic Regression": LogisticRegression(
            random_state=42
        ),
        "Decision Tree": DecisionTreeClassifier(
            random_state=42,
            max_depth=4,
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            max_depth=5,
        ),
    }

    results = {}

    for name, model in models.items():

        model.fit(
            X_train,
            y_train,
        )

        predictions = model.predict(
            X_test
        )

        metrics = calculate_metrics(
            y_test,
            predictions,
        )

        probabilities = None

        if hasattr(
            model,
            "predict_proba",
        ):
            probabilities = (
                model.predict_proba(X_test)[:, 1]
                .round(3)
                .tolist()
            )

        results[name] = {
            "metrics": metrics,
            "predictions": predictions.tolist(),
            "probabilities": probabilities,
        }

    baseline_predictions = [
        predict_baseline(row)
        for row in rows_test
    ]

    results["Rule-Based Baseline"] = {
        "metrics": calculate_metrics(
            y_test,
            baseline_predictions,
        ),
        "predictions": baseline_predictions,
        "probabilities": None,
    }

    return {
        "dataset_size": len(rows),
        "training_examples": len(X_train),
        "test_examples": len(X_test),
        "random_state": 42,
        "results": results,
        "actual": y_test,
        "test_cases": [
            {
                "id": row["id"],
                "project": row["project"],
                "actual": actual,
            }
            for row, actual in zip(
                rows_test,
                y_test,
            )
        ],
    }


if __name__ == "__main__":

    experiment = run_experiment()

    print(
        "ReproLens Model Comparison"
    )
    print("=" * 60)

    print(
        f"Dataset: "
        f"{experiment['dataset_size']} examples"
    )

    print(
        f"Train: "
        f"{experiment['training_examples']}"
    )

    print(
        f"Test: "
        f"{experiment['test_examples']}"
    )

    print()

    for name, result in (
        experiment["results"].items()
    ):

        metrics = result["metrics"]

        print(name)
        print("-" * 60)

        print(
            f"Accuracy : {metrics['accuracy']:.3f}"
        )

        print(
            f"Precision: {metrics['precision']:.3f}"
        )

        print(
            f"Recall   : {metrics['recall']:.3f}"
        )

        print(
            f"F1       : {metrics['f1']:.3f}"
        )

        print(
            f"Confusion Matrix: "
            f"{metrics['confusion_matrix']}"
        )

        print()