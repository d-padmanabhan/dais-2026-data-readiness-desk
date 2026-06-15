"""
Build source-readiness summaries without Spark dependencies.

The helpers in this module support local tests and documentation examples for
the PIN-code readiness logic. Databricks notebooks implement the same concepts
with Spark dataframes, while these functions make the row-grain behavior easy
to verify without cluster compute.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from data_readiness_desk.normalization import normalize_place_name


@dataclass(frozen=True)
class PincodeOffice:
    """
    Post-office grain record from the PIN code directory.

    Args:
        pincode: Six-digit postal index number.
        district: Source district name.
        state: Source state name.
        has_coordinates: Whether the source row has usable latitude and longitude.
    """

    pincode: str
    district: str
    state: str
    has_coordinates: bool


# Flat fields mirror the one-row-per-PIN readiness contract.
@dataclass(frozen=True)
class PincodeReadiness:  # pylint: disable=too-many-instance-attributes
    """
    One-row-per-PIN readiness summary.

    Args:
        pincode: Six-digit postal index number.
        post_office_count: Number of source post-office rows for the PIN.
        district_count: Number of normalized districts represented by the PIN.
        state_count: Number of normalized states represented by the PIN.
        geocoded_office_count: Number of post-office rows with coordinates.
        is_geography_ambiguous: Whether the PIN maps to multiple districts or states.
        representative_district_normalized: Single district when unambiguous, otherwise None.
        representative_state_normalized: Single state when unambiguous, otherwise None.
    """

    pincode: str
    post_office_count: int
    district_count: int
    state_count: int
    geocoded_office_count: int
    is_geography_ambiguous: bool
    representative_district_normalized: str | None
    representative_state_normalized: str | None


def build_pincode_readiness(rows: Iterable[PincodeOffice]) -> list[PincodeReadiness]:
    """
    Aggregate post-office rows into join-safe PIN readiness summaries.

    Args:
        rows: Post-office grain rows.

    Returns:
        One readiness summary per PIN code.
    """
    grouped: dict[str, list[PincodeOffice]] = defaultdict(list)
    for row in rows:
        grouped[row.pincode].append(row)

    summaries: list[PincodeReadiness] = []
    for pincode, offices in sorted(grouped.items()):
        districts = {normalize_place_name(office.district) for office in offices}
        states = {normalize_place_name(office.state) for office in offices}
        districts.discard(None)
        states.discard(None)
        is_ambiguous = len(districts) > 1 or len(states) > 1
        summaries.append(
            PincodeReadiness(
                pincode=pincode,
                post_office_count=len(offices),
                district_count=len(districts),
                state_count=len(states),
                geocoded_office_count=sum(1 for office in offices if office.has_coordinates),
                is_geography_ambiguous=is_ambiguous,
                representative_district_normalized=next(iter(districts)) if not is_ambiguous and districts else None,
                representative_state_normalized=next(iter(states)) if not is_ambiguous and states else None,
            )
        )
    return summaries
