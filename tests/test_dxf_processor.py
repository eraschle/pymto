"""Tests for the DXFProcessor orchestrator class."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from pymto.config import ConfigurationHandler
from pymto.models import Medium
from pymto.processor import DXFProcessor
from pymto.protocols import (
    IAssignmentStrategy,
    IParameterUpdater,
    IElevationUpdater,
    IExporter,
    IObjectCreator,
    IRevitFamilyNameUpdater,
)


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
def mock_extractor():
    """Create mock object creator."""
    return Mock(spec=IObjectCreator)


@pytest.fixture
def processor(config):
    """Create DXFProcessor instance."""
    return DXFProcessor(config)


class TestDXFProcessor:
    """Test DXFProcessor class."""

    def test_processor_initialization(self, processor, config):
        """Test processor initialization."""
        assert processor.config == config

    def test_extract_mediums(self, processor: DXFProcessor, mock_extractor: Mock):
        """Test extracting mediums using object creator."""
        mock_extractor.create_objects.return_value = ([], [])
        processor.extract_mediums(mock_extractor)

        # Verify extractor was called for each medium's point and line configs
        expected_calls = len(processor.config.mediums) * 2  # point + line configs
        assert mock_extractor.create_objects.call_count == expected_calls

    def test_assign_texts_to_mediums(self, processor: DXFProcessor):
        """Test assigning texts to mediums."""
        assigner = Mock(spec=IAssignmentStrategy)
        processor.assign_texts_to_mediums(assigner)

        # Verify assigner was called for each medium
        assert assigner.texts_to_point_based.call_count == len(processor.config.mediums)
        assert assigner.texts_to_line_based.call_count == len(processor.config.mediums)

    def test_update_dimensions(self, processor: DXFProcessor):
        """Test updating dimensions."""
        updater = Mock(spec=IParameterUpdater)
        processor.update_dimensions(updater)

        # Verify updater was called for each medium's point and line data
        expected_calls = len(processor.config.mediums) * 2
        assert updater.update_elements.call_count == expected_calls

    def test_update_points_elevation(self, processor: DXFProcessor):
        """Test updating elevation."""
        updater = Mock(spec=IElevationUpdater)
        processor.update_points_elevation(updater)

        # Verify updater was called for each medium's point and line data
        expected_calls = len(processor.config.mediums) * 2
        assert updater.update_elements.call_count == expected_calls

    def test_update_family_and_types(self, processor: DXFProcessor):
        """Test updating family and types."""
        updater = Mock(spec=IRevitFamilyNameUpdater)
        processor.update_family_and_types(updater)

        # Verify updater was called for each medium's point and line data
        expected_calls = len(processor.config.mediums) * 2
        assert updater.update_elements.call_count == expected_calls

    def test_export_data(self, processor: DXFProcessor):
        """Test exporting data."""
        exporter = Mock(spec=IExporter)
        processor.export_data(exporter)

        # Verify exporter was called with list of mediums
        exporter.export_data.assert_called_once()
        args = exporter.export_data.call_args[0][0]
        assert len(args) == len(processor.config.mediums)

    def test_mediums_property(self, processor: DXFProcessor):
        """Test mediums property returns all mediums."""
        mediums = list(processor.mediums)
        assert len(mediums) == len(processor.config.mediums)
        for medium in mediums:
            assert isinstance(medium, Medium)
