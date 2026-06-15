#!/usr/bin/env -S uv run

"""
Generate `srs_2020_state.csv` from SRS Bulletin 2020 Table 1.

The SRS bulletin PDF is not machine-tabular in this repository, so this script
encodes Table 1 from `SRS_Bulletin_2020_Vol_55_No_1.pdf` into a deterministic
CSV. Keeping this as a script instead of a checked-in generated CSV makes the
source and transformation easy to inspect during the hackathon.

Workflow:
1. Validate that the source PDF path exists.
2. Write Table 1 values to a CSV file with explicit metric columns.
3. Preserve missing values such as `NA*` as blank fields with an explanatory note.

Usage:
    scripts/generate_srs_2020_state_csv.py
    scripts/generate_srs_2020_state_csv.py --output data/srs_2020_state.csv
    scripts/generate_srs_2020_state_csv.py --source-pdf data/SRS_Bulletin_2020_Vol_55_No_1.pdf
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
# Flat fields mirror SRS Bulletin Table 1 output columns.
class SrsTableOneRow:  # pylint: disable=too-many-instance-attributes
    """
    SRS Bulletin 2020 Table 1 row.

    Args:
        state: India, state, or union territory name.
        category: Source table grouping.
        birth_rate_total: Birth rate for total population.
        birth_rate_rural: Birth rate for rural population.
        birth_rate_urban: Birth rate for urban population.
        death_rate_total: Death rate for total population.
        death_rate_rural: Death rate for rural population.
        death_rate_urban: Death rate for urban population.
        natural_growth_rate_total: Natural growth rate for total population.
        natural_growth_rate_rural: Natural growth rate for rural population.
        natural_growth_rate_urban: Natural growth rate for urban population.
        infant_mortality_rate_total: Infant mortality rate for total population.
        infant_mortality_rate_rural: Infant mortality rate for rural population.
        infant_mortality_rate_urban: Infant mortality rate for urban population.
        note: Source note for missing or caveated values.
    """

    state: str
    category: str
    birth_rate_total: float
    birth_rate_rural: float
    birth_rate_urban: float
    death_rate_total: float
    death_rate_rural: float
    death_rate_urban: float
    natural_growth_rate_total: float
    natural_growth_rate_rural: float
    natural_growth_rate_urban: float
    infant_mortality_rate_total: int
    infant_mortality_rate_rural: int
    infant_mortality_rate_urban: int | None
    note: str = ""


TABLE_ONE_ROWS = [
    SrsTableOneRow("India", "India", 19.5, 21.1, 16.1, 6.0, 6.4, 5.1, 13.5, 14.7, 11.0, 28, 31, 19),
    SrsTableOneRow(
        "Andhra Pradesh", "Bigger States/Union Territories", 15.7, 16.0, 15.0, 6.3, 7.0, 4.9, 9.3, 9.0, 10.1, 24, 26, 18
    ),
    SrsTableOneRow(
        "Assam", "Bigger States/Union Territories", 20.8, 21.9, 14.3, 6.2, 6.4, 5.4, 14.5, 15.5, 8.9, 36, 39, 17
    ),
    SrsTableOneRow(
        "Bihar", "Bigger States/Union Territories", 25.5, 26.2, 21.0, 5.4, 5.5, 5.2, 20.0, 20.7, 15.7, 27, 27, 25
    ),
    SrsTableOneRow(
        "Chhattisgarh", "Bigger States/Union Territories", 22.0, 23.4, 17.3, 7.9, 8.4, 6.3, 14.1, 15.0, 11.0, 38, 40, 31
    ),
    SrsTableOneRow(
        "NCT of Delhi", "Bigger States/Union Territories", 14.2, 15.5, 14.1, 3.6, 4.1, 3.5, 10.6, 11.4, 10.6, 12, 20, 12
    ),
    SrsTableOneRow(
        "Gujarat", "Bigger States/Union Territories", 19.3, 21.1, 17.1, 5.6, 6.0, 5.0, 13.7, 15.1, 12.0, 23, 27, 17
    ),
    SrsTableOneRow(
        "Haryana", "Bigger States/Union Territories", 19.9, 21.2, 17.7, 6.1, 6.5, 5.5, 13.8, 14.7, 12.3, 28, 31, 23
    ),
    SrsTableOneRow(
        "Jammu & Kashmir",
        "Bigger States/Union Territories",
        14.6,
        16.1,
        11.1,
        4.6,
        4.9,
        4.1,
        10.0,
        11.3,
        7.0,
        17,
        18,
        13,
    ),
    SrsTableOneRow(
        "Jharkhand", "Bigger States/Union Territories", 22.0, 23.4, 17.6, 5.2, 5.5, 4.5, 16.7, 17.9, 13.1, 25, 26, 21
    ),
    SrsTableOneRow(
        "Karnataka", "Bigger States/Union Territories", 16.5, 17.5, 15.0, 6.2, 7.1, 4.8, 10.4, 10.5, 10.2, 19, 21, 16
    ),
    SrsTableOneRow(
        "Kerala", "Bigger States/Union Territories", 13.2, 13.1, 13.3, 7.0, 7.0, 7.1, 6.2, 6.1, 6.3, 6, 4, 9
    ),
    SrsTableOneRow(
        "Madhya Pradesh",
        "Bigger States/Union Territories",
        24.1,
        26.0,
        18.8,
        6.5,
        6.8,
        5.6,
        17.6,
        19.2,
        13.1,
        43,
        47,
        30,
    ),
    SrsTableOneRow(
        "Maharashtra", "Bigger States/Union Territories", 15.0, 15.3, 14.6, 5.5, 6.2, 4.6, 9.6, 9.1, 10.1, 16, 20, 11
    ),
    SrsTableOneRow(
        "Odisha", "Bigger States/Union Territories", 17.7, 18.7, 13.1, 7.3, 7.5, 6.5, 10.4, 11.2, 6.6, 36, 37, 28
    ),
    SrsTableOneRow(
        "Punjab", "Bigger States/Union Territories", 14.3, 14.9, 13.6, 7.2, 8.3, 5.7, 7.1, 6.6, 7.9, 18, 19, 17
    ),
    SrsTableOneRow(
        "Rajasthan", "Bigger States/Union Territories", 23.5, 24.4, 20.8, 5.6, 5.8, 5.1, 17.9, 18.6, 15.7, 32, 35, 23
    ),
    SrsTableOneRow(
        "Tamil Nadu", "Bigger States/Union Territories", 13.8, 14.0, 13.6, 6.1, 7.2, 5.1, 7.7, 6.8, 8.5, 13, 15, 10
    ),
    SrsTableOneRow(
        "Telangana", "Bigger States/Union Territories", 16.4, 16.8, 15.9, 6.0, 7.2, 4.2, 10.4, 9.6, 11.7, 21, 24, 17
    ),
    SrsTableOneRow(
        "Uttar Pradesh",
        "Bigger States/Union Territories",
        25.1,
        26.1,
        22.1,
        6.5,
        6.8,
        5.4,
        18.7,
        19.3,
        16.7,
        38,
        40,
        28,
    ),
    SrsTableOneRow(
        "Uttarakhand", "Bigger States/Union Territories", 16.6, 17.0, 15.6, 6.3, 6.7, 5.1, 10.4, 10.3, 10.5, 24, 25, 24
    ),
    SrsTableOneRow(
        "West Bengal", "Bigger States/Union Territories", 14.6, 16.1, 11.2, 5.5, 5.3, 5.8, 9.1, 10.8, 5.4, 19, 19, 17
    ),
    SrsTableOneRow(
        "Arunachal Pradesh", "Smaller States", 17.3, 17.8, 15.0, 5.7, 5.9, 4.4, 11.6, 11.8, 10.6, 21, 22, 13
    ),
    SrsTableOneRow("Goa", "Smaller States", 12.1, 11.7, 12.4, 5.9, 6.3, 5.5, 6.2, 5.3, 6.9, 5, 7, 3),
    SrsTableOneRow("Himachal Pradesh", "Smaller States", 15.3, 15.7, 10.0, 6.8, 7.0, 4.4, 8.5, 8.7, 5.6, 17, 18, 15),
    SrsTableOneRow("Manipur", "Smaller States", 13.3, 13.5, 12.8, 4.3, 4.0, 4.8, 9.0, 9.5, 8.0, 6, 6, 5),
    SrsTableOneRow("Meghalaya", "Smaller States", 22.9, 25.1, 12.9, 5.3, 5.5, 4.4, 17.6, 19.6, 8.5, 29, 30, 16),
    SrsTableOneRow("Mizoram", "Smaller States", 14.4, 16.8, 11.7, 4.2, 3.8, 4.6, 10.2, 13.0, 7.1, 3, 3, 3),
    SrsTableOneRow(
        "Nagaland",
        "Smaller States",
        12.5,
        12.9,
        11.8,
        3.7,
        3.9,
        3.5,
        8.8,
        9.0,
        8.4,
        4,
        7,
        None,
        "urban IMR unavailable; no infant death recorded in sample units",
    ),
    SrsTableOneRow("Sikkim", "Smaller States", 15.6, 14.0, 18.2, 4.1, 4.3, 3.7, 11.6, 9.7, 14.5, 5, 8, 1),
    SrsTableOneRow("Tripura", "Smaller States", 12.6, 13.4, 10.7, 5.7, 5.4, 6.5, 6.9, 8.0, 4.2, 18, 18, 17),
    SrsTableOneRow(
        "Andaman & Nicobar Islands", "Union Territories", 10.8, 11.5, 10.0, 5.8, 6.8, 4.5, 5.0, 4.7, 5.4, 7, 7, 6
    ),
    SrsTableOneRow("Chandigarh", "Union Territories", 12.9, 18.1, 12.8, 3.9, 4.0, 3.8, 9.1, 14.0, 9.0, 8, 9, 8),
    SrsTableOneRow(
        "Dadra & Nagar Haveli and Daman & Diu",
        "Union Territories",
        20.3,
        18.0,
        21.4,
        3.7,
        4.7,
        3.3,
        16.5,
        13.3,
        18.1,
        16,
        15,
        11,
    ),
    SrsTableOneRow("Ladakh", "Union Territories", 14.3, 15.2, 10.8, 5.0, 5.2, 4.4, 9.3, 10.0, 6.5, 16, 17, 12),
    SrsTableOneRow("Lakshadweep", "Union Territories", 14.5, 19.9, 13.1, 5.4, 7.2, 5.0, 9.1, 12.7, 8.1, 9, 19, 5),
    SrsTableOneRow("Puducherry", "Union Territories", 13.1, 13.1, 13.1, 6.5, 7.5, 6.1, 6.6, 5.6, 7.0, 6, 8, 5),
]


def row_to_csv_dict(row: SrsTableOneRow) -> dict[str, object]:
    """
    Convert an SRS row to CSV output fields.

    Args:
        row: SRS Table 1 row.

    Returns:
        Dictionary suitable for `csv.DictWriter`.
    """
    return row.__dict__


def write_srs_csv(output_path: Path) -> None:
    """
    Write the SRS table rows to CSV.

    Args:
        output_path: Destination CSV file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(row_to_csv_dict(TABLE_ONE_ROWS[0]).keys())
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in TABLE_ONE_ROWS:
            writer.writerow(row_to_csv_dict(row))


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Generate SRS 2020 state CSV from Bulletin Table 1 values.")
    parser.add_argument("--source-pdf", type=Path, default=Path("data/SRS_Bulletin_2020_Vol_55_No_1.pdf"))
    parser.add_argument("--output", type=Path, default=Path("data/srs_2020_state.csv"))
    return parser.parse_args()


def main() -> int:
    """
    Validate source PDF presence and generate the SRS CSV.

    Returns:
        Process exit code.
    """
    args = parse_args()
    if not args.source_pdf.exists():
        raise FileNotFoundError(f"Source PDF not found: {args.source_pdf}")
    write_srs_csv(args.output)
    print(f"Wrote {len(TABLE_ONE_ROWS)} rows to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
