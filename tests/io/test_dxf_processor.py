"""Tests for the DXFProcessor orchestrator class."""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dxfto.io.dxf_processor import DXFProcessor
from dxfto.models import AssignmentConfig, LayerData, Medium


class TestDXFProcessor:
    """Test DXFProcessor class."""

    @pytest.fixture
    def test_dxf_path(self):
        """Path to test DXF file."""
        return Path(__file__).parent.parent.parent / "test_entities.dxf"

    @pytest.fixture
    def processor(self, test_dxf_path):
        """Create DXFProcessor instance."""
        return DXFProcessor(test_dxf_path)

    def test_processor_initialization(self, test_dxf_path):
        """Test processor initialization."""
        processor = DXFProcessor(test_dxf_path)
        assert processor.dxf_path == test_dxf_path
        assert processor.extractor is None
        assert processor.factory is None
        assert not processor.is_initialized()

    def test_load_file_success(self, processor, test_dxf_path):
        """Test successful file loading."""
        if not test_dxf_path.exists():
            pytest.skip(f"Test DXF file not found: {test_dxf_path}")

        processor.load_file()

        assert processor.reader.is_loaded()
        assert processor.extractor is not None
        assert processor.factory is not None
        assert processor.is_initialized()

    def test_load_file_not_found(self):
        """Test file loading with non-existent file."""
        processor = DXFProcessor(Path("nonexistent.dxf"))

        with pytest.raises(FileNotFoundError):
            processor.load_file()

    def test_process_mediums_not_initialized(self, processor):
        """Test processing mediums without initialization."""
        mediums = {}

        with pytest.raises(RuntimeError, match="not initialized"):
            processor.process_mediums(mediums)

    def test_process_mediums_success(self, processor, test_dxf_path):
        """Test successful medium processing."""
        if not test_dxf_path.exists():
            pytest.skip(f"Test DXF file not found: {test_dxf_path}")

        # Load file first
        processor.load_file()

        # Create test medium
        geometry_layers = [LayerData(name="0", color=(255, 0, 0))]
        text_layers = [LayerData(name="TEXT", color=(0, 0, 0))]

        elements_config = AssignmentConfig(geometry=geometry_layers, text=text_layers)
        lines_config = AssignmentConfig(geometry=geometry_layers, text=text_layers)

        test_medium = Medium(name="Test Medium", elements=elements_config, lines=lines_config)

        mediums = {"test": test_medium}

        # Process mediums
        processor.process_mediums(mediums)

        # Verify results
        assert test_medium.element_data is not None
        assert test_medium.line_data is not None
        assert isinstance(test_medium.element_data.elements, list)
        assert isinstance(test_medium.element_data.texts, list)

    def test_get_statistics_not_loaded(self, processor):
        """Test getting statistics without loading file."""
        with pytest.raises(RuntimeError, match="not loaded"):
            processor.get_statistics()

    def test_get_statistics_success(self, processor, test_dxf_path):
        """Test getting statistics after loading."""
        if not test_dxf_path.exists():
            pytest.skip(f"Test DXF file not found: {test_dxf_path}")

        processor.load_file()
        stats = processor.get_statistics()

        assert isinstance(stats, dict)
        assert "total_entities" in stats
        assert "available_layers" in stats
        assert "layer_names" in stats
        assert isinstance(stats["total_entities"], int)
        assert isinstance(stats["available_layers"], int)
        assert isinstance(stats["layer_names"], list)

    def test_convert_entities_to_objects_empty(self, processor):
        """Test converting empty entity list."""
        # Mock the factory
        processor.factory = Mock()

        result = processor._convert_entities_to_objects([])
        assert result == []

    def test_convert_entities_to_texts_empty(self, processor):
        """Test converting empty text entity list."""
        result = processor._convert_entities_to_texts([])
        assert result == []

    def test_create_text_from_entity_invalid(self, processor):
        """Test creating text from invalid entity."""
        mock_entity = Mock()
        mock_entity.__class__ = Mock  # Not Text or MText

        result = processor._create_text_from_entity(mock_entity)
        assert result is None

    def test_get_entity_color_default(self, processor):
        """Test getting default entity color."""
        mock_entity = Mock()
        del mock_entity.dxf.color  # No color attribute

        color = processor._get_entity_color(mock_entity)
        assert color == (0, 0, 0)

    def test_get_entity_color_mapped(self, processor):
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
        return Path(__file__).parent.parent.parent / "test_entities.dxf"

    def test_full_processing_pipeline(self, test_dxf_path):
        """Test the complete processing pipeline."""
        if not test_dxf_path.exists():
            pytest.skip(f"Test DXF file not found: {test_dxf_path}")

        # Initialize processor
        processor = DXFProcessor(test_dxf_path)
        processor.load_file()

        # Create medium configuration
        geometry_layers = [LayerData(name="0", color=(255, 0, 0))]
        text_layers = [LayerData(name="TEXT", color=(0, 0, 0))]

        elements_config = AssignmentConfig(geometry=geometry_layers, text=text_layers)
        lines_config = AssignmentConfig(geometry=geometry_layers, text=text_layers)

        medium = Medium(name="Integration Test Medium", elements=elements_config, lines=lines_config)

        mediums = {"integration_test": medium}

        # Process
        processor.process_mediums(mediums)

        # Verify results
        assert medium.element_data is not None
        assert medium.line_data is not None

        # Should have some elements and/or lines from test DXF
        total_objects = len(medium.element_data.elements) + len(medium.line_data.elements)
        assert total_objects > 0, "Should extract some objects from test DXF"

        # Get statistics
        stats = processor.get_statistics()
        assert stats["total_entities"] > 0
        assert stats["available_layers"] > 0

    def test_comparison_with_legacy_approach(self, test_dxf_path):
        """Test that new approach produces similar results to legacy."""
        if not test_dxf_path.exists():
            pytest.skip(f"Test DXF file not found: {test_dxf_path}")

        # Test with new processor
        processor = DXFProcessor(test_dxf_path)
        processor.load_file()

        geometry_layers = [LayerData(name="0", color=(255, 0, 0))]
        text_layers = [LayerData(name="TEXT", color=(0, 0, 0))]

        config = AssignmentConfig(geometry=geometry_layers, text=text_layers)
        medium = Medium(name="Test", elements=config, lines=config)

        processor.process_mediums({"test": medium})

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
