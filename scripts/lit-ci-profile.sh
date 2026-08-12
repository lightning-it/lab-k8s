#!/usr/bin/env bash
set -euo pipefail

readonly PROFILE_NAME="repository-quality"
readonly BASE_REF="refs/remotes/origin/develop"
readonly DEVTOOLS_WRAPPER="scripts/wunder-devtools-ee.sh"

fail_closed() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

if [ "$#" -ne 1 ] || [ "$1" != "$PROFILE_NAME" ]; then
  printf 'Usage: %s %s\n' "${0##*/}" "$PROFILE_NAME" >&2
  exit 2
fi

export LC_ALL=C
umask 077

case "$(uname -s)" in
  Darwin|Linux) ;;
  *) fail_closed "repository-quality supports only macOS and Linux hosts" ;;
esac
case "$(uname -m)" in
  x86_64|amd64|arm64|aarch64) ;;
  *) fail_closed "unsupported host architecture: $(uname -m)" ;;
esac

repository_root="$(git rev-parse --show-toplevel 2>/dev/null)" \
  || fail_closed "run the profile from a Git worktree"
repository_root="$(cd "$repository_root" && pwd -P)"
cd "$repository_root"

for required_path in \
  "$DEVTOOLS_WRAPPER" \
  ".lit/repository.yml" \
  "scripts/lit-push-ready.py" \
  "scripts/lit-repository-quality.py"
do
  [ -f "$required_path" ] && [ ! -L "$required_path" ] \
    || fail_closed "required regular profile input is missing: $required_path"
done

[ -z "$(git status --porcelain=v1 --untracked-files=all)" ] \
  || fail_closed "repository-quality requires a clean committed worktree"
git show-ref --verify --quiet "$BASE_REF" \
  || fail_closed "missing authoritative base ref: $BASE_REF"
merge_base="$(git merge-base "$BASE_REF" HEAD)" \
  || fail_closed "cannot resolve authoritative merge base"
[ -n "$merge_base" ] || fail_closed "authoritative merge base is empty"

fingerprint() {
  {
    git rev-parse HEAD
    git write-tree
    git status --porcelain=v1 --untracked-files=all -z
    git diff --no-ext-diff --no-textconv --binary HEAD --
  } | git hash-object --stdin
}

initial_fingerprint="$(fingerprint)" \
  || fail_closed "cannot fingerprint initial worktree"

run_devtools() {
  local network_mode="${1:-}"
  shift || fail_closed "Devtool network mode is required"
  case "$network_mode" in
    none|bridge) ;;
    *) fail_closed "unsupported Devtool network mode: $network_mode" ;;
  esac
  env \
    CONTAINER_HOME=/tmp/wunder \
    WUNDER_DEVTOOLS_CAP_ADD= \
    WUNDER_DEVTOOLS_DOCKER_SOCKET=disabled \
    WUNDER_DEVTOOLS_FORWARD_VAGRANT_SSH=disabled \
    WUNDER_DEVTOOLS_MOUNT_SOURCE_ROOT=disabled \
    WUNDER_DEVTOOLS_NETWORK="$network_mode" \
    WUNDER_DEVTOOLS_PRIVILEGED=0 \
    WUNDER_DEVTOOLS_RUN_AS_HOST_UID=1 \
    WUNDER_DEVTOOLS_WORKSPACE_MODE=ro \
    CI=true \
    GITHUB_ACTIONS= \
    "$DEVTOOLS_WRAPPER" "$@"
}

repository_type="$(
  awk '
    $1 == "repository_type:" {
      count += 1
      if (NF != 2) {
        exit 2
      }
      value = $2
    }
    END {
      if (count != 1) {
        exit 3
      }
      print value
    }
  ' .lit/repository.yml
)" || fail_closed "cannot resolve one repository_type from .lit/repository.yml"
case "$repository_type" in
  terraform_module|terraform_policy) quality_network="bridge" ;;
  ""|*[!a-z0-9_]*) fail_closed "invalid repository_type: $repository_type" ;;
  *) quality_network="none" ;;
esac
readonly quality_network

printf '==> Verify Codex and Copilot instruction binding\n'
python3 scripts/lit-push-ready.py instructions

printf '==> Run repository quality in the pinned Devtool\n'
run_devtools "$quality_network" python3 scripts/lit-repository-quality.py

run_unit_tests() {
  # Tests may execute temporary command shims. Keep their temporary files on
  # the fresh executable HOME tmpfs instead of the generic /tmp mount.
  run_devtools none env TMPDIR=/tmp/wunder "$@"
}

if [ -d tests ] && find tests -type f -name 'test*.py' -print -quit \
  | grep -q .
then
  printf '==> Run repository unit tests from tests in the pinned Devtool\n'
  run_unit_tests \
    python3 -m unittest discover -s tests -p 'test*.py'
fi

if [ -d scripts ] && find scripts -type f -name 'test*.py' -print -quit \
  | grep -q .
then
  printf '==> Run repository unit tests from scripts in the pinned Devtool\n'
  run_unit_tests \
    python3 -m unittest discover -s scripts -p 'test*.py'
fi

printf '==> Validate GitHub Actions workflows in the pinned Devtool\n'
shopt -s nullglob
workflow_paths=(
  .github/workflows/*.yml
  .github/workflows/*.yaml
)
shopt -u nullglob
[ "${#workflow_paths[@]}" -gt 0 ] \
  || fail_closed "no GitHub Actions workflows were found for actionlint"
run_devtools none actionlint "${workflow_paths[@]}"

printf '==> Validate committed and local diffs\n'
git diff --check "$merge_base"...HEAD --
git diff --check
git diff --cached --check

final_fingerprint="$(fingerprint)" \
  || fail_closed "cannot fingerprint final worktree"
[ "$initial_fingerprint" = "$final_fingerprint" ] \
  || fail_closed "repository-quality profile changed the Git worktree"

printf 'Repository-quality profile passed.\n'
