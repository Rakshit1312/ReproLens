# ReproLens

ReproLens is an experimental AI-assisted DevOps system for predicting environment-induced CI failures before CI execution.

## V1 currently implemented

- Repository environment fingerprinting
- Local machine fingerprinting
- GitHub Actions workflow extraction
- Node/Python/Java runtime extraction
- Package manager/build-tool extraction
- Basic project requirement extraction
- Provenance/confidence for extracted values
- Development/CI feature comparison

## Run

```bash
python -m reprolens.cli fingerprint /path/to/repo
python -m reprolens.cli fingerprint /path/to/repo --ci
python -m reprolens.cli fingerprint --local
python -m reprolens.cli compare dev.json ci.json
python -m reprolens.cli analyze . --no-sourcegraph
```

Or after installing:

```bash
pip install -e .
reprolens fingerprint .
```

## Optional LLM explanation

Repository analysis does not call an LLM unless explicitly enabled. The local
retriever is lexical, and the explanation receives repository snippets plus
structured compatibility and prototype-prediction data. It must be treated as
an evidence-limited explanation: it does not imply that a mismatch caused a
failure, and the controlled-benchmark prediction is not a calibrated
real-world probability. Historical incidents and postmortems are not indexed.

Use the configured provider from the CLI:

```bash
reprolens analyze . --llm
reprolens analyze . --llm --json --output reprolens-report.json
```

Or send `"llm": true` in a `POST /analyze` request. The API defaults to
`llm: false`.

Configuration uses environment variables:

| Variable | Purpose |
| --- | --- |
| `REPROLENS_LLM_PROVIDER` | `openai-compatible` (default) or `ollama` |
| `REPROLENS_LLM_BASE_URL` | Hosted API base URL; defaults to `https://api.openai.com/v1`. For Ollama, defaults to `OLLAMA_URL`. |
| `REPROLENS_LLM_MODEL` | Model name; required for hosted providers |
| `REPROLENS_LLM_API_KEY` | Hosted provider credential; never needed by Ollama |
| `REPROLENS_LLM_TIMEOUT` | Request timeout in seconds (default `30`) |
| `OLLAMA_URL` | Ollama endpoint when `REPROLENS_LLM_BASE_URL` is unset (default `http://localhost:11434`) |
| `OLLAMA_MODEL` | Ollama model when `REPROLENS_LLM_MODEL` is unset (default `codellama:7b-instruct`) |

The GitHub Actions workflow always creates a non-LLM JSON report and CI
fingerprint. It only passes the hosted API key to a separate LLM step on pushes
to the repository's default branch; fork pull requests run without hosted
credentials. Reports identify whether an LLM explanation was generated.

## Research principle

A detected environment difference is **not** automatically a failure. ReproLens separates:

1. observed/declarative environment facts,
2. compatibility features,
3. predicted failure risk,
4. historical evidence and explanation.

Unknown information is preserved as unknown rather than guessed.

## Controlled experiment dataset

ReproLens uses controlled perturbation experiments for high-confidence labels. The required causal transition is:

`same source + baseline environment PASS -> one environment change -> perturbed environment FAIL`

Such a case receives evidence level 3. Cases without that transition are not promoted to positive causal labels. Unknown or insufficiently supported cases remain `U`.

Use `reprolens.experiments` to create experiment cases, run commands, classify outcomes, and persist JSONL records.
