"""Tests for entity_handler module."""

import math
from unittest.mock import Mock, patch

import pytest

from dxfto.models import Point3D
from dxfto.process.entity_handler import (
    are_crossing_diagonals,
    calculate_bounding_box_dimensions,
    calculate_center_point,
    calculate_precise_rectangular_dimensions,
    detect_shape_type,
    estimate_diameter_from_polygon,
    extract_points_from_entity,
    is_element_entity,
    is_near_circular_shape,
    is_rectangular_shape,
)


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

            def isinstance_side_effect(obj, cls):
                from ezdxf.entities.line import Line

                return cls == Line

            mock_isinstance.side_effect = isinstance_side_effect

            points = extract_points_from_entity(line_entity)

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

            def isinstance_side_effect(obj, cls):
                from ezdxf.entities.circle import Circle

                return cls == Circle

            mock_isinstance.side_effect = isinstance_side_effect

            points = extract_points_from_entity(circle_entity)

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
        assert detect_shape_type(points) == "linear"

    def test_detect_rectangular_shape(self):
        """Test detection of rectangular shape."""
        # Perfect rectangle
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=5.0, altitude=0.0),
            Point3D(east=0.0, north=5.0, altitude=0.0),
        ]
        assert detect_shape_type(points) == "rectangular"

    def test_detect_multi_sided_shape(self):
        """Test detection of multi-sided shape."""
        # Irregular quadrilateral
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=2.0, altitude=0.0),
            Point3D(east=8.0, north=8.0, altitude=0.0),
            Point3D(east=2.0, north=6.0, altitude=0.0),
        ]
        assert detect_shape_type(points) == "multi_sided"

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

        assert detect_shape_type(points) == "round"


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
        assert is_rectangular_shape(points) == True

    def test_non_rectangle(self):
        """Test non-rectangular shape."""
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=2.0, altitude=0.0),
            Point3D(east=8.0, north=8.0, altitude=0.0),
            Point3D(east=2.0, north=6.0, altitude=0.0),
        ]
        assert is_rectangular_shape(points) == False

    def test_wrong_number_of_points(self):
        """Test with wrong number of points."""
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=5.0, altitude=0.0),
        ]
        assert is_rectangular_shape(points) == False


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

        assert is_near_circular_shape(points) == True

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
        assert is_near_circular_shape(points) == False

    def test_too_few_points(self):
        """Test with too few points."""
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=5.0, altitude=0.0),
        ]
        assert is_near_circular_shape(points) == False


class TestAreCrossingDiagonals:
    """Test are_crossing_diagonals function."""

    def test_crossing_diagonals(self):
        """Test crossing diagonal lines."""
        line1 = ((0.0, 0.0), (10.0, 10.0))  # Diagonal from bottom-left to top-right
        line2 = ((0.0, 10.0), (10.0, 0.0))  # Diagonal from top-left to bottom-right

        assert are_crossing_diagonals(line1, line2) == True

    def test_parallel_lines(self):
        """Test parallel lines (should not be crossing)."""
        line1 = ((0.0, 0.0), (10.0, 0.0))  # Horizontal line
        line2 = ((0.0, 5.0), (10.0, 5.0))  # Parallel horizontal line

        assert are_crossing_diagonals(line1, line2) == False

    def test_vertical_lines(self):
        """Test vertical lines."""
        line1 = ((0.0, 0.0), (0.0, 10.0))  # Vertical line
        line2 = ((5.0, 0.0), (5.0, 10.0))  # Parallel vertical line

        assert are_crossing_diagonals(line1, line2) == False


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
        length, width = calculate_bounding_box_dimensions(points)
        assert length == 10.0
        assert width == 5.0

    def test_empty_points(self):
        """Test with empty points list."""
        points = []
        length, width = calculate_bounding_box_dimensions(points)
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
        length, width = calculate_precise_rectangular_dimensions(points)
        assert length == 10.0
        assert width == 5.0

    def test_non_four_points(self):
        """Test with non-4-point shape (should fall back to bounding box)."""
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=5.0, altitude=0.0),
        ]
        length, width = calculate_precise_rectangular_dimensions(points)
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
        center = calculate_center_point(points)
        assert center.east == 5.0
        assert center.north == 5.0
        assert center.altitude == 0.0

    def test_empty_points(self):
        """Test with empty points list."""
        points = []
        center = calculate_center_point(points)
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

        diameter = estimate_diameter_from_polygon(points)
        assert abs(diameter - 10.0) < 0.01  # Should be close to 2 * radius

    def test_empty_points(self):
        """Test with empty points list."""
        points = []
        diameter = estimate_diameter_from_polygon(points)
        assert diameter == 0.0


class TestIsElementEntity:
    """Test is_element_entity function."""

    def test_insert_entity_is_element(self):
        """Test that INSERT entities are always elements."""
        entity = Mock()
        entity.dxftype.return_value = "INSERT"

        assert is_element_entity(entity) == True

    def test_circle_entity_is_element(self):
        """Test that CIRCLE entities are always elements."""
        entity = Mock()
        entity.dxftype.return_value = "CIRCLE"

        assert is_element_entity(entity) == True

    def test_line_entity_is_not_element(self):
        """Test that LINE entities are not elements."""
        entity = Mock()
        entity.dxftype.return_value = "LINE"

        assert is_element_entity(entity) == False

    def test_complex_polyline_is_element(self):
        """Test that complex polylines are elements."""
        entity = Mock()
        entity.dxftype.return_value = "LWPOLYLINE"
        entity.is_closed = True

        # Mock extract_points_from_entity to return 4+ points
        with pytest.MonkeyPatch().context() as m:
            m.setattr(
                "dxfto.process.entity_handler.extract_points_from_entity", lambda e: [Point3D(0, 0, 0)] * 5
            )

            assert is_element_entity(entity) == True

    def test_simple_polyline_is_not_element(self):
        """Test that simple polylines are not elements."""
        entity = Mock()
        entity.dxftype.return_value = "LWPOLYLINE"
        entity.is_closed = False

        # Mock extract_points_from_entity to return few points
        with pytest.MonkeyPatch().context() as m:
            m.setattr(
                "dxfto.process.entity_handler.extract_points_from_entity", lambda e: [Point3D(0, 0, 0)] * 2
            )

            assert is_element_entity(entity) == False
