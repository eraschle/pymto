"""Tests for the DXFEntityExtractor class."""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dxfto.io.entity_extractor import DXFEntityExtractor
from dxfto.models import LayerData, MediumConfig


class TestDXFEntityExtractor:
    """Test DXFEntityExtractor class."""

    @pytest.fixture
    def mock_reader(self):
        """Create mock DXF reader."""
        reader = Mock()
        return reader

    @pytest.fixture
    def extractor(self, mock_reader):
        """Create DXFEntityExtractor instance."""
        return DXFEntityExtractor(mock_reader)

    @pytest.fixture
    def test_config(self):
        """Create test assignment configuration."""
        geometry_layers = [LayerData(name="GEOMETRY", color=(255, 0, 0))]
        text_layers = [LayerData(name="TEXT", color=(0, 0, 0))]
        return MediumConfig(geometry=geometry_layers, text=text_layers)

    def test_extractor_initialization(self, mock_reader):
        """Test extractor initialization."""
        extractor = DXFEntityExtractor(mock_reader)
        assert extractor.reader == mock_reader

    def test_extract_entities_structure(self, extractor, test_config):
        """Test that extract_entities returns correct structure."""
        # Mock the reader to return empty results
        extractor.reader.query_entities.return_value = []

        result = extractor.extract_entities(test_config)

        assert isinstance(result, dict)
        assert "elements" in result
        assert "lines" in result
        assert "texts" in result
        assert isinstance(result["elements"], list)
        assert isinstance(result["lines"], list)
        assert isinstance(result["texts"], list)

    def test_extract_element_entities(self, extractor, test_config, mock_reader):
        """Test element entity extraction."""
        # Mock entities
        element_entity = Mock()
        element_entity.dxftype.return_value = "CIRCLE"

        line_entity = Mock()
        line_entity.dxftype.return_value = "LINE"

        mock_entities = [element_entity, line_entity]
        mock_reader.query_entities.return_value = mock_entities

        # Mock is_element_entity to return True for CIRCLE, False for LINE
        with pytest.MonkeyPatch().context() as m:

            def mock_is_element(entity):
                return entity.dxftype() == "CIRCLE"

            m.setattr("dxfto.io.entity_extractor.is_element_entity", mock_is_element)

            result = extractor._extract_element_entities(test_config)

        assert len(result) == 1
        assert result[0] == element_entity

    def test_extract_line_entities(self, extractor, test_config, mock_reader):
        """Test line entity extraction."""
        # Mock entities
        element_entity = Mock()
        element_entity.dxftype.return_value = "CIRCLE"

        line_entity = Mock()
        line_entity.dxftype.return_value = "LINE"

        mock_entities = [element_entity, line_entity]
        mock_reader.query_entities.return_value = mock_entities

        # Mock is_element_entity to return True for CIRCLE, False for LINE
        with pytest.MonkeyPatch().context() as m:

            def mock_is_element(entity):
                return entity.dxftype() == "CIRCLE"

            m.setattr("dxfto.io.entity_extractor.is_element_entity", mock_is_element)

            result = extractor._extract_line_entities(test_config)

        assert len(result) == 1
        assert result[0] == line_entity

    def test_extract_text_entities(self, extractor, test_config, mock_reader):
        """Test text entity extraction."""
        # Mock entities
        text_entity = Mock()
        text_entity.dxftype.return_value = "TEXT"

        mtext_entity = Mock()
        mtext_entity.dxftype.return_value = "MTEXT"

        circle_entity = Mock()
        circle_entity.dxftype.return_value = "CIRCLE"

        mock_entities = [text_entity, mtext_entity, circle_entity]
        mock_reader.query_entities.return_value = mock_entities

        result = extractor._extract_text_entities(test_config)

        assert len(result) == 2
        assert text_entity in result
        assert mtext_entity in result
        assert circle_entity not in result

    def test_extract_entities_empty_results(self, extractor, test_config, mock_reader):
        """Test extraction with no entities."""
        mock_reader.query_entities.return_value = []

        result = extractor.extract_entities(test_config)

        assert result["elements"] == []
        assert result["lines"] == []
        assert result["texts"] == []

    def test_extract_entities_mixed_types(self, extractor, test_config, mock_reader):
        """Test extraction with mixed entity types."""
        # Mock various entity types
        circle = Mock()
        circle.dxftype.return_value = "CIRCLE"

        line = Mock()
        line.dxftype.return_value = "LINE"

        text = Mock()
        text.dxftype.return_value = "TEXT"

        insert = Mock()
        insert.dxftype.return_value = "INSERT"

        # Configure mock to return different entities for different layer types
        def query_side_effect(layers):
            # Geometry layers get geometric entities, text layers get text entities
            layer_names = [layer.name for layer in layers]
            if "GEOMETRY" in layer_names:
                return [circle, line, insert]
            elif "TEXT" in layer_names:
                return [text]
            return []

        mock_reader.query_entities.side_effect = query_side_effect

        # Mock is_element_entity
        with pytest.MonkeyPatch().context() as m:

            def mock_is_element(entity):
                return entity.dxftype() in ("CIRCLE", "INSERT")

            m.setattr("dxfto.io.entity_extractor.is_element_entity", mock_is_element)

            result = extractor.extract_entities(test_config)

        # Should have 2 elements (CIRCLE, INSERT), 1 line (LINE), 1 text (TEXT)
        assert len(result["elements"]) == 2
        assert len(result["lines"]) == 1
        assert len(result["texts"]) == 1

        assert circle in result["elements"]
        assert insert in result["elements"]
        assert line in result["lines"]
        assert text in result["texts"]
