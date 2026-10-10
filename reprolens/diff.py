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
    features: dict[str, Any] = {}

    for key in ("os", "architecture", "libc"):
        a, b = _value(dev.get("platform", {}), key), _value(ci.get("platform", {}), key)
        if a is not None and b is not None:
            features[f"{key}_match"] = int(str(a).lower() == str(b).lower())

    for runtime in ("node", "python", "java", "ruby"):
        a, b = _observed_runtime(dev, runtime), _observed_runtime(ci, runtime)
        if a is not None and b is not None:
            features[f"{runtime}_version_match"] = int(str(a) == str(b))
            ma, mb = _major(a), _major(b)
            if ma is not None and mb is not None:
                features[f"{runtime}_major_difference"] = abs(ma - mb)

        declared_dev = _declared_runtime(dev, runtime)
        declared_ci = _declared_runtime(ci, runtime)
        if declared_dev is not None and declared_ci is not None:
            features[f"{runtime}_declaration_version_match"] = int(
                str(declared_dev) == str(declared_ci)
            )
            dev_major, ci_major = _major(declared_dev), _major(declared_ci)
            if dev_major is not None and ci_major is not None:
                features[f"{runtime}_declaration_major_difference"] = abs(
                    dev_major - ci_major
                )

    for tool in ("npm", "pip", "maven", "gradle"):
        a, b = _value(dev.get("package_managers", {}), tool) or _value(dev.get("build_tools", {}), tool), _value(ci.get("package_managers", {}), tool) or _value(ci.get("build_tools", {}), tool)
        if a is not None and b is not None:
            features[f"{tool}_match"] = int(str(a) == str(b))

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
        if req and actual:
            features[f"{runtime}_requirement_declared"] = 1
            # Conservative V1: only evaluate simple >=N / exact-N constraints.
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

    features["environment_difference_count"] = sum(1 for k, v in features.items() if k.endswith("_match") and v == 0) + sum(1 for k, v in features.items() if k.endswith("_violation") and v == 1)
    return features


def analyze_compatibility(dev: dict, ci: dict) -> dict[str, Any]:
    features = compare(dev, ci)
    return {"features": features, "compatibility": analyze(features)}
