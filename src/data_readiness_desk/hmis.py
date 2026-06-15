"""HMIS source parsing helpers.

The currently uploaded HMIS file is a wide state-level extract:
`State`, `S.No.`, `Parameters`, `Type`, then monthly value columns such as
`April - Total [(A+B) or (C+D)]`.

Workflow:
1. Validate the source header before ingest.
2. Parse wide month/value-type columns.
3. Normalize numeric cells while preserving unavailable values as null.
4. Convert rows to long-form records for downstream Spark or test workflows.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from data_readiness_desk.normalization import normalize_place_name

MONTH_COLUMN_PATTERN = re.compile(r"^(?P<month>[A-Za-z]+|Total)\s+-\s+(?P<value_type>[^\[]+)")
REQUIRED_HMIS_COLUMNS = frozenset({"State", "S.No.", "Parameters", "Type"})
UNAVAILABLE_VALUES = frozenset({"", "NA", "N/A", "NULL", "-"})
HMIS_INDICATOR_SERIALS = {
    "anc_registered": "1.1",
    "anc_four_plus": "1.2.7",
    "institutional_deliveries": "2.2",
    "live_birth_male": "4.1.1.a",
    "live_birth_female": "4.1.1.b",
    "fully_immunized_male": "9.2.4.a",
    "fully_immunized_female": "9.2.4.b",
}


@dataclass(frozen=True)
class HmisMeasureColumn:
    """
    Parsed HMIS wide value column.

    Args:
        source_column: Original CSV column name.
        month: Reporting month or `Total`.
        value_type: Total, Public, Private, Urban, or Rural.
    """

    source_column: str
    month: str
    value_type: str


@dataclass(frozen=True)
# Flat fields mirror the long-form HMIS silver table contract.
class HmisLongRecord:  # pylint: disable=too-many-instance-attributes
    """
    Long-form HMIS measurement.

    Args:
        state: Source state name.
        state_normalized: Normalized state key.
        serial_number: HMIS serial number.
        parameter: Cleaned HMIS parameter name.
        reporting_type: Source row type.
        month: Reporting month or `Total`.
        value_type: Total, Public, Private, Urban, or Rural.
        value: Parsed integer value, or None when unavailable.
        geo_grain: Geographic grain for the record.
    """

    state: str
    state_normalized: str | None
    serial_number: str
    parameter: str
    reporting_type: str
    month: str
    value_type: str
    value: int | None
    geo_grain: str = "state"


def clean_hmis_text(value: object) -> str:
    """
    Normalize HMIS text cells.

    Args:
        value: Raw cell value.

    Returns:
        Whitespace-normalized text with non-breaking spaces replaced.
    """
    return " ".join(str(value or "").replace("\xa0", " ").split())


def parse_hmis_number(value: object) -> int | None:
    """
    Parse HMIS numeric cells.

    Args:
        value: Raw cell value.

    Returns:
        Integer value, or None for unavailable markers.

    Raises:
        ValueError: If the value is neither unavailable nor an integer-like number.
    """
    cleaned_value = clean_hmis_text(value).replace(",", "")
    if cleaned_value.upper() in UNAVAILABLE_VALUES:
        return None
    if not re.fullmatch(r"-?\d+", cleaned_value):
        raise ValueError(f"Invalid HMIS numeric value: {value!r}")
    return int(cleaned_value)


def parse_hmis_measure_column(column_name: str) -> HmisMeasureColumn | None:
    """
    Parse a wide HMIS month/value-type column name.

    Args:
        column_name: Raw CSV column name.

    Returns:
        Parsed measure column, or None when the column is not a measure.
    """
    match = MONTH_COLUMN_PATTERN.match(clean_hmis_text(column_name))
    if match is None:
        return None
    return HmisMeasureColumn(
        source_column=column_name,
        month=match.group("month"),
        value_type=clean_hmis_text(match.group("value_type")),
    )


def validate_hmis_header(header: Iterable[str]) -> list[HmisMeasureColumn]:
    """
    Validate HMIS header and return parsed measure columns.

    Args:
        header: CSV header values.

    Returns:
        Parsed measure columns.

    Raises:
        ValueError: If required columns or measure columns are missing.
    """
    header_list = list(header)
    missing_columns = sorted(REQUIRED_HMIS_COLUMNS.difference(header_list))
    if missing_columns:
        raise ValueError(f"HMIS file is missing required columns: {missing_columns}")

    measure_columns = [
        measure_column
        for column_name in header_list
        if (measure_column := parse_hmis_measure_column(column_name)) is not None
    ]
    if not measure_columns:
        raise ValueError("HMIS file has no month/value measure columns")
    return measure_columns


def hmis_rows_to_long_records(rows: Iterable[Mapping[str, object]]) -> list[HmisLongRecord]:
    """
    Convert HMIS wide rows to long-form records.

    Args:
        rows: Iterable of source rows keyed by CSV header.

    Returns:
        Long-form HMIS records.

    Raises:
        ValueError: If rows are empty or have an invalid header/value shape.
    """
    row_list = list(rows)
    if not row_list:
        raise ValueError("At least one HMIS row is required")

    measure_columns = validate_hmis_header(row_list[0].keys())
    records: list[HmisLongRecord] = []
    for row in row_list:
        state = clean_hmis_text(row["State"])
        parameter = clean_hmis_text(row["Parameters"])
        reporting_type = clean_hmis_text(row["Type"])
        serial_number = clean_hmis_text(row["S.No."]).strip("'")
        for measure_column in measure_columns:
            records.append(
                HmisLongRecord(
                    state=state,
                    state_normalized=normalize_place_name(state),
                    serial_number=serial_number,
                    parameter=parameter,
                    reporting_type=reporting_type,
                    month=measure_column.month,
                    value_type=measure_column.value_type,
                    value=parse_hmis_number(row[measure_column.source_column]),
                )
            )
    return records
