#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
charts_root="${repo_root}/helm-charts/charts"

charts=("${charts_root}"/*)
if [ ! -d "${charts[0]}" ]; then
  echo "No embedded product charts found under ${charts_root}." >&2
  exit 1
fi

for chart in "${charts[@]}"; do
  chart_name="$(basename "${chart}")"
  helm lint "${chart}"
  helm template "${chart_name}" "${chart}" >/dev/null
done

echo "Linted and rendered ${#charts[@]} embedded product charts."
