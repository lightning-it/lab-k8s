"""Unit tests for fail-closed Kubernetes policy rules."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate-kubernetes-policy.py"
SPEC = importlib.util.spec_from_file_location("kubernetes_policy", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"unable to load Kubernetes policy module from {SCRIPT}")
POLICY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POLICY)


def secure_deployment() -> dict:
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "example"},
        "spec": {
            "template": {
                "spec": {
                    "automountServiceAccountToken": False,
                    "securityContext": {
                        "runAsNonRoot": True,
                        "seccompProfile": {"type": "RuntimeDefault"},
                    },
                    "containers": [
                        {
                            "name": "app",
                            "image": "example.invalid/app@sha256:" + ("0" * 64),
                            "securityContext": {
                                "runAsNonRoot": True,
                                "allowPrivilegeEscalation": False,
                                "readOnlyRootFilesystem": True,
                                "capabilities": {"drop": ["ALL"]},
                            },
                            "resources": {
                                "requests": {"cpu": "10m", "memory": "16Mi"},
                                "limits": {"cpu": "100m", "memory": "64Mi"},
                            },
                            "readinessProbe": {"exec": {"command": ["true"]}},
                            "livenessProbe": {"exec": {"command": ["true"]}},
                        }
                    ],
                }
            }
        },
    }


class KubernetesPolicyTests(unittest.TestCase):
    def test_secure_workload_passes(self) -> None:
        errors = POLICY.validate([("fixture", secure_deployment())])
        self.assertEqual(errors, [])

    def test_mutable_image_fails(self) -> None:
        resource = secure_deployment()
        resource["spec"]["template"]["spec"]["containers"][0]["image"] = "app:latest"
        errors = POLICY.validate([("fixture", resource)])
        self.assertTrue(any("immutable sha256 digest" in error for error in errors))

    def test_missing_hardening_and_resources_fail(self) -> None:
        resource = secure_deployment()
        container = resource["spec"]["template"]["spec"]["containers"][0]
        container.pop("securityContext")
        container.pop("resources")
        errors = POLICY.validate([("fixture", resource)])
        self.assertTrue(any("securityContext is required" in error for error in errors))
        self.assertTrue(any("resources are required" in error for error in errors))

    def test_rbac_wildcard_fails(self) -> None:
        role = {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "ClusterRole",
            "metadata": {"name": "unsafe"},
            "rules": [{"apiGroups": ["*"], "resources": ["pods"], "verbs": ["get"]}],
        }
        errors = POLICY.validate([("fixture", role)])
        self.assertTrue(any("wildcard apiGroups" in error for error in errors))

    def test_secret_payload_fails(self) -> None:
        secret = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {"name": "unsafe"},
            "stringData": {"token": "not-allowed"},
        }
        errors = POLICY.validate([("fixture", secret)])
        self.assertTrue(any("Secret payloads are forbidden" in error for error in errors))

    def test_secret_checks_data_and_string_data(self) -> None:
        secret = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {"name": "unsafe"},
            "data": {"placeholder": "pleaseoverwrite"},
            "stringData": {"token": "not-allowed"},
        }
        errors = POLICY.validate([("fixture", secret)])
        self.assertTrue(any("Secret payloads are forbidden" in error for error in errors))

    def test_mutable_argocd_revision_fails(self) -> None:
        application = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Application",
            "metadata": {"name": "unsafe"},
            "spec": {"source": {"targetRevision": "main"}},
        }
        errors = POLICY.validate([("fixture", application)])
        self.assertTrue(any("targetRevision" in error for error in errors))

    def test_malformed_nested_objects_fail_without_crashing(self) -> None:
        resource = secure_deployment()
        pod = resource["spec"]["template"]["spec"]
        pod["securityContext"]["seccompProfile"] = "invalid"
        pod["containers"][0]["securityContext"]["capabilities"] = ["invalid"]
        errors = POLICY.validate([("fixture", resource)])
        self.assertTrue(any("seccompProfile" in error for error in errors))
        self.assertTrue(any("capabilities" in error for error in errors))

        malformed_job = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {"name": "malformed"},
            "spec": {"template": "invalid"},
        }
        errors = POLICY.validate([("fixture", malformed_job)])
        self.assertTrue(any("pod spec is required" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
