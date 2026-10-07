from pathlib import Path

from reprolens.services.rag_service import build_repository_retriever
from reprolens.services.sourcegraph_service import SourcegraphService


def test_local_retriever_finds_environment_code(tmp_path: Path):
    (tmp_path / "environment.py").write_text("NODE_VERSION = '20'\nCI_NODE = '18'\n", encoding="utf-8")
    r = build_repository_retriever(tmp_path)
    results = r.retrieve("Node CI environment version", k=3)
    assert results
    assert results[0]["source"] == "environment.py"


def test_sourcegraph_without_credentials_is_safe(monkeypatch):
    monkeypatch.delenv("SRC_ACCESS_TOKEN", raising=False)
    svc = SourcegraphService(endpoint="http://127.0.0.1:9")
    assert svc.search("ReproLens", limit=1) == []
