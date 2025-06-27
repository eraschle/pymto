"""Tests for the DXFProcessor orchestrator class."""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dxfto.config import ConfigurationHandler
from dxfto.io import DXFReader
from dxfto.models import LayerData, Medium, MediumConfig, MediumMasterConfig, ObjectType
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

        elements_config = MediumConfig(
            medium="test_medium",
            geometry=geometry_layers,
            text=text_layers,
            default_unit="mm",
            object_type=ObjectType.UNKNOWN,
        )
        lines_config = MediumConfig(
            medium="test_medium",
            geometry=geometry_layers,
            text=text_layers,
            default_unit="mm",
            object_type=ObjectType.UNKNOWN,
        )
        master = MediumMasterConfig(
            medium="test_medium",
            point_based=[elements_config],
            line_based=[lines_config],
        )
        test_medium = Medium(name="Test Medium", config=master)

        # Process mediums
        reader.load_file()  # Ensure reader is loaded
        processor.extract_mediums(reader)

        # Verify results
        assert test_medium.element_data is not None
        assert test_medium.line_data is not None
        assert isinstance(test_medium.config, MediumMasterConfig)
        point_based_config = test_medium.config.point_based
        assert isinstance(point_based_config, list)
        assert len(point_based_config) == 1
        point_config = test_medium.config.point_based[0]
        assert point_config == elements_config

        line_based_config = test_medium.config.line_based
        assert isinstance(line_based_config, list)
        assert len(line_based_config) == 1
        line_config = test_medium.config.line_based[0]
        assert line_config == lines_config

    def test_convert_entities_to_objects_empty(self, processor: DXFProcessor):
        """Test converting empty entity list."""
        # Mock the factory
        processor.factory = Mock()

        result = processor._convert_to_objects(
            medium="test_medium",
            entities=[],
            object_type=ObjectType.UNKNOWN,
        )
        assert result == []

    def test_convert_entities_to_texts_empty(self, processor: DXFProcessor):
        """Test converting empty text entity list."""
        result = processor._convert_to_texts(
            medium="test_medium",
            entities=[],
        )
        assert result == []

    def test_create_text_from_entity_invalid(self, processor: DXFProcessor):
        """Test creating text from invalid entity."""
        mock_entity = Mock()
        mock_entity.__class__ = Mock  # Not Text or MText

        result = processor._create_text_from(
            medium="test_medium",
            entity=mock_entity,
        )
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
