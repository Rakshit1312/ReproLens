import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reprolens.extractor import fingerprint_ci, fingerprint_local, fingerprint_repository
from reprolens.diff import compare


def test_repository_extraction(tmp_path: Path):
    (tmp_path / ".nvmrc").write_text("20\n")
    (tmp_path / "package.json").write_text(json.dumps({"engines": {"node": ">=20"}}))
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text("""jobs:\n  build:\n    runs-on: ubuntu-22.04\n    steps:\n      - uses: actions/setup-node@v6\n        with:\n          node-version: '18'\n""")
    fp = fingerprint_repository(tmp_path).to_dict()
    ci = fingerprint_ci(tmp_path).to_dict()
    assert fp["runtime_declarations"]["node"]["value"] == "20"
    assert "node" not in fp["runtimes"]
    assert fp["requirements"]["node"]["value"] == ">=20"
    assert ci["platform"]["ci_runner"]["value"] == "ubuntu-22.04"
    assert ci["runtime_declarations"]["node"]["value"] == "18"
    assert "node" not in ci["runtimes"]
    assert "ci_runner" not in fp["platform"]
    assert fp["runtime_declarations"]["node"]["evidence"] == [
        {"source": ".nvmrc", "confidence": "high"}
    ]


def test_runtime_declarations_are_not_observed_local_runtimes(tmp_path: Path):
    (tmp_path / ".python-version").write_text("3.12.2\n", encoding="utf-8")
    (tmp_path / ".nvmrc").write_text("20\n", encoding="utf-8")
    (tmp_path / ".ruby-version").write_text("3.3.0\n", encoding="utf-8")
    (tmp_path / "package.json").write_text(
        json.dumps({
            "devEngines": {
                "runtime": {"name": "node", "version": "22"},
            },
        }),
        encoding="utf-8",
    )

    fingerprint = fingerprint_repository(tmp_path).to_dict()

    assert fingerprint["runtimes"] == {}
    assert fingerprint["runtime_declarations"]["python"]["value"] == "3.12.2"
    assert fingerprint["runtime_declarations"]["node"]["value"] == "20"
    assert fingerprint["runtime_declarations"]["ruby"]["value"] == "3.3.0"
    assert fingerprint["runtime_declarations"]["node"]["evidence"] == [
        {"source": ".nvmrc", "confidence": "high"},
        {
            "source": "package.json:devEngines.runtime.version",
            "confidence": "high",
        },
        {"source": "CONFLICT", "confidence": "low"},
    ]


def test_local_fingerprint_records_observed_runtime_values(monkeypatch):
    from reprolens import extractor

    monkeypatch.setattr(extractor.platform, "system", lambda: "Linux")
    monkeypatch.setattr(extractor.platform, "version", lambda: "kernel")
    monkeypatch.setattr(extractor.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(extractor.os, "cpu_count", lambda: 8)

    def observed_version(command):
        return {
            ("node", "--version"): "v20.11.0",
            ("python", "--version"): "Python 3.12.2",
            ("java", "-version"): '"17.0.10"',
            ("npm", "--version"): "10.2.4",
            ("python", "-m", "pip", "--version"): "pip 24.0",
            ("mvn", "--version"): "Apache Maven 3.9.6",
            ("gradle", "--version"): "Gradle 8.7",
        }.get(tuple(command))

    monkeypatch.setattr(extractor, "_run", observed_version)
    fingerprint = fingerprint_local().to_dict()

    assert fingerprint["runtime_declarations"] == {}
    assert fingerprint["runtimes"]["node"] == {
        "value": "v20.11.0",
        "evidence": [
            {"source": "local:node --version", "confidence": "high"}
        ],
    }
    assert fingerprint["runtimes"]["python"]["value"] == "Python 3.12.2"


def test_runtime_comparison_keeps_observed_and_declared_values_separate():
    features = compare(
        {
            "runtimes": {},
            "runtime_declarations": {
                "python": {"value": "3.12"},
            },
            "requirements": {},
        },
        {
            "runtimes": {
                "python": {"value": "3.11"},
            },
            "runtime_declarations": {},
        },
    )

    assert "python_version_match" not in features
    assert "python_major_difference" not in features
    assert "python_declaration_version_match" not in features


def test_ci_and_repository_runtime_declarations_are_compared_as_declarations():
    features = compare(
        {
            "runtimes": {},
            "runtime_declarations": {
                "node": {"value": "20"},
            },
            "requirements": {
                "node": {"value": ">=20"},
            },
        },
        {
            "runtimes": {},
            "runtime_declarations": {
                "node": {"value": "18"},
            },
        },
    )

    assert "node_version_match" not in features
    assert features["node_declaration_version_match"] == 0
    assert features["node_declaration_major_difference"] == 2
    assert features["node_requirement_violation"] == 1


def test_legacy_repository_and_ci_runtimes_are_treated_as_declarations():
    features = compare(
        {
            "schema_version": "1.0",
            "source": {"type": "repository"},
            "runtimes": {"node": {"value": "20"}},
        },
        {
            "schema_version": "1.0",
            "source": {"type": "ci"},
            "runtimes": {"node": {"value": "18"}},
        },
    )

    assert "node_version_match" not in features
    assert features["node_declaration_version_match"] == 0
    assert features["node_declaration_major_difference"] == 2


def test_untyped_runtime_values_are_not_assumed_observed():
    features = compare(
        {"runtimes": {"python": {"value": "3.12"}}},
        {"runtimes": {"python": {"value": "3.11"}}},
    )

    assert "python_version_match" not in features
    assert "python_major_difference" not in features
