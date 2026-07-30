#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
charts_root="${repo_root}/helm-charts/charts"

shopt -s nullglob
chart_files=("${charts_root}"/*/Chart.yaml)
if [ "${#chart_files[@]}" -eq 0 ]; then
  echo "No embedded product charts found under ${charts_root}." >&2
  exit 1
fi

for chart_file in "${chart_files[@]}"; do
  chart="$(dirname "${chart_file}")"
  chart_name="$(basename "${chart}")"
  helm lint "${chart}"
  helm template "${chart_name}" "${chart}" >/dev/null
done

echo "Linted and rendered ${#chart_files[@]} embedded product charts."
