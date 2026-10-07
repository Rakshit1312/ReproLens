from __future__ import annotations

from pathlib import Path

try:
    from fastapi import FastAPI
    from pydantic import BaseModel
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("Install the api extra: pip install -e '.[api]'") from exc

from reprolens.orchestrator import analyze_repository

app = FastAPI(title="ReproLens API", version="0.2.0")


class AnalyzeRequest(BaseModel):
    repository: str
    question: str | None = None
    top_k: int = 5
    sourcegraph: bool = True


@app.get("/health")
def health():
    return {"status": "ok", "service": "reprolens-api"}


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    return analyze_repository(
        Path(request.repository),
        question=request.question,
        top_k=request.top_k,
        use_sourcegraph=request.sourcegraph,
    )
