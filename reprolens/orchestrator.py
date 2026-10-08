from __future__ import annotations

from pathlib import Path
from typing import Any

from .diff import analyze_compatibility
from .extractor import fingerprint_ci, fingerprint_repository
from .repo_prediction import predict_repository
from .services.rag_service import build_repository_retriever
from .services.sourcegraph_service import SourcegraphService


def analyze_repository(
    repo: str | Path,
    question: str | None = None,
    top_k: int = 5,
    use_sourcegraph: bool = True,
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    dev = fingerprint_repository(repo).to_dict()
    ci = fingerprint_ci(repo).to_dict()
    compatibility = analyze_compatibility(dev, ci)

    prediction = predict_repository(
        compatibility["features"]
    )

    retriever = build_repository_retriever(repo)
    query = question or (
        "environment runtime dependency CI build "
        "configuration compatibility"
    )
    contexts = retriever.retrieve(query, k=top_k)

    sourcegraph_results = []
    if use_sourcegraph:
        try:
            remote = SourcegraphService()
            info = remote.search(
                query,
                repo=None,
                limit=top_k,
            )
            sourcegraph_results = [
                {
                    "path": r.path,
                    "repository": r.repository,
                    "preview": r.preview,
                }
                for r in info
            ]
        except Exception:
            sourcegraph_results = []

    return {
        "repository": str(repo),
        "development_fingerprint": dev,
        "ci_fingerprint": ci,
        "compatibility": compatibility,
        "prediction": prediction,
        "retrieved_context": contexts,
        "sourcegraph_results": sourcegraph_results,
        "llm_input": {
            "question": query,
            "risk": compatibility,
            "prediction": prediction,
            "context_count": len(contexts),
        },
        "note": (
            "Prediction is a prototype benchmark-model signal. "
            "Compatibility candidates are hypotheses until supported "
            "by evidence."
        ),
    }
