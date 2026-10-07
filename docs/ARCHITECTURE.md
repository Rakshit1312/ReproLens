# ReproLens Architecture V1.1

```text
User/UI
  -> API/Gateway
  -> Orchestrator
      -> Git Service
      -> Environment Service
      -> Sourcegraph Service
      -> RAG Service
      -> Compatibility Engine
      -> Prediction Model [next research module]
      -> LLM Service
```

## Service ownership

- Git Service: repository metadata and Git operations.
- Environment Service: development/CI fingerprints.
- Sourcegraph Service: repository-level semantic search.
- RAG Service: chunking and retrieval; local lexical retrieval is the deterministic baseline.
- Compatibility Engine: turns fingerprint differences into candidate causes.
- Prediction Model: estimates failure risk; not yet part of the V1 vertical slice.
- LLM Service: produces evidence-grounded explanations through a local Ollama endpoint.
- Orchestrator: coordinates one request through the services.

## Important methodological rule

Detection, compatibility analysis, causal labeling, prediction, and explanation are separate stages. A mismatch is not automatically a failure.
