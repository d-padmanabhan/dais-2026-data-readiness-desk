#!/usr/bin/env bash
#
# Script Name         : deploy_databricks_app.sh
#
# Purpose             : Sync and deploy the Data Readiness Desk as a Free
#                       Databricks App from the repository's app/ directory.
#
# Dependencies        : databricks, jq, npm
#
# Script Usage        : ./scripts/deploy_databricks_app.sh [options]
#
# Examples            : ./scripts/deploy_databricks_app.sh
#                       ./scripts/deploy_databricks_app.sh --app-name data-readiness-desk
#                       ./scripts/deploy_databricks_app.sh --workspace-path /Workspace/Users/me/data-readiness-desk-app
#
##----------------------------------------------------------------------------------------##
# Turn debug on or off
# set -x
##----------------------------------------------------------------------------------------##

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
GIT_REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly GIT_REPO_ROOT

readonly DEFAULT_APP_NAME="data-readiness-desk"
readonly DEFAULT_APP_SOURCE_DIR="${GIT_REPO_ROOT}/app"

app_name="${DEFAULT_APP_NAME}"
workspace_path=""
app_source_dir="${DEFAULT_APP_SOURCE_DIR}"

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
  deploy_databricks_app.sh [options]

Options:
  --app-name <name>        Databricks App name (default: data-readiness-desk)
  --workspace-path <path>  Workspace path for synced source code
  --app-source-dir <path>  Local app source directory (default: ./app)
  -h, --help              Show help

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
      --workspace-path)
        [[ $# -ge 2 ]] || die "--workspace-path requires a value"
        workspace_path="$2"
        shift 2
        ;;
      --app-source-dir)
        [[ $# -ge 2 ]] || die "--app-source-dir requires a value"
        app_source_dir="$2"
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
  [[ -d "${app_source_dir}" ]] || die "App source directory does not exist: ${app_source_dir}"
  [[ -f "${app_source_dir}/app.yaml" ]] || die "Missing app.yaml in ${app_source_dir}"
  [[ -f "${app_source_dir}/package.json" ]] || die "Missing package.json in ${app_source_dir}"
}

resolve_workspace_path() {
  local user_name

  if [[ -n "${workspace_path}" ]]; then
    return
  fi

  user_name="$(databricks current-user me --output json | jq -r '.userName // .user_name // empty')"
  [[ -n "${user_name}" ]] || die "Could not resolve Databricks current user name"
  workspace_path="/Workspace/Users/${user_name}/${app_name}"
}

create_app_if_needed() {
  if databricks apps get "${app_name}" --output json > /dev/null 2>&1; then
    logmsg "Databricks App already exists: ${app_name}"
    return
  fi

  logmsg "Creating Databricks App: ${app_name}"
  databricks apps create "${app_name}" \
    --description "Data Readiness Desk trust verdict dashboard" \
    --no-compute \
    --output json > /dev/null
}

sync_source() {
  logmsg "Syncing ${app_source_dir} to ${workspace_path}"
  databricks sync "${app_source_dir}" "${workspace_path}" --full
}

deploy_app() {
  logmsg "Starting Databricks App compute: ${app_name}"
  databricks apps start "${app_name}" > /dev/null

  logmsg "Deploying ${app_name} from ${workspace_path}"
  databricks apps deploy "${app_name}" \
    --source-code-path "${workspace_path}" \
    --auto-approve \
    --output json
}

main() {
  parse_args "$@"
  require_command databricks
  require_command jq
  require_command npm

  cd "${GIT_REPO_ROOT}"
  validate_inputs
  logmsg "Validating Databricks auth"
  databricks current-user me > /dev/null
  resolve_workspace_path
  create_app_if_needed
  sync_source
  deploy_app
}

main "$@"
