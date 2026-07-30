#!/usr/bin/env python3
"""Fail-closed policy checks for rendered Kubernetes and GitOps manifests."""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import yaml


ROOT = Path(__file__).resolve().parents[1]
WAIVERS = ROOT / ".lit" / "kubernetes-policy-waivers.yml"
DIGEST_IMAGE = re.compile(r"^[^@\s]+@sha256:[0-9a-f]{64}$")
SHA_REVISION = re.compile(r"^[0-9a-f]{40}$")
WORKLOAD_KINDS = {
    "CronJob",
    "DaemonSet",
    "Deployment",
    "Job",
    "ReplicaSet",
    "StatefulSet",
}


class PolicyError(Exception):
    """A deterministic policy violation."""


def documents(text: str, source: str) -> list[tuple[str, dict[str, Any]]]:
    parsed: list[tuple[str, dict[str, Any]]] = []
    for index, document in enumerate(yaml.safe_load_all(text), start=1):
        if document is None:
            continue
        if not isinstance(document, dict):
            raise PolicyError(f"{source}#{index}: YAML document must be an object")
        parsed.append((f"{source}#{index}", document))
    return parsed


def read_documents(path: Path) -> list[tuple[str, dict[str, Any]]]:
    return documents(path.read_text(encoding="utf-8"), path.relative_to(ROOT).as_posix())


def build_kustomization(path: Path) -> list[tuple[str, dict[str, Any]]]:
    command = ["kubectl", "kustomize", str(path)]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise PolicyError(f"{path.relative_to(ROOT)}: kustomize build failed: {detail}")
    return documents(
        completed.stdout,
        f"kustomize:{path.relative_to(ROOT).as_posix()}",
    )


def render_helm_chart(path: Path) -> list[tuple[str, dict[str, Any]]]:
    command = ["helm", "template", path.name, str(path)]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise PolicyError(f"{path.relative_to(ROOT)}: helm template failed: {detail}")
    return documents(
        completed.stdout,
        f"helm:{path.relative_to(ROOT).as_posix()}",
    )


def pod_spec(resource: dict[str, Any]) -> dict[str, Any] | None:
    kind = resource.get("kind")
    spec = resource.get("spec")
    if not isinstance(spec, dict) or kind not in WORKLOAD_KINDS:
        return None
    if kind == "CronJob":
        spec = spec.get("jobTemplate", {}).get("spec", {})
    if kind in {"CronJob", "Job"}:
        return spec.get("template", {}).get("spec")
    return spec.get("template", {}).get("spec")


def validate_metadata(source: str, resource: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("apiVersion", "kind"):
        if not isinstance(resource.get(key), str) or not resource[key].strip():
            errors.append(f"{source}: {key} is required")
    metadata = resource.get("metadata")
    if not isinstance(metadata, dict) or not metadata.get("name"):
        errors.append(f"{source}: metadata.name is required")
    return errors


def validate_container(source: str, container: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    name = str(container.get("name", "<unnamed>"))
    location = f"{source}: container {name}"
    image = container.get("image")
    if not isinstance(image, str) or not DIGEST_IMAGE.fullmatch(image):
        errors.append(f"{location}: image must use an immutable sha256 digest")

    security = container.get("securityContext")
    if not isinstance(security, dict):
        errors.append(f"{location}: securityContext is required")
    else:
        expected = {
            "runAsNonRoot": True,
            "allowPrivilegeEscalation": False,
            "readOnlyRootFilesystem": True,
        }
        for key, value in expected.items():
            if security.get(key) is not value:
                errors.append(f"{location}: securityContext.{key} must be {value}")
        drop = security.get("capabilities", {}).get("drop", [])
        if "ALL" not in drop:
            errors.append(f"{location}: all Linux capabilities must be dropped")

    resources = container.get("resources")
    if not isinstance(resources, dict):
        errors.append(f"{location}: resources are required")
    else:
        for group in ("requests", "limits"):
            values = resources.get(group)
            if not isinstance(values, dict):
                errors.append(f"{location}: resources.{group} is required")
                continue
            for field in ("cpu", "memory"):
                if not values.get(field):
                    errors.append(
                        f"{location}: resources.{group}.{field} is required"
                    )
    return errors


def validate_workload(source: str, resource: dict[str, Any]) -> list[str]:
    spec = pod_spec(resource)
    if spec is None:
        return []
    errors: list[str] = []
    if not isinstance(spec, dict):
        return [f"{source}: pod spec is required"]
    if (
        spec.get("automountServiceAccountToken") is not False
        and not spec.get("serviceAccountName")
    ):
        errors.append(
            f"{source}: disable service-account token mounting or name a "
            "dedicated service account"
        )
    pod_security = spec.get("securityContext")
    if not isinstance(pod_security, dict):
        errors.append(f"{source}: pod securityContext is required")
    else:
        if pod_security.get("runAsNonRoot") is not True:
            errors.append(f"{source}: pod securityContext.runAsNonRoot must be true")
        if pod_security.get("seccompProfile", {}).get("type") != "RuntimeDefault":
            errors.append(f"{source}: pod seccompProfile.type must be RuntimeDefault")

    containers: list[dict[str, Any]] = []
    for field in ("initContainers", "containers"):
        value = spec.get(field, [])
        if not isinstance(value, list):
            errors.append(f"{source}: {field} must be an array")
            continue
        containers.extend(item for item in value if isinstance(item, dict))
    if not containers:
        errors.append(f"{source}: at least one container is required")
    for container in containers:
        errors.extend(validate_container(source, container))

    if resource.get("kind") not in {"Job", "CronJob"}:
        for container in spec.get("containers", []):
            if not isinstance(container, dict):
                continue
            name = container.get("name", "<unnamed>")
            for probe in ("readinessProbe", "livenessProbe"):
                if not isinstance(container.get(probe), dict):
                    errors.append(f"{source}: container {name}: {probe} is required")
    return errors


def validate_rbac(source: str, resource: dict[str, Any]) -> list[str]:
    if resource.get("kind") not in {"Role", "ClusterRole"}:
        return []
    errors: list[str] = []
    for index, rule in enumerate(resource.get("rules", []), start=1):
        if not isinstance(rule, dict):
            errors.append(f"{source}: RBAC rule {index} must be an object")
            continue
        for field in ("apiGroups", "resources", "verbs"):
            if "*" in rule.get(field, []):
                errors.append(f"{source}: RBAC rule {index} uses wildcard {field}")
    return errors


def validate_secret(source: str, resource: dict[str, Any]) -> list[str]:
    if resource.get("kind") != "Secret":
        return []
    payload = resource.get("data") or resource.get("stringData")
    if not payload:
        return []

    def values(value: object) -> list[str]:
        if isinstance(value, dict):
            return [item for child in value.values() for item in values(child)]
        if isinstance(value, list):
            return [item for child in value for item in values(child)]
        return [str(value)]

    payload_values = values(payload)
    if payload_values and all(
        not value.strip() or "pleaseoverwrite" in value.lower()
        for value in payload_values
    ):
        return []
    if payload:
        return [
            f"{source}: committed Secret payloads are forbidden unless every "
            "value is an explicit non-deployable placeholder"
        ]
    return []


def validate_argocd(source: str, resource: dict[str, Any]) -> list[str]:
    if resource.get("kind") != "Application":
        return []
    revision = resource.get("spec", {}).get("source", {}).get("targetRevision")
    if (
        revision != "<YOUR_TARGET_REVISION>"
        and not (isinstance(revision, str) and SHA_REVISION.fullmatch(revision))
    ):
        return [
            f"{source}: Argo CD targetRevision must be an exact Git SHA or "
            "the non-deployable sanitized placeholder"
        ]
    return []


def validate(items: Iterable[tuple[str, dict[str, Any]]]) -> list[str]:
    errors: list[str] = []
    for source, resource in items:
        errors.extend(validate_metadata(source, resource))
        errors.extend(validate_workload(source, resource))
        errors.extend(validate_rbac(source, resource))
        errors.extend(validate_secret(source, resource))
        errors.extend(validate_argocd(source, resource))
    return sorted(set(errors))


def apply_waivers(errors: list[str]) -> tuple[list[str], int]:
    data = yaml.safe_load(WAIVERS.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise PolicyError(f"{WAIVERS.relative_to(ROOT)}: version must be 1")
    entries = data.get("waivers")
    if not isinstance(entries, list):
        raise PolicyError(f"{WAIVERS.relative_to(ROOT)}: waivers must be an array")

    active: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise PolicyError(f"waiver {index}: must be an object")
        for field in ("finding", "owner", "reason", "compensating_control", "expires"):
            if not entry.get(field):
                raise PolicyError(f"waiver {index}: {field} is required")
        finding = entry["finding"]
        if not isinstance(finding, str):
            raise PolicyError(f"waiver {index}: finding must be a string")
        expiry = entry["expires"]
        if isinstance(expiry, str):
            try:
                expiry = date.fromisoformat(expiry)
            except ValueError as exc:
                raise PolicyError(f"waiver {index}: invalid expiry") from exc
        if not isinstance(expiry, date) or expiry < date.today():
            raise PolicyError(f"waiver {index}: expired on {entry['expires']}")
        if finding in active:
            raise PolicyError(f"waiver {index}: duplicate finding")
        active.add(finding)

    error_set = set(errors)
    stale = sorted(active - error_set)
    if stale:
        raise PolicyError(
            "stale Kubernetes policy waiver(s): " + ", ".join(stale)
        )
    return sorted(error_set - active), len(active)


def all_resources() -> list[tuple[str, dict[str, Any]]]:
    resources: list[tuple[str, dict[str, Any]]] = []
    chart_paths = sorted(
        path.parent
        for path in (ROOT / "helm-charts" / "charts").glob("*/Chart.yaml")
    )
    if not chart_paths:
        raise PolicyError("no embedded Helm product charts found")
    for path in chart_paths:
        resources.extend(render_helm_chart(path))

    kustomizations = sorted(
        path.parent
        for path in (ROOT / "gitops").rglob("kustomization.yaml")
        if "overlays" in path.parts
    )
    if not kustomizations:
        raise PolicyError("no GitOps overlays found")
    for path in kustomizations:
        resources.extend(build_kustomization(path))

    direct_patterns = (
        "gitops/argocd/**/*.yaml",
        "gitops/argocd/**/*.yml",
        "pocs/okms-smoke/*.yaml",
        "pocs/okms-smoke/*.yml",
    )
    direct_paths = sorted(
        {
            path
            for pattern in direct_patterns
            for path in ROOT.glob(pattern)
            if path.is_file()
        }
    )
    for path in direct_paths:
        resources.extend(read_documents(path))
    return resources


def main() -> int:
    try:
        resources = all_resources()
        errors, waiver_count = apply_waivers(validate(resources))
    except (OSError, PolicyError, subprocess.SubprocessError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if errors:
        print("Kubernetes policy violations:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        f"Validated {len(resources)} rendered Kubernetes/GitOps resources "
        f"with {waiver_count} active, unexpired waiver(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
