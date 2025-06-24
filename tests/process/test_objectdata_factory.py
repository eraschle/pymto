"""Tests for objectdata_factory module."""

from unittest.mock import Mock, patch

import pytest

from dxfto.models import (
    ObjectData,
    Point3D,
    RectangularDimensions,
    RoundDimensions,
)
from dxfto.process.objectdata_factory import ObjectDataFactory


class TestObjectDataFactory:
    """Test ObjectDataFactory class."""

    @pytest.fixture
    def mock_doc(self):
        """Create mock DXF document."""
        doc = Mock()
        doc.blocks = {}
        return doc

    @pytest.fixture
    def factory(self, mock_doc):
        """Create ObjectDataFactory instance."""
        return ObjectDataFactory(mock_doc)

    def test_factory_initialization(self, mock_doc):
        """Test factory initialization."""
        factory = ObjectDataFactory(mock_doc)
        assert factory.doc == mock_doc
        assert factory._block_cache == {}

    def test_create_from_unsupported_entity(self, factory):
        """Test creation from unsupported entity type."""
        entity = Mock()
        entity.dxftype.return_value = "UNSUPPORTED"

        result = factory.create_from_entity(entity)
        assert result is None

    def test_create_from_circle_entity(self, factory):
        """Test creation from CIRCLE entity."""
        # Mock CIRCLE entity
        entity = Mock()
        entity.dxftype.return_value = "CIRCLE"
        entity.dxf.center = Mock(x=10.0, y=5.0)
        entity.dxf.radius = 2.5
        entity.dxf.layer = "SHAFT_LAYER"
        entity.dxf.color = 1

        with patch("dxfto.process.objectdata_factory.isinstance") as mock_isinstance:

            def isinstance_side_effect(_, cls):
                from ezdxf.entities.circle import Circle

                return cls == Circle

            mock_isinstance.side_effect = isinstance_side_effect

            result = factory.create_from_entity(entity)

        assert result is not None
        assert isinstance(result, ObjectData)
        assert isinstance(result.dimensions, RoundDimensions)
        assert result.dimensions.diameter == 5.0
        assert len(result.positions) == 1
        assert result.positions[0] == Point3D(east=10.0, north=5.0, altitude=0.0)
        assert result.layer == "SHAFT_LAYER"
        assert result.color == (255, 0, 0)  # Red color

    def test_create_from_line_entity(self, factory):
        """Test creation from LINE entity."""
        entity = Mock()
        entity.dxftype.return_value = "LINE"
        entity.dxf.layer = "PIPE_LAYER"
        entity.dxf.color = 3

        # Mock extract_points_from_entity
        with patch("dxfto.process.objectdata_factory.extract_points_from_entity") as mock_extract:
            mock_extract.return_value = [
                Point3D(east=0.0, north=0.0, altitude=0.0),
                Point3D(east=10.0, north=0.0, altitude=0.0),
            ]

            result = factory.create_from_entity(entity)

        assert result is not None
        assert isinstance(result, ObjectData)
        assert isinstance(result.dimensions, RoundDimensions)
        assert result.dimensions.diameter == 200.0  # Default pipe diameter
        assert len(result.points) == 2
        assert result.layer == "PIPE_LAYER"
        assert result.color == (0, 255, 0)  # Green color

    def test_create_rectangular_object(self, factory):
        """Test creation of rectangular object."""
        entity = Mock()
        entity.dxf.layer = "RECT_LAYER"
        entity.dxf.color = 2

        # Rectangle points
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=0.0, altitude=0.0),
            Point3D(east=10.0, north=5.0, altitude=0.0),
            Point3D(east=0.0, north=5.0, altitude=0.0),
        ]

        result = factory._create_rectangular_object(entity, points)

        assert result is not None
        assert isinstance(result.dimensions, RectangularDimensions)
        assert result.dimensions.length == 10.0
        assert result.dimensions.width == 5.0
        assert len(result.positions) == 1
        assert result.positions[0] == Point3D(east=5.0, north=2.5, altitude=0.0)  # Center
        assert result.layer == "RECT_LAYER"
        assert result.color == (255, 255, 0)  # Yellow color

    def test_create_round_object_from_polygon(self, factory):
        """Test creation of round object from polygonal points."""
        entity = Mock()
        entity.dxf.layer = "ROUND_LAYER"
        entity.dxf.color = 5

        # Octagon points (approximating a circle)
        import math

        center = (0.0, 0.0)
        radius = 5.0
        points = []
        for i in range(8):
            angle = i * 2 * math.pi / 8
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            points.append(Point3D(east=x, north=y, altitude=0.0))

        result = factory._create_round_object_from_polygon(entity, points)

        assert result is not None
        assert isinstance(result.dimensions, RoundDimensions)
        assert abs(result.dimensions.diameter - 10.0) < 0.1  # Approximately 2 * radius
        assert len(result.positions) == 1
        assert abs(result.positions[0].east) < 0.1  # Near center
        assert abs(result.positions[0].north) < 0.1  # Near center
        assert result.layer == "ROUND_LAYER"
        assert result.color == (0, 0, 255)  # Blue color

    def test_create_multi_sided_object(self, factory):
        """Test creation of multi-sided object."""
        entity = Mock()
        entity.dxf.layer = "MULTI_LAYER"
        entity.dxf.color = 6

        # Irregular pentagon
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=8.0, north=2.0, altitude=0.0),
            Point3D(east=10.0, north=8.0, altitude=0.0),
            Point3D(east=3.0, north=10.0, altitude=0.0),
            Point3D(east=-2.0, north=5.0, altitude=0.0),
        ]

        result = factory._create_multi_sided_object(entity, points)

        assert result is not None
        assert isinstance(result.dimensions, RectangularDimensions)
        assert result.dimensions.length == 12.0  # Bounding box width
        assert result.dimensions.width == 10.0  # Bounding box height
        assert len(result.positions) == 1
        assert result.layer == "MULTI_LAYER"
        assert result.color == (255, 0, 255)  # Magenta color

    def test_get_entity_color_default(self, factory):
        """Test getting default entity color."""
        entity = Mock()
        # No color attribute
        del entity.dxf.color

        color = factory._get_entity_color(entity)
        assert color == (0, 0, 0)  # Default black

    def test_get_entity_color_mapped(self, factory):
        """Test getting mapped entity colors."""
        entity = Mock()

        # Test different color indices
        test_cases = [
            (1, (255, 0, 0)),  # Red
            (2, (255, 255, 0)),  # Yellow
            (3, (0, 255, 0)),  # Green
            (4, (0, 255, 255)),  # Cyan
            (5, (0, 0, 255)),  # Blue
            (6, (255, 0, 255)),  # Magenta
            (7, (0, 0, 0)),  # Black/White
            (99, (0, 0, 0)),  # Unknown -> Default
        ]

        for color_index, expected_rgb in test_cases:
            entity.dxf.color = color_index
            color = factory._get_entity_color(entity)
            assert color == expected_rgb

    def test_should_process_as_element(self, factory):
        """Test should_process_as_element method."""
        # Test different entity types
        test_cases = [
            ("INSERT", True),
            ("CIRCLE", True),
            ("LINE", False),
        ]

        for entity_type, expected in test_cases:
            entity = Mock()
            entity.dxftype.return_value = entity_type

            with patch("dxfto.process.objectdata_factory.is_element_entity") as mock_is_element:
                mock_is_element.return_value = expected

                result = factory.should_process_as_element(entity)
                assert result == expected
                mock_is_element.assert_called_once_with(entity)


class TestObjectDataFactoryInsertEntity:
    """Test ObjectDataFactory with INSERT entities (blocks)."""

    @pytest.fixture
    def mock_doc_with_blocks(self):
        """Create mock DXF document with block definitions."""
        doc = Mock()

        # Mock round block with properly set up circle
        round_block = Mock()
        round_circle = Mock()
        round_circle.dxftype.return_value = "CIRCLE"
        round_circle.dxf.radius = 3.0
        round_circle.dxf.center = Mock(x=0.0, y=0.0)
        # Set up the circle to pass isinstance check
        round_circle.__class__.__name__ = "Circle"
        round_block.__iter__ = Mock(return_value=iter([round_circle]))

        # Mock rectangular block
        rect_block = Mock()
        rect_block.__iter__ = Mock(return_value=iter([]))  # Empty block

        doc.blocks = {
            "ROUND_SHAFT": round_block,
            "RECT_SHAFT": rect_block,
        }

        return doc

    @pytest.fixture
    def factory_with_blocks(self, mock_doc_with_blocks):
        """Create ObjectDataFactory with block definitions."""
        return ObjectDataFactory(mock_doc_with_blocks)

    def test_create_from_insert_round_block(self, factory_with_blocks: ObjectDataFactory):
        """Test creation from INSERT entity with round block."""
        # Mock INSERT entity
        entity = Mock()
        entity.dxftype.return_value = "INSERT"
        entity.dxf.name = "ROUND_SHAFT"
        entity.dxf.insert = Mock(x=10.0, y=20.0)
        entity.dxf.layer = "SHAFT_LAYER"
        entity.dxf.color = 1

        with patch("dxfto.process.objectdata_factory.isinstance") as mock_isinstance:

            def isinstance_side_effect(obj, cls):
                from ezdxf.entities.circle import Circle
                from ezdxf.entities.insert import Insert

                if cls == Insert:
                    return True
                elif cls == Circle:
                    clazz = getattr(obj, "__class__", None)
                    assert clazz is not None, "Object must have a class"
                    return clazz.__name__ == "Circle"
                return False

            mock_isinstance.side_effect = isinstance_side_effect

            result = factory_with_blocks.create_from_entity(entity)

        assert result is not None
        assert isinstance(result, ObjectData)
        assert isinstance(result.dimensions, RoundDimensions)
        assert result.dimensions.diameter == 6.0  # 2 * radius
        assert len(result.positions) == 1
        assert result.positions[0] == Point3D(east=10.0, north=20.0, altitude=0.0)
        assert result.layer == "SHAFT_LAYER"

    def test_create_from_insert_unknown_block(self, factory_with_blocks: ObjectDataFactory):
        """Test creation from INSERT entity with unknown block."""
        # Mock INSERT entity
        entity = Mock()
        entity.dxftype.return_value = "INSERT"
        entity.dxf.name = "UNKNOWN_BLOCK"
        entity.dxf.insert = Mock(x=5.0, y=15.0)
        entity.dxf.layer = "UNKNOWN_LAYER"
        entity.dxf.color = 2

        with patch("dxfto.process.objectdata_factory.isinstance") as mock_isinstance:

            def isinstance_side_effect(_, cls):
                from ezdxf.entities.circle import Circle
                from ezdxf.entities.insert import Insert

                if cls == Insert:
                    return True
                elif cls == Circle:
                    return False  # No circles in unknown block
                return False

            mock_isinstance.side_effect = isinstance_side_effect
            result = factory_with_blocks.create_from_entity(entity)

        assert result is not None
        assert isinstance(result, ObjectData)
        # Should use default dimensions for unknown block
        assert isinstance(result.dimensions, RectangularDimensions)
        assert result.dimensions.length == 600.0
        assert result.dimensions.width == 600.0

    def test_get_block_entities_caching(self, factory_with_blocks: ObjectDataFactory):
        """Test that block entities are cached."""
        entity = Mock()
        entity.dxf.name = "ROUND_SHAFT"

        # First call
        entities1 = factory_with_blocks._get_block_entities(entity)

        # Second call (should use cache)
        entities2 = factory_with_blocks._get_block_entities(entity)

        assert entities1 is entities2  # Same object (cached)
        assert "ROUND_SHAFT" in factory_with_blocks._block_cache

    def test_analyze_circular_block(self, factory_with_blocks):
        """Test analysis of circular block."""
        # Mock circles with different sizes
        small_circle = Mock()
        small_circle.dxf.radius = 2.0
        small_circle.dxf.center = Mock(x=0.0, y=0.0)

        large_circle = Mock()
        large_circle.dxf.radius = 5.0
        large_circle.dxf.center = Mock(x=0.0, y=0.0)

        with patch("dxfto.process.objectdata_factory.isinstance") as mock_isinstance:

            def isinstance_side_effect(_, cls):
                from ezdxf.entities.circle import Circle

                return cls == Circle

            mock_isinstance.side_effect = isinstance_side_effect

            dimensions, points = factory_with_blocks._analyze_circular_block([small_circle, large_circle])

        assert isinstance(dimensions, RoundDimensions)
        assert dimensions.diameter == 10.0  # Largest circle diameter
        assert len(points) == 1
        assert points[0] == Point3D(east=0.0, north=0.0, altitude=0.0)

    def test_default_block_dimensions_round_name(self, factory_with_blocks):
        """Test default dimensions for round block names."""
        entity = Mock()
        entity.dxf.name = "ROUND_SHAFT_123"

        dimensions, points = factory_with_blocks._default_block_dimensions(entity)

        assert isinstance(dimensions, RoundDimensions)
        assert dimensions.diameter == 800.0
        assert points == []

    def test_default_block_dimensions_rect_name(self, factory_with_blocks):
        """Test default dimensions for non-round block names."""
        entity = Mock()
        entity.dxf.name = "RECT_DISTRIBUTOR"

        dimensions, _ = factory_with_blocks._default_block_dimensions(entity)

        assert isinstance(dimensions, RectangularDimensions)
        assert dimensions.length == 600.0
        assert dimensions.width == 600.0

    def test_transform_block_geometry(self, factory_with_blocks):
        """Test transformation of block geometry to world coordinates."""
        points = [
            Point3D(east=0.0, north=0.0, altitude=0.0),
            Point3D(east=5.0, north=5.0, altitude=0.0),
        ]

        entity = Mock()
        entity.dxf.insert = Mock(x=10.0, y=20.0)

        transformed = factory_with_blocks._transform_block_geometry(points, entity)

        assert len(transformed) == 2
        assert transformed[0] == Point3D(east=10.0, north=20.0, altitude=0.0)
        assert transformed[1] == Point3D(east=15.0, north=25.0, altitude=0.0)

    def test_transform_empty_geometry(self, factory_with_blocks):
        """Test transformation of empty geometry."""
        points = []
        entity = Mock()

        transformed = factory_with_blocks._transform_block_geometry(points, entity)

        assert transformed == []
