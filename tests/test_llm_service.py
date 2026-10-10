from __future__ import annotations

import io
import json
import urllib.error
from pathlib import Path

import pytest

from reprolens.services.llm_service import (
    LLMConfigurationError,
    LLMProviderError,
    LLMTimeoutError,
    LLMService,
    grounded_prompt,
)


class MockResponse:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


def test_grounded_prompt_contains_question_structured_data_and_untrusted_evidence():
    prompt = grounded_prompt(
        "Why could CI differ?",
        {"features": {"python_version_match": 0}},
        {"prediction": 1, "risk_score": 0.72},
        [{"source": "pyproject.toml", "text": "requires-python = '>=3.11'"}],
    )

    assert "Why could CI differ?" in prompt
    assert '"python_version_match": 0' in prompt
    assert '"risk_score": 0.72' in prompt
    assert "pyproject.toml" in prompt
    assert "untrusted data" in prompt
    assert "not a calibrated real-world probability" in prompt
    assert "Never invent historical incidents" in prompt


def test_openai_compatible_response_is_parsed(monkeypatch):
    captured = {}

    def mock_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = request.headers
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return MockResponse(
            b'{"choices":[{"message":{"content":"Grounded explanation"}}]}'
        )

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
    service = LLMService(
        provider="openai-compatible",
        base_url="https://llm.example/v1/",
        model="research-model",
        api_key="test-secret",
        timeout=8,
    )

    assert service.generate("prompt") == "Grounded explanation"
    assert captured["url"] == "https://llm.example/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-secret"
    assert captured["payload"]["model"] == "research-model"
    assert captured["timeout"] == 8


def test_missing_hosted_api_key_is_a_configuration_error(monkeypatch):
    monkeypatch.delenv("REPROLENS_LLM_API_KEY", raising=False)
    service = LLMService(
        provider="openai-compatible",
        model="configured-model",
        api_key="",
    )

    with pytest.raises(LLMConfigurationError, match="REPROLENS_LLM_API_KEY"):
        service.generate("prompt")


def test_missing_hosted_model_is_a_configuration_error(monkeypatch):
    monkeypatch.delenv("REPROLENS_LLM_MODEL", raising=False)
    service = LLMService(
        provider="openai-compatible",
        model="",
        api_key="test-secret",
    )

    with pytest.raises(LLMConfigurationError, match="REPROLENS_LLM_MODEL"):
        service.generate("prompt")


def test_http_error_does_not_include_response_or_credentials(monkeypatch):
    def mock_urlopen(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url,
            401,
            "Unauthorized",
            {},
            io.BytesIO(b"provider echoed test-secret"),
        )

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
    service = LLMService(model="configured-model", api_key="test-secret")

    with pytest.raises(LLMProviderError, match="HTTP 401") as error:
        service.generate("prompt")
    assert "test-secret" not in str(error.value)
    assert "provider echoed" not in str(error.value)


def test_timeout_is_reported(monkeypatch):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: (_ for _ in ()).throw(TimeoutError()),
    )
    service = LLMService(model="configured-model", api_key="test-secret")

    with pytest.raises(LLMTimeoutError, match="did not respond"):
        service.generate("prompt")


def test_unavailable_provider_is_reported_without_endpoint_details(monkeypatch):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: (_ for _ in ()).throw(
            urllib.error.URLError("connection refused")
        ),
    )
    service = LLMService(model="configured-model", api_key="test-secret")

    with pytest.raises(LLMProviderError, match="unavailable") as error:
        service.generate("prompt")
    assert "test-secret" not in str(error.value)
    assert "connection refused" not in str(error.value)


@pytest.mark.parametrize(
    "body",
    [
        b"not-json",
        b'{"choices":[]}',
        b'{"choices":[{"message":{"content":null}}]}',
    ],
)
def test_malformed_provider_responses_are_reported(monkeypatch, body):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: MockResponse(body),
    )
    service = LLMService(model="configured-model", api_key="test-secret")

    with pytest.raises(LLMProviderError):
        service.generate("prompt")


def test_ollama_response_is_supported_without_api_key(monkeypatch):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: MockResponse(b'{"response":"Local explanation"}'),
    )
    service = LLMService(
        provider="ollama",
        base_url="http://localhost:11434",
        model="local-model",
    )

    assert service.generate("prompt") == "Local explanation"


def test_workflow_report_command_writes_json_without_llm(
    tmp_path: Path, monkeypatch, capsys
):
    from reprolens import cli

    report = {
        "llm_enabled": False,
        "explanation": None,
        "llm_metadata": None,
    }
    calls = {}
    monkeypatch.setattr(
        cli,
        "analyze_repository",
        lambda *args, **kwargs: calls.update(kwargs) or report,
    )
    output = tmp_path / "reprolens-report.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "reprolens",
            "analyze",
            ".",
            "--no-sourcegraph",
            "--json",
            "--output",
            str(output),
        ],
    )

    cli.main()

    assert json.loads(output.read_text(encoding="utf-8")) == report
    assert calls["use_llm"] is False
    assert capsys.readouterr().out == ""


def test_workflow_gates_credentials_to_trusted_default_branch():
    import yaml

    workflow_path = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "reprolens.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["reprolens"]["steps"]
    report_step = next(
        step
        for step in steps
        if step["name"] == "Run ReproLens analysis without hosted credentials"
    )
    hosted_step = next(
        step
        for step in steps
        if step["name"] == "Add hosted LLM explanation on trusted default-branch pushes"
    )

    assert "--output reprolens-report.json" in report_step["run"]
    assert "github.event_name == 'push'" in hosted_step["if"]
    assert "github.event.repository.default_branch" in hosted_step["if"]
    assert "REPROLENS_LLM_API_KEY" in hosted_step["env"]
    upload_step = next(
        step for step in steps if step["name"] == "Upload ReproLens evidence and report"
    )
    assert "ci-fingerprint.json" in upload_step["with"]["path"]
    assert "reprolens-report.json" in upload_step["with"]["path"]
