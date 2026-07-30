#!/usr/bin/env bash
# kms-get-secret.sh
#
# Fetch a Secret Manager secret value from OVH OKMS using mTLS.
# - Logs go to STDERR
# - Secret value is written only to the configured output file
#
# Required args:
#   --cert <path> --key <path>
#
# Env (defaults are safe placeholders; override in K8s ConfigMap):
#   OKMS_REST="https://eu-west-lim.okms.ovh.net"
#   SECRET_UPN="urn:.../secret/poc%2Fvpn"
#   SECRET_KV_KEY="shared-key"
#   SECRET_OUT_FILE="/work/shared-key.txt"   (required)

set -euo pipefail

OKMS_REST="${OKMS_REST:-https://eu-west-lim.okms.ovh.net}"
SECRET_UPN="${SECRET_UPN:-}"
SECRET_KV_KEY="${SECRET_KV_KEY:-shared-key}"
SECRET_OUT_FILE="${SECRET_OUT_FILE:-}"

CERT_PATH=""
KEY_PATH=""

log(){ printf "[kms-get-secret] %s\n" "$*" >&2; }
die(){ printf "[kms-get-secret] ERROR: %s\n" "$*" >&2; exit 1; }

have_cmd(){ command -v "$1" >/dev/null 2>&1; }

usage(){
  cat >&2 <<EOF
Usage: $0 --cert <path> --key <path>

Environment:
  OKMS_REST       Base URL like https://eu-west-lim.okms.ovh.net
  SECRET_UPN      urn:v1:.../secret/<ENCODED_PATH>
  SECRET_KV_KEY   Key in secret payload (default: shared-key)
  SECRET_OUT_FILE Required path for the secret value (never written to stdout)

EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cert) CERT_PATH="$2"; shift 2;;
    --key)  KEY_PATH="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) die "Unknown arg: $1 (use --help)";;
  esac
done

[[ -n "$CERT_PATH" ]] || die "--cert is required"
[[ -n "$KEY_PATH"  ]] || die "--key is required"
[[ -r "$CERT_PATH" ]] || die "Cannot read cert file: $CERT_PATH"
[[ -r "$KEY_PATH"  ]] || die "Cannot read key file:  $KEY_PATH"
[[ -n "$SECRET_UPN" ]] || die "SECRET_UPN env var must be set"
[[ -n "$SECRET_OUT_FILE" ]] || die "SECRET_OUT_FILE env var must be set"

have_cmd curl || die "curl is required"
have_cmd jq   || die "jq is required"

# Parse UPN: urn:v1:eu:resource:okms:<OKMS_ID>/secret/<ENC_PATH>
tmp="${SECRET_UPN#*okms:}"
okms_id="${tmp%%/secret/*}"
enc_path="${tmp#*/secret/}"

[[ -n "$okms_id"  ]] || die "Failed to parse okmsId from SECRET_UPN"
[[ -n "$enc_path" ]] || die "Failed to parse secret path from SECRET_UPN"

# We prefer the *encoded* path exactly as in the URN (e.g. poc%2Fvpn).
# Use --path-as-is to prevent any normalization.
candidates=(
  "${OKMS_REST}/api/${okms_id}/v1/secret/data/${enc_path}"
  "${OKMS_REST}/api/${okms_id}/v2/secret/${enc_path}"
  "${OKMS_REST}/api/${okms_id}/v2/secret/${enc_path}?includeData=true"
  "${OKMS_REST}/api/${okms_id}/v2/secret/${enc_path}?include_data=true"
)

body=""
code=""
found_url=""
endpoint_number=0

for u in "${candidates[@]}"; do
  endpoint_number=$((endpoint_number + 1))
  log "Trying OKMS endpoint variant $endpoint_number"
  # capture http code + body without failing the script on non-2xx
  body_file="$(mktemp)"
  code="$(curl -sS -L --path-as-is --cert "$CERT_PATH" --key "$KEY_PATH"         -H "Accept: application/json"         -o "$body_file" -w "%{http_code}"         "$u" || true)"
  body="$(cat "$body_file")"
  rm -f "$body_file"
  log "-> HTTP $code"
  if [[ "$code" == "200" ]]; then
    found_url="$u"
    break
  fi
done

[[ -n "$found_url" ]] || die "Secret fetch failed on all endpoints. Last HTTP=$code"

# Extract value (try common shapes)
# KV2: .data.data["key"]
# REST: .version.data["key"]
val="$(printf "%s" "$body" | jq -r --arg k "$SECRET_KV_KEY" '(.data.data[$k] // .version.data[$k] // empty)')"

if [[ -z "$val" || "$val" == "null" ]]; then
  die "Requested key was not present in the successful OKMS response"
fi

umask 077
mkdir -p "$(dirname "$SECRET_OUT_FILE")" 2>/dev/null || true
printf "%s" "$val" > "$SECRET_OUT_FILE"
log "Wrote secret value to $SECRET_OUT_FILE"
