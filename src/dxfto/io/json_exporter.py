"""JSON export functionality for Revit-compatible data format.

This module handles exporting processed DXF data (pipes, shafts, texts)
to JSON format suitable for Revit modeling import.
"""

import json
from pathlib import Path
from typing import Any

from ..models import (
    DxfText,
    Medium,
    MediumConfig,
    ObjectData,
    Point3D,
    RectangularDimensions,
    RoundDimensions,
)


def _export_point(point: Point3D) -> dict[str, float]:
    return {"x": point.east, "y": point.north, "z": point.altitude}


def _export_points(points: list[Point3D]) -> dict | list[dict] | None:
    """Export a list of Point3D to a list of dictionaries."""
    points = [point for point in points if point is not None]
    point_data = [_export_point(point) for point in points]
    if len(point_data) == 0:
        return None
    if len(point_data) == 1:
        return point_data[0]
    return point_data


def _export_color(color: tuple[int, int, int]) -> dict[str, int]:
    return {"r": color[0], "g": color[1], "b": color[2]}


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
            with open(self.output_path, "w", encoding="utf-8") as json_file:
                json.dump(export_data, json_file, indent=2, ensure_ascii=False)
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
        elem_export = []
        point_based_data = self._get_element_data(medium.element_data.assigned)
        elem_export.extend(point_based_data)

        line_based_data = self._get_element_data(medium.line_data.assigned)
        elem_export.extend(line_based_data)
        return elem_export

    def _get_element_data(
        self, element_data: list[tuple[list[ObjectData], MediumConfig]]
    ) -> list[dict[str, Any]]:
        """Export elements and texts to dictionary format.

        Parameters
        ----------
        element_data : list[tuple[list[ObjectData], list[DxfText]]]
            List of tuples containing elements and their associated texts

        Returns
        -------
        list[dict[str, Any]]
            List of dictionaries containing element and text information
        """
        elements_export_data = []

        for elements, _ in element_data:
            export_data = [self._export_element(elem) for elem in elements]
            elements_export_data.extend(export_data)
        return elements_export_data

    def _export_element(self, element: ObjectData) -> dict[str, Any]:
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
        element_data = {
            "object_type": element.object_type.name.upper(),
            "layer_name": element.layer,
            "dimensions": self._export_dimensions(element.dimensions),
        }
        assigned_text = element.assigned_text
        if assigned_text is not None:
            if assigned_text.content is None:
                assigned_text.content = ""
            element_data["text"] = assigned_text.content.strip()

        if element.positions:
            element_points = _export_points(element.positions)
        else:
            element_points = _export_points(element.points)

        if element_points is not None:
            element_data["points"] = element_points

        return element_data

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
        dimension_data = {}
        if isinstance(dimensions, RectangularDimensions):
            dimension_data = {
                "length": dimensions.length,
                "width": dimensions.width,
                "angle": dimensions.angle,
            }
        elif isinstance(dimensions, RoundDimensions):
            dimension_data = {
                "radius": dimensions.diameter / 2,
                "diameter": dimensions.diameter,
            }

        if dimensions.height is not None:
            dimension_data["height"] = dimensions.height
        return dimension_data
