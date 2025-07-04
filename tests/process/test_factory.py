#!/usr/bin/env python3
"""Unit tests for ObjectDataFactory."""

from unittest.mock import Mock, patch

import pytest
from ezdxf.entities.insert import Insert
from pymto.models import LayerData, MediumConfig, ObjectType, Parameter
from pymto.process.factory import ObjectDataFactory


@pytest.fixture
def mock_doc():
    """Create mock ezdxf document."""
    doc = Mock()
    doc.blocks = Mock()
    return doc


@pytest.fixture
def factory(mock_doc):
    """Create ObjectDataFactory instance."""
    return ObjectDataFactory(mock_doc)


@pytest.fixture
def shaft_config():
    """Create shaft config."""
    return MediumConfig(
        medium="shaft_medium",
        geometry=[LayerData(name="0", color=(255, 0, 0))],
        text=[LayerData(name="TEXT", color=(0, 0, 0))],
        default_unit="mm",
        object_type=ObjectType.SHAFT,
        family="ShaftFamily",
        family_type="ShaftType",
        elevation_offset=0.0,
        object_id="shaft_id",
    )


@pytest.fixture
def pipe_config():
    """Create pipe config."""
    return MediumConfig(
        medium="pipe_medium",
        geometry=[LayerData(name="PIPE", color=(0, 255, 0))],
        text=[LayerData(name="TEXT", color=(0, 0, 0))],
        default_unit="mm",
        object_type=ObjectType.PIPE_WASTEWATER,
        family="PipeFamily",
        family_type="PipeType",
        elevation_offset=0.0,
        object_id="pipe_id",
    )


class TestObjectDataFactory:
    """Test ObjectDataFactory class."""

    def test_factory_initialization(self, mock_doc):
        """Test factory initialization."""
        factory = ObjectDataFactory(mock_doc)
        assert factory.dxf_doc == mock_doc
        assert factory._block_cache == {}

    # Helper methods for creating mock entities
    def _create_mock_entity(self, entity_type: str, **dxf_attrs):
        """Create mock entity with DXF attributes."""
        entity = Mock()
        entity.dxftype.return_value = entity_type
        entity.dxf = Mock()
        for attr, value in dxf_attrs.items():
            setattr(entity.dxf, attr, value)
        return entity

    def _create_circle_entity(self, center=(0, 0, 0), radius=1.0, layer="0", color=1):
        """Create mock circle entity."""
        return self._create_mock_entity("CIRCLE", center=center, radius=radius, layer=layer, color=color)

    def _create_insert_entity(self, insert=(0, 0, 0), name="TEST_BLOCK", layer="0"):
        """Create mock insert entity."""
        return self._create_mock_entity("INSERT", insert=insert, name=name, layer=layer)

    def _create_line_entity(self, start=(0, 0, 0), end=(10, 0, 0), layer="0"):
        """Create mock line entity."""
        return self._create_mock_entity("LINE", start=start, end=end, layer=layer)

    def _create_polyline_entity(self, layer="0"):
        """Create mock polyline entity."""
        return self._create_mock_entity("LWPOLYLINE", layer=layer)


class TestFactoryRouting:
    """Test entity type routing in factory."""

    def test_circle_routing(self, factory, shaft_config):
        """Test CIRCLE entity routing."""
        circle = self._create_circle_entity()

        with patch.object(factory, "_create_from_circle") as mock_create:
            mock_create.return_value = Mock()
            factory.create_from_entity(circle, shaft_config)
            mock_create.assert_called_once_with(circle, shaft_config)

    def test_insert_routing(self, factory, shaft_config):
        """Test INSERT entity routing."""
        insert = self._create_insert_entity()

        with patch.object(factory, "_create_from_insert") as mock_create:
            mock_create.return_value = Mock()
            factory.create_from_entity(insert, shaft_config)
            mock_create.assert_called_once_with(insert, shaft_config)

    def test_line_routing(self, factory, pipe_config):
        """Test LINE entity routing."""
        line = self._create_line_entity()

        with patch.object(factory, "_create_from_line") as mock_create:
            mock_create.return_value = Mock()
            factory.create_from_entity(line, pipe_config)
            mock_create.assert_called_once_with(line, pipe_config)

    def test_polyline_routing(self, factory, shaft_config):
        """Test POLYLINE entity routing."""
        polyline = self._create_polyline_entity()

        with patch.object(factory, "_create_from_polyline") as mock_create:
            mock_create.return_value = Mock()
            factory.create_from_entity(polyline, shaft_config)
            mock_create.assert_called_once_with(polyline, shaft_config)

    def test_unsupported_entity(self, factory, shaft_config):
        """Test unsupported entity type."""
        entity = Mock()
        entity.dxftype.return_value = "UNSUPPORTED"

        result = factory.create_from_entity(entity, shaft_config)
        assert result is None

    def test_error_handling(self, factory, shaft_config):
        """Test error handling during entity processing."""
        entity = Mock()
        entity.dxftype.side_effect = [Exception("Test error"), "UNKNOWN"]

        result = factory.create_from_entity(entity, shaft_config)
        assert result is None

    # Helper methods (shared with TestObjectDataFactory)
    def _create_mock_entity(self, entity_type: str, **dxf_attrs):
        """Create mock entity with DXF attributes."""
        entity = Mock()
        entity.dxftype.return_value = entity_type
        entity.dxf = Mock()
        for attr, value in dxf_attrs.items():
            setattr(entity.dxf, attr, value)
        return entity

    def _create_circle_entity(self, center=(0, 0, 0), radius=1.0, layer="0", color=1):
        """Create mock circle entity."""
        return self._create_mock_entity("CIRCLE", center=center, radius=radius, layer=layer, color=color)

    def _create_insert_entity(self, insert=(0, 0, 0), name="TEST_BLOCK", layer="0"):
        """Create mock insert entity."""
        return self._create_mock_entity("INSERT", insert=insert, name=name, layer=layer)

    def _create_line_entity(self, start=(0, 0, 0), end=(10, 0, 0), layer="0"):
        """Create mock line entity."""
        return self._create_mock_entity("LINE", start=start, end=end, layer=layer)

    def _create_polyline_entity(self, layer="0"):
        """Create mock polyline entity."""
        return self._create_mock_entity("LWPOLYLINE", layer=layer)


class TestCircleProcessing:
    """Test circle entity processing."""

    def test_circle_creation_success(self, factory, shaft_config):
        """Test successful circle processing."""
        circle = Mock()
        circle.dxftype.return_value = "CIRCLE"
        circle.dxf = Mock()
        circle.dxf.center = (10.0, 20.0, 5.0)
        circle.dxf.radius = 2.5
        circle.dxf.layer = "SHAFTS"
        circle.dxf.color = 1

        # Mock the internal method to return a valid ObjectData
        with patch.object(factory, "_create_from_circle") as mock_create:
            from pymto.models import ObjectData, Point3D, RoundDimensions

            mock_obj = ObjectData(
                medium=shaft_config.medium,
                object_type=shaft_config.object_type,
                family=shaft_config.family,
                family_type=shaft_config.family_type,
                dimensions=RoundDimensions(diameter=5000),
                layer="SHAFTS",
                points=[Point3D(east=10000, north=20000, altitude=5000)],
                color=(255, 0, 0),
                object_id=Parameter(name="object_id", value=shaft_config.object_id),
            )
            mock_create.return_value = mock_obj

            result = factory.create_from_entity(circle, shaft_config)

            assert result is not None
            assert result.object_type == ObjectType.SHAFT
            assert result.dimensions.diameter == 5000
            assert result.medium == "shaft_medium"


class TestInsertProcessing:
    """Test INSERT (block reference) entity processing."""

    def test_insert_creation_success(self, factory, shaft_config):
        """Test successful INSERT processing."""
        insert = Mock(spec=Insert)
        insert.dxftype.return_value = "INSERT"
        insert.dxf = Mock()
        insert.dxf.insert = Mock()
        insert.dxf.insert.x = 15.0
        insert.dxf.insert.y = 25.0
        insert.dxf.name = "ROUND_SHAFT"
        insert.dxf.layer = "BLOCKS"

        # Mock successful processing
        with patch.object(factory, "_create_from_insert") as mock_create:
            from pymto.models import ObjectData, Point3D, RoundDimensions

            mock_obj = ObjectData(
                medium=shaft_config.medium,
                object_type=shaft_config.object_type,
                family=shaft_config.family,
                family_type=shaft_config.family_type,
                dimensions=RoundDimensions(diameter=3000),
                layer="BLOCKS",
                points=[Point3D(east=15000, north=25000, altitude=0)],
                color=(255, 0, 0),
                object_id=Parameter(name="object_id", value=shaft_config.object_id),
            )
            mock_create.return_value = mock_obj

            result = factory.create_from_entity(insert, shaft_config)

            assert result is not None
            assert result.object_type == ObjectType.SHAFT
            assert result.positions[0].east == 15000
            assert result.positions[0].north == 25000


class TestLineProcessing:
    """Test LINE entity processing."""

    def test_line_creation_success(self, factory, pipe_config):
        """Test successful LINE processing."""
        line = Mock()
        line.dxftype.return_value = "LINE"
        line.dxf = Mock()
        line.dxf.start = (0.0, 0.0, 0.0)
        line.dxf.end = (50.0, 0.0, 0.0)
        line.dxf.layer = "PIPES"

        # Mock successful processing
        with patch.object(factory, "_create_from_line") as mock_create:
            from pymto.models import ObjectData, Point3D, RoundDimensions

            mock_obj = ObjectData(
                medium=pipe_config.medium,
                object_type=pipe_config.object_type,
                family=pipe_config.family,
                family_type=pipe_config.family_type,
                dimensions=RoundDimensions(diameter=200),
                layer="PIPES",
                points=[
                    Point3D(east=0, north=0, altitude=0),
                    Point3D(east=50000, north=0, altitude=0),
                ],
                color=(0, 255, 0),
                object_id=Parameter(name="object_id", value=pipe_config.object_id),
            )
            mock_create.return_value = mock_obj

            result = factory.create_from_entity(line, pipe_config)

            assert result is not None
            assert result.object_type == ObjectType.PIPE_WASTEWATER
            assert len(result.points) == 2
            assert result.points[0].east == 0
            assert result.points[1].east == 50000


class TestConfigurationHandling:
    """Test configuration parameter handling."""

    def test_different_object_types(self, factory):
        """Test factory with different object types."""
        entity = Mock()
        entity.dxftype.return_value = "CIRCLE"

        configs = [
            MediumConfig(
                medium="test",
                geometry=[],
                text=[],
                family="F1",
                family_type="T1",
                elevation_offset=0.0,
                default_unit="mm",
                object_type=ObjectType.SHAFT,
                object_id="shaft_id",
            ),
            MediumConfig(
                medium="test",
                geometry=[],
                text=[],
                family="F2",
                family_type="T2",
                elevation_offset=0.0,
                default_unit="mm",
                object_type=ObjectType.PIPE_WATER,
                object_id="pipe_water_id",
            ),
            MediumConfig(
                medium="test",
                geometry=[],
                text=[],
                family="F3",
                family_type="T3",
                elevation_offset=0.0,
                default_unit="mm",
                object_type=ObjectType.PIPE_WASTEWATER,
                object_id="pipe_wastewater_id",
            ),
        ]

        for config in configs:
            with patch.object(factory, "_create_from_circle") as mock_create:
                mock_create.return_value = Mock()
                factory.create_from_entity(entity, config)
                mock_create.assert_called_once_with(entity, config)

    def test_unit_handling(self, factory):
        """Test different unit configurations."""
        entity = Mock()
        entity.dxftype.return_value = "CIRCLE"

        for unit in ["mm", "m", "cm"]:
            config = MediumConfig(
                medium="test",
                geometry=[],
                text=[],
                family="F",
                family_type="T",
                elevation_offset=0.0,
                default_unit=unit,
                object_type=ObjectType.SHAFT,
                object_id="shaft_id",
            )

            with patch.object(factory, "_create_from_circle") as mock_create:
                mock_create.return_value = Mock()
                factory.create_from_entity(entity, config)
                mock_create.assert_called_once_with(entity, config)
