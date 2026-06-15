"""
Compute Trust Verdict scores for the Data Readiness Desk.

The scoring helpers implement the conservative product rule from the requirements:
numeric scores are weighted averages, while display bands are capped by the
weakest dimension and by missing or low-confidence evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class VerdictBand(StrEnum):
    """
    Display bands for trust verdicts.

    Values:
        GREEN: Data is strong enough for the requested planning use.
        AMBER: Data can be used with caveats or requires follow-up.
        RED: Data is not trustworthy enough for the requested planning use.
    """

    GREEN = "green"
    AMBER = "amber"
    RED = "red"


@dataclass(frozen=True)
class ScoringConfig:
    """
    Tunable score thresholds.

    Args:
        green_min: Minimum numeric score for a green band.
        amber_min: Minimum numeric score for an amber band.
    """

    green_min: float = 0.85
    amber_min: float = 0.60


@dataclass(frozen=True)
class DimensionScore:
    """
    A scored trust dimension.

    Args:
        name: Dimension name shown in the verdict reason.
        score: Numeric score in the inclusive range 0.0 to 1.0.
        missing_or_low_confidence: Whether this dimension must cap the band at amber.
    """

    name: str
    score: float
    missing_or_low_confidence: bool = False


DEFAULT_SCORING_CONFIG = ScoringConfig()


@dataclass(frozen=True)
class TrustVerdict:
    """
    Trust verdict shown by the app.

    Args:
        band: Green, amber, or red display band.
        numeric_score: Weighted score across dimensions.
        binding_dimension: Dimension causing the strongest trust constraint.
        reason: One-line human-readable explanation.
    """

    band: VerdictBand
    numeric_score: float
    binding_dimension: str
    reason: str


def band_for_score(score: float, config: ScoringConfig = DEFAULT_SCORING_CONFIG) -> VerdictBand:
    """
    Convert a numeric score to a band.

    Args:
        score: Numeric score in the inclusive range 0.0 to 1.0.
        config: Score threshold configuration.

    Returns:
        Verdict band for the score.
    """
    if score >= config.green_min:
        return VerdictBand.GREEN
    if score >= config.amber_min:
        return VerdictBand.AMBER
    return VerdictBand.RED


def cap_band(current: VerdictBand, cap: VerdictBand) -> VerdictBand:
    """
    Apply a weakest-link cap to a verdict band.

    Args:
        current: Current band.
        cap: Maximum allowed band.

    Returns:
        Band no stronger than the cap.
    """
    order = {
        VerdictBand.RED: 0,
        VerdictBand.AMBER: 1,
        VerdictBand.GREEN: 2,
    }
    return current if order[current] <= order[cap] else cap


def compute_trust_verdict(
    dimensions: list[DimensionScore],
    weights: dict[str, float] | None = None,
    config: ScoringConfig = DEFAULT_SCORING_CONFIG,
) -> TrustVerdict:
    """
    Compute a conservative Trust Verdict.

    Args:
        dimensions: Dimension scores for an entity/question.
        weights: Optional per-dimension weights. Missing weights default to 1.0.
        config: Score threshold configuration.

    Returns:
        Trust verdict with a numeric score and binding reason.

    Raises:
        ValueError: If no dimensions are supplied or a dimension score is out of range.
    """
    if not dimensions:
        raise ValueError("At least one dimension is required to compute a trust verdict")

    weights = weights or {}
    weighted_total = 0.0
    weight_total = 0.0
    for dimension in dimensions:
        if dimension.score < 0.0 or dimension.score > 1.0:
            raise ValueError(f"Dimension {dimension.name} score must be between 0.0 and 1.0")
        weight = weights.get(dimension.name, 1.0)
        weighted_total += dimension.score * weight
        weight_total += weight

    numeric_score = weighted_total / weight_total
    binding_dimension = min(dimensions, key=lambda dimension: dimension.score)
    band = band_for_score(numeric_score, config)
    band = cap_band(band, band_for_score(binding_dimension.score, config))

    if any(dimension.missing_or_low_confidence for dimension in dimensions):
        band = cap_band(band, VerdictBand.AMBER)

    reason = f"{band.value.title()} - {binding_dimension.name}: binding trust constraint"
    return TrustVerdict(
        band=band,
        numeric_score=round(numeric_score, 4),
        binding_dimension=binding_dimension.name,
        reason=reason,
    )
