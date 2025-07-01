"""Protocol definitions for grouping and text assignment strategies.

This module defines the interfaces that allow different strategies
for grouping DXF elements and assigning texts to pipes to be
easily interchangeable following SOLID principles.
"""

from typing import Protocol

from .models import (
    AssingmentData,
    AssingmentGroup,
    DxfText,
    Medium,
    MediumConfig,
    ObjectData,
)


class IAssignmentStrategy(Protocol):
    """Protocol for assigning texts to pipes.

    Implementations should assign text elements to pipes based on
    spatial proximity and validity rules.
    """

    def texts_to_point_based(self, medium: Medium, groups: list[AssingmentGroup]) -> None:
        """Assign texts to elements based on spatial proximity.

        Parameters
        ----------
        medium : Medium
            Medium containing elements and texts for assignment
        groups : list[AssingmentGroup]
            List of groups containing elements and texts for assignment
        """
        ...

    def texts_to_line_based(self, medium: Medium, groups: list[AssingmentGroup]) -> None:
        """Assign texts to elements based on spatial proximity.

        Parameters
        ----------
        medium : Medium
            Medium containing elements and texts for assignment
        groups : list[AssingmentGroup]
            List of groups containing elements and texts for assignment
        """
        ...


class IObjectCreator(Protocol):
    """Protocol for creating objects from DXF entities."""

    def create_objects(self, configs: list[MediumConfig]) -> tuple[list[list[ObjectData]], list[list[DxfText]]]:
        """Create objects and texts from DXF entities based on configurations.

        Parameters
        ----------
        configs : list[MediumConfig]
            List of configurations specifying which layers to process

        Returns
        -------
        tuple[list[list[ObjectData]], list[list[DxfText]]]
            Tuple containing lists of extracted objects and texts
        """
        ...


class IElevationUpdater(Protocol):
    def update_elements(self, assigment: AssingmentData) -> None:
        """Update elevation of all elements in the assignment data container.

        Parameters
        ----------
        assignment : AssingmentData
            Assignment data containing elements and their assigned texts
        """
        ...


class IDimensionUpdater(Protocol):
    """Protocol for updating dimensions of media based on their elements."""

    def update_elements(self, assigment: AssingmentData) -> None:
        """Update dimensions of all elements in the assignment data container.

        This method should iterate through all elements in the assignment
        and use the `update_dimension` method to update each element's

        Parameters
        ----------
        assignment : AssingmentData
            Assignment data containing elements and their assigned texts
        """
        ...


class IRevitFamilyNameUpdater(Protocol):
    """Protocol for update family and family type names of medium on their elements."""

    def update_elements(self, assigment: AssingmentData) -> None:
        """Update family and family type names of all elements in the assignment data container.

        This method should iterate through all elements in the assignment and
        replace placeholder names with actual values of the element's.

        Parameters
        ----------
        assignment : AssingmentData
            Assignment data containing elements and their assigned texts
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

    def get_exported_statistics(self) -> dict[str, dict[str, int]]:
        """Get statistics of exported media.

        Returns
        -------
        dict[str, dict[str, int]]
            Statistics of exported elements grouped by medium
        """
        ...
