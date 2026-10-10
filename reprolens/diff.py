from __future__ import annotations

import re
from typing import Any

from .compatibility import analyze


def _value(section, key):
    item = section.get(key)
    return item.get("value") if item else None


def _observed_runtime(fingerprint: dict, runtime: str):
    source_type = fingerprint.get("source", {}).get("type")
    if source_type != "local":
        return None
    return _value(fingerprint.get("runtimes", {}), runtime)


def _declared_runtime(fingerprint: dict, runtime: str):
    value = _value(fingerprint.get("runtime_declarations", {}), runtime)
    if value is not None:
        return value

    source_type = fingerprint.get("source", {}).get("type")
    if (
        fingerprint.get("schema_version") == "1.0"
        and source_type in {"repository", "ci"}
    ):
        return _value(fingerprint.get("runtimes", {}), runtime)
    return None


def _major(value):
    if value is None:
        return None
    m = re.search(r"(?:^|\D)(\d+)(?:\.|$)", str(value))
    return int(m.group(1)) if m else None


def compare(dev: dict, ci: dict) -> dict[str, Any]:
    features: dict[str, Any] = {
        "dependency_environment_conflict": None,
        "required_env_missing": None,
        "resource_constraint_detected": None,
        "os_match": None,
        "architecture_match": None,
        "libc_match": None,
    }

    for key in ("os", "architecture", "libc"):
        a, b = _value(dev.get("platform", {}), key), _value(ci.get("platform", {}), key)
        if a is not None or b is not None:
            features[f"{key}_match"] = (
                int(str(a).lower() == str(b).lower())
                if a is not None and b is not None
                else None
            )

    for runtime in ("node", "python", "java", "ruby"):
        a, b = _observed_runtime(dev, runtime), _observed_runtime(ci, runtime)
        if a is not None or b is not None:
            features[f"{runtime}_version_match"] = (
                int(str(a) == str(b))
                if a is not None and b is not None
                else None
            )
            if a is not None and b is not None:
                ma, mb = _major(a), _major(b)
                if ma is not None and mb is not None:
                    features[f"{runtime}_major_difference"] = abs(ma - mb)

        declared_dev = _declared_runtime(dev, runtime)
        declared_ci = _declared_runtime(ci, runtime)
        if declared_dev is not None or declared_ci is not None:
            features[f"{runtime}_declaration_version_match"] = (
                int(str(declared_dev) == str(declared_ci))
                if declared_dev is not None and declared_ci is not None
                else None
            )
            if declared_dev is not None and declared_ci is not None:
                dev_major, ci_major = _major(declared_dev), _major(declared_ci)
                if dev_major is not None and ci_major is not None:
                    features[f"{runtime}_declaration_major_difference"] = abs(
                        dev_major - ci_major
                    )

    for tool in ("npm", "pip", "maven", "gradle"):
        a, b = _value(dev.get("package_managers", {}), tool) or _value(dev.get("build_tools", {}), tool), _value(ci.get("package_managers", {}), tool) or _value(ci.get("build_tools", {}), tool)
        if a is not None or b is not None:
            features[f"{tool}_match"] = (
                int(str(a) == str(b))
                if a is not None and b is not None
                else None
            )

    dev_req = dev.get("requirements", {})
    ci_runtime = {}
    for runtime in ("node", "python", "java"):
        value = _observed_runtime(ci, runtime)
        if value is None:
            value = _declared_runtime(ci, runtime)
        if value is not None:
            ci_runtime[runtime] = {"value": value}
    for runtime in ("node", "python", "java"):
        req = _value(dev_req, runtime)
        actual = _value(ci_runtime, runtime)
        if req:
            features[f"{runtime}_requirement_violation"] = None
            if actual:
                features[f"{runtime}_requirement_declared"] = 1
            # Conservative V1: only evaluate simple >=N / exact-N constraints.
            if actual:
                m = re.search(r">=\s*(\d+)(?:\.(\d+))?", str(req))
                if m:
                    required_major = int(m.group(1))
                    actual_major = _major(actual)
                    if actual_major is not None:
                        features[f"{runtime}_requirement_violation"] = int(actual_major < required_major)

    dev_dep = _value(dev.get("dependencies", {}), "dependency_count")
    ci_dep = _value(ci.get("dependencies", {}), "dependency_count")
    if dev_dep is not None:
        features["dependency_count_dev"] = dev_dep
    if ci_dep is not None:
        features["dependency_count_ci"] = ci_dep

    comparable_values = [
        value
        for key, value in features.items()
        if key.endswith("_match") or key.endswith("_violation")
    ] + [
        features["dependency_environment_conflict"],
        features["required_env_missing"],
        features["resource_constraint_detected"],
    ]
    known_values = [value for value in comparable_values if value in (0, 1)]
    features["environment_comparison_count"] = len(known_values)
    features["environment_difference_count"] = sum(
        1
        for key, value in features.items()
        if (
            key.endswith("_match") and value == 0
        )
        or (
            key.endswith("_violation") and value == 1
        )
        or (
            key in {
                "dependency_environment_conflict",
                "required_env_missing",
                "resource_constraint_detected",
            }
            and value == 1
        )
    )
    return features


def analyze_compatibility(dev: dict, ci: dict) -> dict[str, Any]:
    features = compare(dev, ci)
    statuses = {
        "runtime": _runtime_status(features),
        "dependencies": _status_for_feature(
            features.get("dependency_environment_conflict"), 1
        ),
        "os": _status_for_keys(
            features,
            [f"{dimension}_match" for dimension in ("os", "architecture", "libc")],
            0,
        ),
        "configuration": _status_for_feature(
            features.get("required_env_missing"), 1
        ),
        "resources": _status_for_feature(
            features.get("resource_constraint_detected"), 1
        ),
    }
    return {
        "features": features,
        "statuses": statuses,
        "compatibility": analyze(features),
    }


def _status_for_feature(value: Any, mismatch_value: int) -> str:
    if value not in (0, 1):
        return "unknown"
    return "mismatch" if value == mismatch_value else "compatible"


def _status_for_keys(
    features: dict[str, Any],
    keys: list[str],
    mismatch_value: int,
) -> str:
    applicable_keys = [key for key in keys if key in features]
    if not applicable_keys:
        return "unknown"
    return _combined_status(
        [
            _status_for_feature(features[key], mismatch_value)
            for key in applicable_keys
        ]
    )


def _runtime_status(features: dict[str, Any]) -> str:
    check_mismatch_values = {
        f"{runtime}_version_match": 0
        for runtime in ("node", "python", "java", "ruby")
    }
    check_mismatch_values.update(
        {
            f"{runtime}_declaration_version_match": 0
            for runtime in ("node", "python", "java", "ruby")
        }
    )
    check_mismatch_values.update(
        {
            f"{runtime}_requirement_violation": 1
            for runtime in ("node", "python", "java")
        }
    )
    applicable = [
        _status_for_feature(features[key], mismatch_value)
        for key, mismatch_value in check_mismatch_values.items()
        if key in features
    ]
    return _combined_status(applicable)


def _combined_status(statuses: list[str]) -> str:
    if "mismatch" in statuses:
        return "mismatch"
    if not statuses or "unknown" in statuses:
        return "unknown"
    return "compatible"
