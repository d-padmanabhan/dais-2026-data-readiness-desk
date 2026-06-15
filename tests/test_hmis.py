"""Tests for HMIS parsing helpers."""

from __future__ import annotations

import pytest

from data_readiness_desk.hmis import (
    HMIS_INDICATOR_SERIALS,
    clean_hmis_text,
    hmis_rows_to_long_records,
    parse_hmis_measure_column,
    parse_hmis_number,
    validate_hmis_header,
)


def sample_hmis_row() -> dict[str, object]:
    """
    Build a representative HMIS source row.

    Returns:
        Dictionary with required HMIS metadata columns and sample monthly values.
    """
    return {
        "State": "A & N Islands",
        "S.No.": "'1.2.1'",
        "Parameters": "Number of PW given\xa0TT1",
        "Type": "TOTAL",
        "April - Total [(A+B) or (C+D)]": "328",
        "April - Public [A]": "328",
        "April - Private [B]": "NA",
    }


def test_clean_hmis_text_removes_non_breaking_spaces() -> None:
    """HMIS text cleanup handles cp1252 non-breaking spaces."""
    assert clean_hmis_text("Number of PW given\xa0TT1") == "Number of PW given TT1"


def test_hmis_indicator_serials_include_demo_measures() -> None:
    """Curated HMIS mapping includes measures needed by the demo story."""
    assert HMIS_INDICATOR_SERIALS["anc_registered"] == "1.1"
    assert HMIS_INDICATOR_SERIALS["anc_four_plus"] == "1.2.7"
    assert HMIS_INDICATOR_SERIALS["institutional_deliveries"] == "2.2"
    assert HMIS_INDICATOR_SERIALS["fully_immunized_male"] == "9.2.4.a"
    assert HMIS_INDICATOR_SERIALS["fully_immunized_female"] == "9.2.4.b"


def test_parse_hmis_number_handles_unavailable_values() -> None:
    """Unavailable HMIS values become null."""
    assert parse_hmis_number("NA") is None
    assert parse_hmis_number("") is None


def test_parse_hmis_number_rejects_invalid_values() -> None:
    """Unexpected numeric cells fail fast."""
    with pytest.raises(ValueError, match="Invalid HMIS numeric value"):
        parse_hmis_number("not-a-number")


def test_parse_hmis_measure_column_extracts_month_and_value_type() -> None:
    """Wide HMIS measure columns are parsed into month and value type."""
    parsed = parse_hmis_measure_column("April - Total [(A+B) or (C+D)]")

    assert parsed is not None
    assert parsed.month == "April"
    assert parsed.value_type == "Total"


def test_validate_hmis_header_requires_source_columns() -> None:
    """Header validation rejects files without required metadata columns."""
    with pytest.raises(ValueError, match="missing required columns"):
        validate_hmis_header(["State", "Parameters", "April - Total [(A+B) or (C+D)]"])


def test_hmis_rows_to_long_records_melts_wide_values() -> None:
    """Wide HMIS rows become long-form state-grain records."""
    records = hmis_rows_to_long_records([sample_hmis_row()])

    assert len(records) == 3
    assert records[0].state == "A & N Islands"
    assert records[0].state_normalized == "a and n islands"
    assert records[0].serial_number == "1.2.1"
    assert records[0].parameter == "Number of PW given TT1"
    assert records[0].month == "April"
    assert records[0].value_type == "Total"
    assert records[0].value == 328
    assert records[2].value is None
    assert records[2].geo_grain == "state"
