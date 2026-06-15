#!/usr/bin/env bash
#
# Script Name         : fetch_pincode_directory.sh
#
# Purpose             : Fetch the India Post PIN code directory from the
#                       official data.gov.in API when an API key is available.
#
# Dependencies        : curl, jq
#
# Script Usage        : DATA_GOV_API_KEY=<key> ./scripts/fetch_pincode_directory.sh
#                       ./scripts/fetch_pincode_directory.sh --output data/india_post_pincode_directory.csv
#                       ./scripts/fetch_pincode_directory.sh --all-states
#
##----------------------------------------------------------------------------------------##
# set -x
##----------------------------------------------------------------------------------------##

set -euo pipefail

readonly RESOURCE_ID="6176ee09-3d56-4a3b-8115-21841576b2f6"
readonly API_BASE_URL="https://api.data.gov.in/resource/${RESOURCE_ID}"
readonly DEFAULT_OUTPUT="data/india_post_pincode_directory.csv"
readonly DEFAULT_LIMIT="1000"
readonly DEFAULT_STATES="TAMIL NADU,KERALA,TELANGANA,ANDHRA PRADESH,KARNATAKA,GOA,MAHARASHTRA"

api_key="${DATA_GOV_API_KEY:-}"
output_path="${DEFAULT_OUTPUT}"
limit="${DEFAULT_LIMIT}"
states_csv="${DEFAULT_STATES}"
all_states="0"

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
  DATA_GOV_API_KEY=<key> fetch_pincode_directory.sh [options]

Options:
  --api-key <key>      data.gov.in API key. Defaults to DATA_GOV_API_KEY.
  --output <path>      Output CSV path.
  --limit <rows>       API page size. Default: 1000.
  --states <csv>       Comma-separated uppercase state names to keep.
                       Default: Tamil Nadu, Kerala, Telangana, Andhra Pradesh,
                       Karnataka, Goa, Maharashtra.
  --all-states         Disable state filtering and fetch all records.
  -h, --help           Show help.

Notes:
  The official OGD API requires a data.gov.in API key. If you do not have one,
  use the data.gov.in web UI to download the CSV manually.
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --api-key)
        [[ $# -ge 2 ]] || die "--api-key requires a value"
        api_key="$2"
        shift 2
        ;;
      --output)
        [[ $# -ge 2 ]] || die "--output requires a value"
        output_path="$2"
        shift 2
        ;;
      --limit)
        [[ $# -ge 2 ]] || die "--limit requires a value"
        limit="$2"
        shift 2
        ;;
      --states)
        [[ $# -ge 2 ]] || die "--states requires a value"
        states_csv="$2"
        all_states="0"
        shift 2
        ;;
      --all-states)
        all_states="1"
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

  [[ -n "${api_key}" ]] || die "DATA_GOV_API_KEY or --api-key is required for the official OGD API"
}

fetch_page() {
  local offset="$1"
  curl -fsSLG "${API_BASE_URL}" \
    --data-urlencode "api-key=${api_key}" \
    --data-urlencode "format=json" \
    --data-urlencode "limit=${limit}" \
    --data-urlencode "offset=${offset}"
}

main() {
  parse_args "$@"
  require_command curl
  require_command jq

  mkdir -p "$(dirname "${output_path}")"
  local temp_json
  temp_json="$(mktemp)"
  trap 'rm -f "${temp_json}"' EXIT

  local offset=0
  local wrote_header="0"
  : > "${output_path}"

  while true; do
    logmsg "Fetching PIN directory rows at offset ${offset}"
    fetch_page "${offset}" > "${temp_json}"

    local record_count
    record_count="$(jq '.records | length' "${temp_json}")"
    if [[ "${record_count}" == "0" ]]; then
      break
    fi

    local filtered_count
    if [[ "${all_states}" == "1" ]]; then
      filtered_count="$(jq ".records | length" "${temp_json}")"
    else
      filtered_count="$(
        jq --arg states_csv "${states_csv}" \
          '.records
          | map(select(((.statename // .state_name // .StateName // .state // "") | ascii_upcase) as $state
          | ($states_csv | split(",") | map(ascii_upcase | gsub("^\\s+|\\s+$"; "")) | index($state)))) | length' \
          "${temp_json}"
      )"
    fi

    if [[ "${filtered_count}" != "0" ]]; then
      if [[ "${wrote_header}" == "0" ]]; then
        if [[ "${all_states}" == "1" ]]; then
          jq -r ".records[0] | keys_unsorted | @csv" "${temp_json}" >> "${output_path}"
        else
          jq -r --arg states_csv "${states_csv}" \
            '.records
            | map(select(((.statename // .state_name // .StateName // .state // "") | ascii_upcase) as $state
            | ($states_csv | split(",") | map(ascii_upcase | gsub("^\\s+|\\s+$"; "")) | index($state))))[0]
            | keys_unsorted
            | @csv' \
            "${temp_json}" >> "${output_path}"
        fi
        wrote_header="1"
      fi
      if [[ "${all_states}" == "1" ]]; then
        jq -r ".records[] | [.[]] | @csv" "${temp_json}" >> "${output_path}"
      else
        jq -r --arg states_csv "${states_csv}" \
          '.records
          | map(select(((.statename // .state_name // .StateName // .state // "") | ascii_upcase) as $state
          | ($states_csv | split(",") | map(ascii_upcase | gsub("^\\s+|\\s+$"; "")) | index($state))))
          | .[]
          | [.[]]
          | @csv' \
          "${temp_json}" >> "${output_path}"
      fi
    fi

    if ((record_count < limit)); then
      break
    fi
    offset=$((offset + limit))
  done

  if [[ "${wrote_header}" == "0" ]]; then
    die "No PIN directory rows matched the selected state filter: ${states_csv}"
  fi

  logmsg "Wrote PIN directory CSV to ${output_path}"
}

main "$@"
