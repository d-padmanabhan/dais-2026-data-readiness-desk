#!/usr/bin/env bash
#
# Script Name         : fetch_district_boundaries.sh
#
# Purpose             : Download an India district GeoJSON file for facility
#                       point-in-polygon assignment.
#
# Dependencies        : curl, jq
#
# Script Usage        : ./scripts/fetch_district_boundaries.sh
#                       ./scripts/fetch_district_boundaries.sh --output data/india_districts.geojson
#
##----------------------------------------------------------------------------------------##
# set -x
##----------------------------------------------------------------------------------------##

set -euo pipefail

readonly DEFAULT_SOURCE_URL="https://raw.githubusercontent.com/geohacker/india/master/district/india_district.geojson"
readonly DEFAULT_OUTPUT="data/india_districts.geojson"

source_url="${DEFAULT_SOURCE_URL}"
output_path="${DEFAULT_OUTPUT}"


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
  fetch_district_boundaries.sh [options]

Options:
  --source-url <url>   GeoJSON URL to download
  --output <path>      Output path (default: data/india_districts.geojson)
  -h, --help           Show help
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --source-url)
        [[ $# -ge 2 ]] || die "--source-url requires a value"
        source_url="$2"
        shift 2
        ;;
      --output)
        [[ $# -ge 2 ]] || die "--output requires a value"
        output_path="$2"
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

main() {
  parse_args "$@"
  require_command curl
  require_command jq

  mkdir -p "$(dirname "${output_path}")"
  logmsg "Downloading district boundaries from ${source_url}"
  curl -fsSL "${source_url}" -o "${output_path}"

  jq -e '
    .type == "FeatureCollection"
    and (.features | length > 0)
    and (.features[0].properties.NAME_1 | type == "string")
    and (.features[0].properties.NAME_2 | type == "string")
  ' "${output_path}" > /dev/null
  logmsg "Wrote district boundaries to ${output_path}"
}

main "$@"
