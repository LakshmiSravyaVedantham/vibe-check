"""Tests for the scoring module."""

from vibe_check.scoring import (
    DETECTOR_WEIGHTS,
    ScoreBreakdown,
    aggregate_repo_score,
    compute_vibe_score,
    get_score_label,
)


class TestComputeVibeScore:
    def test_all_zero_scores_gives_zero(self):
        detector_scores = {name: 0.0 for name in DETECTOR_WEIGHTS}
        result = compute_vibe_score(detector_scores)
        assert result.final_score == 0
        assert result.label == "MOSTLY HUMAN"

    def test_all_max_scores_gives_100(self):
        detector_scores = {name: 1.0 for name in DETECTOR_WEIGHTS}
        result = compute_vibe_score(detector_scores)
        assert result.final_score == 100

    def test_empty_scores_gives_zero(self):
        result = compute_vibe_score({})
        assert result.final_score == 0
        assert result.label == "MOSTLY HUMAN"

    def test_security_has_highest_weight(self):
        # Verify the weight configuration directly
        assert DETECTOR_WEIGHTS["security"] > DETECTOR_WEIGHTS["naming"]

    def test_score_is_bounded_0_to_100(self):
        detector_scores = {"security": 1.5, "naming": 2.0}
        result = compute_vibe_score(detector_scores)
        assert 0 <= result.final_score <= 100

    def test_partial_detectors_still_works(self):
        scores = {"security": 0.5, "naming": 0.8}
        result = compute_vibe_score(scores)
        assert isinstance(result.final_score, int)
        assert 0 <= result.final_score <= 100
        valid_labels = ["MOSTLY HUMAN", "SLIGHTLY VIBED", "MODERATELY VIBED", "HEAVILY VIBED", "EXTREMELY VIBED"]
        assert result.label in valid_labels

    def test_returns_score_breakdown_type(self):
        scores = {"security": 0.3, "naming": 0.2}
        result = compute_vibe_score(scores)
        assert isinstance(result, ScoreBreakdown)
        assert isinstance(result.final_score, int)
        assert isinstance(result.weighted_scores, dict)
        assert isinstance(result.raw_scores, dict)

    def test_mid_range_score_gives_correct_label(self):
        # Force a score around 50
        scores = {name: 0.5 for name in DETECTOR_WEIGHTS}
        result = compute_vibe_score(scores)
        assert result.final_score == 50
        assert result.label == "MODERATELY VIBED"


class TestGetScoreLabel:
    def test_zero_is_mostly_human(self):
        label, color = get_score_label(0)
        assert label == "MOSTLY HUMAN"
        assert color == "green"

    def test_10_is_mostly_human(self):
        label, color = get_score_label(10)
        assert label == "MOSTLY HUMAN"
        assert color == "green"

    def test_20_is_slightly_vibed(self):
        label, color = get_score_label(20)
        assert label == "SLIGHTLY VIBED"

    def test_40_is_moderately_vibed(self):
        label, color = get_score_label(40)
        assert label == "MODERATELY VIBED"

    def test_60_is_heavily_vibed(self):
        label, color = get_score_label(60)
        assert label == "HEAVILY VIBED"

    def test_80_is_extremely_vibed(self):
        label, color = get_score_label(80)
        assert label == "EXTREMELY VIBED"
        assert color == "red"

    def test_100_is_extremely_vibed(self):
        label, color = get_score_label(100)
        assert label == "EXTREMELY VIBED"


class TestAggregateRepoScore:
    def test_empty_list_returns_zero(self):
        assert aggregate_repo_score([]) == 0

    def test_all_zero_scores(self):
        assert aggregate_repo_score([0, 0, 0]) == 0

    def test_all_hundred_scores(self):
        result = aggregate_repo_score([100, 100, 100])
        assert result == 100

    def test_mixed_scores_weighted_toward_high(self):
        # A single very high score should pull the average up
        low_avg = aggregate_repo_score([10, 10, 10, 10])
        high_pull = aggregate_repo_score([10, 10, 10, 90])
        assert high_pull > low_avg

    def test_single_score(self):
        result = aggregate_repo_score([75])
        assert 0 <= result <= 100
