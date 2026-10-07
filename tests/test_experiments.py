from reprolens.experiments import controlled_label, make_case


def test_controlled_pass_to_fail_is_positive():
    case = make_case(
        case_id="java-17-11",
        repository="example/java-app",
        baseline_environment={"java": "17"},
        perturbed_environment={"java": "11"},
        change={"runtime": "java", "from": "17", "to": "11"},
        baseline_outcome="PASS",
        perturbed_outcome="FAIL",
        failure_type="E1",
    )
    result = controlled_label(case)
    assert result["environment_induced_label"] == 1
    assert result["evidence"][0]["level"] == 3


def test_no_transition_is_not_positive():
    case = make_case(
        case_id="node-20-18-pass",
        repository="example/node-app",
        baseline_environment={"node": "20"},
        perturbed_environment={"node": "18"},
        change={"runtime": "node", "from": "20", "to": "18"},
        baseline_outcome="PASS",
        perturbed_outcome="PASS",
    )
    result = controlled_label(case)
    assert result["environment_induced_label"] == 0
