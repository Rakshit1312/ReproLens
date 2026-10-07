from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any, Literal

Label = Literal[0, 1, "U"]


@dataclass
class FailureEvidence:
    level: int
    source: str
    statement: str
    supports: bool

    @property
    def evidence_type(self) -> str:
        return {
            3: "controlled_perturbation",
            2: "explicit_failure_evidence",
            1: "historical_correlation",
            0: "guess",
        }.get(self.level, "unknown")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence_type"] = self.evidence_type
        return data


def classify_evidence(evidence: list[FailureEvidence]) -> dict[str, Any]:
    """Assign a conservative environment-induced label.

    1 = supported environment-induced failure
    0 = supported non-environment failure
    U = insufficient/conflicting evidence
    """
    if not evidence:
        return {"label": "U", "reason": "No causal evidence supplied."}

    strongest = max(e.level for e in evidence)
    strongest_items = [e for e in evidence if e.level == strongest]

    if strongest == 0:
        return {"label": "U", "reason": "Guess-level evidence cannot establish causality."}

    positive = any(e.supports for e in strongest_items)
    negative = any(not e.supports for e in strongest_items)
    if positive and negative:
        return {"label": "U", "reason": "Strongest evidence is conflicting."}
    if positive:
        return {"label": 1, "reason": f"Supported by level-{strongest} evidence."}
    return {"label": 0, "reason": f"Strongest evidence supports a non-environment cause (level {strongest})."}


def make_record(*, repository: str, outcome: int | None, evidence: list[FailureEvidence], failure_type: str | None = None) -> dict[str, Any]:
    """Create a dataset-ready causal-label record."""
    classification = classify_evidence(evidence)
    record = {
        "repository": repository,
        "ci_failed": outcome,
        "environment_induced_label": classification["label"],
        "label_reason": classification["reason"],
        "failure_type": failure_type if classification["label"] == 1 else None,
        "evidence": [e.to_dict() for e in evidence],
    }
    return record
