"""Tests for models module."""

import numpy as np
import pytest

from dxfto.models import (
    AssingmentData,
    DxfColor,
    DxfText,
    LayerData,
    Medium,
    MediumConfig,
    MediumMasterConfig,
    ObjectData,
    ObjectType,
    Point3D,
    RectangularDimensions,
    RoundDimensions,
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


class TestRectangularDimensions:
    """Test RectangularDimensions class."""

    def test_rectangular_dimensions_creation(self):
        """Test RectangularDimensions creation."""
        dims = RectangularDimensions(length=10.0, width=5.0, angle=45.0, height=3.0)
        assert dims.length == 10.0
        assert dims.width == 5.0
        assert dims.angle == 45.0
        assert dims.height == 3.0

    def test_rectangular_dimensions_no_height(self):
        """Test RectangularDimensions without height."""
        dims = RectangularDimensions(length=8.0, width=4.0, angle=0.0)
        assert dims.length == 8.0
        assert dims.width == 4.0
        assert dims.angle == 0.0
        assert dims.height is None


class TestRoundDimensions:
    """Test RoundDimensions class."""

    def test_round_dimensions_creation(self):
        """Test RoundDimensions creation."""
        dims = RoundDimensions(diameter=6.0, height=2.0)
        assert dims.diameter == 6.0
        assert dims.height == 2.0

    def test_round_dimensions_no_height(self):
        """Test RoundDimensions without height."""
        dims = RoundDimensions(diameter=8.0)
        assert dims.diameter == 8.0
        assert dims.height is None


class TestDxfText:
    """Test DxfText class."""

    def test_dxf_text_creation(self):
        """Test DxfText creation."""
        position = Point3D(east=10.0, north=20.0, altitude=0.0)
        text = DxfText(
            medium="Test Medium",
            content="Test Text",
            position=position,
            layer="TEXT_LAYER",
            color=(255, 0, 0),
        )

        assert text.content == "Test Text"
        assert text.position == position
        assert text.layer == "TEXT_LAYER"
        assert text.color == (255, 0, 0)


class TestObjectData:
    """Test ObjectData class."""

    def test_object_data_with_round_dimensions(self):
        """Test ObjectData with round dimensions."""
        dims = RoundDimensions(diameter=5.0)
        position = Point3D(east=10.0, north=20.0, altitude=0.0)

        obj = ObjectData(
            medium="Test Medium",
            object_type=ObjectType.UNKNOWN,
            dimensions=dims,
            layer="CIRCLE_LAYER",
            positions=(position,),
            color=(0, 255, 0),
        )

        assert obj.dimensions == dims
        assert obj.layer == "CIRCLE_LAYER"
        assert len(obj.positions) == 1
        assert obj.positions[0] == position
        assert obj.color == (0, 255, 0)
        assert obj.points == []  # Default empty list
        assert obj.assigned_text is None

    def test_object_data_with_rectangular_dimensions(self):
        """Test ObjectData with rectangular dimensions."""
        dims = RectangularDimensions(length=10.0, width=5.0, angle=0.0)
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=5.0, altitude=0.0),
            Point3D(east=0.0, north=5.0, altitude=0.0),
        ]

        obj = ObjectData(
            medium="Test Medium",
            object_type=ObjectType.UNKNOWN,
            dimensions=dims,
            layer="RECT_LAYER",
            points=points,
            color=(0, 0, 255),
        )

        assert obj.dimensions == dims
        assert obj.layer == "RECT_LAYER"
        assert obj.points == points
        assert obj.positions == []  # Default empty list
        assert obj.color == (0, 0, 255)

    def test_object_data_with_assigned_text(self):
        """Test ObjectData with assigned text."""
        dims = RoundDimensions(diameter=3.0)
        text_pos = Point3D(east=5.0, north=10.0, altitude=0.0)
        assigned_text = DxfText(
            medium="Test Medium",
            content="SHAFT_01",
            position=text_pos,
            layer="TEXT",
            color=(0, 0, 0),
        )

        obj = ObjectData(
            medium="Test Medium",
            object_type=ObjectType.UNKNOWN,
            dimensions=dims,
            layer="SHAFT_LAYER",
            assigned_text=assigned_text,
        )

        assert obj.assigned_text == assigned_text
        assert obj.assigned_text is not None
        assert obj.assigned_text.content == "SHAFT_01"


class TestDxfColor:
    """Test DxfColor class."""

    def test_dxf_color_creation(self):
        """Test DxfColor creation."""
        color = DxfColor(red=255, green=128, blue=0)
        assert color.red == 255
        assert color.green == 128
        assert color.blue == 0

    def test_to_tuple(self):
        """Test color conversion to tuple."""
        color = DxfColor(red=100, green=200, blue=50)
        tuple_color = color.to_tuple()
        assert tuple_color == (100, 200, 50)

    def test_frozen_dataclass(self):
        """Test that DxfColor is frozen (immutable)."""
        color = DxfColor(red=255, green=0, blue=0)

        with pytest.raises(AttributeError):
            color.red = 128  # Should not be allowed #pyright:ignore


class TestLayerData:
    """Test LayerData class."""

    def test_layer_data_creation(self):
        """Test LayerData creation."""
        layer = LayerData(name="PIPES", color=(0, 255, 0))
        assert layer.name == "PIPES"
        assert layer.color == (0, 255, 0)

    def test_layer_data_post_init_none_color(self):
        """Test LayerData post-init with None color."""
        layer = LayerData(name="DEFAULT", color=None)
        assert layer.name == "DEFAULT"
        assert layer.color == (0, 0, 0)  # Should be set to black

    def test_layer_data_string_color(self):
        """Test LayerData with string color."""
        layer = LayerData(name="SPECIAL", color="red")
        assert layer.name == "SPECIAL"
        assert layer.color == "red"


class TestAssignmentConfig:
    """Test AssignmentConfig class."""

    def test_assignment_config_creation(self):
        """Test AssignmentConfig creation."""
        geometry_layers = [
            LayerData(name="PIPES", color=(0, 255, 0)),
            LayerData(name="SHAFTS", color=(255, 0, 0)),
        ]
        text_layers = [
            LayerData(name="TEXT", color=(0, 0, 0)),
        ]

        config = MediumConfig(
            medium="Test Medium",
            geometry=geometry_layers,
            text=text_layers,
            default_unit="mm",
            object_type=ObjectType.UNKNOWN,
        )
        assert config.geometry == geometry_layers
        assert config.text == text_layers


class TestAssingmentData:
    """Test AssingmentData class."""

    def test_assignment_data_creation(self):
        """Test AssingmentData creation."""
        assignment = AssingmentData()
        assert assignment.data == []

    def test_add_element(self):
        """Test adding element to assignment data."""
        dims = RoundDimensions(diameter=5.0)
        position = Point3D(east=0.0, north=0.0, altitude=0.0)
        element = ObjectData(
            medium="Test Medium",
            object_type=ObjectType.UNKNOWN,
            dimensions=dims,
            layer="TEST",
            positions=(position,),
        )
        assignment = AssingmentData()
        assignment.setup(medium="Test Medium", elements=[[element]], texts=[[]])

        assert len(assignment.data) == 1
        assert len(assignment.data[0]) == 2
        elem_data, text_data = assignment.data[0]
        assert len(elem_data) == 1
        assert len(text_data) == 0
        assert elem_data[0] == element

    def test_add_text(self):
        """Test adding text to assignment data."""
        position = Point3D(east=0.0, north=0.0, altitude=0.0)
        text = DxfText(
            medium="Test Medium",
            content="Test",
            position=position,
            layer="TEXT",
            color=(0, 0, 0),
        )

        assignment = AssingmentData()
        assignment.setup(medium="Test Medium", elements=[[]], texts=[[text]])

        assert len(assignment.data) == 1
        assert len(assignment.data[0]) == 2
        elem_data, text_data = assignment.data[0]
        assert len(elem_data) == 0
        assert len(text_data) == 1
        assert text_data[0] == text


class TestMedium:
    """Test Medium class."""

    def test_medium_creation(self):
        """Test Medium creation."""
        geometry_layers = [LayerData(name="PIPES", color=(0, 255, 0))]
        text_layers = [LayerData(name="TEXT", color=(0, 0, 0))]

        elements_config = MediumConfig(
            medium="Test Medium",
            geometry=geometry_layers,
            text=text_layers,
            default_unit="mm",
            object_type=ObjectType.UNKNOWN,
        )
        lines_config = MediumConfig(
            medium="Test Medium",
            geometry=geometry_layers,
            text=text_layers,
            default_unit="mm",
            object_type=ObjectType.UNKNOWN,
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
        assert isinstance(medium.element_data, AssingmentData)
        assert isinstance(medium.line_data, AssingmentData)
