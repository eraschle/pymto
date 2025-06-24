"""Tests for text assignment strategies."""

import pytest
from dxfto.assigners import SpatialTextAssigner, ZoneBasedTextAssigner
from dxfto.models import DXFText, Pipe, Point3D, RoundDimensions, ShapeType


class TestSpatialTextAssigner:
    """Test SpatialTextAssigner."""

    def test_point_to_line_distance(self):
        """Test point to line distance calculation."""
        assigner = SpatialTextAssigner()

        # Point directly on line
        point = Point3D(x=5.0, y=0.0, z=0.0)
        line_start = Point3D(x=0.0, y=0.0, z=0.0)
        line_end = Point3D(x=10.0, y=0.0, z=0.0)

        distance = assigner._point_to_line_distance(point, line_start, line_end)
        assert distance == pytest.approx(0.0, abs=1e-6)

        # Point perpendicular to line
        point = Point3D(x=5.0, y=3.0, z=0.0)
        distance = assigner._point_to_line_distance(point, line_start, line_end)
        assert distance == pytest.approx(3.0, abs=1e-6)

        # Point beyond line end
        point = Point3D(x=15.0, y=0.0, z=0.0)
        distance = assigner._point_to_line_distance(point, line_start, line_end)
        assert distance == pytest.approx(5.0, abs=1e-6)

        # Point before line start
        point = Point3D(x=-5.0, y=0.0, z=0.0)
        distance = assigner._point_to_line_distance(point, line_start, line_end)
        assert distance == pytest.approx(5.0, abs=1e-6)

    def test_assign_texts_to_pipes_simple(self):
        """Test simple text assignment to pipes."""
        pipes = [
            Pipe(
                shape=ShapeType.ROUND,
                points=[Point3D(x=0.0, y=0.0, z=0.0), Point3D(x=10.0, y=0.0, z=0.0)],
                dimensions=RoundDimensions(diameter=200.0),
                layer="PIPE1",
                color=(255, 0, 0),
            ),
            Pipe(
                shape=ShapeType.ROUND,
                points=[Point3D(x=0.0, y=10.0, z=0.0), Point3D(x=10.0, y=10.0, z=0.0)],
                dimensions=RoundDimensions(diameter=150.0),
                layer="PIPE2",
                color=(0, 255, 0),
            ),
        ]

        texts = [
            DXFText(
                content="DN200",
                position=Point3D(x=5.0, y=1.0, z=0.0),  # Close to first pipe
                layer="TEXT1",
                color=(255, 100, 100),
            ),
            DXFText(
                content="DN150",
                position=Point3D(x=5.0, y=9.0, z=0.0),  # Close to second pipe
                layer="TEXT2",
                color=(100, 255, 100),
            ),
        ]

        assigner = SpatialTextAssigner(max_distance=5.0)
        assigned_pipes = assigner.assign_texts_to_pipes(pipes, texts)

        assert len(assigned_pipes) == 2

        # Check that texts were assigned to correct pipes
        pipe1_text = assigned_pipes[0].assigned_text
        pipe2_text = assigned_pipes[1].assigned_text

        assert pipe1_text is not None
        assert pipe2_text is not None
        assert pipe1_text.content == "DN200"
        assert pipe2_text.content == "DN150"

    def test_assign_texts_max_distance(self):
        """Test text assignment respects maximum distance."""
        pipes = [
            Pipe(
                shape=ShapeType.ROUND,
                points=[Point3D(x=0.0, y=0.0, z=0.0), Point3D(x=10.0, y=0.0, z=0.0)],
                dimensions=RoundDimensions(diameter=200.0),
                layer="PIPE1",
                color=(255, 0, 0),
            )
        ]

        texts = [
            DXFText(
                content="Close",
                position=Point3D(x=5.0, y=2.0, z=0.0),  # Distance = 2.0
                layer="TEXT1",
                color=(255, 100, 100),
            ),
            DXFText(
                content="Far",
                position=Point3D(x=5.0, y=20.0, z=0.0),  # Distance = 20.0
                layer="TEXT2",
                color=(255, 100, 100),
            ),
        ]

        assigner = SpatialTextAssigner(max_distance=5.0)
        assigned_pipes = assigner.assign_texts_to_pipes(pipes, texts)

        assert len(assigned_pipes) == 1
        assert assigned_pipes[0].assigned_text is not None
        assert assigned_pipes[0].assigned_text.content == "Close"

    def test_assign_texts_one_per_pipe(self):
        """Test that each pipe gets at most one text."""
        pipes = [
            Pipe(
                shape=ShapeType.ROUND,
                points=[Point3D(x=0.0, y=0.0, z=0.0), Point3D(x=10.0, y=0.0, z=0.0)],
                dimensions=RoundDimensions(diameter=200.0),
                layer="PIPE1",
                color=(255, 0, 0),
            )
        ]

        texts = [
            DXFText(
                content="Text1",
                position=Point3D(x=3.0, y=1.0, z=0.0),
                layer="TEXT1",
                color=(255, 100, 100),
            ),
            DXFText(
                content="Text2",
                position=Point3D(x=7.0, y=1.0, z=0.0),
                layer="TEXT2",
                color=(255, 100, 100),
            ),
        ]

        assigner = SpatialTextAssigner(max_distance=5.0)
        assigned_pipes = assigner.assign_texts_to_pipes(pipes, texts)

        assert len(assigned_pipes) == 1
        assert assigned_pipes[0].assigned_text is not None
        # Should have assigned only one text (the closest one)

    def test_assign_texts_empty_inputs(self):
        """Test text assignment with empty inputs."""
        assigner = SpatialTextAssigner()

        # Empty pipes
        result = assigner.assign_texts_to_pipes([], [])
        assert result == []

        # Empty texts
        pipes = [
            Pipe(
                shape=ShapeType.ROUND,
                points=[Point3D(x=0.0, y=0.0, z=0.0)],
                dimensions=RoundDimensions(diameter=200.0),
                layer="PIPE1",
                color=(255, 0, 0),
            )
        ]
        result = assigner.assign_texts_to_pipes(pipes, [])
        assert len(result) == 1
        assert result[0].assigned_text is None


class TestZoneBasedTextAssigner:
    """Test ZoneBasedTextAssigner."""

    def test_point_distance_2d(self):
        """Test 2D point distance calculation."""
        assigner = ZoneBasedTextAssigner()

        point1 = Point3D(x=0.0, y=0.0, z=0.0)
        point2 = Point3D(x=3.0, y=4.0, z=10.0)  # Z coordinate should be ignored

        distance = assigner._point_distance_2d(point1, point2)
        assert distance == pytest.approx(5.0, abs=1e-6)  # 3-4-5 triangle

    def test_assign_texts_with_zone_validation(self):
        """Test text assignment with zone-based validation."""
        pipes = [
            Pipe(
                shape=ShapeType.ROUND,
                points=[Point3D(x=0.0, y=0.0, z=0.0), Point3D(x=20.0, y=0.0, z=0.0)],
                dimensions=RoundDimensions(diameter=200.0),
                layer="PIPE1",
                color=(255, 0, 0),
            )
        ]

        texts = [
            DXFText(
                content="Valid",
                position=Point3D(x=10.0, y=1.0, z=0.0),  # Middle of pipe
                layer="TEXT1",
                color=(255, 100, 100),
            ),
            DXFText(
                content="TooCloseToStart",
                position=Point3D(x=2.0, y=1.0, z=0.0),  # Close to start
                layer="TEXT2",
                color=(255, 100, 100),
            ),
            DXFText(
                content="TooCloseToEnd",
                position=Point3D(x=18.0, y=1.0, z=0.0),  # Close to end
                layer="TEXT3",
                color=(255, 100, 100),
            ),
        ]

        assigner = ZoneBasedTextAssigner(max_distance=5.0, zone_buffer=5.0)
        assigned_pipes = assigner.assign_texts_to_pipes(pipes, texts)

        assert len(assigned_pipes) == 1

        # Should only assign the text in the middle, not the ones close to endpoints
        assigned_text = assigned_pipes[0].assigned_text
        if assigned_text is not None:
            assert assigned_text.content == "Valid"

    def test_assign_texts_inherits_spatial_behavior(self):
        """Test that zone-based assigner inherits spatial assignment behavior."""
        pipes = [
            Pipe(
                shape=ShapeType.ROUND,
                points=[
                    Point3D(x=0.0, y=0.0, z=0.0),
                    Point3D(x=100.0, y=0.0, z=0.0),  # Long pipe
                ],
                dimensions=RoundDimensions(diameter=200.0),
                layer="PIPE1",
                color=(255, 0, 0),
            )
        ]

        texts = [
            DXFText(
                content="MiddleText",
                position=Point3D(x=50.0, y=1.0, z=0.0),  # Far from endpoints
                layer="TEXT1",
                color=(255, 100, 100),
            )
        ]

        assigner = ZoneBasedTextAssigner(max_distance=5.0, zone_buffer=15.0)
        assigned_pipes = assigner.assign_texts_to_pipes(pipes, texts)

        assert len(assigned_pipes) == 1
        assert assigned_pipes[0].assigned_text is not None
        assert assigned_pipes[0].assigned_text.content == "MiddleText"
