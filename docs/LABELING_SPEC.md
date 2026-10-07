# ReproLens V1 Failure Labeling Specification

## Target label

`environment_induced_label` has three states:

- `1`: environment-induced CI failure supported by evidence.
- `0`: CI failure supported as non-environment-induced.
- `U`: unknown / insufficient evidence.

Unknown examples must not be silently converted to 0 or 1.

## Evidence hierarchy

### Level 3 — controlled perturbation
Same source code and controlled setup; change an environment variable while holding other relevant factors constant, and observe the outcome change.

Example: Java 17 passes and Java 11 fails for the same source and test procedure.

### Level 2 — explicit failure evidence
The CI output directly identifies an environment incompatibility.

Example: `UnsupportedClassVersionError`, or an explicit message that Java 17 is required while Java 11 is active.

### Level 1 — historical correlation
Repeated historical association between an environment configuration and similar failures. Useful for retrieval and prioritization, but weaker causal evidence.

### Level 0 — guess
Analyst/model suspicion without supporting evidence. Cannot establish a positive or negative causal label.

## V1 taxonomy

- `E1`: runtime / toolchain mismatch
- `E2`: dependency–environment incompatibility
- `E3`: OS / platform mismatch
- `E4`: configuration mismatch
- `E5`: resource mismatch

## Labeling rule

Use the strongest available evidence. If the strongest evidence conflicts, label `U`.

A detected environment difference is never itself sufficient to label a failure as environment-induced.

## Dataset record

Each sample should retain:

- repository identifier
- development fingerprint
- CI fingerprint
- difference features
- CI outcome
- environment-induced label
- failure type when label = 1
- evidence records
- evidence source and level

## Pre-CI constraint

Prediction features must be restricted to information available before the target CI execution. Post-execution logs may be used for evaluation/causal labeling, but never as prediction inputs for that same target run.
