"""Tests for Trust Verdict scoring helpers."""

from __future__ import annotations

import pytest

from data_readiness_desk.scoring import DimensionScore, VerdictBand, compute_trust_verdict


def test_compute_trust_verdict_caps_green_when_dimension_is_amber() -> None:
    """Weakest-link capping prevents a high average from hiding an amber dimension."""
    verdict = compute_trust_verdict(
        [
            DimensionScore("completeness", 1.0),
            DimensionScore("corroboration", 0.7),
            DimensionScore("provenance", 1.0),
        ]
    )

    assert verdict.numeric_score == 0.9
    assert verdict.band == VerdictBand.AMBER
    assert verdict.binding_dimension == "corroboration"


def test_compute_trust_verdict_caps_missingness_at_amber() -> None:
    """Missing or low-confidence data can never produce a green verdict."""
    verdict = compute_trust_verdict(
        [
            DimensionScore("completeness", 1.0),
            DimensionScore("nfhs_quality", 0.95, missing_or_low_confidence=True),
        ]
    )

    assert verdict.band == VerdictBand.AMBER


def test_compute_trust_verdict_rejects_empty_dimensions() -> None:
    """At least one scored dimension is required."""
    with pytest.raises(ValueError, match="At least one dimension"):
        compute_trust_verdict([])


def test_compute_trust_verdict_rejects_out_of_range_scores() -> None:
    """Dimension scores must be normalized before scoring."""
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        compute_trust_verdict([DimensionScore("bad_score", 1.2)])
