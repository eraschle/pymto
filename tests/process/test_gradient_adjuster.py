"""Tests for pipeline gradient adjustment with medium compatibility."""

import pytest

from pymto.models import ObjectData, ObjectType, Parameter, Point3D, RoundDimensions
from pymto.process.gradient import (
    ExplicitRulesCompatibility,
    PrefixBasedCompatibility,
)
from pymto.process.gradient.adjuster import (
    GradientAdjustmentParams,
    PipelineGradientAdjuster,
)


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
            points=[Point3D(east=0.0, north=0.0, altitude=100.0)],
            object_id=Parameter(name="object_id", value="manhole_id"),
        )

        manhole2 = ObjectData(
            medium="Regenabwasser Privat",
            object_type=ObjectType.WASTE_WATER_SPECIAL,
            family="Schacht",
            family_type="Test",
            dimensions=RoundDimensions(diameter=1.0),
            layer="test",
            points=[Point3D(east=100.0, north=0.0, altitude=98.0)],
            object_id=Parameter(name="object_id", value="manhole_id"),
        )

        # Create pipeline (initially uphill - should be corrected)
        pipeline = ObjectData(
            medium="Regenabwasser Gemeinde",
            object_type=ObjectType.PIPE_WASTEWATER,
            family="Rohr",
            family_type="Test",
            dimensions=RoundDimensions(diameter=0.3),
            layer="test",
            points=[
                Point3D(east=1.0, north=0.0, altitude=99.5),  # Near manhole1
                Point3D(east=99.0, north=0.0, altitude=99.8),  # Near manhole2 (uphill!)
            ],
            object_id=Parameter(name="object_id", value="pipe_id"),
        )

        return [manhole1, manhole2, pipeline]

    def test_gradient_adjustment_with_prefix_strategy(self, sample_objects):
        """Test gradient adjustment using prefix-based compatibility."""
        adjuster = PipelineGradientAdjuster(
            mediums=[],
            params=GradientAdjustmentParams(
                manhole_search_radius=5.0,
                min_gradient_percent=2.0,
            ),
            compatibility=PrefixBasedCompatibility(),
        )

        adjustments = adjuster.adjust_gradients_by(sample_objects)

        # Should find one adjustment
        assert len(adjustments) == 1

        adjustment = adjustments[0]
        assert adjustment.pipeline.medium == "Regenabwasser Gemeinde"

        # Should create downhill gradient
        assert adjustment.calculated_gradient < 0  # Negative = downhill
        assert adjustment.adjusted_start == 100.0  # From manhole1
        assert adjustment.adjusted_end == 98.0  # From manhole2

        # Check adjustment reason
        assert "shaft" in adjustment.adjustment_reason.lower() or "manhole" in adjustment.adjustment_reason.lower()

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
            points=[Point3D(east=0.0, north=0.0, altitude=100.0)],
            object_id=Parameter(name="object_id", value="manhole_id"),
        )

        pipeline = ObjectData(
            medium="Abwasser Gemeinde",  # Different medium
            object_type=ObjectType.PIPE_WASTEWATER,
            family="Rohr",
            family_type="Test",
            dimensions=RoundDimensions(diameter=0.3),
            layer="test",
            points=[
                Point3D(east=1.0, north=0.0, altitude=99.0),
                Point3D(east=10.0, north=0.0, altitude=99.5),  # Uphill
            ],
            object_id=Parameter(name="object_id", value="pipe_id"),
        )

        adjuster = PipelineGradientAdjuster(mediums=[])
        adjustments = adjuster.adjust_gradients_by([manhole, pipeline])

        # Should still make adjustment to fix uphill gradient
        assert len(adjustments) == 1
        adjustment = adjustments[0]
        # No manhole connections available
        assert "DGM" in adjustment.adjustment_reason or "uphill" in adjustment.adjustment_reason
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
            points=[Point3D(east=0.0, north=0.0, altitude=100.0)],
            object_id=Parameter(name="object_id", value="manhole1_id"),
        )

        manhole2 = ObjectData(
            medium="Abwasser",
            object_type=ObjectType.SHAFT,
            family="Schacht",
            family_type="Test",
            dimensions=RoundDimensions(diameter=1.0),
            layer="test",
            points=[Point3D(east=100.0, north=0.0, altitude=99.9)],  # Only 0.1m drop over 100m
            object_id=Parameter(name="object_id", value="manhole2_id"),
        )

        pipeline = ObjectData(
            medium="Abwasser",
            object_type=ObjectType.PIPE_WASTEWATER,
            family="Rohr",
            family_type="Test",
            dimensions=RoundDimensions(diameter=0.3),
            layer="test",
            points=[
                Point3D(east=1.0, north=0.0, altitude=100.0),
                Point3D(east=99.0, north=0.0, altitude=99.9),
            ],
            object_id=Parameter(name="object_id", value="pipeline_id"),
        )

        adjuster = PipelineGradientAdjuster(mediums=[], params=GradientAdjustmentParams(min_gradient_percent=0.5))
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
        adjuster = PipelineGradientAdjuster(mediums=[], compatibility=strategy)

        manhole1 = ObjectData(
            medium="Medium A",
            object_type=ObjectType.SHAFT,
            family="Test",
            family_type="Test",
            dimensions=RoundDimensions(diameter=1.0),
            layer="test",
            points=[Point3D(east=0.0, north=0.0, altitude=100.0)],
            object_id=Parameter(name="object_id", value="manhole1_id"),
        )

        manhole2 = ObjectData(
            medium="Medium B",
            object_type=ObjectType.SHAFT,
            family="Test",
            family_type="Test",
            dimensions=RoundDimensions(diameter=1.0),
            layer="test",
            points=[Point3D(east=10.0, north=0.0, altitude=98.0)],
            object_id=Parameter(name="object_id", value="manhole2_id"),
        )

        pipeline = ObjectData(
            medium="Medium A",
            object_type=ObjectType.PIPE_WASTEWATER,
            family="Test",
            family_type="Test",
            dimensions=RoundDimensions(diameter=0.3),
            layer="test",
            points=[
                Point3D(east=1.0, north=0.0, altitude=99.0),
                Point3D(east=9.0, north=0.0, altitude=99.0),
            ],
            object_id=Parameter(name="object_id", value="pipeline_id"),
        )

        adjustments = adjuster.adjust_gradients_by([manhole1, manhole2, pipeline])

        assert len(adjustments) == 1
        adjustment = adjustments[0]

        # Check that adjustment was made based on explicit rules
        assert "shaft" in adjustment.adjustment_reason.lower() or "manhole" in adjustment.adjustment_reason.lower()

    def test_intermediate_points_interpolation(self):
        """Test that intermediate points are properly interpolated."""
        manhole1 = ObjectData(
            medium="Test",
            object_type=ObjectType.SHAFT,
            family="Test",
            family_type="Test",
            dimensions=RoundDimensions(diameter=1.0),
            layer="test",
            points=[Point3D(east=0.0, north=0.0, altitude=100.0)],
            object_id=Parameter(name="object_id", value="manhole1_id"),
        )

        manhole2 = ObjectData(
            medium="Test",
            object_type=ObjectType.SHAFT,
            family="Test",
            family_type="Test",
            dimensions=RoundDimensions(diameter=1.0),
            layer="test",
            points=[Point3D(east=20.0, north=0.0, altitude=98.0)],
            object_id=Parameter(name="object_id", value="manhole2_id"),
        )

        # Pipeline with intermediate points (wrong elevations to force adjustment)
        pipeline = ObjectData(
            medium="Test",
            object_type=ObjectType.PIPE_WASTEWATER,
            family="Test",
            family_type="Test",
            dimensions=RoundDimensions(diameter=0.3),
            layer="test",
            points=[
                Point3D(east=1.0, north=0.0, altitude=95.0),  # Start (wrong)
                Point3D(east=10.0, north=0.0, altitude=95.2),  # Middle (wrong)
                Point3D(east=19.0, north=0.0, altitude=95.5),  # End (wrong)
            ],
            object_id=Parameter(name="object_id", value="pipeline_id"),
        )

        adjuster = PipelineGradientAdjuster(mediums=[])
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
        adjuster = PipelineGradientAdjuster(mediums=[])
        adjustments = adjuster.adjust_gradients_by(sample_objects)
        report = adjuster.generate_report(adjustments)

        assert report["total_adjustments"] == len(adjustments)
        assert "medium_groups" in report
        assert "adjustments_by_medium" in report
        assert "adjustments" in report
        assert report["total_elevation_change_meters"] > 0

        # Check individual adjustment details
        adjustment_detail = report["adjustments"][0]
        assert "pipeline_medium" in adjustment_detail
        assert "pipeline_medium" in adjustment_detail
        assert "gradient_percent" in adjustment_detail
        assert "reason" in adjustment_detail

    def test_empty_adjustments_report(self):
        """Test report generation with no adjustments."""
        adjuster = PipelineGradientAdjuster(mediums=[])
        report = adjuster.generate_report([])

        assert report["total_adjustments"] == 0
        assert "No pipeline adjustments needed" in report["summary"]
        assert report["adjustments"] == []
