#!/usr/bin/env python3
"""Generate deterministic structural JSON schemas for embedded product charts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
CHARTS_ROOT = ROOT / "helm-charts" / "charts"


def schema_for(value: object) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if isinstance(value, str):
        return {"type": "string"}
    if isinstance(value, list):
        item_schemas = [schema_for(item) for item in value]
        unique = {
            json.dumps(item, sort_keys=True, separators=(",", ":")): item
            for item in item_schemas
        }
        if not unique:
            items: dict[str, Any] = {}
        elif len(unique) == 1:
            items = next(iter(unique.values()))
        else:
            items = {"anyOf": list(unique.values())}
        return {"type": "array", "items": items}
    if isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise ValueError(
                    "values keys must be strings; "
                    f"got {key!r} ({type(key).__name__})"
                )
        return {
            "type": "object",
            "properties": {
                key: schema_for(child)
                for key, child in sorted(value.items())
            },
            "additionalProperties": True,
        }
    raise ValueError(f"unsupported YAML value type: {type(value).__name__}")


def generated_schema(values_path: Path) -> str:
    values = yaml.safe_load(values_path.read_text(encoding="utf-8"))
    if values is None:
        values = {}
    if not isinstance(values, dict):
        raise ValueError(f"{values_path}: root values document must be an object")
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"{values_path.parent.name} values",
        **schema_for(values),
    }
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()

    stale: list[str] = []
    charts = sorted(path.parent for path in CHARTS_ROOT.glob("*/Chart.yaml"))
    if not charts:
        raise ValueError(f"no product charts found under {CHARTS_ROOT.relative_to(ROOT)}")

    for chart in charts:
        values_path = chart / "values.yaml"
        if not values_path.is_file():
            raise ValueError(f"{chart}: values.yaml is required")
        target = chart / "values.schema.json"
        expected = generated_schema(values_path)
        if args.write:
            target.write_text(expected, encoding="utf-8")
        elif not target.is_file() or target.read_text(encoding="utf-8") != expected:
            stale.append(target.relative_to(ROOT).as_posix())

    if stale:
        print(
            "ERROR: generated values schemas are missing or stale:\n"
            + "\n".join(f"- {path}" for path in stale),
            file=sys.stderr,
        )
        return 1
    print(f"Validated {len(charts)} deterministic values schemas.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
