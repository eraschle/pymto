"""Integration tests for ObjectData factory using real DXF file."""

from pathlib import Path

import ezdxf.filemanagement as ezdxf
import pytest
from pymto.models import (
    MediumConfig,
    ObjectData,
    ObjectType,
    RectangularDimensions,
    RoundDimensions,
)
from pymto.process import factory
from pymto.process.factory import Insert, ObjectDataFactory
from ezdxf.document import Drawing


class TestIntegration:
    """Integration tests using the test DXF file."""

    @pytest.fixture
    def test_dxf_path(self):
        """Path to test DXF file."""
        return Path(__file__).parent.parent / "test_entities.dxf"

    @pytest.fixture
    def dxf_doc(self, test_dxf_path):
        """Load test DXF document."""
        if not test_dxf_path.exists():
            pytest.skip(f"Test DXF file not found: {test_dxf_path}")

        return ezdxf.readfile(str(test_dxf_path))

    @pytest.fixture
    def config(self):
        """Load test DXF document."""
        return MediumConfig(
            medium="TestMedium",
            geometry=[],
            text=[],
            family="TestFamily",
            family_type="TestType",
            elevation_offset=0.0,
            default_unit="mm",
            object_type=ObjectType.PIPE_WATER,
            object_id="TestObject",
        )

    @pytest.fixture
    def factory(self, dxf_doc):
        """Create ObjectDataFactory with test document."""
        return ObjectDataFactory(dxf_doc)

    def test_process_all_entities(self, factory: ObjectDataFactory, dxf_doc: Drawing, config: MediumConfig):
        """Test processing all entities in the test DXF file."""
        elements = []
        lines = []

        for entity in dxf_doc.modelspace():
            if entity.dxftype() == "TEXT":
                continue  # Skip text entities for this test

            is_element = factory.should_process_as_element(entity)
            obj_data = factory.create_from_entity(entity, config)

            if obj_data is not None:
                if is_element:
                    elements.append(obj_data)
                else:
                    lines.append(obj_data)

        # Verify we got the expected number of objects
        assert len(elements) >= 8  # At least 8 elements (circles, blocks, polylines)
        assert len(lines) >= 4  # At least 4 lines

        # Verify all objects are valid
        for element in elements:
            assert isinstance(element, ObjectData)
            assert element.dimensions is not None
            assert element.layer is not None
            assert element.color is not None

        element = elements[0]  # Take first element for further checks
        for line in lines:
            assert isinstance(line, ObjectData)
            assert element.dimensions is not None
            assert element.layer is not None
            assert element.color is not None

    def test_circle_entities(self, factory: ObjectDataFactory, dxf_doc: Drawing, config: MediumConfig):
        """Test processing of CIRCLE entities."""
        circle_objects = []

        for entity in dxf_doc.modelspace():
            if entity.dxftype() == "CIRCLE":
                obj_data = factory.create_from_entity(entity, config)
                if obj_data is not None:
                    circle_objects.append(obj_data)

        assert len(circle_objects) >= 2  # At least 2 circles in test file

        for obj in circle_objects:
            assert isinstance(obj.dimensions, RoundDimensions)
            assert obj.dimensions.diameter > 0
            assert len(obj.positions) == 1
            assert obj.positions[0] is not None

    def test_insert_entities(self, factory: ObjectDataFactory, dxf_doc: Drawing, config: MediumConfig):
        """Test processing of INSERT entities (blocks)."""
        insert_objects = []

        for entity in dxf_doc.modelspace():
            if entity.dxftype() == "INSERT":
                obj_data = factory.create_from_entity(entity, config)
                if obj_data is not None:
                    insert_objects.append(obj_data)

        assert len(insert_objects) >= 4  # At least 4 block references in test file

        for obj in insert_objects:
            assert obj.dimensions is not None
            assert len(obj.positions) == 1
            assert obj.positions[0] is not None

    def test_polyline_entities(self, factory: ObjectDataFactory, dxf_doc: Drawing, config: MediumConfig):
        """Test processing of POLYLINE/LWPOLYLINE entities."""
        polyline_objects = []

        for entity in dxf_doc.modelspace():
            if entity.dxftype() in ("POLYLINE", "LWPOLYLINE"):
                obj_data = factory.create_from_entity(entity, config)
                if obj_data is not None:
                    polyline_objects.append(obj_data)

        assert len(polyline_objects) >= 3  # At least 3 polylines in test file

        # Check for both element-type and line-type polylines
        element_polylines = [obj for obj in polyline_objects if obj.positions]
        line_polylines = [obj for obj in polyline_objects if obj.points and obj.positions]

        assert len(element_polylines) >= 2  # Complex polylines as elements
        assert len(line_polylines) >= 1  # Simple polylines as lines

    def test_line_entities(self, factory: ObjectDataFactory, dxf_doc: Drawing, config: MediumConfig):
        """Test processing of LINE entities."""
        line_objects = []

        for entity in dxf_doc.modelspace():
            if entity.dxftype() == "LINE":
                obj_data = factory.create_from_entity(entity, config)
                if obj_data is not None:
                    line_objects.append(obj_data)

        assert len(line_objects) >= 5  # At least 5 lines in test file

        for obj in line_objects:
            assert isinstance(obj.dimensions, RoundDimensions)
            assert obj.dimensions.diameter == 50.0 / 1000  # ObjectType.PIPE_WATER default is 50mm
            assert len(obj.points) == 2  # Lines have 2 points
            assert len(obj.positions) == 2  # Lines should have 2 positions

    def test_rectangular_shape_detection(self, factory: ObjectDataFactory, dxf_doc: Drawing, config: MediumConfig):
        """Test detection of rectangular shapes."""
        rectangular_objects = []

        for entity in dxf_doc.modelspace():
            if entity.dxftype() in ("POLYLINE", "LWPOLYLINE", "INSERT"):
                obj_data = factory.create_from_entity(entity, config)
                if obj_data is not None and isinstance(obj_data.dimensions, RectangularDimensions):
                    rectangular_objects.append(obj_data)

        assert len(rectangular_objects) >= 2  # At least 2 rectangular objects

        for obj in rectangular_objects:
            assert obj.dimensions.length > 0
            assert obj.dimensions.width > 0
            # Length may be either >= or <= width depending on orientation

    def test_round_shape_detection(self, factory: ObjectDataFactory, dxf_doc: Drawing, config: MediumConfig):
        """Test detection of round shapes."""
        round_objects = []

        for entity in dxf_doc.modelspace():
            obj_data = factory.create_from_entity(entity, config)
            if obj_data is not None and isinstance(obj_data.dimensions, RoundDimensions):
                round_objects.append(obj_data)

        assert len(round_objects) >= 6  # Circles, round blocks, and some polygons

        for obj in round_objects:
            assert obj.dimensions.diameter > 0

    def test_block_geometry_extraction(self, factory: ObjectDataFactory, dxf_doc: Drawing):
        """Test extraction of geometry from block definitions."""
        for entity in dxf_doc.modelspace():
            if isinstance(entity, Insert):
                block_entities = factory._get_block_entities(entity)
                # Block entities should be cached after first access
                cached_entities = factory._get_block_entities(entity)
                assert block_entities is cached_entities

                # Verify block analysis
                if block_entities:
                    analysis = factory._analyze_block_shape(entity, block_entities)
                    assert analysis is not None
                    dimensions, _ = analysis
                    assert dimensions is not None

    def test_color_extraction(self, dxf_doc: Drawing):
        """Test color extraction from entities."""
        for entity in dxf_doc.modelspace():
            if entity.dxftype() != "TEXT":
                color = factory._get_entity_color(entity)
                assert isinstance(color, tuple)
                assert len(color) == 3
                assert all(0 <= c <= 255 for c in color)

    def test_layer_extraction(self, factory: ObjectDataFactory, dxf_doc: Drawing, config: MediumConfig):
        """Test layer extraction from entities."""
        layers_found = set()

        for entity in dxf_doc.modelspace():
            if entity.dxftype() != "TEXT":
                obj_data = factory.create_from_entity(entity, config)
                if obj_data is not None:
                    layers_found.add(obj_data.layer)

        assert len(layers_found) >= 1  # At least one layer
        assert all(isinstance(layer, str) for layer in layers_found)

    def test_entity_classification_consistency(
        self, factory: ObjectDataFactory, dxf_doc: Drawing, config: MediumConfig
    ):
        """Test that entity classification is consistent."""
        for entity in dxf_doc.modelspace():
            if entity.dxftype() == "TEXT":
                continue

            is_element = factory.should_process_as_element(entity)
            obj_data = factory.create_from_entity(entity, config)

            if obj_data is not None:
                if is_element:
                    # Elements should have positions
                    assert obj_data.positions, f"Element {entity.dxftype()} should have positions"
                else:
                    # Lines should have points but no positions
                    assert obj_data.points, f"Line {entity.dxftype()} should have points"
                    assert len(obj_data.positions) == 2, f"Line {entity.dxftype()} should have 2 positions"
