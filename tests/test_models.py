"""Tests for data models."""

import pytest

from dxfto.models import (
    DXFText,
    GroupingConfig,
    Medium,
    Pipe,
    Point3D,
    RectangularDimensions,
    RoundDimensions,
    Shaft,
    ShapeType,
)


class TestPoint3D:
    """Test Point3D dataclass."""

    def test_point_creation(self):
        """Test creating a Point3D."""
        point = Point3D(x=10.5, y=20.3, z=5.0)

        assert point.x == 10.5
        assert point.y == 20.3
        assert point.z == 5.0

    def test_point_equality(self):
        """Test Point3D equality."""
        point1 = Point3D(x=1.0, y=2.0, z=3.0)
        point2 = Point3D(x=1.0, y=2.0, z=3.0)
        point3 = Point3D(x=1.1, y=2.0, z=3.0)

        assert point1 == point2
        assert point1 != point3


class TestDimensions:
    """Test dimension classes."""

    def test_rectangular_dimensions(self):
        """Test RectangularDimensions."""
        dims = RectangularDimensions(length=100.0, width=50.0, angle=45.0, height=25.0)

        assert dims.length == 100.0
        assert dims.width == 50.0
        assert dims.angle == 45.0
        assert dims.height == 25.0

    def test_rectangular_dimensions_without_height(self):
        """Test RectangularDimensions without height."""
        dims = RectangularDimensions(length=100.0, width=50.0, angle=0.0)

        assert dims.length == 100.0
        assert dims.width == 50.0
        assert dims.angle == 0.0
        assert dims.height is None

    def test_round_dimensions(self):
        """Test RoundDimensions."""
        dims = RoundDimensions(diameter=200.0, height=100.0)

        assert dims.diameter == 200.0
        assert dims.height == 100.0

    def test_round_dimensions_without_height(self):
        """Test RoundDimensions without height."""
        dims = RoundDimensions(diameter=300.0)

        assert dims.diameter == 300.0
        assert dims.height is None


class TestDXFText:
    """Test DXFText dataclass."""

    def test_text_creation(self):
        """Test creating a DXFText."""
        position = Point3D(x=10.0, y=20.0, z=0.0)
        text = DXFText(content="DN200", position=position, layer="TEXT_LAYER", color=(255, 0, 0))

        assert text.content == "DN200"
        assert text.position == position
        assert text.layer == "TEXT_LAYER"
        assert text.color == (255, 0, 0)


class TestShaft:
    """Test Shaft dataclass."""

    def test_round_shaft(self):
        """Test creating a round shaft."""
        position = Point3D(x=0.0, y=0.0, z=10.0)
        dimensions = RoundDimensions(diameter=1000.0)

        shaft = Shaft(
            shape=ShapeType.ROUND,
            position=position,
            dimensions=dimensions,
            layer="SHAFT_LAYER",
            color=(0, 255, 0),
        )

        assert shaft.shape == ShapeType.ROUND
        assert shaft.position == position
        assert shaft.dimensions == dimensions
        assert shaft.layer == "SHAFT_LAYER"
        assert shaft.color == (0, 255, 0)

    def test_rectangular_shaft(self):
        """Test creating a rectangular shaft."""
        position = Point3D(x=5.0, y=5.0, z=15.0)
        dimensions = RectangularDimensions(length=2000.0, width=1500.0, angle=0.0)

        shaft = Shaft(
            shape=ShapeType.RECTANGULAR,
            position=position,
            dimensions=dimensions,
            layer="RECT_SHAFT",
            color=(0, 0, 255),
        )

        assert shaft.shape == ShapeType.RECTANGULAR
        assert isinstance(shaft.dimensions, RectangularDimensions)
        assert shaft.dimensions.length == 2000.0
        assert shaft.dimensions.width == 1500.0


class TestPipe:
    """Test Pipe dataclass."""

    def test_pipe_creation(self):
        """Test creating a pipe."""
        points = [
            Point3D(x=0.0, y=0.0, z=0.0),
            Point3D(x=10.0, y=0.0, z=0.0),
            Point3D(x=10.0, y=10.0, z=0.0),
        ]
        dimensions = RoundDimensions(diameter=200.0)

        pipe = Pipe(
            shape=ShapeType.ROUND,
            points=points,
            dimensions=dimensions,
            layer="PIPE_LAYER",
            color=(255, 255, 0),
        )

        assert pipe.shape == ShapeType.ROUND
        assert len(pipe.points) == 3
        assert pipe.points[0] == points[0]
        assert pipe.dimensions == dimensions
        assert pipe.layer == "PIPE_LAYER"
        assert pipe.color == (255, 255, 0)
        assert pipe.assigned_text is None

    def test_pipe_with_assigned_text(self):
        """Test pipe with assigned text."""
        points = [Point3D(x=0.0, y=0.0, z=0.0), Point3D(x=10.0, y=0.0, z=0.0)]
        dimensions = RoundDimensions(diameter=150.0)
        text = DXFText(
            content="DN150", position=Point3D(x=5.0, y=1.0, z=0.0), layer="TEXT", color=(0, 0, 0)
        )

        pipe = Pipe(
            shape=ShapeType.ROUND,
            points=points,
            dimensions=dimensions,
            layer="PIPE",
            color=(255, 0, 0),
            assigned_text=text,
        )

        assert pipe.assigned_text == text
        assert pipe.assigned_text is not None
        assert pipe.assigned_text.content == "DN150"


class TestMedium:
    """Test Medium dataclass."""

    def test_medium_creation(self):
        """Test creating a medium."""
        pipe = Pipe(
            shape=ShapeType.ROUND,
            points=[Point3D(x=0.0, y=0.0, z=0.0)],
            dimensions=RoundDimensions(diameter=200.0),
            layer="PIPE",
            color=(255, 0, 0),
        )

        shaft = Shaft(
            shape=ShapeType.ROUND,
            position=Point3D(x=0.0, y=0.0, z=0.0),
            dimensions=RoundDimensions(diameter=1000.0),
            layer="SHAFT",
            color=(200, 0, 0),
        )

        text = DXFText(
            content="DN200",
            position=Point3D(x=1.0, y=1.0, z=0.0),
            layer="TEXT",
            color=(255, 100, 100),
        )

        medium = Medium(name="Abwasserleitung", pipes=[pipe], shafts=[shaft], texts=[text])

        assert medium.name == "Abwasserleitung"
        assert len(medium.pipes) == 1
        assert len(medium.shafts) == 1
        assert len(medium.texts) == 1
        assert medium.pipes[0] == pipe
        assert medium.shafts[0] == shaft
        assert medium.texts[0] == text


class TestGroupingConfig:
    """Test GroupingConfig dataclass."""

    def test_grouping_config_with_colors(self):
        """Test GroupingConfig with colors."""
        config = GroupingConfig(
            pipe_layer="PIPE_SEWER",
            shaft_layer="SHAFT_SEWER",
            text_layer="TEXT_SEWER",
            pipe_color=(255, 0, 0),
            shaft_color=(200, 0, 0),
            text_color=(255, 100, 100),
        )

        assert config.pipe_layer == "PIPE_SEWER"
        assert config.shaft_layer == "SHAFT_SEWER"
        assert config.text_layer == "TEXT_SEWER"
        assert config.pipe_color == (255, 0, 0)
        assert config.shaft_color == (200, 0, 0)
        assert config.text_color == (255, 100, 100)

    def test_grouping_config_without_colors(self):
        """Test GroupingConfig without colors."""
        config = GroupingConfig(
            pipe_layer="PIPE_WATER", shaft_layer="SHAFT_WATER", text_layer="TEXT_WATER"
        )

        assert config.pipe_layer == "PIPE_WATER"
        assert config.shaft_layer == "SHAFT_WATER"
        assert config.text_layer == "TEXT_WATER"
        assert config.pipe_color is None
        assert config.shaft_color is None
        assert config.text_color is None
