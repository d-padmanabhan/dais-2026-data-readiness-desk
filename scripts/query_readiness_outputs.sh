#!/usr/bin/env bash
#
# Script Name         : query_readiness_outputs.sh
#
# Purpose             : Query important cached Data Readiness Desk tables through
#                       the Databricks SQL Statement Execution API.
#
# Dependencies        : databricks, jq
#
# Script Usage        : ./scripts/query_readiness_outputs.sh --warehouse-id <id>
#
# Examples            : ./scripts/query_readiness_outputs.sh --warehouse-id 4e307d33a4466b55
#                       ./scripts/query_readiness_outputs.sh --warehouse-id 4e307d33a4466b55 --limit 10
#                       ./scripts/query_readiness_outputs.sh --warehouse-id 4e307d33a4466b55 --table pipeline_quality_checks
#
##----------------------------------------------------------------------------------------##
# Turn debug on or off
# set -x
##----------------------------------------------------------------------------------------##

set -euo pipefail

readonly DEFAULT_CATALOG="data_readiness_desk"
readonly DEFAULT_SCHEMA="pipeline"
readonly DEFAULT_LIMIT="5"
readonly DEFAULT_TABLES=(
  "gold_hmis_state_indicator_summary"
  "gold_facility_verdicts"
  "silver_facilities_geo"
  "pipeline_quality_checks"
)

warehouse_id=""
catalog="${DEFAULT_CATALOG}"
schema="${DEFAULT_SCHEMA}"
limit="${DEFAULT_LIMIT}"
tables=("${DEFAULT_TABLES[@]}")

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
  query_readiness_outputs.sh --warehouse-id <warehouse-id> [options]

Options:
  --warehouse-id <id>  Required SQL Warehouse ID used to execute queries
  --catalog <name>     Unity Catalog catalog name (default: data_readiness_desk)
  --schema <name>      Schema name (default: pipeline)
  --limit <n>          Number of rows to return per table (default: 5)
  --table <name>       Table to query. Can be repeated. Defaults to key readiness tables.
  -h, --help           Show help

Environment:
  DATABRICKS_HOST
  DATABRICKS_CLIENT_ID
  DATABRICKS_CLIENT_SECRET
EOF
}

parse_args() {
  local custom_tables=()

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
        schema="$2"
        shift 2
        ;;
      --limit)
        [[ $# -ge 2 ]] || die "--limit requires a value"
        limit="$2"
        shift 2
        ;;
      --table)
        [[ $# -ge 2 ]] || die "--table requires a value"
        custom_tables+=("$2")
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

  [[ -n "${warehouse_id}" ]] || die "--warehouse-id is required"
  [[ "${limit}" =~ ^[0-9]+$ ]] || die "--limit must be a positive integer"

  if [[ "${#custom_tables[@]}" -gt 0 ]]; then
    tables=("${custom_tables[@]}")
  fi
}

validate_databricks_auth() {
  databricks current-user me > /dev/null
}

query_table() {
  local table="$1"
  local statement
  local payload

  statement="SELECT * FROM ${catalog}.${schema}.${table} LIMIT ${limit}"
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

  printf "\n-- %s\n" "${table}"
  databricks api post /api/2.0/sql/statements --json "${payload}" --output json \
    | jq '{status: .status, columns: .manifest.schema.columns, rows: .result.data_array}'
}

main() {
  parse_args "$@"
  require_command databricks
  require_command jq
  validate_databricks_auth

  for table in "${tables[@]}"; do
    query_table "${table}"
  done
}

main "$@"
