"""Tests for source-specific normalization helpers."""

from data_readiness_desk.normalization import normalize_place_name, parse_nfhs_indicator, to_snake_case


def test_to_snake_case_handles_human_readable_indicator_names() -> None:
    """Column names become stable snake_case identifiers."""
    assert to_snake_case("Women (age 15-49 years) who are anaemic (%)") == (
        "women_age_15_49_years_who_are_anaemic_percent"
    )


def test_normalize_place_name_removes_case_and_punctuation_noise() -> None:
    """Place normalization removes casing, spacing, and punctuation noise."""
    assert normalize_place_name("  South-West & Delhi ") == "southwest and delhi"


def test_parse_nfhs_indicator_treats_suppressed_as_null() -> None:
    """Suppressed NFHS values are null and flagged."""
    parsed = parse_nfhs_indicator("*")

    assert parsed.value is None
    assert parsed.is_suppressed is True
    assert parsed.is_low_sample_estimate is False


def test_parse_nfhs_indicator_flags_parenthesized_low_sample_estimate() -> None:
    """Parenthesized NFHS values become flagged low-sample estimates."""
    parsed = parse_nfhs_indicator("(29.5)")

    assert parsed.value == 29.5
    assert parsed.is_suppressed is False
    assert parsed.is_low_sample_estimate is True


def test_parse_nfhs_indicator_extracts_numeric_values() -> None:
    """Plain numeric NFHS values parse to floats."""
    parsed = parse_nfhs_indicator("72.4")

    assert parsed.value == 72.4
    assert parsed.is_suppressed is False
    assert parsed.is_low_sample_estimate is False
