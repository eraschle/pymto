"""Tests for entity_handler module."""

import math
from unittest.mock import Mock, patch

import pytest

from dxfto.models import Point3D
from dxfto.process import entity_handler as dxf


class TestExtractPointsFromEntity:
    """Test extract_points_from_entity function."""

    def test_extract_points_from_line(self):
        """Test extracting points from LINE entity."""
        # Mock LINE entity
        line_entity = Mock()
        line_entity.dxf.start = Mock(x=0.0, y=0.0)
        line_entity.dxf.end = Mock(x=10.0, y=5.0)

        # Mock isinstance to return True for Line
        with patch("dxfto.process.entity_handler.isinstance") as mock_isinstance:

            def isinstance_side_effect(_, cls):
                from ezdxf.entities.line import Line

                return cls == Line

            mock_isinstance.side_effect = isinstance_side_effect

            points = dxf.extract_points_from(line_entity)

        assert len(points) == 2
        assert points[0] == Point3D(east=0.0, north=0.0, altitude=0.0)
        assert points[1] == Point3D(east=10.0, north=5.0, altitude=0.0)

    def test_extract_points_from_circle(self):
        """Test extracting center point from CIRCLE entity."""
        # Mock CIRCLE entity
        circle_entity = Mock()
        circle_entity.dxf.center = Mock(x=5.0, y=5.0)

        # Mock isinstance to return True for Circle
        with patch("dxfto.process.entity_handler.isinstance") as mock_isinstance:

            def isinstance_side_effect(_, cls):
                from ezdxf.entities.circle import Circle

                return cls == Circle

            mock_isinstance.side_effect = isinstance_side_effect

            points = dxf.extract_points_from(circle_entity)

        assert len(points) == 1
        assert points[0] == Point3D(east=5.0, north=5.0, altitude=0.0)


class TestDetectShapeType:
    """Test detect_shape_type function."""

    def test_detect_linear_shape_two_points(self):
        """Test detection of linear shape with 2 points."""
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=0.0, altitude=0.0),
        ]
        assert dxf.detect_shape_type(points) == "linear"

    def test_detect_rectangular_shape(self):
        """Test detection of rectangular shape."""
        # Perfect rectangle
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=5.0, altitude=0.0),
            Point3D(east=0.0, north=5.0, altitude=0.0),
        ]
        assert dxf.detect_shape_type(points) == "rectangular"

    def test_detect_multi_sided_shape(self):
        """Test detection of multi-sided shape."""
        # Irregular quadrilateral
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=2.0, altitude=0.0),
            Point3D(east=8.0, north=8.0, altitude=0.0),
            Point3D(east=2.0, north=6.0, altitude=0.0),
        ]
        assert dxf.detect_shape_type(points) == "multi_sided"

    def test_detect_circular_shape(self):
        """Test detection of near-circular shape (regular polygon)."""
        # Create octagon (should be detected as round)
        center = Point3D(east=0.0, north=0.0, altitude=0.0)
        radius = 5.0
        points = []
        for i in range(8):
            angle = i * 2 * math.pi / 8
            x = center.east + radius * math.cos(angle)
            y = center.north + radius * math.sin(angle)
            points.append(Point3D(east=x, north=y, altitude=0.0))

        assert dxf.detect_shape_type(points) == "round"


class TestIsRectangularShape:
    """Test is_rectangular_shape function."""

    def test_perfect_rectangle(self):
        """Test perfect rectangle recognition."""
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=5.0, altitude=0.0),
            Point3D(east=0.0, north=5.0, altitude=0.0),
        ]
        assert dxf.is_rectangular(points)

    def test_non_rectangle(self):
        """Test non-rectangular shape."""
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=2.0, altitude=0.0),
            Point3D(east=8.0, north=8.0, altitude=0.0),
            Point3D(east=2.0, north=6.0, altitude=0.0),
        ]
        assert not dxf.is_rectangular(points)

    def test_wrong_number_of_points(self):
        """Test with wrong number of points."""
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=5.0, altitude=0.0),
        ]
        assert not dxf.is_rectangular(points)


class TestIsNearCircularShape:
    """Test is_near_circular_shape function."""

    def test_regular_octagon(self):
        """Test regular octagon (should be circular)."""
        center = Point3D(east=0.0, north=0.0, altitude=0.0)
        radius = 5.0
        points = []
        for i in range(8):
            angle = i * 2 * math.pi / 8
            x = center.east + radius * math.cos(angle)
            y = center.north + radius * math.sin(angle)
            points.append(Point3D(east=x, north=y, altitude=0.0))

        assert dxf.is_near_circular(points)

    def test_irregular_polygon(self):
        """Test irregular polygon (should not be circular)."""
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=2.0, altitude=0.0),
            Point3D(east=8.0, north=8.0, altitude=0.0),
            Point3D(east=2.0, north=6.0, altitude=0.0),
            Point3D(east=-2.0, north=4.0, altitude=0.0),
            Point3D(east=-5.0, north=1.0, altitude=0.0),
        ]
        assert not dxf.is_near_circular(points)

    def test_too_few_points(self):
        """Test with too few points."""
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=5.0, altitude=0.0),
        ]
        assert not dxf.is_near_circular(points)


class TestAreCrossingDiagonals:
    """Test are_crossing_diagonals function."""

    def test_crossing_diagonals(self):
        """Test crossing diagonal lines."""
        line1 = ((0.0, 0.0), (10.0, 10.0))  # Diagonal from bottom-left to top-right
        line2 = ((0.0, 10.0), (10.0, 0.0))  # Diagonal from top-left to bottom-right

        assert dxf.are_crossing_diagonals(line1, line2) is True

    def test_parallel_lines(self):
        """Test parallel lines (should not be crossing)."""
        line1 = ((0.0, 0.0), (10.0, 0.0))  # Horizontal line
        line2 = ((0.0, 5.0), (10.0, 5.0))  # Parallel horizontal line

        assert dxf.are_crossing_diagonals(line1, line2) is False

    def test_vertical_lines(self):
        """Test vertical lines."""
        line1 = ((0.0, 0.0), (0.0, 10.0))  # Vertical line
        line2 = ((5.0, 0.0), (5.0, 10.0))  # Parallel vertical line

        assert dxf.are_crossing_diagonals(line1, line2) is False


class TestCalculateBoundingBoxDimensions:
    """Test calculate_bounding_box_dimensions function."""

    def test_rectangular_bounding_box(self):
        """Test bounding box calculation for rectangle."""
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=5.0, altitude=0.0),
            Point3D(east=0.0, north=5.0, altitude=0.0),
        ]
        length, width = dxf.calculate_bbox_dimensions(points)
        assert length == 10.0
        assert width == 5.0

    def test_empty_points(self):
        """Test with empty points list."""
        points = []
        length, width = dxf.calculate_bbox_dimensions(points)
        assert length == 0.0
        assert width == 0.0


class TestCalculatePreciseRectangularDimensions:
    """Test calculate_precise_rectangular_dimensions function."""

    def test_precise_rectangle_dimensions(self):
        """Test precise rectangular dimension calculation."""
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=5.0, altitude=0.0),
            Point3D(east=0.0, north=5.0, altitude=0.0),
        ]
        length, width = dxf.calculate_rect_dimensions(points)
        assert length == 10.0
        assert width == 5.0

    def test_non_four_points(self):
        """Test with non-4-point shape (should fall back to bounding box)."""
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=5.0, altitude=0.0),
        ]
        length, width = dxf.calculate_rect_dimensions(points)
        assert length == 10.0
        assert width == 5.0


class TestCalculateCenterPoint:
    """Test calculate_center_point function."""

    def test_center_point_calculation(self):
        """Test center point calculation."""
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=10.0, altitude=0.0),
            Point3D(east=0.0, north=10.0, altitude=0.0),
        ]
        center = dxf.calculate_center_point(points)
        assert center.east == 5.0
        assert center.north == 5.0
        assert center.altitude == 0.0

    def test_empty_points(self):
        """Test with empty points list."""
        points = []
        center = dxf.calculate_center_point(points)
        assert center.east == 0.0
        assert center.north == 0.0
        assert center.altitude == 0.0


class TestEstimateDiameterFromPolygon:
    """Test estimate_diameter_from_polygon function."""

    def test_regular_octagon_diameter(self):
        """Test diameter estimation for regular octagon."""
        center = Point3D(east=0.0, north=0.0, altitude=0.0)
        radius = 5.0
        points = []
        for i in range(8):
            angle = i * 2 * math.pi / 8
            x = center.east + radius * math.cos(angle)
            y = center.north + radius * math.sin(angle)
            points.append(Point3D(east=x, north=y, altitude=0.0))

        diameter = dxf.estimate_diameter_from(points)
        assert abs(diameter - 10.0) < 0.01  # Should be close to 2 * radius

    def test_empty_points(self):
        """Test with empty points list."""
        points = []
        diameter = dxf.estimate_diameter_from(points)
        assert diameter == 0.0
