from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reprolens.labels import FailureEvidence, classify_evidence, make_record


def test_controlled_positive():
    evidence = [FailureEvidence(3, "experiment-01", "Java 17 passes; Java 11 fails with the same source.", True)]
    result = classify_evidence(evidence)
    assert result["label"] == 1


def test_explicit_non_environment():
    evidence = [FailureEvidence(2, "ci-log", "AssertionError in test; runtime versions match.", False)]
    assert classify_evidence(evidence)["label"] == 0


def test_unknown_without_evidence():
    assert classify_evidence([])["label"] == "U"


def test_guess_is_unknown():
    evidence = [FailureEvidence(0, "analyst", "Probably caused by Node.", True)]
    assert classify_evidence(evidence)["label"] == "U"


def test_record():
    evidence = [FailureEvidence(3, "exp-1", "Node 20 passes; Node 18 fails.", True)]
    record = make_record(repository="example/repo", outcome=1, evidence=evidence, failure_type="E1")
    assert record["environment_induced_label"] == 1
    assert record["failure_type"] == "E1"
