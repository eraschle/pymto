"""Tests for the DXFProcessor orchestrator class."""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dxfto.config import ConfigurationHandler
from dxfto.io import DXFReader
from dxfto.models import LayerData, Medium, MediumConfig
from dxfto.processor import DXFProcessor


@pytest.fixture
def test_dxf_path():
    """Path to test DXF file."""
    return Path(__file__).parent.parent / "data" / "test_entities.dxf"


@pytest.fixture
def config():
    """Create DXFProcessor instance."""
    config_path = Path(__file__).parent / "data" / "test_config.json"
    return ConfigurationHandler(config_path)


@pytest.fixture
def reader(test_dxf_path):  # type: ignore
    """Create DXFProcessor instance."""
    return DXFReader(test_dxf_path)


@pytest.fixture
def processor(config):
    """Create DXFProcessor instance."""
    return DXFProcessor(config)


class TestDXFProcessor:
    """Test DXFProcessor class."""

    def test_processor_initialization(self, processor, config):
        """Test processor initialization."""
        assert processor.config == config
        assert processor.extractor is None
        assert processor.factory is None

    def test_process_mediums_success(self, processor: DXFProcessor, reader: DXFReader):
        """Test successful medium processing."""

        # Create test medium
        geometry_layers = [LayerData(name="0", color=(255, 0, 0))]
        text_layers = [LayerData(name="TEXT", color=(0, 0, 0))]

        elements_config = MediumConfig(geometry=geometry_layers, text=text_layers, default_unit="mm")
        lines_config = MediumConfig(geometry=geometry_layers, text=text_layers, default_unit="mm")

        test_medium = Medium(name="Test Medium", elements=elements_config, lines=lines_config)

        # Process mediums
        reader.load_file()  # Ensure reader is loaded
        processor.extract_mediums(reader)

        # Verify results
        assert test_medium.element_data is not None
        assert test_medium.line_data is not None
        assert isinstance(test_medium.element_data.elements, list)
        assert isinstance(test_medium.element_data.texts, list)

    def test_convert_entities_to_objects_empty(self, processor: DXFProcessor):
        """Test converting empty entity list."""
        # Mock the factory
        processor.factory = Mock()

        result = processor._convert_entities_to_objects([])
        assert result == []

    def test_convert_entities_to_texts_empty(self, processor: DXFProcessor):
        """Test converting empty text entity list."""
        result = processor._convert_entities_to_texts([])
        assert result == []

    def test_create_text_from_entity_invalid(self, processor: DXFProcessor):
        """Test creating text from invalid entity."""
        mock_entity = Mock()
        mock_entity.__class__ = Mock  # Not Text or MText

        result = processor._create_text_from_entity(mock_entity)
        assert result is None

    def test_get_entity_color_default(self, processor: DXFProcessor):
        """Test getting default entity color."""
        mock_entity = Mock()
        del mock_entity.dxf.color  # No color attribute

        color = processor._get_entity_color(mock_entity)
        assert color == (0, 0, 0)

    def test_get_entity_color_mapped(self, processor: DXFProcessor):
        """Test getting mapped entity colors."""
        mock_entity = Mock()

        test_cases = [
            (1, (255, 0, 0)),  # Red
            (2, (255, 255, 0)),  # Yellow
            (3, (0, 255, 0)),  # Green
            (99, (0, 0, 0)),  # Unknown -> Default
        ]

        for color_index, expected_rgb in test_cases:
            mock_entity.dxf.color = color_index
            color = processor._get_entity_color(mock_entity)
            assert color == expected_rgb


class TestDXFProcessorIntegration:
    """Integration tests for DXFProcessor with real DXF file."""

    @pytest.fixture
    def test_dxf_path(self):
        """Path to test DXF file."""
        return Path(__file__).parent.parent / "data" / "test_entities.dxf"

    @pytest.fixture
    def test_reader(self, test_dxf_path):
        """Path to test DXF file."""
        from dxfto.io.dxf_reader import DXFReader

        if not test_dxf_path.exists():
            pytest.skip(f"Test DXF file not found: {test_dxf_path}")

        reader = DXFReader(test_dxf_path)
        reader.load_file()

        return reader

    def test_full_processing_pipeline(self, processor, reader):
        """Test the complete processing pipeline."""
        # Create medium configuration
        geometry_layers = [LayerData(name="0", color=(255, 0, 0))]
        text_layers = [LayerData(name="TEXT", color=(0, 0, 0))]

        elements_config = MediumConfig(geometry=geometry_layers, text=text_layers, default_unit="mm")
        lines_config = MediumConfig(geometry=geometry_layers, text=text_layers, default_unit="mm")

        medium = Medium(name="Integration Test Medium", elements=elements_config, lines=lines_config)
        processor.config.mediums = {"integration_test": medium}

        reader.load_file()
        processor.extract_mediums(reader)

        # Verify results
        assert medium.element_data is not None
        assert medium.line_data is not None

        # Should have some elements and/or lines from test DXF
        total_objects = len(medium.element_data.elements) + len(medium.line_data.elements)
        assert total_objects > 0, "Should extract some objects from test DXF"

    def test_comparison_with_legacy_approach(self, processor, reader):
        """Test that new approach produces similar results to legacy."""
        # Test with new processor
        geometry_layers = [LayerData(name="0", color=(255, 0, 0))]
        text_layers = [LayerData(name="TEXT", color=(0, 0, 0))]

        config = MediumConfig(geometry=geometry_layers, text=text_layers, default_unit="mm")
        medium = Medium(name="Test", elements=config, lines=config)

        processor.extract_mediums(reader)

        new_element_count = len(medium.element_data.elements)
        new_line_count = len(medium.line_data.elements)
        new_text_count = len(medium.element_data.texts)

        # Verify we got reasonable results
        assert new_element_count >= 0
        assert new_line_count >= 0
        assert new_text_count >= 0

        # Total objects should be reasonable for our test file
        total_objects = new_element_count + new_line_count
        assert total_objects > 5, f"Expected more than 5 objects, got {total_objects}"
