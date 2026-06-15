#!/usr/bin/env bash
#
# Script Name         : bootstrap_databricks_workspace.sh
#
# Purpose             : Create the Unity Catalog objects needed by the Data
#                       Readiness Desk and upload any local source files that
#                       exist under the repository's data/ directory.
#
# Dependencies        : databricks, jq
#
# Script Usage        : ./scripts/bootstrap_databricks_workspace.sh [--warehouse-id <id>]
#
# Examples            : ./scripts/bootstrap_databricks_workspace.sh --warehouse-id 4e307d33a4466b55
#                       DATABRICKS_WAREHOUSE_ID=4e307d33a4466b55 ./scripts/bootstrap_databricks_workspace.sh --require-all-files
#                       ./scripts/bootstrap_databricks_workspace.sh --warehouse-id 4e307d33a4466b55 --catalog data_readiness_desk --schema pipeline
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
readonly DEFAULT_CATALOG="data_readiness_desk"
readonly DEFAULT_TABLE_SCHEMA="pipeline"
readonly DEFAULT_VOLUME_SCHEMA="bronze"
readonly DEFAULT_VOLUME="files"
readonly DEFAULT_DATA_DIR="${GIT_REPO_ROOT}/data"
readonly SOURCE_FILES=(
  "hmis_2019_20_slice.csv"
  "srs_2020_state.csv"
  "india_post_pincode_directory.csv"
  "india_districts.geojson"
)

warehouse_id="${DATABRICKS_WAREHOUSE_ID:-}"
catalog="${DEFAULT_CATALOG}"
table_schema="${DEFAULT_TABLE_SCHEMA}"
volume_schema="${DEFAULT_VOLUME_SCHEMA}"
volume="${DEFAULT_VOLUME}"
data_dir="${DEFAULT_DATA_DIR}"
require_all_files="0"

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
  bootstrap_databricks_workspace.sh [--warehouse-id <warehouse-id>] [options]

Options:
  --warehouse-id <id>      SQL Warehouse ID used to execute setup SQL
  --catalog <name>         Unity Catalog catalog name (default: data_readiness_desk)
  --schema <name>          Table schema used by the bundle (default: pipeline)
  --volume-schema <name>   Schema containing the source-file Volume (default: bronze)
  --volume <name>          Source-file Volume name (default: files)
  --data-dir <path>        Local source file directory (default: ./data)
  --require-all-files      Fail if any expected source file is missing
  -h, --help               Show help

Environment:
  DATABRICKS_HOST
  DATABRICKS_CLIENT_ID
  DATABRICKS_CLIENT_SECRET
  DATABRICKS_WAREHOUSE_ID
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --warehouse-id)
        [[ $# -ge 2 ]] || die "--warehouse-id requires a value"
        warehouse_id="$2"
        shift 2
        ;;
      --catalog)
        [[ $# -ge 2 ]] || die "--catalog requires a value"
        catalog="$2"
        shift 2
        ;;
      --schema)
        [[ $# -ge 2 ]] || die "--schema requires a value"
        table_schema="$2"
        shift 2
        ;;
      --volume-schema | --bronze-schema)
        [[ $# -ge 2 ]] || die "$1 requires a value"
        volume_schema="$2"
        shift 2
        ;;
      --volume)
        [[ $# -ge 2 ]] || die "--volume requires a value"
        volume="$2"
        shift 2
        ;;
      --data-dir)
        [[ $# -ge 2 ]] || die "--data-dir requires a value"
        data_dir="$2"
        shift 2
        ;;
      --require-all-files)
        require_all_files="1"
        shift
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

  [[ -n "${warehouse_id}" ]] || die "--warehouse-id or DATABRICKS_WAREHOUSE_ID is required"
}

validate_databricks_auth() {
  logmsg "Validating Databricks service-principal auth"
  databricks current-user me > /dev/null
}

volume_path() {
  printf "/Volumes/%s/%s/%s" "${catalog}" "${volume_schema}" "${volume}"
}

execute_sql_statement() {
  local statement="$1"
  local payload

  payload="$(
    jq -n \
      --arg warehouse_id "${warehouse_id}" \
      --arg statement "${statement}" \
      '{
        warehouse_id: $warehouse_id,
        statement: $statement,
        wait_timeout: "50s",
        on_wait_timeout: "CONTINUE"
      }'
  )"

  logmsg "Executing SQL: ${statement}"
  databricks api post /api/2.0/sql/statements --json "${payload}" --output json > /dev/null
}

create_unity_catalog_objects() {
  execute_sql_statement "CREATE CATALOG IF NOT EXISTS ${catalog}"
  execute_sql_statement "CREATE SCHEMA IF NOT EXISTS ${catalog}.${table_schema}"
  execute_sql_statement "CREATE SCHEMA IF NOT EXISTS ${catalog}.${volume_schema}"
  execute_sql_statement "CREATE VOLUME IF NOT EXISTS ${catalog}.${volume_schema}.${volume}"
}

upload_source_files() {
  local destination_base
  local file_name
  local local_path
  local missing_files=()
  local uploaded_files=()

  destination_base="dbfs:$(volume_path)"

  for file_name in "${SOURCE_FILES[@]}"; do
    local_path="${data_dir%/}/${file_name}"
    if [[ -f "${local_path}" ]]; then
      logmsg "Uploading ${local_path} to ${destination_base}/${file_name}"
      databricks fs cp "${local_path}" "${destination_base}/${file_name}" --overwrite
      uploaded_files+=("${file_name}")
    else
      missing_files+=("${file_name}")
    fi
  done

  if [[ "${require_all_files}" == "1" && "${#missing_files[@]}" -gt 0 ]]; then
    die "Missing required source files: ${missing_files[*]}"
  fi

  if [[ "${#missing_files[@]}" -gt 0 ]]; then
    logmsg "Skipped missing optional source files: ${missing_files[*]}"
  fi
  logmsg "Uploaded source files: ${uploaded_files[*]:-none}"
}

list_volume_contents() {
  logmsg "Listing Volume contents: $(volume_path)"
  databricks fs ls "dbfs:$(volume_path)/"
}

main() {
  parse_args "$@"
  require_command databricks
  require_command jq

  cd "${GIT_REPO_ROOT}"
  validate_databricks_auth
  create_unity_catalog_objects
  upload_source_files
  list_volume_contents
}

main "$@"
