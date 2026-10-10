from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from reprolens import cli, orchestrator
from reprolens.services.llm_service import (
    LLMConfigurationError,
    LLMProviderError,
    LLMTimeoutError,
)


def _stub_analysis(monkeypatch, llm_service=None):
    captured = {}
    monkeypatch.setattr(
        orchestrator,
        "fingerprint_repository",
        lambda repo: SimpleNamespace(to_dict=lambda: {"side": "development"}),
    )
    monkeypatch.setattr(
        orchestrator,
        "fingerprint_ci",
        lambda repo: SimpleNamespace(to_dict=lambda: {"side": "ci"}),
    )
    monkeypatch.setattr(
        orchestrator,
        "analyze_compatibility",
        lambda dev, ci: {
            "features": {"python_version_match": 0},
            "compatibility": {"candidates": [{"code": "runtime_mismatch"}]},
        },
    )
    monkeypatch.setattr(
        orchestrator,
        "predict_repository",
        lambda features: {
            "prediction": 1,
            "risk_score": 0.7,
            "warning": "Not calibrated.",
        },
    )

    class Retriever:
        def retrieve(self, query, k):
            captured["query"] = query
            return [{"source": "pyproject.toml", "text": "requires-python >=3.11"}]

    monkeypatch.setattr(
        orchestrator,
        "build_repository_retriever",
        lambda repo: Retriever(),
    )
    if llm_service is not None:
        monkeypatch.setattr(orchestrator, "LLMService", llm_service)
    return captured


def test_analysis_without_llm_preserves_analysis_and_does_not_call_provider(
    tmp_path: Path, monkeypatch
):
    def unexpected_provider():
        raise AssertionError("LLM should remain opt-in")

    captured = _stub_analysis(monkeypatch, unexpected_provider)

    result = orchestrator.analyze_repository(
        tmp_path,
        use_sourcegraph=False,
    )

    assert result["compatibility"]["features"]["python_version_match"] == 0
    assert result["prediction"]["prediction"] == 1
    assert result["retrieved_context"][0]["source"] == "pyproject.toml"
    assert result["llm_enabled"] is False
    assert result["llm_status"] == "disabled"
    assert result["explanation"] is None
    assert result["llm_metadata"] is None
    assert captured["query"] == (
        "CI workflow runtime version requirements dependencies "
        "pyproject.toml package.json Dockerfile"
    )


def test_analysis_uses_grounded_prompt_and_returns_provider_metadata(
    tmp_path: Path, monkeypatch
):
    captured = {}

    class MockLLM:
        provider = "openai-compatible"
        model = "mock-model"

        def generate(self, prompt):
            captured["prompt"] = prompt
            return "Evidence in pyproject.toml supports checking Python versions."

    _stub_analysis(monkeypatch, MockLLM)

    result = orchestrator.analyze_repository(
        tmp_path,
        question="Could the Python requirement conflict with CI?",
        use_sourcegraph=False,
        use_llm=True,
    )

    assert "Could the Python requirement conflict with CI?" in captured["prompt"]
    assert "pyproject.toml" in captured["prompt"]
    assert '"risk_score": 0.7' in captured["prompt"]
    assert result["explanation"].startswith("Evidence in pyproject.toml")
    assert result["llm_status"] == "generated"
    assert result["llm_metadata"] == {
        "provider": "openai-compatible",
        "model": "mock-model",
    }


def test_api_request_defaults_to_non_llm_and_returns_llm_shape(monkeypatch):
    from api import app as api

    calls = []

    def fake_analyze_repository(repository, **kwargs):
        calls.append(kwargs)
        enabled = kwargs["use_llm"]
        return {
            "llm_enabled": enabled,
            "explanation": "Grounded explanation" if enabled else None,
            "llm_metadata": (
                {"provider": "ollama", "model": "test-model"} if enabled else None
            ),
        }

    monkeypatch.setattr(api, "analyze_repository", fake_analyze_repository)

    disabled = api.analyze(
        api.AnalyzeRequest(repository=".", sourcegraph=False),
    )
    enabled = api.analyze(
        api.AnalyzeRequest(repository=".", sourcegraph=False, llm=True),
    )

    assert disabled["llm_enabled"] is False
    assert enabled["explanation"] == "Grounded explanation"
    assert enabled["llm_metadata"]["provider"] == "ollama"
    assert calls[0]["use_llm"] is False
    assert calls[1]["use_llm"] is True


def test_api_analysis_preserves_observed_and_declared_runtime_sections(
    monkeypatch,
):
    from api import app as api

    expected = {
        "development_fingerprint": {
            "schema_version": "1.1",
            "runtimes": {"python": {"value": "3.12"}},
            "runtime_declarations": {"python": {"value": "3.11"}},
        },
        "ci_fingerprint": {
            "schema_version": "1.1",
            "runtimes": {},
            "runtime_declarations": {"python": {"value": "3.11"}},
        },
    }
    monkeypatch.setattr(
        api,
        "analyze_repository",
        lambda repository, **kwargs: expected,
    )

    response = api.analyze(api.AnalyzeRequest(repository=".", llm=False))

    assert response["development_fingerprint"]["runtimes"] == {
        "python": {"value": "3.12"}
    }
    assert response["development_fingerprint"]["runtime_declarations"] == {
        "python": {"value": "3.11"}
    }
    assert response["ci_fingerprint"]["runtimes"] == {}
    assert response["ci_fingerprint"]["runtime_declarations"] == {
        "python": {"value": "3.11"}
    }


def test_api_serializes_unknown_compatibility_states(monkeypatch):
    from fastapi.encoders import jsonable_encoder

    from api import app as api
    from reprolens.diff import analyze_compatibility

    analysis = analyze_compatibility(
        {"source": {"type": "repository"}},
        {"source": {"type": "ci"}},
    )
    monkeypatch.setattr(
        api,
        "analyze_repository",
        lambda repository, **kwargs: {
            "compatibility": analysis,
            "development_fingerprint": {"source": {"type": "repository"}},
            "ci_fingerprint": {"source": {"type": "ci"}},
        },
    )

    response = api.analyze(
        api.AnalyzeRequest(repository=".", sourcegraph=False)
    )
    payload = json.loads(json.dumps(jsonable_encoder(response)))

    assert payload["compatibility"]["features"]["os_match"] is None
    assert "python_version_match" not in payload["compatibility"]["features"]
    assert payload["compatibility"]["statuses"] == {
        "runtime": "unknown",
        "dependencies": "unknown",
        "os": "unknown",
        "configuration": "unknown",
        "resources": "unknown",
    }


def test_api_reports_llm_configuration_error_without_secret_details(monkeypatch):
    from api import app as api

    def fail_analysis(*args, **kwargs):
        raise LLMConfigurationError(
            "Set REPROLENS_LLM_API_KEY before using the hosted LLM provider."
        )

    monkeypatch.setattr(api, "analyze_repository", fail_analysis)
    with pytest.raises(api.HTTPException) as raised:
        api.analyze(api.AnalyzeRequest(repository=".", llm=True))

    assert raised.value.status_code == 503
    assert "API key" in raised.value.detail
    assert "test-secret" not in raised.value.detail


@pytest.mark.parametrize(
    ("error", "status_code", "safe_detail"),
    [
        (
            LLMProviderError("raw provider response contains test-secret"),
            503,
            "LLM provider is unavailable or returned an invalid response.",
        ),
        (
            LLMTimeoutError("raw provider response contains test-secret"),
            504,
            "LLM provider request timed out. Retry or check provider availability.",
        ),
    ],
)
def test_api_sanitizes_llm_provider_and_timeout_errors(
    monkeypatch, error, status_code, safe_detail
):
    from api import app as api

    def fail_analysis(*args, **kwargs):
        raise error

    monkeypatch.setattr(api, "analyze_repository", fail_analysis)
    with pytest.raises(api.HTTPException) as raised:
        api.analyze(api.AnalyzeRequest(repository=".", llm=True))

    assert raised.value.status_code == status_code
    assert raised.value.detail == safe_detail
    assert "test-secret" not in raised.value.detail
    assert "raw provider response" not in raised.value.detail


def test_cli_json_output_includes_enabled_explanation(monkeypatch, capsys):
    captured = {}

    def fake_analyze_repository(*args, **kwargs):
        captured.update(kwargs)
        return {
            "llm_enabled": True,
            "explanation": "Check pyproject.toml against the CI runtime.",
            "llm_metadata": {"provider": "openai-compatible", "model": "mock"},
        }

    monkeypatch.setattr(cli, "analyze_repository", fake_analyze_repository)
    monkeypatch.setattr(
        sys,
        "argv",
        ["reprolens", "analyze", ".", "--llm", "--json", "--no-sourcegraph"],
    )

    cli.main()
    result = json.loads(capsys.readouterr().out)

    assert captured["use_llm"] is True
    assert result["explanation"] == "Check pyproject.toml against the CI runtime."
    assert result["llm_metadata"]["model"] == "mock"


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            LLMConfigurationError("configuration contains test-secret"),
            "LLM configuration error",
        ),
        (
            LLMProviderError("raw provider response contains test-secret"),
            "LLM provider failed or is unavailable",
        ),
        (
            LLMTimeoutError("raw provider response contains test-secret"),
            "LLM request timed out",
        ),
    ],
)
def test_cli_reports_llm_failures_without_traceback(
    monkeypatch, capsys, error, message
):
    def fail_analysis(*args, **kwargs):
        raise error

    monkeypatch.setattr(cli, "analyze_repository", fail_analysis)
    monkeypatch.setattr(
        sys,
        "argv",
        ["reprolens", "analyze", ".", "--llm", "--no-sourcegraph"],
    )

    with pytest.raises(SystemExit) as raised:
        cli.main()

    output = capsys.readouterr()
    assert raised.value.code == 2
    assert message in output.err
    assert "test-secret" not in output.err
    assert "raw provider response" not in output.err
    assert "Traceback" not in output.err
    assert output.out == ""


def test_human_analysis_output_includes_explanation(capsys):
    cli.print_analysis(
        {
            "repository": "sample/repo",
            "development_fingerprint": {"requirements": {}},
            "ci_fingerprint": {"runtimes": {}, "platform": {}},
            "compatibility": {
                "features": {},
                "compatibility": {"candidates": []},
            },
            "prediction": {
                "prediction": 0,
                "risk_score": 0.1,
                "threshold": 0.5,
                "status": "prototype_benchmark_model",
            },
            "retrieved_context": [],
            "sourcegraph_results": [],
            "explanation": "Verify the CI Python runtime against pyproject.toml.",
            "llm_metadata": {
                "provider": "openai-compatible",
                "model": "test-model",
            },
        }
    )

    output = capsys.readouterr().out
    assert "LLM EXPLANATION (openai-compatible / test-model)" in output
    assert "Verify the CI Python runtime against pyproject.toml." in output
