"""JSON export functionality for Revit-compatible data format.

This module handles exporting processed DXF data (pipes, shafts, texts)
to JSON format suitable for Revit modeling import.
"""

import json
from pathlib import Path
from typing import Any

from ..models import DxfText, Medium, ObjectData, Point3D, RectangularDimensions, RoundDimensions


class JsonExporter:
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

    def export_data(self, mediums: list[Medium]) -> None:
        export_data = {}

        for medium in mediums:
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
            Medium containing elements and lines

        Returns
        -------
        list[dict[str, Any]]
            List of elements (pipes and shafts) in the medium
        """
        elements = []

        # Export elements (shafts)
        for element in medium.element_data.elements:
            if element.positions:
                elements.append(self._export_point_element(element))
            else:
                elements.append(self._export_line_element(element))

        # Export lines (pipes)
        for line in medium.line_data.elements:
            elements.append(self._export_line_element(line))

        return elements

    def _export_line_element(self, element: ObjectData) -> dict[str, Any]:
        """Export a pipe to dictionary format.

        Parameters
        ----------
        element : ObjectData
            Element to export

        Returns
        -------
        dict[str, Any]
            Dictionary containing pipe information
        """
        pipe_data = {
            "type": "pipe",
            "layer": element.layer,
            # "color": self._export_color(element.color),
            "points": [self._export_point(point) for point in element.points],
            "dimensions": self._export_dimensions(element.dimensions),
        }

        # Add assigned text if available
        if element.assigned_text is not None:
            pipe_data["assigned_text"] = self._export_text(element.assigned_text)

        return pipe_data

    def _export_point_element(self, element: ObjectData) -> dict[str, Any]:
        """Export a shaft to dictionary format.

        Parameters
        ----------
        element : ObjectData
            Element to export

        Returns
        -------
        dict[str, Any]
            Dictionary containing shaft information
        """

        element_data = {
            "type": "shaft",
            "layer": element.layer,
            # "color": self._export_color(element.color),
            "position": self._export_point(element.positions[0]),
            "dimensions": self._export_dimensions(element.dimensions),
        }

        # Add assigned text if available
        if element.assigned_text is not None:
            element_data["assigned_text"] = self._export_text(element.assigned_text)

        return element_data

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
        return {"x": point.east, "y": point.north, "z": point.altitude}

    def _export_dimensions(self, dimensions: RectangularDimensions | RoundDimensions) -> dict[str, Any]:
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
            dim_data = {
                "type": "round",
                "diameter": dimensions.diameter,
            }

            if dimensions.height is not None:
                dim_data["height"] = dimensions.height

            return dim_data

    def _export_color(self, color: tuple[int, int, int]) -> dict[str, int]:
        """Export color to dictionary format.

        Parameters
        ----------
        color : tuple[int, int, int]
            RGB color tuple

        Returns
        -------
        dict[str, int]
            Dictionary with r, g, b values
        """
        return {"r": color[0], "g": color[1], "b": color[2]}

    def _export_text(self, text: DxfText) -> dict[str, Any]:
        """Export a text element to dictionary format.

        Parameters
        ----------
        text : DxfText
            Text to export

        Returns
        -------
        dict[str, Any]
            Dictionary containing text information
        """
        return {
            "content": text.content,
            # "layer": text.layer,
            # "position": self._export_point(text.position),
        }


class AsIsDataJsonExporter(JsonExporter):
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
        pipes = []
        shafts = []

        # Separate elements and lines for Revit export
        for element in medium.element_data.elements:
            if element.positions:
                shafts.append(self._export_shaft_revit(element))
            else:
                pipes.append(self._export_pipe_revit(element))

        for line in medium.line_data.elements:
            pipes.append(self._export_pipe_revit(line))

        return {
            "pipes": pipes,
            "shafts": shafts,
            "metadata": {
                "pipe_count": len(medium.line_data.elements),
                "shaft_count": len([e for e in medium.element_data.elements if e.positions]),
                "text_count": len(medium.element_data.texts) + len(medium.line_data.texts),
            },
        }

    def _export_pipe_revit(self, pipe: ObjectData) -> dict[str, Any]:
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
        pipe_data = self._export_line_element(pipe)

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

    def _export_shaft_revit(self, shaft: ObjectData) -> dict[str, Any]:
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
        shaft_data = self._export_point_element(shaft)

        # Add Revit-specific metadata
        shaft_data["revit_metadata"] = {}

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
            dx = p2.east - p1.east
            dy = p2.north - p1.north
            dz = p2.altitude - p1.altitude

            segment_length = (dx**2 + dy**2 + dz**2) ** 0.5
            total_length += segment_length

        return total_length
