
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any


EVIDENCE_LEVELS = {
    3: "controlled_perturbation",
    2: "explicit_failure_evidence",
    1: "historical_correlation",
    0: "guess",
}

TAXONOMY = {
    "E1": "runtime_toolchain_mismatch",
    "E2": "dependency_environment_incompatibility",
    "E3": "os_platform_mismatch",
    "E4": "configuration_mismatch",
    "E5": "resource_mismatch",
}


@dataclass
class Candidate:
    code: str
    reason: str
    features: list[str]
    severity: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def analyze(features: dict[str, Any]) -> dict[str, Any]:
    """Turn environment differences into compatibility *candidates*.

    This is intentionally not a failure classifier. A difference is only a
    potential cause until evidence establishes causality.
    """
    candidates: list[Candidate] = []

    runtime_violation = [k for k, v in features.items() if k.endswith("_requirement_violation") and v == 1]
    runtime_diff = [k for k, v in features.items() if k.endswith("_major_difference") and isinstance(v, (int, float)) and v > 0]
    if runtime_violation:
        candidates.append(Candidate("E1", "CI runtime configuration violates a declared project requirement.", runtime_violation, "high"))
    elif runtime_diff:
        candidates.append(Candidate("E1", "Development and CI runtime declarations or observed versions differ.", runtime_diff, "medium"))

    dep_conflict = features.get("dependency_environment_conflict")
    if dep_conflict == 1:
        candidates.append(Candidate("E2", "A dependency is incompatible with the CI environment.", ["dependency_environment_conflict"], "high"))

    platform_mismatch = [k for k, v in features.items() if k.endswith("_match") and v == 0 and k.split("_")[0] in {"os", "architecture", "libc"}]
    if platform_mismatch:
        candidates.append(Candidate("E3", "Development and CI platform attributes differ.", platform_mismatch, "medium"))

    if features.get("required_env_missing") == 1:
        candidates.append(Candidate("E4", "A required environment variable is missing from CI.", ["required_env_missing"], "high"))

    if features.get("resource_constraint_detected") == 1:
        candidates.append(Candidate("E5", "CI resources are below a detected project requirement.", ["resource_constraint_detected"], "high"))

    return {
        "candidates": [c.to_dict() for c in candidates],
        "candidate_count": len(candidates),
        "note": "Candidates are hypotheses until supported by evidence.",
    }
