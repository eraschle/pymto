"""Tests for models module."""

import numpy as np
import pytest

from pymto.models import (
    AssignmentData,
    DxfText,
    LayerData,
    Medium,
    MediumConfig,
    MediumMasterConfig,
    ObjectData,
    ObjectType,
    Parameter,
    Point3D,
    Dimension,
    ShapeType,
    LayerGroup,
    Unit,
)


class TestPoint3D:
    """Test Point3D class."""

    def test_point_creation(self):
        """Test Point3D creation."""
        point = Point3D(east=10.5, north=20.3, altitude=5.0)
        assert point.east == 10.5
        assert point.north == 20.3
        assert point.altitude == 5.0

    def test_distance_2d_calculation(self):
        """Test 2D distance calculation between points."""
        point1 = Point3D(east=0.0, north=0.0, altitude=0.0)
        point2 = Point3D(east=3.0, north=4.0, altitude=0.0)

        distance = point1.distance_2d(point2)
        assert distance == 5.0  # 3-4-5 triangle

    def test_distance_2d_same_point(self):
        """Test distance calculation for same point."""
        point = Point3D(east=5.0, north=10.0, altitude=0.0)

        distance = point.distance_2d(point)
        assert distance == 0.0

    def test_distance_2d_negative_coordinates(self):
        """Test distance calculation with negative coordinates."""
        point1 = Point3D(east=-5.0, north=-3.0, altitude=0.0)
        point2 = Point3D(east=1.0, north=2.0, altitude=0.0)

        distance = point1.distance_2d(point2)
        expected = np.sqrt((1 - (-5)) ** 2 + (2 - (-3)) ** 2)
        assert abs(distance - expected) < 1e-10


class TestDimension:
    """Test Dimension class."""

    def test_rectangular_dimensions_creation(self):
        """Test Dimension creation with rectangular shape."""
        dims = Dimension(shape=ShapeType.RECTANGULAR, length=10.0, width=5.0, angle=45.0, height=3.0)
        assert dims.length == 10.0
        assert dims.width == 5.0
        assert dims.angle == 45.0
        assert dims.height == 3.0
        assert dims.is_rectangular

    def test_rectangular_dimensions_no_height(self):
        """Test Dimension without height."""
        dims = Dimension(shape=ShapeType.RECTANGULAR, length=8.0, width=4.0, angle=0.0)
        assert dims.length == 8.0
        assert dims.width == 4.0
        assert dims.angle == 0.0
        assert dims.height == 0.0  # Default height is 0.0
        assert dims.is_rectangular


    def test_round_dimensions_creation(self):
        """Test Dimension creation with round shape."""
        dims = Dimension(shape=ShapeType.ROUND, diameter=6.0, height=2.0)
        assert dims.diameter == 6.0
        assert dims.height == 2.0
        assert dims.is_round

    def test_round_dimensions_no_height(self):
        """Test Dimension without height."""
        dims = Dimension(shape=ShapeType.ROUND, diameter=8.0)
        assert dims.diameter == 8.0
        assert dims.height == 0.0  # Default height is 0.0
        assert dims.is_round


class TestDxfText:
    """Test DxfText class."""

    def test_dxf_text_creation(self):
        """Test DxfText creation."""
        position = Point3D(east=10.0, north=20.0, altitude=0.0)
        text = DxfText(
            uuid="test-uuid",
            medium="Test Medium",
            content="Test Text",
            position=position,
            layer="TEXT_LAYER",
        )

        assert text.content == "Test Text"
        assert text.position == position
        assert text.layer == "TEXT_LAYER"
        assert text.uuid == "test-uuid"


class TestObjectData:
    """Test ObjectData class."""

    def test_object_data_with_round_dimensions(self):
        """Test ObjectData with round dimensions."""
        dims = Dimension(shape=ShapeType.ROUND, diameter=5.0)
        position = Point3D(east=10.0, north=20.0, altitude=0.0)

        obj = ObjectData(
            uuid="test-uuid",
            medium="Test Medium",
            object_type=ObjectType.UNKNOWN,
            family="Test Family",
            family_type="Test Type",
            dimension=dims,
            points=[position],
        )

        assert obj.dimension == dims
        assert len(obj.points) == 1
        assert obj.points[0] == position
        assert obj.assigned_text is None

    def test_object_data_with_rectangular_dimensions(self):
        """Test ObjectData with rectangular dimensions."""
        dims = Dimension(shape=ShapeType.RECTANGULAR, length=10.0, width=5.0, angle=0.0)
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=5.0, altitude=0.0),
            Point3D(east=0.0, north=5.0, altitude=0.0),
        ]

        obj = ObjectData(
            uuid="test-uuid",
            medium="Test Medium",
            object_type=ObjectType.UNKNOWN,
            family="Test Family",
            family_type="Test Type",
            dimension=dims,
            points=points,
        )

        assert obj.dimension == dims
        assert obj.points == points

    def test_object_data_with_assigned_text(self):
        """Test ObjectData with assigned text."""
        dims = Dimension(shape=ShapeType.ROUND, diameter=3.0)
        text_pos = Point3D(east=5.0, north=10.0, altitude=0.0)
        assigned_text = DxfText(
            uuid="text-uuid",
            medium="Test Medium",
            content="SHAFT_01",
            position=text_pos,
            layer="TEXT",
        )

        obj = ObjectData(
            uuid="test-uuid",
            medium="Test Medium",
            object_type=ObjectType.UNKNOWN,
            family="Test Family",
            family_type="Test Type",
            dimension=dims,
            assigned_text=assigned_text,
        )

        assert obj.assigned_text == assigned_text
        assert obj.assigned_text is not None
        assert obj.assigned_text.content == "SHAFT_01"


class TestLayerData:
    """Test LayerData class."""

    def test_layer_data_creation(self):
        """Test LayerData creation."""
        layer = LayerData(name="PIPES", color=(0, 255, 0))
        assert layer.name == "PIPES"
        assert layer.color == (0, 255, 0)

    def test_layer_data_none_color(self):
        """Test LayerData with None color."""
        layer = LayerData(name="DEFAULT", color=None)
        assert layer.name == "DEFAULT"
        assert layer.color is None  # Color remains None

    def test_layer_data_string_color(self):
        """Test LayerData with string color."""
        layer = LayerData(name="SPECIAL", color="red")
        assert layer.name == "SPECIAL"
        assert layer.color == "red"


class TestMediumConfig:
    """Test MediumConfig class."""

    def test_medium_config_creation(self):
        """Test MediumConfig creation."""
        geometry_layers = [
            LayerData(name="PIPES", color=(0, 255, 0)),
            LayerData(name="SHAFTS", color=(255, 0, 0)),
        ]
        text_layers = [
            LayerData(name="TEXT", color=(0, 0, 0)),
        ]
        layer_group = LayerGroup(geometry=geometry_layers, text=text_layers)

        config = MediumConfig(
            medium="Test Medium",
            layer_group=layer_group,
            family="Test Family",
            family_type="Test Type",
            elevation_offset=0.0,
            default_unit=Unit.MILLIMETER,
            object_type=ObjectType.UNKNOWN,
            object_id="12345",
        )
        assert config.layer_group.geometry == geometry_layers
        assert config.layer_group.text == text_layers


class TestAssignmentData:
    """Test AssignmentData class."""

    def test_assignment_data_creation(self):
        """Test AssignmentData creation."""
        assignment = AssignmentData()
        assert assignment.assigned == []

    def test_add_element(self):
        """Test adding element to assignment data."""
        dims = Dimension(shape=ShapeType.ROUND, diameter=5.0)
        position = Point3D(east=0.0, north=0.0, altitude=0.0)
        element = ObjectData(
            uuid="test-uuid",
            medium="Test Medium",
            object_type=ObjectType.UNKNOWN,
            family="Test Family",
            family_type="Test Family Type",
            dimension=dims,
            points=[position],
        )

        layer_group = LayerGroup(
            geometry=[LayerData(name="TEST", color=(255, 0, 0))],
            text=[LayerData(name="TEXT", color=(0, 0, 0))],
        )
        config = MediumConfig(
            medium="Test Medium",
            layer_group=layer_group,
            family="Test Family",
            family_type="Test Family Type",
            elevation_offset=0.0,
            default_unit=Unit.MILLIMETER,
            object_type=ObjectType.UNKNOWN,
            object_id="12345",
        )

        assignment = AssignmentData()
        assignment.add_assignment(config, [element])

        assert len(assignment.assigned) == 1
        assert assignment.assigned[0][0] == [element]
        assert assignment.assigned[0][1] == config

    def test_add_text(self):
        """Test adding text to assignment data."""
        layer_group = LayerGroup(
            geometry=[LayerData(name="GEOM", color=(255, 0, 0))],
            text=[LayerData(name="TEXT", color=(0, 0, 0))],
        )
        config = MediumConfig(
            medium="Test Medium",
            layer_group=layer_group,
            family="Test Family",
            family_type="Test Type",
            elevation_offset=0.0,
            default_unit=Unit.MILLIMETER,
            object_type=ObjectType.UNKNOWN,
            object_id="12345",
        )

        assignment = AssignmentData()
        assignment.add_assignment(config, [])

        assert len(assignment.assigned) == 1
        assert assignment.assigned[0][0] == []  # Empty elements list
        assert assignment.assigned[0][1] == config


class TestMedium:
    """Test Medium class."""

    def test_medium_creation(self):
        """Test Medium creation."""
        geometry_layers = [LayerData(name="PIPES", color=(0, 255, 0))]
        text_layers = [LayerData(name="TEXT", color=(0, 0, 0))]
        layer_group = LayerGroup(geometry=geometry_layers, text=text_layers)

        elements_config = MediumConfig(
            medium="Test Medium",
            layer_group=layer_group,
            default_unit=Unit.MILLIMETER,
            object_type=ObjectType.UNKNOWN,
            elevation_offset=0.0,
            family="Test Family",
            family_type="Test Family Type",
            object_id="12345",
        )
        lines_config = MediumConfig(
            medium="Test Medium",
            layer_group=layer_group,
            default_unit=Unit.MILLIMETER,
            object_type=ObjectType.UNKNOWN,
            elevation_offset=0.0,
            family="Test Family",
            family_type="Test Family Type",
            object_id="12345",
        )
        master = MediumMasterConfig(
            medium="Abwasserleitung",
            point_based=[elements_config],
            line_based=[lines_config],
        )

        medium = Medium(name="Abwasserleitung", config=master)

        assert medium.name == "Abwasserleitung"
        assert len(medium.config.point_based) == 1
        assert medium.config.point_based[0] == elements_config
        assert len(medium.config.line_based) == 1
        assert medium.config.line_based[0] == lines_config
        assert isinstance(medium.point_data, AssignmentData)
        assert isinstance(medium.line_data, AssignmentData)
