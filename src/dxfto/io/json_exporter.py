"""JSON export functionality for Revit-compatible data format.

This module handles exporting processed DXF data (pipes, shafts, texts)
to JSON format suitable for Revit modeling import.
"""

import abc
import json
from pathlib import Path
from typing import Any

from ..models import (
    DXFText,
    Medium,
    Pipe,
    Point3D,
    RectangularDimensions,
    RoundDimensions,
    Shaft,
    ShapeType,
)


class JSONExporter(abc.ABC):
    """Exports processed DXF data to JSON format for Revit compatibility.

    The exported JSON format organizes data by medium with detailed
    information for each pipe and shaft element.
    """

    def __init__(self, output_path: Path) -> None:
        """Initialize JSON exporter with output file path.

        Parameters
        ----------
        output_path : Path
            Path where the JSON file will be saved
        """
        self.output_path = output_path

    def export_media(self, media: list[Medium]) -> None:
        """Export list of media to JSON file.

        Parameters
        ----------
        media : list[Medium]
            List of media containing pipes, shafts, and texts

        Raises
        ------
        IOError
            If the output file cannot be written
        """
        export_data = {}

        for medium in media:
            export_data[medium.name] = self._export_medium(medium)

        try:
            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            raise OSError(f"Cannot write JSON file {self.output_path}: {e}") from e

    def _export_medium(self, medium: Medium) -> list[dict[str, Any]]:
        """Export a single medium to dictionary format.

        Parameters
        ----------
        medium : Medium
            Medium containing pipes, shafts, and texts

        Returns
        -------
        list[dict[str, Any]]
            List of elements (pipes and shafts) in the medium
        """
        elements = []

        # Export pipes
        for pipe in medium.pipes:
            elements.append(self._export_pipe(pipe))

        # Export shafts
        for shaft in medium.shafts:
            elements.append(self._export_shaft(shaft))

        return elements

    def _export_pipe(self, pipe: Pipe) -> dict[str, Any]:
        """Export a pipe to dictionary format.

        Parameters
        ----------
        pipe : Pipe
            Pipe to export

        Returns
        -------
        dict[str, Any]
            Dictionary containing pipe information
        """
        pipe_data = {
            "type": "pipe",
            "shape": pipe.shape.value,
            "layer": pipe.layer,
            "color": {"r": pipe.color[0], "g": pipe.color[1], "b": pipe.color[2]},
            "points": [self._export_point(point) for point in pipe.points],
            "dimensions": self._export_dimensions(pipe.dimensions),
        }

        # Add assigned text if available
        if pipe.assigned_text is not None:
            pipe_data["assigned_text"] = self._export_text(pipe.assigned_text)

        return pipe_data

    def _export_shaft(self, shaft: Shaft) -> dict[str, Any]:
        """Export a shaft to dictionary format.

        Parameters
        ----------
        shaft : Shaft
            Shaft to export

        Returns
        -------
        dict[str, Any]
            Dictionary containing shaft information
        """
        return {
            "type": "shaft",
            "shape": shaft.shape.value,
            "layer": shaft.layer,
            "color": {"r": shaft.color[0], "g": shaft.color[1], "b": shaft.color[2]},
            "position": self._export_point(shaft.position),
            "dimensions": self._export_dimensions(shaft.dimensions),
        }

    def _export_point(self, point: Point3D) -> dict[str, float]:
        """Export a 3D point to dictionary format.

        Parameters
        ----------
        point : Point3D
            Point to export

        Returns
        -------
        dict[str, float]
            Dictionary with x, y, z coordinates
        """
        return {"x": point.x, "y": point.y, "z": point.z}

    def _export_dimensions(
        self, dimensions: RectangularDimensions | RoundDimensions
    ) -> dict[str, Any]:
        """Export dimensions to dictionary format.

        Parameters
        ----------
        dimensions : RectangularDimensions | RoundDimensions
            Dimensions to export

        Returns
        -------
        dict[str, Any]
            Dictionary containing dimension information
        """
        if isinstance(dimensions, RectangularDimensions):
            dim_data = {
                "type": "rectangular",
                "length": dimensions.length,
                "width": dimensions.width,
                "angle": dimensions.angle,
            }

            if dimensions.height is not None:
                dim_data["height"] = dimensions.height

            return dim_data

        elif isinstance(dimensions, RoundDimensions):
            dim_data = {"type": "round", "diameter": dimensions.diameter}

            if dimensions.height is not None:
                dim_data["height"] = dimensions.height

            return dim_data

        else:
            raise ValueError(f"Unknown dimension type: {type(dimensions)}")

    def _export_text(self, text: DXFText) -> dict[str, Any]:
        """Export a text element to dictionary format.

        Parameters
        ----------
        text : DXFText
            Text to export

        Returns
        -------
        dict[str, Any]
            Dictionary containing text information
        """
        return {
            "content": text.content,
            "layer": text.layer,
            "color": {"r": text.color[0], "g": text.color[1], "b": text.color[2]},
            "position": self._export_point(text.position),
        }


class AsIsDataJsonExporter(JSONExporter):
    """Specialized JSON exporter with Revit-specific formatting.

    This exporter formats the JSON output specifically for Revit
    modeling requirements, with additional metadata and formatting.
    """

    def export_media(self, media: list[Medium]) -> None:
        """Export media with Revit-specific formatting.

        Parameters
        ----------
        media : list[Medium]
            List of media containing pipes, shafts, and texts
        """
        export_data = {
            "version": "1.0",
            "format": "revit_compatible",
            "units": "mm",  # Assuming millimeters as default unit
            "media": {},
        }

        for medium in media:
            export_data["media"][medium.name] = self._export_medium_revit(medium)

        try:
            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            raise OSError(f"Cannot write JSON file {self.output_path}: {e}") from e

    def _export_medium_revit(self, medium: Medium) -> dict[str, Any]:
        """Export medium with Revit-specific structure.

        Parameters
        ----------
        medium : Medium
            Medium to export

        Returns
        -------
        dict[str, Any]
            Dictionary with pipes and shafts separated
        """
        return {
            "pipes": [self._export_pipe_revit(pipe) for pipe in medium.pipes],
            "shafts": [self._export_shaft_revit(shaft) for shaft in medium.shafts],
            "metadata": {
                "pipe_count": len(medium.pipes),
                "shaft_count": len(medium.shafts),
                "text_count": len(medium.texts),
            },
        }

    def _export_pipe_revit(self, pipe: Pipe) -> dict[str, Any]:
        """Export pipe with Revit-specific formatting.

        Parameters
        ----------
        pipe : Pipe
            Pipe to export

        Returns
        -------
        dict[str, Any]
            Dictionary with Revit-compatible pipe data
        """
        pipe_data = self._export_pipe(pipe)

        # Add Revit-specific metadata
        pipe_data["revit_metadata"] = {
            "family": "Pipe",
            "system_type": "Sanitary",  # Default system type
            "level": "Level 1",  # Default level
            "routing_preferences": "Standard",
        }

        # Add path information for Revit routing
        if len(pipe.points) >= 2:
            pipe_data["path_length"] = self._calculate_path_length(pipe.points)
            pipe_data["start_point"] = self._export_point(pipe.points[0])
            pipe_data["end_point"] = self._export_point(pipe.points[-1])

        return pipe_data

    def _export_shaft_revit(self, shaft: Shaft) -> dict[str, Any]:
        """Export shaft with Revit-specific formatting.

        Parameters
        ----------
        shaft : Shaft
            Shaft to export

        Returns
        -------
        dict[str, Any]
            Dictionary with Revit-compatible shaft data
        """
        shaft_data = self._export_shaft(shaft)

        # Add Revit-specific metadata
        shaft_data["revit_metadata"] = {
            "family": "Generic Model" if shaft.shape == ShapeType.RECTANGULAR else "Pipe Accessory",
            "category": "Plumbing Fixtures",
            "level": "Level 1",
            "workset": "Plumbing",
        }

        return shaft_data

    def _calculate_path_length(self, points: list[Point3D]) -> float:
        """Calculate total length of a path defined by points.

        Parameters
        ----------
        points : list[Point3D]
            List of points defining the path

        Returns
        -------
        float
            Total path length
        """
        if len(points) < 2:
            return 0.0

        total_length = 0.0

        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]

            # Calculate 3D distance between consecutive points
            dx = p2.x - p1.x
            dy = p2.y - p1.y
            dz = p2.z - p1.z

            segment_length = (dx**2 + dy**2 + dz**2) ** 0.5
            total_length += segment_length

        return total_length
