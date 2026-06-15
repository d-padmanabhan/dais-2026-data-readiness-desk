"""
Expose reusable helpers for the Data Readiness Desk project.

The package keeps parsing, readiness, and scoring logic outside notebooks so the
core behavior can be tested locally and reused by Databricks jobs or app code.
"""

from data_readiness_desk.hmis import (
    HmisLongRecord,
    HmisMeasureColumn,
    clean_hmis_text,
    hmis_rows_to_long_records,
    parse_hmis_measure_column,
    parse_hmis_number,
    validate_hmis_header,
)
from data_readiness_desk.normalization import ParsedIndicator, normalize_place_name, parse_nfhs_indicator, to_snake_case
from data_readiness_desk.readiness import PincodeOffice, PincodeReadiness, build_pincode_readiness
from data_readiness_desk.scoring import DimensionScore, ScoringConfig, TrustVerdict, VerdictBand, compute_trust_verdict

__all__ = [
    "DimensionScore",
    "HmisLongRecord",
    "HmisMeasureColumn",
    "ParsedIndicator",
    "PincodeOffice",
    "PincodeReadiness",
    "ScoringConfig",
    "TrustVerdict",
    "VerdictBand",
    "build_pincode_readiness",
    "clean_hmis_text",
    "compute_trust_verdict",
    "hmis_rows_to_long_records",
    "normalize_place_name",
    "parse_hmis_measure_column",
    "parse_hmis_number",
    "parse_nfhs_indicator",
    "to_snake_case",
    "validate_hmis_header",
]
