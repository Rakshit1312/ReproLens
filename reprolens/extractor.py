from __future__ import annotations

import json
import os
import platform
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

from .models import Evidence, Field, Fingerprint


def _field(value: Any, source: str, confidence: str = "high") -> Field:
    return Field(value=value, evidence=[Evidence(source, confidence)])


def _put(section: dict, key: str, value: Any, source: str, confidence: str = "high"):
    if value is None:
        return
    if key not in section:
        section[key] = _field(value, source, confidence)
    else:
        section[key].evidence.append(Evidence(source, confidence))
        if section[key].value != value:
            section[key].evidence.append(Evidence("CONFLICT", "low"))


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _first_existing(root: Path, names: list[str]) -> Path | None:
    for name in names:
        p = root / name
        if p.is_file():
            return p
    return None


def _extract_version_file(root: Path, names: list[str], runtime: str, fp: Fingerprint):
    p = _first_existing(root, names)
    if not p:
        return
    text = _read_text(p)
    if text is None:
        return
    value = text.strip().splitlines()[0].strip()
    if value:
        _put(fp.runtimes, runtime, value, str(p.relative_to(root)), "high")


def _extract_package_json(root: Path, fp: Fingerprint):
    p = root / "package.json"
    if not p.is_file():
        return
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    source = "package.json"
    engines = data.get("engines", {}) or {}
    if isinstance(engines, dict):
        if engines.get("node"):
            _put(fp.requirements, "node", engines["node"], source + ":engines.node", "high")
        if engines.get("npm"):
            _put(fp.requirements, "npm", engines["npm"], source + ":engines.npm", "high")
    dev = data.get("devEngines", {}) or {}
    if isinstance(dev, dict):
        runtime = dev.get("runtime")
        if isinstance(runtime, dict):
            if runtime.get("name"):
                _put(fp.runtimes, runtime["name"], runtime.get("version") or "declared", source + ":devEngines.runtime", "high")
        pm = dev.get("packageManager")
        if isinstance(pm, dict) and pm.get("name"):
            _put(fp.package_managers, pm["name"], pm.get("version") or "declared", source + ":devEngines.packageManager", "high")
        for key in ("os", "cpu", "libc"):
            value = dev.get(key)
            if value:
                _put(fp.requirements, key, value, source + f":devEngines.{key}", "high")
    if data.get("os"):
        _put(fp.requirements, "os", data["os"], source + ":os", "high")
    if data.get("cpu"):
        _put(fp.requirements, "cpu", data["cpu"], source + ":cpu", "high")
    if data.get("libc"):
        _put(fp.requirements, "libc", data["libc"], source + ":libc", "high")
    deps = data.get("dependencies", {}) or {}
    devdeps = data.get("devDependencies", {}) or {}
    _put(fp.dependencies, "dependency_count", len(deps) + len(devdeps), source, "high")
    _put(fp.dependencies, "lockfile_present", any((root / n).is_file() for n in ("package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml")), source, "high")
    if data.get("packageManager"):
        _put(fp.package_managers, "declared", data["packageManager"], source + ":packageManager", "high")


def _extract_pyproject(root: Path, fp: Fingerprint):
    p = root / "pyproject.toml"
    if not p.is_file():
        return
    try:
        import tomllib
        data = tomllib.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return
    project = data.get("project", {}) or {}
    if project.get("requires-python"):
        _put(fp.requirements, "python", project["requires-python"], "pyproject.toml:project.requires-python", "high")
    deps = project.get("dependencies", []) or []
    optional = project.get("optional-dependencies", {}) or {}
    optional_count = sum(len(v) for v in optional.values() if isinstance(v, list))
    _put(fp.dependencies, "dependency_count", len(deps) + optional_count, "pyproject.toml:project.dependencies", "high")
    _put(fp.dependencies, "lockfile_present", any((root / n).is_file() for n in ("poetry.lock", "uv.lock", "pylock.toml")), "pyproject.toml", "high")


def _extract_java(root: Path, fp: Fingerprint):
    p = root / "pom.xml"
    if p.is_file():
        text = _read_text(p) or ""
        m = re.search(r"<maven.compiler(?:\.release|\.source|\.target)>\s*([^<]+)\s*</", text)
        if m:
            _put(fp.requirements, "java", m.group(1).strip(), "pom.xml:compiler", "medium")
        _put(fp.build_tools, "maven", "declared", "pom.xml", "high")
    for name in ("build.gradle", "build.gradle.kts"):
        p = root / name
        if p.is_file():
            text = _read_text(p) or ""
            m = re.search(r"(?:sourceCompatibility|JavaLanguageVersion\.of)\s*[=:]\s*['\"]?(\d+)", text)
            if m:
                _put(fp.requirements, "java", m.group(1), f"{name}:java", "medium")
            _put(fp.build_tools, "gradle", "declared", name, "high")
            break
    if (root / "gradlew").is_file() or (root / "gradlew.bat").is_file():
        _put(fp.build_tools, "gradle_wrapper", "present", "gradle wrapper", "high")


def _extract_devcontainer(root: Path, fp: Fingerprint):
    candidates = [root / ".devcontainer" / "devcontainer.json", root / ".devcontainer.json"]
    p = next((x for x in candidates if x.is_file()), None)
    if not p:
        return
    text = _read_text(p) or ""
    # JSONC: remove simple // comments and trailing commas for V1.
    cleaned = re.sub(r"//.*", "", text)
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return
    image = data.get("image")
    if image:
        _put(fp.platform, "devcontainer_image", image, str(p.relative_to(root)), "high")
    dockerfile = data.get("dockerFile")
    if dockerfile:
        _put(fp.platform, "devcontainer_dockerfile", dockerfile, str(p.relative_to(root)), "high")
    for key in ("containerEnv", "remoteEnv"):
        env = data.get(key)
        if isinstance(env, dict):
            for name in env:
                _put(fp.configuration, f"env:{name}", "present", str(p.relative_to(root)) + f":{key}", "high")


def _extract_dockerfile(root: Path, fp: Fingerprint):
    p = root / "Dockerfile"
    if not p.is_file():
        return
    text = _read_text(p) or ""
    m = re.search(r"^\s*FROM\s+([^\s]+)", text, flags=re.I | re.M)
    if m:
        _put(fp.platform, "docker_base_image", m.group(1), "Dockerfile:FROM", "high")


def _extract_workflows(root: Path, fp: Fingerprint):
    wf = root / ".github" / "workflows"
    if not wf.is_dir():
        return
    for p in sorted(list(wf.glob("*.yml")) + list(wf.glob("*.yaml"))):
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        jobs = data.get("jobs", {}) or {}
        if not isinstance(jobs, dict):
            continue
        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                continue
            runner = job.get("runs-on")
            if runner:
                _put(fp.platform, "ci_runner", runner, f"{p.relative_to(root)}:jobs.{job_name}.runs-on", "high")
            env = job.get("env", {}) or {}
            if isinstance(env, dict):
                for name in env:
                    _put(fp.configuration, f"ci_env:{name}", "present", f"{p.relative_to(root)}:jobs.{job_name}.env", "high")
            for step in job.get("steps", []) or []:
                if not isinstance(step, dict):
                    continue
                uses = str(step.get("uses", ""))
                with_args = step.get("with", {}) or {}
                if "actions/setup-node" in uses and isinstance(with_args, dict) and with_args.get("node-version"):
                    _put(fp.runtimes, "node", str(with_args["node-version"]), f"{p.relative_to(root)}:setup-node", "high")
                if "actions/setup-python" in uses and isinstance(with_args, dict) and with_args.get("python-version"):
                    _put(fp.runtimes, "python", str(with_args["python-version"]), f"{p.relative_to(root)}:setup-python", "high")
                if "actions/setup-java" in uses and isinstance(with_args, dict) and with_args.get("java-version"):
                    _put(fp.runtimes, "java", str(with_args["java-version"]), f"{p.relative_to(root)}:setup-java", "high")
                step_env = step.get("env", {}) or {}
                if isinstance(step_env, dict):
                    for name in step_env:
                        _put(fp.configuration, f"ci_env:{name}", "present", f"{p.relative_to(root)}:step.env", "high")
                shell = step.get("shell")
                if shell:
                    _put(fp.platform, "ci_shell", shell, f"{p.relative_to(root)}:step.shell", "high")


def fingerprint_repository(root: str | Path) -> Fingerprint:
    """Extract development-side declarations only."""
    root = Path(root).resolve()
    fp = Fingerprint(source_type="repository")
    _extract_version_file(root, [".nvmrc", ".node-version"], "node", fp)
    _extract_version_file(root, [".python-version"], "python", fp)
    _extract_version_file(root, [".ruby-version"], "ruby", fp)
    _extract_package_json(root, fp)
    _extract_pyproject(root, fp)
    _extract_java(root, fp)
    _extract_devcontainer(root, fp)
    _extract_dockerfile(root, fp)
    return fp


def fingerprint_ci(root: str | Path) -> Fingerprint:
    """Extract CI-side declarations from GitHub Actions workflows."""
    root = Path(root).resolve()
    fp = Fingerprint(source_type="ci")
    _extract_workflows(root, fp)
    return fp


def _run(command: list[str]) -> str | None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def fingerprint_local() -> Fingerprint:
    fp = Fingerprint(source_type="local")
    _put(fp.platform, "os", platform.system(), "local:platform.system", "high")
    _put(fp.platform, "os_version", platform.version(), "local:platform.version", "high")
    _put(fp.platform, "architecture", platform.machine(), "local:platform.machine", "high")
    _put(fp.resources, "cpu_cores", os.cpu_count(), "local:os.cpu_count", "high")
    for runtime, cmd in {
        "node": ["node", "--version"],
        "python": ["python", "--version"],
        "java": ["java", "-version"],
        "npm": ["npm", "--version"],
        "pip": ["python", "-m", "pip", "--version"],
        "maven": ["mvn", "--version"],
        "gradle": ["gradle", "--version"],
    }.items():
        value = _run(cmd)
        if value:
            first = value.splitlines()[0]
            _put(fp.runtimes if runtime in {"node", "python", "java"} else fp.package_managers if runtime in {"npm", "pip"} else fp.build_tools, runtime, first, "local:" + " ".join(cmd), "high")
    return fp
