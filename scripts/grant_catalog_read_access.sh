#!/usr/bin/env bash
#
# Script Name         : grant_catalog_read_access.sh
#
# Purpose             : Grant least-privilege read access to the Data Readiness
#                       Desk Unity Catalog objects for a named user or group.
#
# Dependencies        : databricks, jq
#
# Script Usage        : ./scripts/grant_catalog_read_access.sh --principal <email-or-group>
#
# Examples            : ./scripts/grant_catalog_read_access.sh --principal john.doe@acme.com
#                       ./scripts/grant_catalog_read_access.sh --principal john.doe@acme.com --warehouse-id 4e307d33a4466b55
#                       DATABRICKS_WAREHOUSE_ID=4e307d33a4466b55 ./scripts/grant_catalog_read_access.sh --principal analysts
#                       ./scripts/grant_catalog_read_access.sh --app-name data-readiness-desk --warehouse-id 4e307d33a4466b55
#
##----------------------------------------------------------------------------------------##
# Turn debug on or off
# set -x
##----------------------------------------------------------------------------------------##

set -euo pipefail

readonly DEFAULT_CATALOG="data_readiness_desk"
readonly DEFAULT_TABLE_SCHEMA="pipeline"
readonly DEFAULT_VOLUME_SCHEMA="bronze"
readonly DEFAULT_VOLUME="files"

warehouse_id="${DATABRICKS_WAREHOUSE_ID:-}"
principal=""
app_name=""
catalog="${DEFAULT_CATALOG}"
table_schema="${DEFAULT_TABLE_SCHEMA}"
volume_schema="${DEFAULT_VOLUME_SCHEMA}"
volume="${DEFAULT_VOLUME}"

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
  grant_catalog_read_access.sh (--principal <email-or-group> | --app-name <name>) [options]

Options:
  --principal <name>      Required Databricks user, service principal, or group
  --app-name <name>       Resolve and grant to a Databricks App service principal
  --warehouse-id <id>     SQL Warehouse ID used to execute grant SQL
  --catalog <name>        Unity Catalog catalog name (default: data_readiness_desk)
  --schema <name>         Table schema used by the bundle (default: pipeline)
  --volume-schema <name>  Schema containing the source-file Volume (default: bronze)
  --volume <name>         Source-file Volume name (default: files)
  -h, --help              Show help

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
      --principal)
        [[ $# -ge 2 ]] || die "--principal requires a value"
        principal="$2"
        shift 2
        ;;
      --app-name)
        [[ $# -ge 2 ]] || die "--app-name requires a value"
        app_name="$2"
        shift 2
        ;;
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
      --volume-schema)
        [[ $# -ge 2 ]] || die "--volume-schema requires a value"
        volume_schema="$2"
        shift 2
        ;;
      --volume)
        [[ $# -ge 2 ]] || die "--volume requires a value"
        volume="$2"
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

  [[ -n "${principal}" || -n "${app_name}" ]] || die "--principal or --app-name is required"
  [[ -n "${warehouse_id}" ]] || die "--warehouse-id or DATABRICKS_WAREHOUSE_ID is required"
}

validate_identifier() {
  local name="$1"
  local value="$2"
  [[ "${value}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || die "Invalid ${name}: ${value}"
}

quoted_principal() {
  [[ "${principal}" != *'`'* ]] || die "Principal cannot contain a backtick"
  printf '`%s`' "${principal}"
}

resolve_app_principal() {
  local app_payload
  local app_service_principal_client_id
  local app_service_principal_name

  [[ -z "${principal}" || -z "${app_name}" ]] || die "Use only one of --principal or --app-name"
  [[ -n "${app_name}" ]] || return

  logmsg "Resolving service principal for Databricks App: ${app_name}"
  app_payload="$(databricks apps get "${app_name}" --output json)"
  app_service_principal_client_id="$(jq -r '.service_principal_client_id // empty' <<< "${app_payload}")"
  app_service_principal_name="$(jq -r '.service_principal_name // empty' <<< "${app_payload}")"
  [[ -n "${app_service_principal_client_id}" ]] || die "App did not expose service_principal_client_id: ${app_name}"

  principal="${app_service_principal_client_id}"
  logmsg "Resolved ${app_name} to service principal ${principal} (${app_service_principal_name})"
}

execute_sql_statement() {
  local statement="$1"
  local payload
  local response
  local state
  local message

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
  response="$(databricks api post /api/2.0/sql/statements --json "${payload}" --output json)"
  state="$(jq -r '.status.state // "UNKNOWN"' <<< "${response}")"
  message="$(jq -r '.status.error.message // ""' <<< "${response}")"

  if [[ "${state}" != "SUCCEEDED" ]]; then
    [[ -z "${message}" ]] || logmsg "Databricks message: ${message}"
    die "SQL statement did not succeed. State: ${state}"
  fi
}

grant_read_access() {
  local grant_principal
  grant_principal="$(quoted_principal)"

  execute_sql_statement "GRANT USE CATALOG ON CATALOG ${catalog} TO ${grant_principal}"
  execute_sql_statement "GRANT USE SCHEMA ON SCHEMA ${catalog}.${table_schema} TO ${grant_principal}"
  execute_sql_statement "GRANT SELECT ON SCHEMA ${catalog}.${table_schema} TO ${grant_principal}"
  execute_sql_statement "GRANT USE SCHEMA ON SCHEMA ${catalog}.${volume_schema} TO ${grant_principal}"
  execute_sql_statement "GRANT READ VOLUME ON VOLUME ${catalog}.${volume_schema}.${volume} TO ${grant_principal}"
}

main() {
  parse_args "$@"
  require_command databricks
  require_command jq

  logmsg "Validating Databricks service-principal auth"
  databricks current-user me > /dev/null
  resolve_app_principal

  validate_identifier "catalog" "${catalog}"
  validate_identifier "schema" "${table_schema}"
  validate_identifier "volume schema" "${volume_schema}"
  validate_identifier "volume" "${volume}"

  grant_read_access
  logmsg "Granted read access on ${catalog} to ${principal}"
}

main "$@"
