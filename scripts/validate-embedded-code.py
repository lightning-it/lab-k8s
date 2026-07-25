#!/usr/bin/env python3
"""Validate fenced YAML, shell, and Ansible examples in changed Markdown."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:  # Local quality runs remain useful without optional CI deps.
    yaml = None

SCRIPT = Path(__file__).resolve()
ROOT = (
    SCRIPT.parents[2]
    if SCRIPT.parent.parent.name == "default"
    else SCRIPT.parents[1]
)
FENCE = re.compile(
    r"^[ \t]*`{3,}[ \t]*(yaml|yml|bash|sh|shell|ansible)\b[^\r\n]*\r?\n"
    r"(.*?)^[ \t]*`{3,}[ \t]*$",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)
VALIDATOR_TIMEOUT_SECONDS = 60


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as temporary:
        temp = Path(temporary)
        for name in args.paths:
            relative_path = Path(name)
            if (
                not name
                or relative_path.is_absolute()
                or ".." in relative_path.parts
                or relative_path.as_posix() != name
            ):
                failures.append(
                    f"{name}: Markdown path must be normalized and repository-relative"
                )
                continue
            path = ROOT / relative_path
            if not path.is_file() or path.suffix != ".md":
                continue
            try:
                source = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as error:
                failures.append(f"{name}: cannot read Markdown as UTF-8: {error}")
                continue
            for index, match in enumerate(FENCE.finditer(source), 1):
                language, content = match.groups()
                language = language.lower()
                label = f"{name}:fence-{index}"
                if language in {"yaml", "yml", "ansible"}:
                    if yaml is None:
                        print(f"PyYAML unavailable; skipped YAML parse for {label}")
                    else:
                        try:
                            yaml.safe_load(content)
                        except yaml.YAMLError as error:
                            failures.append(f"{label}: invalid YAML: {error}")
                    if language == "ansible" and shutil.which("ansible-lint"):
                        candidate = temp / f"ansible-{index}.yml"
                        candidate.write_text(content, encoding="utf-8")
                        try:
                            result = subprocess.run(
                                ["ansible-lint", str(candidate)],
                                text=True,
                                capture_output=True,
                                timeout=VALIDATOR_TIMEOUT_SECONDS,
                            )
                        except subprocess.TimeoutExpired:
                            failures.append(
                                f"{label}: ansible-lint timed out after "
                                f"{VALIDATOR_TIMEOUT_SECONDS} seconds"
                            )
                            continue
                        if result.returncode:
                            details = "\n".join(
                                output.strip()
                                for output in (result.stdout, result.stderr)
                                if output.strip()
                            )
                            failures.append(
                                f"{label}: ansible-lint failed\n{details}".rstrip()
                            )
                elif shutil.which("shellcheck"):
                    candidate = temp / f"shell-{index}.sh"
                    interpreter = "bash" if language == "bash" else "sh"
                    candidate.write_text(
                        f"#!/usr/bin/env {interpreter}\n" + content,
                        encoding="utf-8",
                    )
                    try:
                        result = subprocess.run(
                            ["shellcheck", "-x", str(candidate)],
                            text=True,
                            capture_output=True,
                            timeout=VALIDATOR_TIMEOUT_SECONDS,
                        )
                    except subprocess.TimeoutExpired:
                        failures.append(
                            f"{label}: ShellCheck timed out after "
                            f"{VALIDATOR_TIMEOUT_SECONDS} seconds"
                        )
                        continue
                    if result.returncode:
                        details = "\n".join(
                            output.strip()
                            for output in (result.stdout, result.stderr)
                            if output.strip()
                        )
                        failures.append(
                            f"{label}: ShellCheck failed\n{details}".rstrip()
                        )
    for failure in failures:
        print(f"ERROR: {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
