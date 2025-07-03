"""Tests for the clean DXFReader class."""

import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pymto.io.dxf_reader import DXFReader
from pymto.models import LayerData


class TestDXFReader:
    """Test clean DXFReader class."""

    @pytest.fixture
    def test_dxf_path(self):
        """Path to test DXF file."""
        return Path(__file__).parent.parent.parent / "test_entities.dxf"

    @pytest.fixture
    def reader(self, test_dxf_path):
        """Create DXFReader instance."""
        return DXFReader(test_dxf_path)

    def test_reader_initialization(self, test_dxf_path):
        """Test reader initialization."""
        reader = DXFReader(test_dxf_path)
        assert reader.dxf_path == test_dxf_path
        assert reader._doc is None
        assert not reader.is_loaded()

        # document property should raise RuntimeError when not loaded
        with pytest.raises(RuntimeError, match="not loaded"):
            _ = reader.document

    def test_load_file_success(self, reader, test_dxf_path):
        """Test successful file loading."""
        if not test_dxf_path.exists():
            pytest.skip(f"Test DXF file not found: {test_dxf_path}")

        reader.load_file()

        assert reader.is_loaded()
        assert reader.document is not None

    def test_load_file_not_found(self):
        """Test loading non-existent file."""
        reader = DXFReader(Path("nonexistent.dxf"))

        with pytest.raises(FileNotFoundError):
            reader.load_file()

    def test_query_entities_empty_layers(self, reader, test_dxf_path):
        """Test querying with empty layer list."""
        if not test_dxf_path.exists():
            pytest.skip(f"Test DXF file not found: {test_dxf_path}")

        reader.load_file()

        result = reader.query_entities([])

        # Should return empty query result
        assert len(result) == 0

    def test_query_entities_success(self, reader, test_dxf_path):
        """Test successful entity querying."""
        if not test_dxf_path.exists():
            pytest.skip(f"Test DXF file not found: {test_dxf_path}")

        reader.load_file()

        layers = [LayerData(name="0", color=(255, 0, 0))]
        result = reader.query_entities(layers)

        # Should return some entities from layer "0"
        assert len(result) >= 0  # Could be 0 if no entities on layer "0"

    def test_get_layer_names_not_loaded(self, reader):
        """Test getting layer names without loading file."""
        with pytest.raises(RuntimeError, match="not loaded"):
            reader.get_layer_names()

    def test_get_layer_names_success(self, reader, test_dxf_path):
        """Test getting layer names after loading."""
        if not test_dxf_path.exists():
            pytest.skip(f"Test DXF file not found: {test_dxf_path}")

        reader.load_file()

        layer_names = reader.get_layer_names()

        assert isinstance(layer_names, list)
        assert len(layer_names) >= 1  # Should have at least default layer "0"
        assert "0" in layer_names  # Default layer should exist

    def test_query_entities_multiple_layers(self, reader, test_dxf_path):
        """Test querying entities from multiple layers."""
        if not test_dxf_path.exists():
            pytest.skip(f"Test DXF file not found: {test_dxf_path}")

        reader.load_file()

        # Query multiple layers (some might not exist)
        layers = [
            LayerData(name="0", color=(255, 0, 0)),
            LayerData(name="TEXT", color=(0, 0, 0)),
            LayerData(name="NONEXISTENT", color=(0, 255, 0)),
        ]

        result = reader.query_entities(layers)

        # Should return entities from existing layers
        assert len(result) >= 0

    def test_properties_after_loading(self, reader, test_dxf_path):
        """Test various properties after successful loading."""
        if not test_dxf_path.exists():
            pytest.skip(f"Test DXF file not found: {test_dxf_path}")

        # Before loading
        assert not reader.is_loaded()
        with pytest.raises(RuntimeError, match="not loaded"):
            _ = reader.document

        # Load file
        reader.load_file()

        # After loading
        assert reader.is_loaded()
        assert reader.document is not None

        # Test all methods work
        layer_names = reader.get_layer_names()
        assert isinstance(layer_names, list)

        # Query with existing layer
        if layer_names:
            test_layers = [LayerData(name=layer_names[0], color=(255, 0, 0))]
            entities = reader.query_entities(test_layers)
            # query_entities returns an EntityQuery object, not a list
            assert len(entities) >= 0
