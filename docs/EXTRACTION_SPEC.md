# ReproLens V1 Environment Extraction Specification

## Research purpose

Construct a reproducible, structured representation of build-relevant development and CI environments, then convert their differences into predictive features for environment-induced CI failure.

## Sources

### Development-side sources
- Actual local machine via `reprolens fingerprint --local`.
- `.nvmrc`, `.node-version`, `.python-version`, `.ruby-version`.
- `package.json` (`engines`, `devEngines`, `os`, `cpu`, `libc`, package manager).
- `pyproject.toml` (`requires-python`, dependencies).
- `pom.xml`, `build.gradle`, `build.gradle.kts`.
- `Dockerfile`.
- `.devcontainer/devcontainer.json` or `.devcontainer.json`.

### CI-side sources
- `.github/workflows/*.yml` and `*.yaml`.
- `runs-on` for runner/OS information.
- `actions/setup-node`, `actions/setup-python`, `actions/setup-java` version inputs.
- workflow/job/step `env` declarations.
- step shell declarations.

## Provenance rule

Every extracted value records its source and confidence. Repository declarations are not treated as proof of actual local state.

Runtime values observed by local machine probes belong in `runtimes`
(fingerprint schema 1.1).
Repository version files, `package.json` `devEngines.runtime` declarations,
and CI `actions/setup-*` version inputs belong in `runtime_declarations`.
Compare declared versions with declared versions and observed versions with
observed versions; do not infer an observed local version from repository
configuration. If a value was not observed or declared, preserve it as unknown.
When reading schema 1.0 repository or CI fingerprints, interpret their `runtimes`
entries as declarations for comparison, not observed local machine values.

## Confidence

- High: direct machine observation or explicit machine/configuration declaration.
- Medium: inferred from build configuration or partial declaration.
- Low: weak documentation inference.

## Security rule

Never collect secret values. For environment variables, record presence/name only where appropriate.

## V1 feature principles

- Keep features interpretable.
- Do not turn every raw dependency into a separate feature.
- Do not assume mismatch means failure.
- Preserve unknown values.
- Do not use post-CI failure information when constructing pre-CI prediction inputs.

## Target features

Platform: OS match, architecture match, libc match.

Runtime: version match, major-version difference, requirement violation.

Tools: package-manager/build-tool match and requirement violation.

Dependencies: dependency count, lockfile presence, environment conflict indicators.

Configuration: missing required environment variables, configuration difference count.

Resources: CPU/memory ratios when actual observations are available.

General: total environment difference count and unknown-field count.
