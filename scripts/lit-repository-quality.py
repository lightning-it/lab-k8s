#!/usr/bin/env python3
"""Repository quality checks for the Lightning IT release model."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path.cwd()
GENERATED = [ROOT / "README.md", ROOT / "RELEASE.md", ROOT / "TESTING.md", ROOT / "OPENSSF.md"]
BEGIN = "<!-- BEGIN LIT_SHARED_RELEASE_MODEL -->"
END = "<!-- END LIT_SHARED_RELEASE_MODEL -->"
QUALITY_BEGIN = "<!-- BEGIN LIT_QUALITY_BADGES -->"
QUALITY_END = "<!-- END LIT_QUALITY_BADGES -->"
COMPAT_BEGIN = "<!-- BEGIN LIT_COMPATIBILITY_MATRIX -->"
COMPAT_END = "<!-- END LIT_COMPATIBILITY_MATRIX -->"
RELEASE_QUALITY_BEGIN = "<!-- BEGIN LIT_RELEASE_QUALITY_MODEL -->"
RELEASE_QUALITY_END = "<!-- END LIT_RELEASE_QUALITY_MODEL -->"
DISALLOWED_GENERATED_TERMS = [
    "Production Ready",
    "Enterprise Ready",
    "Battle Tested",
    "100% Tested",
    "github/stars",
    "github/forks",
    "container (none)",
    "(none)",
    "TODO",
    "PLACEHOLDER",
]
INVALID_BADGE_VALUE = re.compile(r"(container\s+\((?:none|null|undefined)\)|\((?:none|null|undefined)\))", re.I)
ENTERPRISE_README_TYPES = {
    "ansible_collection",
    "container_image",
    "playbook_runbook",
    "private_infrastructure",
    "terraform_module",
    "terraform_policy",
    "helm_chart",
    "documentation",
    "packer_template",
    "shared_assets",
    "repository_profile",
    "generic_managed",
}


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
    start = readme.find(RELEASE_QUALITY_BEGIN)
    end = readme.find(RELEASE_QUALITY_END)
    end_marker = RELEASE_QUALITY_END
    if start == -1 or end == -1 or end < start:
        start = readme.find(BEGIN)
        end = readme.find(END)
        end_marker = END
    if start == -1 or end == -1 or end < start:
        raise AssertionError("README.md is missing the managed release-model block")
    return readme[start : end + len(end_marker)]


def quality_badge_block(readme: str) -> str:
    start = readme.find(QUALITY_BEGIN)
    end = readme.find(QUALITY_END)
    if start == -1 or end == -1 or end < start:
        raise AssertionError("README.md is missing the managed quality badge block")
    return readme[start : end + len(QUALITY_END)]


def readme_looks_collapsed(readme: str) -> bool:
    lines = readme.splitlines()
    if len(lines) < 10:
        return True
    return any(len(line) > 1000 and ("[![" in line or "## " in line or "|---|" in line) for line in lines)


def readme_has_human_intro_before_matrix(readme: str) -> bool:
    quality_end = readme.find(QUALITY_END)
    compat_begin = readme.find(COMPAT_BEGIN)
    if quality_end == -1 or compat_begin == -1 or compat_begin < quality_end:
        return False
    between = readme[quality_end + len(QUALITY_END):compat_begin]
    between = re.sub(r"<!--.*?-->", "", between, flags=re.DOTALL)
    between = re.sub(r"## Release and Quality Model.*", "", between, flags=re.DOTALL)
    return len(between.strip()) >= 80


def readme_section_order_ok(readme: str) -> bool:
    first_heading = readme.find("\n## ")
    quality_begin = readme.find(QUALITY_BEGIN)
    quality_end = readme.find(QUALITY_END)
    release_begin = readme.find(RELEASE_QUALITY_BEGIN)
    compat_begin = readme.find(COMPAT_BEGIN)
    evidence = readme.find("## Release Evidence")
    if min(quality_begin, quality_end, release_begin, compat_begin, evidence) == -1:
        return False
    return quality_begin < quality_end and quality_begin < first_heading < release_begin < compat_begin < evidence


def readme_has_exact_heading(readme: str, heading: str) -> bool:
    return re.search(rf"^{re.escape(heading)}$", readme, re.MULTILINE) is not None


def check_container_badge_mapping(meta: dict[str, str], readme: str) -> None:
    if meta.get("repository_type") != "container_image":
        return
    quality_block = quality_badge_block(readme)
    if "container_build" in quality_block:
        raise AssertionError("README.md quality badge block leaked metadata key container_build")
    if INVALID_BADGE_VALUE.search(quality_block):
        raise AssertionError("README.md quality badge block contains invalid empty badge value")
    if "Container Build" in quality_block and "container-build-publish.yml/badge.svg" in quality_block:
        raise AssertionError("README.md uses release workflow as Container Build badge")
    if "Container Build" in quality_block and "container-build.yml/badge.svg" not in quality_block:
        raise AssertionError("README.md Container Build badge does not point to container-build.yml")


def check_generated_docs(meta: dict[str, str]) -> None:
    readme = assert_file(ROOT / "README.md")
    release = assert_file(ROOT / "RELEASE.md")
    testing = assert_file(ROOT / "TESTING.md")
    openssf = assert_file(ROOT / "OPENSSF.md")
    assert_file(ROOT / ".lit" / "repository.yml")

    if readme_looks_collapsed(readme):
        raise AssertionError("README.md markdown appears collapsed or structurally invalid")
    new_release_model = RELEASE_QUALITY_BEGIN in readme and RELEASE_QUALITY_END in readme
    old_release_model = BEGIN in readme and END in readme
    if not new_release_model and not old_release_model:
        raise AssertionError("README.md is missing the managed release-model block")
    if QUALITY_BEGIN not in readme or QUALITY_END not in readme:
        raise AssertionError("README.md is missing the managed quality badge block")
    if meta.get("repository_type") in ENTERPRISE_README_TYPES:
        if COMPAT_BEGIN not in readme or COMPAT_END not in readme:
            raise AssertionError("README.md is missing the managed compatibility matrix block")
        if not new_release_model:
            raise AssertionError("README.md is missing the managed release quality model block")
        if not readme_section_order_ok(readme):
            raise AssertionError("README.md managed sections are not in enterprise order")
        if not readme_has_human_intro_before_matrix(readme):
            raise AssertionError("README.md lacks human project content before compatibility matrix")
        if "## Release Evidence" not in readme:
            raise AssertionError("README.md is missing the Release Evidence section")
        for heading in ["## Security", "## Contributing"]:
            if not readme_has_exact_heading(readme, heading):
                raise AssertionError(f"README.md is missing the exact {heading} section")
        if (ROOT / "LICENSE").exists() and not readme_has_exact_heading(readme, "## License"):
            raise AssertionError("README.md is missing the exact ## License section")
    if "[RELEASE.md](./RELEASE.md)" not in readme:
        raise AssertionError("README.md does not link to RELEASE.md")
    if meta.get("repository_type") in ENTERPRISE_README_TYPES:
        if "## Compatibility Matrix" not in readme:
            raise AssertionError("README.md does not include the compatibility matrix")
    elif "## Supported and Tested Platforms" not in readme and "## Compatibility Matrix" not in readme:
        raise AssertionError("README.md does not include the supported/tested platforms matrix")
    for term in DISALLOWED_GENERATED_TERMS:
        if term in readme:
            raise AssertionError(f"README.md contains disallowed badge term {term}")
    if "quay.io/repository/" in readme and "/status" in readme:
        raise AssertionError("README.md uses Quay status badge that can render container none")
    if meta.get("repository_type") in {"container", "container_image", "container-image", "container-ee", "container_ee"}:
        if "Container Version" not in readme:
            raise AssertionError("README.md is missing the Container Version badge")
        for term in ["container | none", "container (none)", "(none)", "undefined"]:
            if term in readme:
                raise AssertionError(f"README.md contains invalid container badge placeholder {term}")
    check_container_badge_mapping(meta, readme)
    if meta.get("repository_type", "") not in release:
        raise AssertionError("RELEASE.md does not include the repository type")
    if "Release Evidence" not in release:
        raise AssertionError("RELEASE.md does not describe release evidence")
    if "Test Profiles" not in testing:
        raise AssertionError("TESTING.md does not describe test profiles")
    for term in ["OpenSSF Readiness", "Scorecard", "Best Practices Badge", "Security Policy"]:
        if term not in openssf:
            raise AssertionError(f"OPENSSF.md does not include {term}")

    placeholder = re.compile(r"(TODO|TBD|PLACEHOLDER|FIXME)", re.IGNORECASE)
    generated_texts = [
        ("README.md managed block", managed_readme_block(readme)),
        ("README.md quality badge block", quality_badge_block(readme)),
        ("RELEASE.md", release),
        ("TESTING.md", testing),
        ("OPENSSF.md", openssf),
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
        ("OPENSSF.md", assert_file(ROOT / "OPENSSF.md")),
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
