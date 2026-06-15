"""
Normalize public-sector source fields for the Data Readiness Desk.

This module contains pure Python helpers used by tests and notebook-adjacent
code. It intentionally avoids Spark dependencies so value parsing and naming
rules can be validated locally before running Databricks jobs.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_NON_ALNUM_RE = re.compile(r"[^0-9a-zA-Z]+")
_MULTI_UNDERSCORE_RE = re.compile(r"_+")
_LOW_SAMPLE_RE = re.compile(r"^\((?P<value>[-+]?\d+(?:\.\d+)?)\)$")
_NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")


@dataclass(frozen=True)
class ParsedIndicator:
    """
    Parsed NFHS indicator value and quality flags.

    Args:
        raw_value: Original source cell text, or None when the source is null.
        value: Parsed numeric value, or None when unavailable.
        is_suppressed: Whether the source value was an NFHS suppressed marker.
        is_low_sample_estimate: Whether the value came from a parenthesized low-sample estimate.
    """

    raw_value: str | None
    value: float | None
    is_suppressed: bool
    is_low_sample_estimate: bool


def to_snake_case(value: str) -> str:
    """
    Convert a human-readable column name to stable snake_case.

    Args:
        value: Source column name.

    Returns:
        ASCII snake_case column name safe for Delta table fields.
    """
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.replace("%", " percent ")
    normalized = normalized.replace("&", " and ")
    normalized = _NON_ALNUM_RE.sub("_", normalized.lower())
    normalized = _MULTI_UNDERSCORE_RE.sub("_", normalized).strip("_")
    return normalized or "unnamed_column"


def normalize_place_name(value: str | None) -> str | None:
    """
    Normalize district and state strings for approximate joins and grouping.

    Args:
        value: Source place name.

    Returns:
        Normalized place name, or None when the input is empty.
    """
    if value is None:
        return None

    cleaned = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    cleaned = cleaned.strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.replace("&", "and")
    cleaned = re.sub(r"[^0-9a-z ]+", "", cleaned)
    return cleaned or None


def parse_nfhs_indicator(value: object) -> ParsedIndicator:
    """
    Parse NFHS indicator cells.

    Rules:
    - `*` and empty values are unavailable and become null
    - `(29.5)` becomes 29.5 and is flagged as a low-sample estimate
    - numeric strings become floats
    - non-numeric cells become null without being marked suppressed

    Args:
        value: Raw NFHS cell value.

    Returns:
        Parsed indicator value and quality flags.
    """
    if value is None:
        return ParsedIndicator(None, None, False, False)

    raw_value = str(value).strip()
    if raw_value == "":
        return ParsedIndicator(raw_value, None, False, False)

    if raw_value == "*":
        return ParsedIndicator(raw_value, None, True, False)

    low_sample_match = _LOW_SAMPLE_RE.match(raw_value)
    if low_sample_match:
        return ParsedIndicator(raw_value, float(low_sample_match.group("value")), False, True)

    number_match = _NUMBER_RE.search(raw_value.replace(",", ""))
    if number_match:
        return ParsedIndicator(raw_value, float(number_match.group(0)), False, False)

    return ParsedIndicator(raw_value, None, False, False)
