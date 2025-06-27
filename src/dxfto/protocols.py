"""Protocol definitions for grouping and text assignment strategies.

This module defines the interfaces that allow different strategies
for grouping DXF elements and assigning texts to pipes to be
easily interchangeable following SOLID principles.
"""

from typing import Iterable, Protocol

from .models import (
    AssingmentData,
    DxfText,
    Medium,
    MediumConfig,
    ObjectData,
    Point3D,
)


class IGroupingStrategy(Protocol):
    """Protocol for grouping DXF elements into media.

    Implementations should group pipes, shafts, and texts into
    logical media (e.g., "Abwasserleitung", "Wasserleitung").
    """

    def group_elements(self, elements: list[ObjectData], texts: list[DxfText]) -> list[Medium]:
        """Group DXF elements into media.

        Parameters
        ----------
        elements : list[ObjectData]
            List of elements from DXF file
        texts : list[DxfText]
            List of texts from DXF file

        Returns
        -------
        list[Medium]
            List of media with grouped elements
        """
        ...


class IAssignmentStrategy(Protocol):
    """Protocol for assigning texts to pipes.

    Implementations should assign text elements to pipes based on
    spatial proximity and validity rules.
    """

    def texts_to_line_based(self, elements: list[ObjectData], texts: list[DxfText]) -> list[ObjectData]:
        """Assign texts to elements based on spatial proximity.

        Parameters
        ----------
        elements : list[ObjectData]
            List of line based elements to assign texts to
        texts : list[DxfText]
            List of available texts for assignment

        Returns
        -------
        list[ObjectData]
            List of elements with assigned texts where applicable
        """
        ...

    def texts_to_point_based(self, elements: list[ObjectData], texts: list[DxfText]) -> list[ObjectData]:
        """Assign texts to elements based on spatial proximity.

        Parameters
        ----------
        elements : list[ObjectData]
            List of point based elements to assign texts to
        texts : list[DxfText]
            List of available texts for assignment

        Returns
        -------
        list[ObjectData]
            List of elements with assigned texts where applicable
        """

        ...


class IElevationUpdater(Protocol):
    def update_elevation(self, points: Iterable[Point3D]) -> list[Point3D]:
        """Update Z coordinates for a list of points using elevation data.

        Parameters
        ----------
        points : list[Point3D]
            List of points to update with elevation data

        Returns
        -------
        list[Point3D]
            List of points with updated Z coordinates
        """
        ...


class IDimensionUpdater(Protocol):
    """Protocol for updating dimensions of media based on their elements."""

    def update_elements(self, assignment: AssingmentData) -> None:
        """Update dimensions of all elements in the assignment data container.

        This method should iterate through all elements in the assignment
        and use the `update_dimension` method to update each element's

        Parameters
        ----------
        assignment : AssingmentData
            Assignment data containing elements and their assigned texts
        """
        ...

    def update_dimension(self, element: ObjectData, config: MediumConfig) -> None:
        """Update dimensions of a single element based on other information.

        Default unit is used to determine how to interpret dimensions
        when no unit is specified or could be extracted from the element.

        Parameters
        ----------
        element : ObjectData
            Element to update dimensions for
        config : MediumConfig
            Configuration for the medium containing the default unit
        """
        ...


class IExporter(Protocol):
    """Protocol for exporting media data to a specified format."""

    def export_data(self, mediums: list[Medium]) -> None:
        """Export media data to a specified format (e.g., JSON).

        Parameters
        ----------
        mediums : list[Medium]
            List of media to export

        Returns
        -------
        None
        """
        ...
