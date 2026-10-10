from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional


@dataclass
class Evidence:
    source: str
    confidence: str = "medium"


@dataclass
class Field:
    value: Any = None
    evidence: list[Evidence] = field(default_factory=list)

    def to_dict(self):
        return {
            "value": self.value,
            "evidence": [asdict(e) for e in self.evidence],
        }


@dataclass
class Fingerprint:
    schema_version: str = "1.1"
    source_type: str = "repository"
    platform: Dict[str, Field] = field(default_factory=dict)
    runtimes: Dict[str, Field] = field(default_factory=dict)
    runtime_declarations: Dict[str, Field] = field(default_factory=dict)
    package_managers: Dict[str, Field] = field(default_factory=dict)
    build_tools: Dict[str, Field] = field(default_factory=dict)
    dependencies: Dict[str, Field] = field(default_factory=dict)
    requirements: Dict[str, Field] = field(default_factory=dict)
    configuration: Dict[str, Field] = field(default_factory=dict)
    resources: Dict[str, Field] = field(default_factory=dict)
    conflicts: list[dict] = field(default_factory=list)

    def to_dict(self):
        def convert(section):
            return {k: v.to_dict() for k, v in section.items()}

        return {
            "schema_version": self.schema_version,
            "source": {"type": self.source_type},
            "platform": convert(self.platform),
            "runtimes": convert(self.runtimes),
            "runtime_declarations": convert(self.runtime_declarations),
            "package_managers": convert(self.package_managers),
            "build_tools": convert(self.build_tools),
            "dependencies": convert(self.dependencies),
            "requirements": convert(self.requirements),
            "configuration": convert(self.configuration),
            "resources": convert(self.resources),
            "conflicts": self.conflicts,
        }
