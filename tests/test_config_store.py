"""
Tests for the Config layer — Pydantic models and validation.
"""

from __future__ import annotations

import pytest

from src.config.models import (
    DimensionWeights,
    ScoringConfig,
    OnTimeDefinition,
    OnTimeMethod,
    TierBoundary,
    AlertConfig,
    AlertRule,
    AlertSeverityLevel,
)
from src.config.defaults import DEFAULT_SCORING_CONFIG, DEFAULT_ALERT_CONFIG


class TestDimensionWeights:
    """Test weight validation."""

    def test_valid_weights(self):
        w = DimensionWeights(
            quality=25, pricing=20, delivery=25,
            communication=15, reliability=15
        )
        assert w.quality == 25

    def test_weights_must_sum_to_100(self):
        with pytest.raises(ValueError, match="sum to 100"):
            DimensionWeights(
                quality=30, pricing=30, delivery=30,
                communication=30, reliability=30
            )

    def test_weights_zero_allowed(self):
        w = DimensionWeights(
            quality=50, pricing=50, delivery=0,
            communication=0, reliability=0
        )
        assert w.delivery == 0

    def test_negative_weight_rejected(self):
        with pytest.raises(ValueError):
            DimensionWeights(
                quality=-10, pricing=40, delivery=30,
                communication=20, reliability=20
            )


class TestScoringConfig:
    """Test scoring config validation."""

    def test_default_config_valid(self):
        assert DEFAULT_SCORING_CONFIG.weights.quality == 25
        assert DEFAULT_SCORING_CONFIG.current_window_days == 90

    def test_tiers_must_be_ordered(self):
        with pytest.raises(ValueError, match="ordered"):
            ScoringConfig(
                weights=DimensionWeights(
                    quality=25, pricing=20, delivery=25,
                    communication=15, reliability=15
                ),
                tiers=[
                    TierBoundary(name="Low", min_score=0),
                    TierBoundary(name="High", min_score=90),  # Out of order
                ],
            )

    def test_on_time_grace_window(self):
        config = DEFAULT_SCORING_CONFIG
        assert config.on_time.method == OnTimeMethod.GRACE_WINDOW
        assert config.on_time.grace_days == 2


class TestAlertConfig:
    """Test alert config validation."""

    def test_default_alert_config_valid(self):
        assert len(DEFAULT_ALERT_CONFIG.rules) > 0
        for rule in DEFAULT_ALERT_CONFIG.rules:
            assert rule.rule_type in {"delay", "price", "quality", "communication", "composite"}

    def test_alert_rule_creation(self):
        rule = AlertRule(
            rule_type="delay",
            description="Test rule",
            threshold_value=5,
            window_days=30,
            count_threshold=3,
            severity=AlertSeverityLevel.HIGH,
        )
        assert rule.enabled is True
        assert rule.severity == AlertSeverityLevel.HIGH
