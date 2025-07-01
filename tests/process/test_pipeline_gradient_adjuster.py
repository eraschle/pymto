"""Tests for pipeline gradient adjustment with medium compatibility."""

import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dxfto.models import ObjectData, ObjectType, Point3D, RoundDimensions
from dxfto.process.gradient_adjuster import (
    ExplicitRulesCompatibility,
    GradientAdjustmentParams,
    PatternBasedCompatibility,
    PipelineGradientAdjuster,
    PrefixBasedCompatibility,
)


class TestMediumCompatibilityStrategies:
    """Test different medium compatibility strategies."""

    def test_prefix_based_compatibility(self):
        """Test prefix-based compatibility checking."""
        strategy = PrefixBasedCompatibility(separator=" ")

        # Same prefix - compatible
        assert strategy.are_compatible("Regenabwasser Gemeinde", "Regenabwasser Privat")
        assert strategy.are_compatible("Abwasser Gemeinde", "Abwasser Privat")

        # Different prefix - incompatible
        assert not strategy.are_compatible("Regenabwasser Gemeinde", "Abwasser Privat")
        assert not strategy.are_compatible("Wasser Gemeinde", "Gas Privat")

        # Exact match - compatible
        assert strategy.are_compatible("Wasser", "Wasser")

        # Prefix extraction
        assert strategy.get_medium_prefix("Regenabwasser Gemeinde") == "Regenabwasser"
        assert strategy.get_medium_prefix("Wasser") == "Wasser"
        assert strategy.get_group("Regenabwasser Privat") == "Regenabwasser"

    def test_explicit_rules_compatibility(self):
        """Test explicit rules-based compatibility."""
        rules = {
            "Regenabwasser Gemeinde": ["Regenabwasser Privat"],
            "Regenabwasser Privat": ["Regenabwasser Gemeinde"],
            "Abwasser Gemeinde": ["Abwasser Privat"],
            "Abwasser Privat": ["Abwasser Gemeinde"],
        }

        strategy = ExplicitRulesCompatibility(rules)

        # Rule-based compatibility
        assert strategy.are_compatible("Regenabwasser Gemeinde", "Regenabwasser Privat")
        assert strategy.are_compatible("Abwasser Privat", "Abwasser Gemeinde")

        # No rule - incompatible
        assert not strategy.are_compatible("Regenabwasser Gemeinde", "Abwasser Privat")
        assert not strategy.are_compatible("Wasser", "Gas")

        # Exact match always compatible
        assert strategy.are_compatible("Wasser", "Wasser")

    def test_pattern_based_compatibility(self):
        """Test pattern-based compatibility."""
        patterns = {
            "regenabwasser": ["Regenabwasser*", "Regenwasser*"],
            "abwasser": ["Abwasser*", "Schmutzwasser*"],
            "wasser": ["Wasser*"],
        }

        strategy = PatternBasedCompatibility(patterns)

        # Pattern group compatibility
        assert strategy.are_compatible("Regenabwasser Gemeinde", "Regenabwasser Privat")
        assert strategy.are_compatible("Regenabwasser Test", "Regenwasser ABC")
        assert strategy.are_compatible("Abwasser A", "Schmutzwasser B")

        # Different groups - incompatible
        assert not strategy.are_compatible("Regenabwasser Test", "Abwasser Test")
        assert not strategy.are_compatible("Wasser Test", "Gas Test")

        # Group identification
        assert strategy.get_group("Regenabwasser Gemeinde") == "regenabwasser"
        assert strategy.get_group("Regenwasser Test") == "regenabwasser"
        assert strategy.get_group("Unknown Medium") == "Unknown Medium"


class TestPipelineGradientAdjuster:
    """Test pipeline gradient adjustment functionality."""

    @pytest.fixture
    def sample_objects(self):
        """Create sample objects for testing."""
        # Create manholes
        manhole1 = ObjectData(
            medium="Regenabwasser Gemeinde",
            object_type=ObjectType.WASTE_WATER_SPECIAL,
            family="Schacht",
            family_type="Test",
            dimensions=RoundDimensions(diameter=1.0),
            layer="test",
            positions=(Point3D(east=0.0, north=0.0, altitude=100.0),),
        )

        manhole2 = ObjectData(
            medium="Regenabwasser Privat",
            object_type=ObjectType.WASTE_WATER_SPECIAL,
            family="Schacht",
            family_type="Test",
            dimensions=RoundDimensions(diameter=1.0),
            layer="test",
            positions=(Point3D(east=100.0, north=0.0, altitude=98.0),),
        )

        # Create pipeline (initially uphill - should be corrected)
        pipeline = ObjectData(
            medium="Regenabwasser Gemeinde",
            object_type=ObjectType.PIPE_WASTEWATER,
            family="Rohr",
            family_type="Test",
            dimensions=RoundDimensions(diameter=0.3),
            layer="test",
            positions=(
                Point3D(east=1.0, north=0.0, altitude=99.5),  # Near manhole1
                Point3D(east=99.0, north=0.0, altitude=99.8),  # Near manhole2 (uphill!)
            ),
        )

        return [manhole1, manhole2, pipeline]

    def test_gradient_adjustment_with_prefix_strategy(self, sample_objects):
        """Test gradient adjustment using prefix-based compatibility."""
        adjuster = PipelineGradientAdjuster(
            params=GradientAdjustmentParams(
                manhole_search_radius=5.0,
                min_gradient_percent=0.5,
                max_gradient_percent=10.0,
            ),
            compatibility=PrefixBasedCompatibility(),
        )

        adjustments = adjuster.adjust_gradients_by(sample_objects)

        # Should find one adjustment
        assert len(adjustments) == 1

        adjustment = adjustments[0]
        assert adjustment.pipeline.medium == "Regenabwasser Gemeinde"
        assert adjustment.start_manhole is not None
        assert adjustment.end_manhole is not None
        assert adjustment.start_manhole.medium == "Regenabwasser Gemeinde"
        assert adjustment.end_manhole.medium == "Regenabwasser Privat"

        # Should create downhill gradient
        assert adjustment.calculated_gradient < 0  # Negative = downhill
        assert adjustment.adjusted_start == 100.0  # From manhole1
        assert adjustment.adjusted_end == 98.0  # From manhole2

        # Check compatibility description
        assert "compatible" in adjustment.medium_compatibility.lower()

    def test_no_compatible_manholes(self):
        """Test behavior when no compatible manholes are found."""
        # Create objects with incompatible mediums
        manhole = ObjectData(
            medium="Wasser",  # Different medium
            object_type=ObjectType.WATER_SPECIAL,
            family="Schacht",
            family_type="Test",
            dimensions=RoundDimensions(diameter=1.0),
            layer="test",
            positions=(Point3D(east=0.0, north=0.0, altitude=100.0),),
        )

        pipeline = ObjectData(
            medium="Abwasser Gemeinde",  # Different medium
            object_type=ObjectType.PIPE_WASTEWATER,
            family="Rohr",
            family_type="Test",
            dimensions=RoundDimensions(diameter=0.3),
            layer="test",
            positions=(
                Point3D(east=1.0, north=0.0, altitude=99.0),
                Point3D(east=10.0, north=0.0, altitude=99.5),  # Uphill
            ),
        )

        adjuster = PipelineGradientAdjuster()
        adjustments = adjuster.adjust_gradients_by([manhole, pipeline])

        # Should still make adjustment to fix uphill gradient
        assert len(adjustments) == 1
        adjustment = adjustments[0]
        assert adjustment.start_manhole is None
        assert adjustment.end_manhole is None
        assert "Fixed uphill DGM gradient" in adjustment.adjustment_reason

    def test_minimum_gradient_enforcement(self):
        """Test that minimum gradient is enforced."""
        # Create manholes with very small elevation difference
        manhole1 = ObjectData(
            medium="Abwasser",
            object_type=ObjectType.SHAFT,
            family="Schacht",
            family_type="Test",
            dimensions=RoundDimensions(diameter=1.0),
            layer="test",
            positions=(Point3D(east=0.0, north=0.0, altitude=100.0),),
        )

        manhole2 = ObjectData(
            medium="Abwasser",
            object_type=ObjectType.SHAFT,
            family="Schacht",
            family_type="Test",
            dimensions=RoundDimensions(diameter=1.0),
            layer="test",
            positions=(Point3D(east=100.0, north=0.0, altitude=99.9),),  # Only 0.1m drop over 100m
        )

        pipeline = ObjectData(
            medium="Abwasser",
            object_type=ObjectType.PIPE_WASTEWATER,
            family="Rohr",
            family_type="Test",
            dimensions=RoundDimensions(diameter=0.3),
            layer="test",
            positions=(Point3D(east=1.0, north=0.0, altitude=100.0), Point3D(east=99.0, north=0.0, altitude=99.9)),
        )

        adjuster = PipelineGradientAdjuster(params=GradientAdjustmentParams(min_gradient_percent=0.5))
        adjustments = adjuster.adjust_gradients_by([manhole1, manhole2, pipeline])

        assert len(adjustments) == 1
        adjustment = adjustments[0]

        # Should enforce minimum 0.5% gradient
        assert adjustment.calculated_gradient <= -0.5
        assert "minimum gradient" in adjustment.adjustment_reason.lower()

    def test_explicit_rules_strategy(self):
        """Test using explicit rules compatibility strategy."""
        rules = {"Medium A": ["Medium B"], "Medium B": ["Medium A"]}

        strategy = ExplicitRulesCompatibility(rules)
        adjuster = PipelineGradientAdjuster(compatibility=strategy)

        manhole1 = ObjectData(
            medium="Medium A",
            object_type=ObjectType.SHAFT,
            family="Test",
            family_type="Test",
            dimensions=RoundDimensions(diameter=1.0),
            layer="test",
            positions=(Point3D(east=0.0, north=0.0, altitude=100.0),),
        )

        manhole2 = ObjectData(
            medium="Medium B",
            object_type=ObjectType.SHAFT,
            family="Test",
            family_type="Test",
            dimensions=RoundDimensions(diameter=1.0),
            layer="test",
            positions=(Point3D(east=10.0, north=0.0, altitude=98.0),),
        )

        pipeline = ObjectData(
            medium="Medium A",
            object_type=ObjectType.PIPE_WASTEWATER,
            family="Test",
            family_type="Test",
            dimensions=RoundDimensions(diameter=0.3),
            layer="test",
            positions=(Point3D(east=1.0, north=0.0, altitude=99.0), Point3D(east=9.0, north=0.0, altitude=99.0)),
        )

        adjustments = adjuster.adjust_gradients_by([manhole1, manhole2, pipeline])

        assert len(adjustments) == 1
        adjustment = adjustments[0]

        assert adjustment.start_manhole is not None
        assert adjustment.start_manhole.medium == "Medium A"

        assert adjustment.end_manhole is not None
        assert adjustment.end_manhole.medium == "Medium B"
        assert "explicit rule" in adjustment.medium_compatibility

    def test_intermediate_points_interpolation(self):
        """Test that intermediate points are properly interpolated."""
        manhole1 = ObjectData(
            medium="Test",
            object_type=ObjectType.SHAFT,
            family="Test",
            family_type="Test",
            dimensions=RoundDimensions(diameter=1.0),
            layer="test",
            positions=(Point3D(east=0.0, north=0.0, altitude=100.0),),
        )

        manhole2 = ObjectData(
            medium="Test",
            object_type=ObjectType.SHAFT,
            family="Test",
            family_type="Test",
            dimensions=RoundDimensions(diameter=1.0),
            layer="test",
            positions=(Point3D(east=20.0, north=0.0, altitude=98.0),),
        )

        # Pipeline with intermediate points
        pipeline = ObjectData(
            medium="Test",
            object_type=ObjectType.PIPE_WASTEWATER,
            family="Test",
            family_type="Test",
            dimensions=RoundDimensions(diameter=0.3),
            layer="test",
            positions=(
                Point3D(east=1.0, north=0.0, altitude=100.0),
                Point3D(east=19.0, north=0.0, altitude=98.0),
            ),
            points=[
                Point3D(east=1.0, north=0.0, altitude=100.0),  # Start
                Point3D(east=10.0, north=0.0, altitude=99.0),  # Middle
                Point3D(east=19.0, north=0.0, altitude=98.0),  # End
            ],
        )

        adjuster = PipelineGradientAdjuster()
        adjustments = adjuster.adjust_gradients_by([manhole1, manhole2, pipeline])

        assert len(adjustments) == 1
        # Check that intermediate points were interpolated
        assert len(pipeline.points) == 3
        # Start point should match manhole1
        assert pipeline.points[0].altitude == 100.0
        # End point should match manhole2
        assert pipeline.points[-1].altitude == 98.0
        # Middle point should be interpolated (approximately halfway)
        middle_elevation = pipeline.points[1].altitude
        assert 98.0 < middle_elevation < 100.0

    def test_adjustment_report_generation(self, sample_objects):
        """Test generation of adjustment reports."""
        adjuster = PipelineGradientAdjuster()
        adjustments = adjuster.adjust_gradients_by(sample_objects)
        report = adjuster.generate_report(adjustments)

        assert report["total_adjustments"] == len(adjustments)
        assert "compatibility_strategy" in report
        assert "compatibility_groups" in report
        assert "adjustments" in report
        assert report["total_elevation_change_meters"] > 0

        # Check individual adjustment details
        adjustment_detail = report["adjustments"][0]
        assert "pipeline_medium" in adjustment_detail
        assert "medium_compatibility" in adjustment_detail
        assert "gradient_percent" in adjustment_detail
        assert "reason" in adjustment_detail

    def test_empty_adjustments_report(self):
        """Test report generation with no adjustments."""
        adjuster = PipelineGradientAdjuster()
        report = adjuster.generate_report([])

        assert report["total_adjustments"] == 0
        assert "No pipeline adjustments needed" in report["summary"]
        assert report["adjustments"] == []
