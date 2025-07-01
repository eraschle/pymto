"""Tests for the LandXMLReader class."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dxfto.io.landxml_reader import LandXMLReader
from dxfto.models import Point3D


class TestLandXMLReader:
    """Test LandXMLReader class."""

    @pytest.fixture
    def mock_landxml_path(self, tmp_path):
        """Create a mock LandXML file path."""
        return tmp_path / "test.xml"

    @pytest.fixture
    def sample_elevation_points(self):
        """Sample elevation points for testing."""
        return [
            Point3D(east=0.0, north=0.0, altitude=100.0),
            Point3D(east=10.0, north=0.0, altitude=105.0),
            Point3D(east=0.0, north=10.0, altitude=110.0),
            Point3D(east=10.0, north=10.0, altitude=115.0),
        ]

    @pytest.fixture
    def reader_with_points(self, mock_landxml_path, sample_elevation_points):
        """Create a LandXMLReader with mock elevation points."""
        reader = LandXMLReader(mock_landxml_path)
        reader.elevation_points = sample_elevation_points

        # Build KDTree manually
        xy_points = np.array([(p.east, p.north) for p in sample_elevation_points])
        from scipy.spatial import KDTree

        reader._kdtree = KDTree(xy_points)

        return reader

    def test_reader_initialization(self, mock_landxml_path):
        """Test reader initialization."""
        reader = LandXMLReader(mock_landxml_path)
        assert reader.landxml_path == mock_landxml_path
        assert reader.elevation_points == []
        assert reader._kdtree is None

    def test_get_elevation_no_points_loaded(self, mock_landxml_path):
        """Test get_elevation when no points are loaded."""
        reader = LandXMLReader(mock_landxml_path)

        with pytest.raises(RuntimeError, match="Elevation points not loaded"):
            reader.get_elevation(5.0, 5.0)

    def test_get_elevation_single_nearest_point(self, reader_with_points):
        """Test get_elevation with single nearest point scenario."""
        # Mock KDTree to return single index instead of array
        with patch.object(reader_with_points._kdtree, "query") as mock_query:
            # Simulate single nearest point case
            mock_query.return_value = (2.5, 0)  # distance, single index

            result = reader_with_points.get_elevation(1.0, 1.0)

            # Should return altitude of first point (index 0)
            assert result == 100.0

    def test_get_elevation_interpolation_center_point(self, reader_with_points):
        """Test get_elevation with interpolation at center of square."""
        # Query point at center of the 4 elevation points
        result = reader_with_points.get_elevation(5.0, 5.0)

        # At center of square, all points are equidistant
        # Expected interpolated value should be average: (100+105+110+115)/4 = 107.5
        expected = 107.5
        assert abs(result - expected) < 0.1  # Allow small floating point error

    def test_get_elevation_interpolation_weighted(self, reader_with_points):
        """Test get_elevation with weighted interpolation closer to one point."""
        # Query point closer to first elevation point (0,0) with altitude 100
        result = reader_with_points.get_elevation(1.0, 1.0)

        # Should be closer to 100 due to weighting
        assert result < 107.5  # Less than center average
        assert result > 100.0  # But greater than nearest point

    def test_get_elevation_interpolation_corner_cases(self, reader_with_points):
        """Test get_elevation at exact elevation point locations."""
        # Test at exact point locations
        assert reader_with_points.get_elevation(0.0, 0.0) == pytest.approx(100.0, abs=0.1)
        assert reader_with_points.get_elevation(10.0, 0.0) == pytest.approx(105.0, abs=0.1)
        assert reader_with_points.get_elevation(0.0, 10.0) == pytest.approx(110.0, abs=0.1)
        assert reader_with_points.get_elevation(10.0, 10.0) == pytest.approx(115.0, abs=0.1)

    def test_get_elevation_weights_calculation(self, reader_with_points):
        """Test that the weighted calculation is working correctly."""
        # Test point closer to bottom-left corner (0,0,100)
        x, y = 2.0, 2.0
        result = reader_with_points.get_elevation(x, y)

        # Manually calculate expected result
        points = reader_with_points.elevation_points
        distances = [np.sqrt((x - p.east) ** 2 + (y - p.north) ** 2) for p in points]

        # Inverse distance weighting
        weights = [1.0 / (d + 1e-10) for d in distances]
        total_weight = sum(weights)
        expected = sum(w * p.altitude for w, p in zip(weights, points, strict=True)) / total_weight

        assert abs(result - expected) < 0.001

    def test_get_elevation_different_query_points(self, reader_with_points):
        """Test get_elevation returns different values for different query points."""
        # Test several different points to ensure interpolation varies
        results = []
        test_points = [(2, 2), (5, 5), (8, 8), (3, 7)]

        for x, y in test_points:
            result = reader_with_points.get_elevation(x, y)
            results.append(result)

        # All results should be different (within the range of our elevation points)
        assert len(set(results)) == len(results)  # All unique
        assert all(100.0 <= r <= 115.0 for r in results)  # Within expected range

    def test_get_elevation_extrapolation(self, reader_with_points):
        """Test get_elevation outside the bounds of elevation points."""
        # Query point outside the elevation point bounds
        result = reader_with_points.get_elevation(-5.0, -5.0)

        # Should still return a reasonable value based on nearest points
        assert isinstance(result, float)
        # Since we're extrapolating, result might be outside original range
        assert 50.0 <= result <= 150.0  # Reasonable bounds

    @pytest.fixture
    def reader_with_single_point(self, mock_landxml_path):
        """Create a LandXMLReader with single elevation point."""
        reader = LandXMLReader(mock_landxml_path)
        reader.elevation_points = [Point3D(east=0.0, north=0.0, altitude=100.0)]

        # Build KDTree manually
        xy_points = np.array([(0.0, 0.0)])
        from scipy.spatial import KDTree

        reader._kdtree = KDTree(xy_points)

        return reader

    def test_get_elevation_single_point(self, reader_with_single_point):
        """Test get_elevation with only one elevation point."""
        # Any query should return the single point's altitude
        result = reader_with_single_point.get_elevation(5.0, 5.0)
        assert result == 100.0

        result = reader_with_single_point.get_elevation(-10.0, 20.0)
        assert result == 100.0

    def test_create_3d_point_coordinate_parsing(self, mock_landxml_path):
        """Test that _create_3d_point correctly parses coordinates."""
        reader = LandXMLReader(mock_landxml_path)
        
        # Test coordinate parsing with space-separated values
        # Format should be: north east altitude
        coords_text = "1183969.6 2811039.9 1436.56"
        point = reader._create_3d_point(coords_text)
        
        assert point is not None
        # First coordinate should be north, second east, third altitude
        assert point.north == 1183969.6
        assert point.east == 2811039.9
        assert point.altitude == 1436.56
        
        # Test with comma-separated values
        coords_text_comma = "1183969.6,2811039.9,1436.56"
        point_comma = reader._create_3d_point(coords_text_comma)
        
        assert point_comma is not None
        assert point_comma.north == 1183969.6
        assert point_comma.east == 2811039.9
        assert point_comma.altitude == 1436.56

    def test_real_landxml_coordinate_loading(self, tmp_path):
        """Test loading real LandXML data with correct coordinate parsing."""
        # Create a minimal LandXML file with real data format
        landxml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<LandXML xmlns="http://www.landxml.org/schema/LandXML-1.2">
    <Surfaces>
        <Surface name="Test DGM">
            <Definition surfType="TIN">
                <Pnts>
                    <P id="1">1184000.0 2811000.0 1440.0</P>
                    <P id="2">1184010.0 2811000.0 1445.0</P>
                    <P id="3">1184000.0 2811010.0 1442.0</P>
                    <P id="4">1184010.0 2811010.0 1447.0</P>
                </Pnts>
            </Definition>
        </Surface>
    </Surfaces>
</LandXML>'''
        
        # Write test LandXML file
        landxml_path = tmp_path / "test.xml"
        landxml_path.write_text(landxml_content)
        
        # Load and test
        reader = LandXMLReader(landxml_path)
        reader.load_file()
        
        # Verify points were loaded correctly
        assert len(reader.elevation_points) == 4
        
        # Check first point (coordinates should be correctly parsed as north, east, altitude)
        point1 = reader.elevation_points[0]
        assert point1.north == 1184000.0
        assert point1.east == 2811000.0
        assert point1.altitude == 1440.0
        
        # Test elevation interpolation at center of square
        # Center should be at (east=2811005.0, north=1184005.0) 
        result = reader.get_elevation(2811005.0, 1184005.0)
        
        # Center elevation should be average: (1440+1445+1442+1447)/4 = 1443.5
        expected = 1443.5
        assert abs(result - expected) < 0.1
        
        # Test that different coordinates give different elevations
        result1 = reader.get_elevation(2811002.0, 1184002.0)  # Closer to point1
        result2 = reader.get_elevation(2811008.0, 1184008.0)  # Closer to point4
        
        assert result1 != result2  # Should be different
        assert result1 < result2   # Result1 should be lower (closer to 1440)
