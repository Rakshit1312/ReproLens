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
```

Or after installing:

```bash
pip install -e .
reprolens fingerprint .
```

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
