"""JSON export functionality for Revit-compatible data format.

This module handles exporting processed DXF data (pipes, shafts, texts)
to JSON format suitable for Revit modeling import.
"""

import json
from pathlib import Path
from typing import Any

from ..models import (
    Dimension,
    Medium,
    MediumConfig,
    ObjectData,
    Point3D,
)


def _export_point(point: Point3D) -> dict[str, float]:
    return {
        "east": point.east,
        "north": point.north,
        "altitude": point.altitude,
    }


def _export_points(points: list[Point3D]) -> dict | list[dict] | None:
    """Export a list of Point3D to a list of dictionaries."""
    points = [point for point in points if point is not None]
    point_data = [_export_point(point) for point in points]
    return point_data


def export_color(color: tuple[int, int, int]) -> dict[str, int]:
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
        self.exported_elements: dict[str, list[ObjectData]] = {}
        self.not_exported_elements: dict[str, list[ObjectData]] = {}

    def has_not_exported_elements(self) -> bool:
        """Check if there are any elements that were not exported.

        Returns
        -------
        bool
            True if there are not exported elements, False otherwise
        """
        if len(self.not_exported_elements) == 0:
            return False
        return any(len(elems) > 0 for elems in self.not_exported_elements.values())

    def export_data(self, mediums: list[Medium]) -> None:
        export_data = {}

        for medium in mediums:
            export_data[medium.name] = self._export_medium(medium)

        try:
            with open(self.output_path, "w", encoding="utf-8") as json_file:
                json.dump(export_data, json_file, indent=2, ensure_ascii=False)
        except OSError as e:
            raise OSError(f"Cannot write JSON file {self.output_path}: {e}") from e

    def get_exported_statistics(self) -> dict[str, Any]:
        """Get statistics of exported elements.

        Returns
        -------
        dict[str, Any]
            Dictionary containing statistics of exported elements
        """
        statistics = {}
        for medium, elements in self.exported_elements.items():
            not_exported = self.not_exported_elements.get(medium, [])
            statistics[medium] = {
                "exported": len(elements),
                "not_exported": len(not_exported),
                "total": len(elements) + len(not_exported),
            }
        return statistics

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
        point_based_data = self._get_element_data(medium.point_data.assigned)
        elem_export.extend(point_based_data)

        line_based_data = self._get_element_data(medium.line_data.assigned)
        elem_export.extend(line_based_data)
        return elem_export

    def _append_exported_elements(
        self, config: MediumConfig, export: list[dict | None], elements: list[ObjectData]
    ) -> None:
        exported_idx = [idx for idx in range(len(export)) if export[idx] is not None]
        exported_elements = [elements[idx] for idx in exported_idx]
        if config.medium not in self.exported_elements:
            self.exported_elements[config.medium] = []
        self.exported_elements[config.medium].extend(exported_elements)

    def _append_not_exported_elements(
        self, config: MediumConfig, export: list[dict | None], elements: list[ObjectData]
    ) -> None:
        not_exp_idx = [idx for idx in range(len(export)) if export[idx] is None]
        not_exported_data = [elements[idx] for idx in not_exp_idx]

        if config.medium not in self.not_exported_elements:
            self.not_exported_elements[config.medium] = []
        self.not_exported_elements[config.medium].extend(not_exported_data)

    def _get_element_data(self, element_data: list[tuple[list[ObjectData], MediumConfig]]) -> list[dict[str, Any]]:
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

        for elements, config in element_data:
            result = [self._export_element(elem) for elem in elements]
            export_data = [data for data in result if data is not None]
            elements_export_data.extend(export_data)
            self._append_exported_elements(config, result, elements)
            self._append_not_exported_elements(config, result, elements)
        return elements_export_data

    def _get_parameters(self, element: ObjectData) -> list[dict[str, Any]]:
        """Export parameters of an element to dictionary format.

        Parameters
        ----------
        element : ObjectData
            Element whose parameters to export

        Returns
        -------
        list[dict[str, Any]]
            List of dictionaries containing parameter information
        """
        parameters = []
        for param in element.get_parameters(update=True):
            parameters.append(param.to_dict())
        return parameters

    def _export_element(self, element: ObjectData) -> dict[str, Any] | None:
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
        element_data: dict = {
            "object_type": element.object_type.name.upper(),
            "family": element.family,
            "family_type": element.family_type,
        }
        if element.is_point_based:
            element_data["insert_point"] = _export_point(element.point)
        elif element.is_line_based:
            element_data["line_points"] = _export_points(element.points)
        else:
            return None

        parameters = self._get_parameters(element)
        if len(parameters) > 0:
            element_data["parameters"] = parameters
        return element_data

    def _export_dimensions(self, dimensions: Dimension) -> list[dict[str, Any]]:
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
        dimension_dict = [param.to_dict() for param in dimensions.to_parameters()]
        for dim in dimension_dict:
            if "name" not in dim or dim["name"] != "Height":
                continue
            dim["value"] = max(dim["value"], 1.2)
        return dimension_dict
