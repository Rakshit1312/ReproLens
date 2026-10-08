from __future__ import annotations

from pathlib import Path

try:
    from fastapi import FastAPI
    from pydantic import BaseModel
except ImportError as exc:
    raise RuntimeError(
        "Install the api extra: pip install -e '.[api]'"
    ) from exc

from reprolens.orchestrator import analyze_repository
from reprolens.predictor import run_experiment
from reprolens.model_comparison import compare_models


app = FastAPI(
    title="ReproLens API",
    version="0.3.0",
)


class AnalyzeRequest(BaseModel):
    repository: str
    question: str | None = None
    top_k: int = 5
    sourcegraph: bool = True


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "reprolens-api",
    }


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    return analyze_repository(
        Path(request.repository),
        question=request.question,
        top_k=request.top_k,
        use_sourcegraph=request.sourcegraph,
    )


@app.get("/models")
def models():
    """
    Compare all ReproLens prediction approaches
    on the controlled benchmark.
    """

    experiment = run_experiment()
    cross_validation = compare_models()

    return {
        "dataset_size": experiment["dataset_size"],
        "training_examples": experiment["training_examples"],
        "test_examples": experiment["test_examples"],
        "random_state": experiment["random_state"],
        "evaluation_type": "controlled_holdout",
        "warning": (
            "Results are preliminary because the benchmark "
            "contains only 20 controlled examples."
        ),
        "models": experiment["results"],
        "cross_validation": cross_validation,
    }