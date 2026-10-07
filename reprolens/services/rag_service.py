from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Chunk:
    chunk_id: str
    source: str
    text: str


class LocalRetriever:
    """Deterministic lexical retriever used as the offline baseline.

    It is deliberately simple: this is the retrieval baseline, not the final
    claim of semantic retrieval quality. A LangChain adapter can replace it
    when the course environment has LangChain/vector-store dependencies.
    """

    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self.df: dict[str, int] = {}
        self.tokens: list[set[str]] = []
        for chunk in chunks:
            toks = self._tokens(chunk.text)
            self.tokens.append(toks)
            for t in toks:
                self.df[t] = self.df.get(t, 0) + 1

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[A-Za-z0-9]{2,}", text.lower()))

    def retrieve(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        q = self._tokens(query)
        scored = []
        n = max(len(self.chunks), 1)
        for chunk, toks in zip(self.chunks, self.tokens):
            overlap = q & toks
            if not overlap:
                score = 0.0
            else:
                score = sum(math.log((n + 1) / max(self.df[t], 1)) for t in overlap) / max(len(q), 1)
            scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"source": c.source, "text": c.text, "score": round(s, 4)} for s, c in scored[:k] if s > 0]


def build_repository_retriever(repo: str | Path, max_file_bytes: int = 200_000) -> LocalRetriever:
    root = Path(repo)
    ignore_dirs = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__"}
    chunks: list[Chunk] = []
    extensions = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".md", ".json", ".toml", ".yml", ".yaml", ".xml", ".gradle", ".txt"}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        if any(part in ignore_dirs for part in path.parts):
            continue
        try:
            if path.stat().st_size > max_file_bytes:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lines = text.splitlines()
        # Small deterministic chunks: 80 lines with 10-line overlap.
        for start in range(0, len(lines), 70):
            block = "\n".join(lines[start:start + 80]).strip()
            if not block:
                continue
            cid = hashlib.sha1(f"{path}:{start}".encode()).hexdigest()[:12]
            chunks.append(Chunk(cid, str(path.relative_to(root)), block))
    return LocalRetriever(chunks)


def langchain_status() -> dict[str, Any]:
    try:
        import langchain  # type: ignore
        return {"available": True, "version": getattr(langchain, "__version__", "unknown")}
    except ImportError:
        return {"available": False, "version": None}
