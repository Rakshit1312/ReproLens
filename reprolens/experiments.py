from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .labels import FailureEvidence, make_record


@dataclass
class ExperimentCase:
    case_id: str
    repository: str
    baseline_environment: dict[str, Any]
    perturbed_environment: dict[str, Any]
    change: dict[str, Any]
    baseline_outcome: str
    perturbed_outcome: str
    evidence_level: int
    failure_type: str | None = None
    evidence_source: str = "controlled_experiment"
    notes: str = ""
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_outcome(returncode: int) -> str:
    return "PASS" if returncode == 0 else "FAIL"


def run_command(command: list[str], *, cwd: str | Path, timeout: int = 900) -> dict[str, Any]:
    """Run a reproducible build/test command and capture only useful metadata."""
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "outcome": classify_outcome(completed.returncode),
            "returncode": completed.returncode,
            "stdout_tail": completed.stdout[-4000:],
            "stderr_tail": completed.stderr[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "outcome": "TIMEOUT",
            "returncode": None,
            "stdout_tail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
        }


def controlled_label(case: ExperimentCase) -> dict[str, Any]:
    """Create a causal label only when the controlled perturbation changes outcome.

    The source code and test command are assumed unchanged by the experiment harness.
    """
    baseline_passed = case.baseline_outcome == "PASS"
    perturbed_failed = case.perturbed_outcome in {"FAIL", "TIMEOUT"}

    if baseline_passed and perturbed_failed:
        evidence = FailureEvidence(
            level=3,
            source=case.evidence_source,
            statement=(
                "The same repository passed in the baseline environment and failed "
                "after the recorded environment perturbation."
            ),
            supports=True,
        )
        return make_record(
            repository=case.repository,
            outcome=1,
            evidence=[evidence],
            failure_type=case.failure_type,
        )

    if case.baseline_outcome == "FAIL" and case.perturbed_outcome == "FAIL":
        evidence = FailureEvidence(
            level=3,
            source=case.evidence_source,
            statement="Both baseline and perturbed environments failed; the perturbation did not isolate the failure.",
            supports=False,
        )
        return make_record(repository=case.repository, outcome=1, evidence=[evidence])

    return make_record(
        repository=case.repository,
        outcome=0 if case.perturbed_outcome == "PASS" else None,
        evidence=[
            FailureEvidence(
                level=3,
                source=case.evidence_source,
                statement="The controlled perturbation did not produce the required PASS-to-FAIL transition.",
                supports=False,
            )
        ],
    )


def append_jsonl(path: str | Path, record: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def save_experiment(path: str | Path, case: ExperimentCase, label_record: dict[str, Any]) -> None:
    record = case.to_dict()
    record["label"] = label_record
    append_jsonl(path, record)


def make_case(
    *,
    case_id: str,
    repository: str,
    baseline_environment: dict[str, Any],
    perturbed_environment: dict[str, Any],
    change: dict[str, Any],
    baseline_outcome: str,
    perturbed_outcome: str,
    failure_type: str | None = None,
    notes: str = "",
) -> ExperimentCase:
    return ExperimentCase(
        case_id=case_id,
        repository=repository,
        baseline_environment=baseline_environment,
        perturbed_environment=perturbed_environment,
        change=change,
        baseline_outcome=baseline_outcome,
        perturbed_outcome=perturbed_outcome,
        evidence_level=3,
        failure_type=failure_type,
        notes=notes,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
