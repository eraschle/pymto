"""Tests for grouping strategies."""

import json
import tempfile
from pathlib import Path

import pytest

from dxfto.groupers import ColorBasedGrouper, LayerBasedGrouper
from dxfto.models import (
    DXFText,
    Pipe,
    Point3D,
    RoundDimensions,
    Shaft,
    ShapeType,
)


class TestLayerBasedGrouper:
    """Test LayerBasedGrouper."""
    
    def test_load_config(self):
        """Test loading configuration from JSON file."""
        config_data = {
            "Abwasserleitung": {
                "Leitung": {
                    "Layer": "PIPE_SEWER",
                    "Farbe": [255, 0, 0]
                },
                "Schacht": {
                    "Layer": "SHAFT_SEWER",
                    "Farbe": [200, 0, 0]
                },
                "Text": {
                    "Layer": "TEXT_SEWER",
                    "Farbe": [255, 100, 100]
                }
            },
            "Wasserleitung": {
                "Leitung": {
                    "Layer": "PIPE_WATER"
                },
                "Schacht": {
                    "Layer": "SHAFT_WATER"
                },
                "Text": {
                    "Layer": "TEXT_WATER"
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_path = Path(f.name)
        
        try:
            grouper = LayerBasedGrouper(config_path)
            grouper.load_config()
            
            assert len(grouper.medium_configs) == 2
            assert "Abwasserleitung" in grouper.medium_configs
            assert "Wasserleitung" in grouper.medium_configs
            
            # Check Abwasserleitung config
            sewer_config = grouper.medium_configs["Abwasserleitung"]
            assert sewer_config.pipe_layer == "PIPE_SEWER"
            assert sewer_config.shaft_layer == "SHAFT_SEWER"
            assert sewer_config.text_layer == "TEXT_SEWER"
            assert sewer_config.pipe_color == (255, 0, 0)
            assert sewer_config.shaft_color == (200, 0, 0)
            assert sewer_config.text_color == (255, 100, 100)
            
            # Check Wasserleitung config (no colors)
            water_config = grouper.medium_configs["Wasserleitung"]
            assert water_config.pipe_layer == "PIPE_WATER"
            assert water_config.shaft_layer == "SHAFT_WATER"
            assert water_config.text_layer == "TEXT_WATER"
            assert water_config.pipe_color is None
            assert water_config.shaft_color is None
            assert water_config.text_color is None
        
        finally:
            config_path.unlink()
    
    def test_load_config_file_not_found(self):
        """Test loading config with non-existent file."""
        grouper = LayerBasedGrouper(Path("nonexistent.json"))
        
        with pytest.raises(FileNotFoundError):
            grouper.load_config()
    
    def test_group_elements(self):
        """Test grouping elements by layer configuration."""
        # Create test data
        pipes = [
            Pipe(
                shape=ShapeType.ROUND,
                points=[Point3D(x=0.0, y=0.0, z=0.0)],
                dimensions=RoundDimensions(diameter=200.0),
                layer="PIPE_SEWER",
                color=(255, 0, 0)
            ),
            Pipe(
                shape=ShapeType.ROUND,
                points=[Point3D(x=10.0, y=0.0, z=0.0)],
                dimensions=RoundDimensions(diameter=150.0),
                layer="PIPE_WATER",
                color=(0, 0, 255)
            ),
            Pipe(
                shape=ShapeType.ROUND,
                points=[Point3D(x=20.0, y=0.0, z=0.0)],
                dimensions=RoundDimensions(diameter=100.0),
                layer="UNKNOWN_LAYER",
                color=(0, 255, 0)
            )
        ]
        
        shafts = [
            Shaft(
                shape=ShapeType.ROUND,
                position=Point3D(x=0.0, y=0.0, z=0.0),
                dimensions=RoundDimensions(diameter=1000.0),
                layer="SHAFT_SEWER",
                color=(200, 0, 0)
            ),
            Shaft(
                shape=ShapeType.ROUND,
                position=Point3D(x=10.0, y=0.0, z=0.0),
                dimensions=RoundDimensions(diameter=800.0),
                layer="SHAFT_WATER",
                color=(0, 0, 200)
            )
        ]
        
        texts = [
            DXFText(
                content="DN200",
                position=Point3D(x=1.0, y=1.0, z=0.0),
                layer="TEXT_SEWER",
                color=(255, 100, 100)
            ),
            DXFText(
                content="DN150",
                position=Point3D(x=11.0, y=1.0, z=0.0),
                layer="TEXT_WATER",
                color=(100, 100, 255)
            )
        ]
        
        # Create config
        config_data = {
            "Abwasserleitung": {
                "Leitung": {"Layer": "PIPE_SEWER"},
                "Schacht": {"Layer": "SHAFT_SEWER"},
                "Text": {"Layer": "TEXT_SEWER"}
            },
            "Wasserleitung": {
                "Leitung": {"Layer": "PIPE_WATER"},
                "Schacht": {"Layer": "SHAFT_WATER"},
                "Text": {"Layer": "TEXT_WATER"}
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_path = Path(f.name)
        
        try:
            grouper = LayerBasedGrouper(config_path)
            grouper.load_config()
            media = grouper.group_elements(pipes, shafts, texts)
            
            assert len(media) == 2
            
            # Find media by name
            sewer_medium = next(m for m in media if m.name == "Abwasserleitung")
            water_medium = next(m for m in media if m.name == "Wasserleitung")
            
            # Check sewer medium
            assert len(sewer_medium.pipes) == 1
            assert len(sewer_medium.shafts) == 1
            assert len(sewer_medium.texts) == 1
            assert sewer_medium.pipes[0].layer == "PIPE_SEWER"
            assert sewer_medium.shafts[0].layer == "SHAFT_SEWER"
            assert sewer_medium.texts[0].layer == "TEXT_SEWER"
            
            # Check water medium
            assert len(water_medium.pipes) == 1
            assert len(water_medium.shafts) == 1
            assert len(water_medium.texts) == 1
            assert water_medium.pipes[0].layer == "PIPE_WATER"
            assert water_medium.shafts[0].layer == "SHAFT_WATER"
            assert water_medium.texts[0].layer == "TEXT_WATER"
        
        finally:
            config_path.unlink()
    
    def test_group_elements_with_color_matching(self):
        """Test grouping with both layer and color matching."""
        pipes = [
            Pipe(
                shape=ShapeType.ROUND,
                points=[Point3D(x=0.0, y=0.0, z=0.0)],
                dimensions=RoundDimensions(diameter=200.0),
                layer="PIPE_SEWER",
                color=(255, 0, 0)  # Correct color
            ),
            Pipe(
                shape=ShapeType.ROUND,
                points=[Point3D(x=10.0, y=0.0, z=0.0)],
                dimensions=RoundDimensions(diameter=200.0),
                layer="PIPE_SEWER",
                color=(0, 255, 0)  # Wrong color
            )
        ]
        
        config_data = {
            "Abwasserleitung": {
                "Leitung": {
                    "Layer": "PIPE_SEWER",
                    "Farbe": [255, 0, 0]  # Only red pipes should match
                },
                "Schacht": {"Layer": "SHAFT_SEWER"},
                "Text": {"Layer": "TEXT_SEWER"}
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_path = Path(f.name)
        
        try:
            grouper = LayerBasedGrouper(config_path)
            grouper.load_config()
            media = grouper.group_elements(pipes, [], [])
            
            assert len(media) == 1
            assert len(media[0].pipes) == 1  # Only the red pipe should be included
            assert media[0].pipes[0].color == (255, 0, 0)
        
        finally:
            config_path.unlink()


class TestColorBasedGrouper:
    """Test ColorBasedGrouper."""
    
    def test_color_distance(self):
        """Test color distance calculation."""
        grouper = ColorBasedGrouper()
        
        # Same colors
        distance = grouper._color_distance((255, 0, 0), (255, 0, 0))
        assert distance == 0.0
        
        # Different colors
        distance = grouper._color_distance((255, 0, 0), (0, 255, 0))
        assert distance > 0.0
        
        # Close colors
        distance = grouper._color_distance((255, 0, 0), (250, 5, 5))
        assert distance < 10.0
    
    def test_group_similar_colors(self):
        """Test grouping similar colors."""
        grouper = ColorBasedGrouper(color_tolerance=20.0)
        
        colors = [
            (255, 0, 0),    # Red
            (250, 5, 5),    # Close to red
            (0, 255, 0),    # Green
            (5, 250, 5),    # Close to green
            (0, 0, 255),    # Blue
        ]
        
        color_groups = grouper._group_similar_colors(colors)
        
        # Should have 3 groups: red-like, green-like, blue
        assert len(color_groups) == 3
        
        # Find groups by checking if they contain specific colors
        red_group = next(g for g in color_groups if (255, 0, 0) in g)
        green_group = next(g for g in color_groups if (0, 255, 0) in g)
        blue_group = next(g for g in color_groups if (0, 0, 255) in g)
        
        assert len(red_group) == 2  # (255,0,0) and (250,5,5)
        assert len(green_group) == 2  # (0,255,0) and (5,250,5)
        assert len(blue_group) == 1  # (0,0,255)
    
    def test_group_elements(self):
        """Test grouping elements by color."""
        pipes = [
            Pipe(
                shape=ShapeType.ROUND,
                points=[Point3D(x=0.0, y=0.0, z=0.0)],
                dimensions=RoundDimensions(diameter=200.0),
                layer="PIPE1",
                color=(255, 0, 0)  # Red
            ),
            Pipe(
                shape=ShapeType.ROUND,
                points=[Point3D(x=10.0, y=0.0, z=0.0)],
                dimensions=RoundDimensions(diameter=200.0),
                layer="PIPE2",
                color=(250, 5, 5)  # Close to red
            ),
            Pipe(
                shape=ShapeType.ROUND,
                points=[Point3D(x=20.0, y=0.0, z=0.0)],
                dimensions=RoundDimensions(diameter=200.0),
                layer="PIPE3",
                color=(0, 255, 0)  # Green
            )
        ]
        
        shafts = [
            Shaft(
                shape=ShapeType.ROUND,
                position=Point3D(x=0.0, y=0.0, z=0.0),
                dimensions=RoundDimensions(diameter=1000.0),
                layer="SHAFT1",
                color=(200, 0, 0)  # Dark red
            ),
            Shaft(
                shape=ShapeType.ROUND,
                position=Point3D(x=20.0, y=0.0, z=0.0),
                dimensions=RoundDimensions(diameter=1000.0),
                layer="SHAFT2",
                color=(0, 200, 0)  # Dark green
            )
        ]
        
        texts = [
            DXFText(
                content="DN200",
                position=Point3D(x=1.0, y=1.0, z=0.0),
                layer="TEXT1",
                color=(255, 100, 100)  # Light red
            ),
            DXFText(
                content="DN150",
                position=Point3D(x=21.0, y=1.0, z=0.0),
                layer="TEXT2",
                color=(100, 255, 100)  # Light green
            )
        ]
        
        grouper = ColorBasedGrouper(color_tolerance=50.0)
        media = grouper.group_elements(pipes, shafts, texts)
        
        # Should create media for similar color groups
        assert len(media) >= 2
        
        # Check that elements with similar colors are grouped together
        # This is a simplified check - in practice you'd verify specific groupings
        total_elements = sum(
            len(medium.pipes) + len(medium.shafts) + len(medium.texts)
            for medium in media
        )
        assert total_elements == len(pipes) + len(shafts) + len(texts)
    
    def test_color_to_medium_name(self):
        """Test color to medium name conversion."""
        grouper = ColorBasedGrouper()
        
        # Test primary colors
        assert "Rot" in grouper._color_to_medium_name((255, 0, 0))
        assert "Grün" in grouper._color_to_medium_name((0, 255, 0))
        assert "Blau" in grouper._color_to_medium_name((0, 0, 255))
        
        # Test dark colors
        assert "Dunkel" in grouper._color_to_medium_name((100, 0, 0))
        
        # Test other colors
        assert "Gelb" in grouper._color_to_medium_name((200, 200, 0))
        assert "Schwarz" in grouper._color_to_medium_name((10, 10, 10))
        assert "Weiß" in grouper._color_to_medium_name((250, 250, 250))