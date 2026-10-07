# ReproLens — Faculty Phase 2 Alignment

This document maps the implementation to the course Phase 2 requirements.

| Faculty requirement | ReproLens implementation | Status |
|---|---|---|
| RAG-based Q&A bot | `services/rag_service.py` + repository retriever | Working local retrieval baseline; LangChain adapter is optional next step |
| LangChain or LlamaIndex | `langchain_status()` and integration boundary | Dependency-ready; install and wire the selected vector stack in the lab environment |
| GitHub Actions CI/CD | `.github/workflows/reprolens.yml` | Implemented |
| Sweep.dev automation | CI integration boundary reserved | Requires the course-provided Sweep configuration/account; not fabricated here |
| AI-assisted test generation | `data/evaluation/questions.json` + test suite; Codeium/Codium can be used in IDE | Partially implemented; external assistant integration requires its account/tooling |
| Repository understanding | Sourcegraph adapter + local repository retrieval | Implemented as adapters |
| Quantitative research | experiment/labeling modules | In progress |

## Research boundary

The primary research question remains:

> Can structured development–CI environment differences accurately predict whether a software project will experience an environment-induced build failure?

RAG and repository-level retrieval are supporting evidence/explanation components. They must not be treated as proof of causality.
