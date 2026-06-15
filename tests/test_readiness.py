"""Tests for data-readiness aggregation helpers."""

from __future__ import annotations

import csv
from pathlib import Path

from data_readiness_desk.readiness import PincodeOffice, build_pincode_readiness


def load_fixture_rows() -> list[PincodeOffice]:
    """Load post-office fixture rows."""
    fixture_path = Path(__file__).parent / "fixtures" / "pincode_directory_sample.csv"
    with fixture_path.open(newline="") as handle:
        return [
            PincodeOffice(
                pincode=row["pincode"],
                district=row["district"],
                state=row["statename"],
                has_coordinates=row["latitude"] != "NA" and row["longitude"] != "NA",
            )
            for row in csv.DictReader(handle)
        ]


def test_build_pincode_readiness_flags_ambiguous_geography() -> None:
    """A PIN with multiple districts is flagged ambiguous."""
    summaries = {summary.pincode: summary for summary in build_pincode_readiness(load_fixture_rows())}

    ambiguous = summaries["110001"]

    assert ambiguous.post_office_count == 2
    assert ambiguous.district_count == 2
    assert ambiguous.state_count == 1
    assert ambiguous.geocoded_office_count == 1
    assert ambiguous.is_geography_ambiguous is True
    assert ambiguous.representative_district_normalized is None
    assert ambiguous.representative_state_normalized is None


def test_build_pincode_readiness_preserves_unambiguous_representative_geography() -> None:
    """A single-district PIN keeps representative geography."""
    summaries = {summary.pincode: summary for summary in build_pincode_readiness(load_fixture_rows())}

    unambiguous = summaries["560001"]

    assert unambiguous.post_office_count == 1
    assert unambiguous.is_geography_ambiguous is False
    assert unambiguous.representative_district_normalized == "bengaluru urban"
    assert unambiguous.representative_state_normalized == "karnataka"
