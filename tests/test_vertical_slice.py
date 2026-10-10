from pathlib import Path

from reprolens.services.rag_service import build_repository_retriever
from reprolens.services.sourcegraph_service import SourcegraphService


def test_local_retriever_finds_environment_code(tmp_path: Path):
    (tmp_path / "environment.py").write_text("NODE_VERSION = '20'\nCI_NODE = '18'\n", encoding="utf-8")
    r = build_repository_retriever(tmp_path)
    results = r.retrieve("Node CI environment version", k=3)
    assert results
    assert results[0]["source"] == "environment.py"


def test_targeted_environment_query_prefers_extraction_evidence(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "EXTRACTION_SPEC.md").write_text(
        "CI workflow runtime version requirements dependencies "
        "pyproject.toml package.json Dockerfile",
        encoding="utf-8",
    )
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "App.jsx").write_text(
        "environment runtime dependency CI build configuration compatibility",
        encoding="utf-8",
    )

    retriever = build_repository_retriever(tmp_path)
    results = retriever.retrieve(
        "CI workflow runtime version requirements dependencies "
        "pyproject.toml package.json Dockerfile",
        k=2,
    )

    assert Path(results[0]["source"]) == Path("docs") / "EXTRACTION_SPEC.md"


def test_sourcegraph_without_credentials_is_safe(monkeypatch):
    monkeypatch.delenv("SRC_ACCESS_TOKEN", raising=False)
    svc = SourcegraphService(endpoint="http://127.0.0.1:9")
    assert svc.search("ReproLens", limit=1) == []
