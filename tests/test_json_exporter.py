"""Tests for JSON export functionality."""

import json
import tempfile
from pathlib import Path

import pytest

from dxfto.io.json_exporter import JSONExporter, AsIsDataJSONExporter
from dxfto.models import (
    DXFText,
    Medium,
    Pipe,
    Point3D,
    RectangularDimensions,
    RoundDimensions,
    Shaft,
    ShapeType,
)


class TestJSONExporter:
    """Test JSONExporter."""

    def test_export_point(self):
        """Test exporting a Point3D."""
        exporter = JSONExporter(Path("dummy.json"))
        point = Point3D(x=10.5, y=20.3, z=5.0)

        result = exporter._export_point(point)

        assert result == {"x": 10.5, "y": 20.3, "z": 5.0}

    def test_export_round_dimensions(self):
        """Test exporting round dimensions."""
        exporter = JSONExporter(Path("dummy.json"))

        # With height
        dims_with_height = RoundDimensions(diameter=200.0, height=100.0)
        result = exporter._export_dimensions(dims_with_height)

        assert result == {"type": "round", "diameter": 200.0, "height": 100.0}

        # Without height
        dims_without_height = RoundDimensions(diameter=300.0)
        result = exporter._export_dimensions(dims_without_height)

        assert result == {"type": "round", "diameter": 300.0}

    def test_export_rectangular_dimensions(self):
        """Test exporting rectangular dimensions."""
        exporter = JSONExporter(Path("dummy.json"))

        # With height
        dims_with_height = RectangularDimensions(length=100.0, width=50.0, angle=45.0, height=25.0)
        result = exporter._export_dimensions(dims_with_height)

        assert result == {
            "type": "rectangular",
            "length": 100.0,
            "width": 50.0,
            "angle": 45.0,
            "height": 25.0,
        }

        # Without height
        dims_without_height = RectangularDimensions(length=200.0, width=75.0, angle=0.0)
        result = exporter._export_dimensions(dims_without_height)

        assert result == {"type": "rectangular", "length": 200.0, "width": 75.0, "angle": 0.0}

    def test_export_text(self):
        """Test exporting a DXFText."""
        exporter = JSONExporter(Path("dummy.json"))
        text = DXFText(
            content="DN200",
            position=Point3D(x=10.0, y=20.0, z=0.0),
            layer="TEXT_LAYER",
            color=(255, 0, 0),
        )

        result = exporter._export_text(text)

        assert result == {
            "content": "DN200",
            "layer": "TEXT_LAYER",
            "color": {"r": 255, "g": 0, "b": 0},
            "position": {"x": 10.0, "y": 20.0, "z": 0.0},
        }

    def test_export_pipe(self):
        """Test exporting a Pipe."""
        exporter = JSONExporter(Path("dummy.json"))

        points = [
            Point3D(x=0.0, y=0.0, z=0.0),
            Point3D(x=10.0, y=0.0, z=0.0),
            Point3D(x=10.0, y=10.0, z=0.0),
        ]

        text = DXFText(
            content="DN200", position=Point3D(x=5.0, y=1.0, z=0.0), layer="TEXT", color=(0, 0, 0)
        )

        pipe = Pipe(
            shape=ShapeType.ROUND,
            points=points,
            dimensions=RoundDimensions(diameter=200.0),
            layer="PIPE_LAYER",
            color=(255, 0, 0),
            assigned_text=text,
        )

        result = exporter._export_pipe(pipe)

        expected = {
            "type": "pipe",
            "shape": "round",
            "layer": "PIPE_LAYER",
            "color": {"r": 255, "g": 0, "b": 0},
            "points": [
                {"x": 0.0, "y": 0.0, "z": 0.0},
                {"x": 10.0, "y": 0.0, "z": 0.0},
                {"x": 10.0, "y": 10.0, "z": 0.0},
            ],
            "dimensions": {"type": "round", "diameter": 200.0},
            "assigned_text": {
                "content": "DN200",
                "layer": "TEXT",
                "color": {"r": 0, "g": 0, "b": 0},
                "position": {"x": 5.0, "y": 1.0, "z": 0.0},
            },
        }

        assert result == expected

    def test_export_pipe_without_text(self):
        """Test exporting a Pipe without assigned text."""
        exporter = JSONExporter(Path("dummy.json"))

        pipe = Pipe(
            shape=ShapeType.RECTANGULAR,
            points=[Point3D(x=0.0, y=0.0, z=0.0)],
            dimensions=RectangularDimensions(length=100.0, width=50.0, angle=0.0),
            layer="PIPE_LAYER",
            color=(0, 255, 0),
        )

        result = exporter._export_pipe(pipe)

        assert "assigned_text" not in result
        assert result["type"] == "pipe"
        assert result["shape"] == "rectangular"

    def test_export_shaft(self):
        """Test exporting a Shaft."""
        exporter = JSONExporter(Path("dummy.json"))

        shaft = Shaft(
            shape=ShapeType.ROUND,
            position=Point3D(x=10.0, y=20.0, z=5.0),
            dimensions=RoundDimensions(diameter=1000.0, height=2000.0),
            layer="SHAFT_LAYER",
            color=(0, 0, 255),
        )

        result = exporter._export_shaft(shaft)

        expected = {
            "type": "shaft",
            "shape": "round",
            "layer": "SHAFT_LAYER",
            "color": {"r": 0, "g": 0, "b": 255},
            "position": {"x": 10.0, "y": 20.0, "z": 5.0},
            "dimensions": {"type": "round", "diameter": 1000.0, "height": 2000.0},
        }

        assert result == expected

    def test_export_media_to_file(self):
        """Test exporting media to JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_path = Path(f.name)

        try:
            exporter = JSONExporter(output_path)

            # Create test data
            pipe = Pipe(
                shape=ShapeType.ROUND,
                points=[Point3D(x=0.0, y=0.0, z=0.0)],
                dimensions=RoundDimensions(diameter=200.0),
                layer="PIPE",
                color=(255, 0, 0),
            )

            shaft = Shaft(
                shape=ShapeType.ROUND,
                position=Point3D(x=0.0, y=0.0, z=0.0),
                dimensions=RoundDimensions(diameter=1000.0),
                layer="SHAFT",
                color=(200, 0, 0),
            )

            text = DXFText(
                content="DN200",
                position=Point3D(x=1.0, y=1.0, z=0.0),
                layer="TEXT",
                color=(255, 100, 100),
            )

            medium = Medium(name="Abwasserleitung", pipes=[pipe], shafts=[shaft], texts=[text])

            # Export to file
            exporter.export_media([medium])

            # Verify file was created and contains expected data
            assert output_path.exists()

            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert "Abwasserleitung" in data
            assert len(data["Abwasserleitung"]) == 2  # 1 pipe + 1 shaft

            # Find pipe and shaft in exported data
            pipe_data = next(item for item in data["Abwasserleitung"] if item["type"] == "pipe")
            shaft_data = next(item for item in data["Abwasserleitung"] if item["type"] == "shaft")

            assert pipe_data["shape"] == "round"
            assert pipe_data["layer"] == "PIPE"
            assert shaft_data["shape"] == "round"
            assert shaft_data["layer"] == "SHAFT"

        finally:
            output_path.unlink()


class TestRevitJSONExporter:
    """Test RevitJSONExporter."""

    def test_calculate_path_length(self):
        """Test path length calculation."""
        exporter = AsIsDataJSONExporter(Path("dummy.json"))

        # Simple straight line
        points = [Point3D(x=0.0, y=0.0, z=0.0), Point3D(x=10.0, y=0.0, z=0.0)]
        length = exporter._calculate_path_length(points)
        assert length == pytest.approx(10.0, abs=1e-6)

        # 3D path
        points = [
            Point3D(x=0.0, y=0.0, z=0.0),
            Point3D(x=3.0, y=4.0, z=0.0),  # Distance = 5
            Point3D(x=3.0, y=4.0, z=12.0),  # Distance = 12
        ]
        length = exporter._calculate_path_length(points)
        assert length == pytest.approx(17.0, abs=1e-6)  # 5 + 12

        # Single point
        points = [Point3D(x=0.0, y=0.0, z=0.0)]
        length = exporter._calculate_path_length(points)
        assert length == 0.0

    def test_export_pipe_revit(self):
        """Test Revit-specific pipe export."""
        exporter = AsIsDataJSONExporter(Path("dummy.json"))

        points = [Point3D(x=0.0, y=0.0, z=0.0), Point3D(x=10.0, y=0.0, z=0.0)]

        pipe = Pipe(
            shape=ShapeType.ROUND,
            points=points,
            dimensions=RoundDimensions(diameter=200.0),
            layer="PIPE_LAYER",
            color=(255, 0, 0),
        )

        result = exporter._export_pipe_revit(pipe)

        # Check Revit-specific metadata
        assert "revit_metadata" in result
        assert result["revit_metadata"]["family"] == "Pipe"
        assert result["revit_metadata"]["system_type"] == "Sanitary"

        # Check path information
        assert "path_length" in result
        assert result["path_length"] == pytest.approx(10.0, abs=1e-6)
        assert "start_point" in result
        assert "end_point" in result
        assert result["start_point"] == {"x": 0.0, "y": 0.0, "z": 0.0}
        assert result["end_point"] == {"x": 10.0, "y": 0.0, "z": 0.0}

    def test_export_shaft_revit(self):
        """Test Revit-specific shaft export."""
        exporter = AsIsDataJSONExporter(Path("dummy.json"))

        shaft = Shaft(
            shape=ShapeType.RECTANGULAR,
            position=Point3D(x=0.0, y=0.0, z=0.0),
            dimensions=RectangularDimensions(length=2000.0, width=1500.0, angle=0.0),
            layer="SHAFT_LAYER",
            color=(0, 0, 255),
        )

        result = exporter._export_shaft_revit(shaft)

        # Check Revit-specific metadata
        assert "revit_metadata" in result
        assert result["revit_metadata"]["family"] == "Generic Model"
        assert result["revit_metadata"]["category"] == "Plumbing Fixtures"

    def test_export_media_revit_format(self):
        """Test exporting media in Revit format."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_path = Path(f.name)

        try:
            exporter = AsIsDataJSONExporter(output_path)

            pipe = Pipe(
                shape=ShapeType.ROUND,
                points=[Point3D(x=0.0, y=0.0, z=0.0)],
                dimensions=RoundDimensions(diameter=200.0),
                layer="PIPE",
                color=(255, 0, 0),
            )

            medium = Medium(name="Abwasserleitung", pipes=[pipe], shafts=[], texts=[])

            exporter.export_media([medium])

            # Verify Revit format structure
            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert "version" in data
            assert "format" in data
            assert "units" in data
            assert "media" in data

            assert data["format"] == "revit_compatible"
            assert "Abwasserleitung" in data["media"]

            medium_data = data["media"]["Abwasserleitung"]
            assert "pipes" in medium_data
            assert "shafts" in medium_data
            assert "metadata" in medium_data

            metadata = medium_data["metadata"]
            assert metadata["pipe_count"] == 1
            assert metadata["shaft_count"] == 0
            assert metadata["text_count"] == 0

        finally:
            output_path.unlink()
