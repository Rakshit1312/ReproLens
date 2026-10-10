import numpy as np

from reprolens import model_comparison


def test_compare_models_uses_precision_scorer_with_zero_division(monkeypatch):
    captured = []

    def fake_cross_validate(model, X, y, cv, scoring):
        captured.append((model, X, y, cv, scoring))
        return {
            "test_accuracy": np.array([0.5]),
            "test_precision": np.array([0.0]),
            "test_recall": np.array([0.0]),
            "test_f1": np.array([0.0]),
        }

    monkeypatch.setattr(model_comparison, "cross_validate", fake_cross_validate)

    result = model_comparison.compare_models()

    assert len(captured) == 5
    assert all(len(X) == 20 for _, X, _, _, _ in captured)
    assert all(
        cv.n_splits == 5
        and cv.shuffle is True
        and cv.random_state == 42
        for _, _, _, cv, _ in captured
    )

    scoring = captured[0][4]
    assert set(scoring) == {"accuracy", "precision", "recall", "f1"}
    assert scoring["accuracy"] == "accuracy"
    assert scoring["recall"] == "recall"
    assert scoring["f1"] == "f1"
    assert scoring["precision"]._kwargs == {"zero_division": 0}

    assert set(result) == {
        "dataset",
        "rows",
        "features",
        "validation",
        "results",
        "best_by_f1",
        "warning",
    }
    assert result["rows"] == 20
    assert "20 rows are insufficient" in result["warning"]
