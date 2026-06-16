#!/usr/bin/env bash
#
# Script Name         : grant_databricks_app_access.sh
#
# Purpose             : Grant CAN_USE viewer access on the Free Databricks App
#                       without changing Unity Catalog data permissions.
#
# Dependencies        : databricks, jq
#
# Script Usage        : ./scripts/grant_databricks_app_access.sh --user <email>
#
# Examples            : ./scripts/grant_databricks_app_access.sh --user john.doe@acme.com
#                       ./scripts/grant_databricks_app_access.sh --group users
#                       ./scripts/grant_databricks_app_access.sh --app-name data-readiness-desk --group users
#
##----------------------------------------------------------------------------------------##
# Turn debug on or off
# set -x
##----------------------------------------------------------------------------------------##

set -euo pipefail

readonly DEFAULT_APP_NAME="data-readiness-desk"
readonly DEFAULT_PERMISSION_LEVEL="CAN_USE"

app_name="${DEFAULT_APP_NAME}"
permission_level="${DEFAULT_PERMISSION_LEVEL}"
user_name=""
group_name=""
service_principal_name=""

logmsg() {
  local timestamp
  timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  printf "%s %s\n" "${timestamp}" "$*" >&2
}

die() {
  logmsg "ERROR: $*"
  exit 1
}

require_command() {
  local command_name="$1"
  command -v "${command_name}" > /dev/null 2>&1 || die "Missing required command: ${command_name}"
}

show_help() {
  cat << 'EOF'
Usage:
  grant_databricks_app_access.sh (--user <email> | --group <name> | --service-principal <id-or-name>) [options]

Options:
  --app-name <name>              Databricks App name (default: data-readiness-desk)
  --user <email>                 User to grant app access
  --group <name>                 Group to grant app access
  --service-principal <id-name>  Service principal to grant app access
  --permission-level <level>     Permission level (default: CAN_USE)
  -h, --help                     Show help

Environment:
  DATABRICKS_HOST
  DATABRICKS_CLIENT_ID
  DATABRICKS_CLIENT_SECRET
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --app-name)
        [[ $# -ge 2 ]] || die "--app-name requires a value"
        app_name="$2"
        shift 2
        ;;
      --user)
        [[ $# -ge 2 ]] || die "--user requires a value"
        user_name="$2"
        shift 2
        ;;
      --group)
        [[ $# -ge 2 ]] || die "--group requires a value"
        group_name="$2"
        shift 2
        ;;
      --service-principal)
        [[ $# -ge 2 ]] || die "--service-principal requires a value"
        service_principal_name="$2"
        shift 2
        ;;
      --permission-level)
        [[ $# -ge 2 ]] || die "--permission-level requires a value"
        permission_level="$2"
        shift 2
        ;;
      -h | --help)
        show_help
        exit 0
        ;;
      *)
        die "Unknown argument: $1"
        ;;
    esac
  done
}

validate_inputs() {
  local subject_count=0

  [[ -n "${user_name}" ]] && subject_count=$((subject_count + 1))
  [[ -n "${group_name}" ]] && subject_count=$((subject_count + 1))
  [[ -n "${service_principal_name}" ]] && subject_count=$((subject_count + 1))

  [[ "${subject_count}" -eq 1 ]] || die "Specify exactly one of --user, --group, or --service-principal"
  [[ "${permission_level}" == "CAN_USE" || "${permission_level}" == "CAN_MANAGE" ]] || die "Unsupported permission level: ${permission_level}"
}

build_access_control_payload() {
  if [[ -n "${user_name}" ]]; then
    jq -n \
      --arg user_name "${user_name}" \
      --arg permission_level "${permission_level}" \
      '{access_control_list: [{user_name: $user_name, permission_level: $permission_level}]}'
    return
  fi

  if [[ -n "${group_name}" ]]; then
    jq -n \
      --arg group_name "${group_name}" \
      --arg permission_level "${permission_level}" \
      '{access_control_list: [{group_name: $group_name, permission_level: $permission_level}]}'
    return
  fi

  jq -n \
    --arg service_principal_name "${service_principal_name}" \
    --arg permission_level "${permission_level}" \
    '{access_control_list: [{service_principal_name: $service_principal_name, permission_level: $permission_level}]}'
}

grant_app_access() {
  local payload
  payload="$(build_access_control_payload)"

  logmsg "Granting ${permission_level} on app ${app_name}"
  databricks apps update-permissions "${app_name}" --json "${payload}" --output json \
    | jq '{object_id, access_control_list}'
}

main() {
  parse_args "$@"
  require_command databricks
  require_command jq
  validate_inputs

  logmsg "Validating Databricks auth"
  databricks current-user me > /dev/null
  grant_app_access
}

main "$@"
