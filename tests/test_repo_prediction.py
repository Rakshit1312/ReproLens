from reprolens.predictor import FEATURE_COLUMNS
from reprolens.repo_prediction import (
    _prototype_vector,
    _unknown_prototype_features,
)


def test_unknown_checks_keep_v1_model_vector_and_are_reported_separately():
    features = {
        "dependency_environment_conflict": None,
        "os_match": None,
        "required_env_missing": None,
        "resource_constraint_detected": None,
        "python_version_match": None,
        "python_declaration_version_match": None,
        "python_requirement_violation": None,
    }

    vector = _prototype_vector(features)

    assert len(vector) == len(FEATURE_COLUMNS)
    assert vector == [0, 0, 0, 0, 0, 1, 1, 1, 1, 1]
    assert set(_unknown_prototype_features(features)) == set(FEATURE_COLUMNS)


def test_observed_runtime_mismatch_still_sets_the_trained_feature():
    vector = _prototype_vector({"python_version_match": 0})

    assert vector[FEATURE_COLUMNS.index("runtime_mismatch")] == 1
