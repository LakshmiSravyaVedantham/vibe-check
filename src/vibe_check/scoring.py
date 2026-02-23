"""Aggregate detector scores into a final 0-100 vibe score."""

from dataclasses import dataclass, field
from typing import Dict, List

# Detector weights must sum to 1.0
DETECTOR_WEIGHTS: Dict[str, float] = {
    "security": 0.25,
    "repetitive": 0.15,
    "naming": 0.15,
    "imports": 0.15,
    "comments": 0.10,
    "placeholders": 0.10,
    "ratio": 0.10,
}

# Vibe score thresholds
SCORE_LABELS = [
    (80, "EXTREMELY VIBED", "red"),
    (60, "HEAVILY VIBED", "red"),
    (40, "MODERATELY VIBED", "yellow"),
    (20, "SLIGHTLY VIBED", "yellow"),
    (0, "MOSTLY HUMAN", "green"),
]


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of the vibe score computation."""

    final_score: int  # 0-100
    weighted_scores: Dict[str, float] = field(default_factory=dict)
    raw_scores: Dict[str, float] = field(default_factory=dict)
    label: str = ""
    label_color: str = "white"

    def __post_init__(self) -> None:
        if not self.label:
            self.label, self.label_color = get_score_label(self.final_score)


def get_score_label(score: int) -> tuple:
    """Return (label, color) string for a given score."""
    for threshold, label, color in SCORE_LABELS:
        if score >= threshold:
            return label, color
    return "MOSTLY HUMAN", "green"


def compute_vibe_score(detector_scores: Dict[str, float]) -> ScoreBreakdown:
    """
    Compute the final vibe score from individual detector scores.

    Args:
        detector_scores: Dict mapping detector name -> raw score (0.0 - 1.0)

    Returns:
        ScoreBreakdown with final 0-100 score and per-detector breakdown
    """
    if not detector_scores:
        label, color = get_score_label(0)
        return ScoreBreakdown(
            final_score=0,
            weighted_scores={},
            raw_scores={},
            label=label,
            label_color=color,
        )

    weighted_scores: Dict[str, float] = {}
    total_weighted = 0.0
    total_weight_used = 0.0

    for detector_name, raw_score in detector_scores.items():
        weight = DETECTOR_WEIGHTS.get(detector_name, 0.05)
        weighted = raw_score * weight
        weighted_scores[detector_name] = weighted
        total_weighted += weighted
        total_weight_used += weight

    # Normalize by the total weight actually used (handles missing detectors)
    if total_weight_used > 0:
        normalized = total_weighted / total_weight_used
    else:
        normalized = 0.0

    final_score = int(round(normalized * 100))
    final_score = max(0, min(100, final_score))

    label, color = get_score_label(final_score)

    return ScoreBreakdown(
        final_score=final_score,
        weighted_scores=weighted_scores,
        raw_scores=dict(detector_scores),
        label=label,
        label_color=color,
    )


def aggregate_repo_score(file_scores: List[int]) -> int:
    """
    Compute an aggregate score across a repo.

    Uses weighted average with higher scores weighted more heavily
    to surface problematic files.
    """
    if not file_scores:
        return 0

    # Weight higher scores more — a few highly vibed files pull up the average
    weighted_sum = sum(s**1.5 for s in file_scores)
    weight_total = sum(100**1.5 for _ in file_scores)

    if weight_total == 0:
        return 0

    normalized = weighted_sum / weight_total
    return int(round(normalized * 100))
