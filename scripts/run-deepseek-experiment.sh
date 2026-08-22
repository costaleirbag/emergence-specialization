#!/usr/bin/env bash
# Run one experiment with a DeepSeek key fetched once from the local Bitwarden CLI.
#
# This launcher deliberately owns Bitwarden access. The Python experiment and its
# OMP subprocesses inherit DEEPSEEK_API_KEY only for this process tree; they never
# inherit BW_SESSION.

set -euo pipefail
set +x
umask 077

readonly BITWARDEN_ITEM_NAME="DeepSeek API"

bw_command="bw"
uv_command="uv"
bw_session=""
deepseek_api_key=""
lock_required=0

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found on PATH: $1"
}

cleanup() {
  local exit_code=$?
  trap - EXIT HUP INT TERM
  set +e

  unset DEEPSEEK_API_KEY BW_SESSION
  if [[ "$lock_required" == "1" && -n "$bw_session" ]]; then
    "$bw_command" lock --session "$bw_session" >/dev/null 2>&1 || true
  fi
  deepseek_api_key=""
  bw_session=""
  unset deepseek_api_key bw_session

  exit "$exit_code"
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP

[[ "$#" -gt 0 ]] || fail "Usage: scripts/run-deepseek-experiment.sh --config <config.yaml> [experiment options]"

require_command "$bw_command"
require_command "jq"
require_command "$uv_command"

bw_status_json="$("$bw_command" status 2>/dev/null)" || fail "Unable to query Bitwarden CLI status."
bw_state="$(printf '%s' "$bw_status_json" | jq -er '.status // empty' 2>/dev/null)" \
  || fail "Bitwarden CLI returned an invalid status response."
unset bw_status_json

case "$bw_state" in
  unauthenticated)
    fail "Bitwarden CLI is unauthenticated. Run bw login in your terminal, then retry."
    ;;
  locked)
    bw_session="$("$bw_command" unlock --raw)" || fail "Unable to unlock the Bitwarden vault."
    ;;
  unlocked)
    if [[ -n "${BW_SESSION:-}" ]]; then
      bw_session="$BW_SESSION"
    else
      bw_session="$("$bw_command" unlock --raw)" || fail "Unable to obtain a Bitwarden session."
    fi
    ;;
  *)
    fail "Unsupported Bitwarden CLI status: $bw_state"
    ;;
esac

[[ -n "$bw_session" ]] || fail "Bitwarden did not provide a usable session."
lock_required=1

"$bw_command" sync --session "$bw_session" >/dev/null \
  || fail "Unable to sync the Bitwarden vault."

matching_items_json="$("$bw_command" list items --search "$BITWARDEN_ITEM_NAME" --session "$bw_session")" \
  || fail "Unable to search Bitwarden items."
matching_item_count="$(
  printf '%s' "$matching_items_json" \
    | jq -er --arg item_name "$BITWARDEN_ITEM_NAME" '[.[] | select(.name == $item_name)] | length'
)" || fail "Bitwarden item search returned invalid JSON."

[[ "$matching_item_count" == "1" ]] \
  || fail "Expected exactly one Bitwarden item named $BITWARDEN_ITEM_NAME; found $matching_item_count."

item_id="$(
  printf '%s' "$matching_items_json" \
    | jq -er --arg item_name "$BITWARDEN_ITEM_NAME" '[.[] | select(.name == $item_name)][0].id'
)" || fail "The Bitwarden item named $BITWARDEN_ITEM_NAME has no usable ID."
unset matching_items_json matching_item_count

deepseek_api_key="$("$bw_command" get password "$item_id" --session "$bw_session")" \
  || fail "Unable to obtain the password from the Bitwarden item named $BITWARDEN_ITEM_NAME."
unset item_id
[[ -n "$deepseek_api_key" ]] || fail "The Bitwarden item named $BITWARDEN_ITEM_NAME has an empty password."

# Lock before starting Python. The session stays local to this launcher and is
# explicitly removed from the child environment.
"$bw_command" lock --session "$bw_session" >/dev/null 2>&1 \
  || fail "Unable to lock the Bitwarden vault after retrieving the key."
lock_required=0
unset BW_SESSION

export DEEPSEEK_API_KEY="$deepseek_api_key"
set +e
"$uv_command" run python -m emergent_specialization.runtime.experiment "$@"
experiment_exit=$?
set -e
exit "$experiment_exit"
