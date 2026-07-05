#!/usr/bin/env python3
"""Repository quality checks for the Lightning IT release model."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path.cwd()
GENERATED = [ROOT / "README.md", ROOT / "RELEASE.md", ROOT / "TESTING.md"]
BEGIN = "<!-- BEGIN LIT_SHARED_RELEASE_MODEL -->"
END = "<!-- END LIT_SHARED_RELEASE_MODEL -->"


def metadata() -> dict[str, str]:
    path = ROOT / ".lit" / "repository.yml"
    if not path.exists():
        raise AssertionError(".lit/repository.yml is missing")
    data: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line or line.startswith((" ", "-")):
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip("'\"")
    return data


def run(command: list[str], *, required: bool = True) -> None:
    if not required and not shutil_which(command[0]):
        print(f"Skipping {' '.join(command)}: {command[0]} is not installed")
        return
    print("+ " + " ".join(command))
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        raise subprocess.CalledProcessError(result.returncode, command)


def shutil_which(command: str) -> str | None:
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / command
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def assert_file(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"{path.relative_to(ROOT)} is missing")
    return path.read_text(encoding="utf-8")


def managed_readme_block(readme: str) -> str:
    start = readme.find(BEGIN)
    end = readme.find(END)
    if start == -1 or end == -1 or end < start:
        raise AssertionError("README.md is missing the managed release-model block")
    return readme[start : end + len(END)]


def check_generated_docs(meta: dict[str, str]) -> None:
    readme = assert_file(ROOT / "README.md")
    release = assert_file(ROOT / "RELEASE.md")
    testing = assert_file(ROOT / "TESTING.md")
    assert_file(ROOT / ".lit" / "repository.yml")

    if BEGIN not in readme or END not in readme:
        raise AssertionError("README.md is missing the managed release-model block")
    if "[RELEASE.md](./RELEASE.md)" not in readme:
        raise AssertionError("README.md does not link to RELEASE.md")
    if meta.get("repository_type", "") not in release:
        raise AssertionError("RELEASE.md does not include the repository type")
    if "Release Evidence" not in release:
        raise AssertionError("RELEASE.md does not describe release evidence")
    if "Test Profiles" not in testing:
        raise AssertionError("TESTING.md does not describe test profiles")

    placeholder = re.compile(r"(TODO|TBD|PLACEHOLDER|FIXME)", re.IGNORECASE)
    generated_texts = [
        ("README.md managed block", managed_readme_block(readme)),
        ("RELEASE.md", release),
        ("TESTING.md", testing),
    ]
    for label, text in generated_texts:
        if placeholder.search(text):
            raise AssertionError(f"{label} contains unresolved placeholder text")

    if "License-MIT" in readme and not (ROOT / "LICENSE").exists():
        raise AssertionError("README.md has a license badge but no root LICENSE")


def check_secret_safe_generated_docs() -> None:
    secret_patterns = [
        re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
        re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
        re.compile(r"-----BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
        re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{16,}"),
    ]
    readme = assert_file(ROOT / "README.md")
    generated_texts = [
        ("README.md managed block", managed_readme_block(readme)),
        ("RELEASE.md", assert_file(ROOT / "RELEASE.md")),
        ("TESTING.md", assert_file(ROOT / "TESTING.md")),
        (".lit/repository.yml", assert_file(ROOT / ".lit" / "repository.yml")),
    ]
    for label, text in generated_texts:
        for pattern in secret_patterns:
            if pattern.search(text):
                raise AssertionError(f"{label} appears to contain secret-like material")


def check_terraform(repo_type: str) -> None:
    if repo_type not in {"terraform_module", "terraform_policy"}:
        return
    tf_files = sorted(ROOT.glob("*.tf"))
    if not tf_files:
        raise AssertionError("Terraform repository has no root *.tf files")
    if shutil_which("terraform"):
        run(["terraform", "fmt", "-check", "-recursive"])
        run(["terraform", "init", "-backend=false", "-input=false"])
        run(["terraform", "validate", "-no-color"])
    else:
        print("Terraform CLI not installed; checked Terraform file presence only")


def check_helm(repo_type: str) -> None:
    if repo_type != "helm_chart":
        return
    chart_files = sorted(ROOT.glob("**/Chart.yaml"))
    if not chart_files:
        print("No Chart.yaml files found; treating repository as chart placeholder")
        return
    if shutil_which("helm"):
        for chart in chart_files:
            run(["helm", "lint", str(chart.parent)])
            run(["helm", "template", "lit-quality", str(chart.parent)])
    else:
        print("Helm CLI not installed; checked Chart.yaml presence only")


def check_packer(repo_type: str) -> None:
    if repo_type != "packer_template":
        return
    pkr_files = sorted(ROOT.glob("*.pkr.hcl"))
    if not pkr_files:
        print("No root *.pkr.hcl files found; treating repository as template placeholder")
        return
    if shutil_which("packer"):
        run(["packer", "fmt", "-check", "."])
        run(["packer", "validate", "-syntax-only", "."])
    else:
        print("Packer CLI not installed; checked Packer file presence only")


def check_markdown() -> None:
    for path in GENERATED:
        text = assert_file(path)
        if "\t" in text:
            raise AssertionError(f"{path.name} contains tab characters")
        if not text.endswith("\n"):
            raise AssertionError(f"{path.name} must end with a newline")


def main() -> int:
    try:
        meta = metadata()
        check_generated_docs(meta)
        check_secret_safe_generated_docs()
        check_markdown()
        repo_type = meta.get("repository_type", "")
        check_terraform(repo_type)
        check_helm(repo_type)
        check_packer(repo_type)
    except subprocess.CalledProcessError as exc:
        return exc.returncode
    except AssertionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("Lightning IT repository quality checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
