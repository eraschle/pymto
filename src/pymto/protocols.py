"""Protocol definitions for grouping and text assignment strategies.

This module defines the interfaces that allow different strategies
for grouping DXF elements and assigning texts to pipes to be
easily interchangeable following SOLID principles.
"""

from collections.abc import Iterable
from typing import Any, Protocol

from .models import (
    AssignmentData,
    AssignmentGroup,
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

    def texts_to_point_based(self, medium: Medium, groups: list[AssignmentGroup]) -> None:
        """Assign texts to elements based on spatial proximity.

        Parameters
        ----------
        medium : Medium
            Medium containing elements and texts for assignment
        groups : list[AssignmentGroup]
            List of groups containing elements and texts for assignment
        """
        ...

    def texts_to_line_based(self, medium: Medium, groups: list[AssignmentGroup]) -> None:
        """Assign texts to elements based on spatial proximity.

        Parameters
        ----------
        medium : Medium
            Medium containing elements and texts for assignment
        groups : list[AssignmentGroup]
            List of groups containing elements and texts for assignment
        """
        ...


class IObjectCreator(Protocol):
    """Protocol for creating objects from DXF entities."""

    def create_objects(self, configs: list[MediumConfig]) -> list[tuple[list[ObjectData], list[DxfText]]]:
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
    def update_elements(self, assignment: AssignmentData) -> None:
        """Update elevation of all elements in the assignment data container.

        Parameters
        ----------
        assignment : AssignmentData
            Assignment data containing elements and their assigned texts
        """
        ...


class IGradientAnalyzer(Protocol):
    def load_mediums(self, mediums: Iterable[Medium]) -> None:
        """Load mediums for gradient analysis.

        Parameters
        ----------
        mediums : Iterable[Medium]
            List of mediums to analyze
        """
        ...

    def adjust_gradient(self) -> None:
        """Update gradient of all elements in the assignment data container.

        Parameters
        ----------
        assignment : AssingmentData
            Assignment data containing elements and their assigned texts
        """
        ...

    def calculate_shaft_height(self, elements: list[ObjectData]) -> None:
        """Calculate shaft height for all elements in the assignment data container.

        Parameters
        ----------
        assignment : AssingmentData
            Assignment data containing elements and their assigned texts
        """
        ...


class IParameterUpdater(Protocol):
    """Protocol for updating dimensions of media based on their elements."""

    def update_elements(self, assignment: AssignmentData) -> None:
        """Update dimensions of all elements in the assignment data container.

        This method should iterate through all elements in the assignment
        and use the `update_dimension` method to update each element's

        Parameters
        ----------
        assignment : AssignmentData
            Assignment data containing elements and their assigned texts
        """
        ...


class IRevitFamilyNameUpdater(Protocol):
    """Protocol for update family and family type names of medium on their elements."""

    def update_elements(self, assignment: AssignmentData) -> None:
        """Update family and family type names of all elements in the assignment data container.

        This method should iterate through all elements in the assignment and
        replace placeholder names with actual values of the element's.

        Parameters
        ----------
        assignment : AssignmentData
            Assignment data containing elements and their assigned texts
        """
        ...

    def add_parameters(self, assignment: AssignmentData) -> None:
        """Add parameters to all elements in the assignment data container.

        This method iterate through all elements in the assignment and
        add parameters based on the medium configuration.

        Parameters
        ----------
        assignment : AssignmentData
            Assignment data containing elements and their assigned texts
        """
        ...

    def remove_duplicate_point_based(self, assignment: AssignmentData) -> tuple[list[ObjectData], list[ObjectData]]:
        """Remove duplicate point-based objects in the assignment data.

        This method should iterate through all point-based elements in the assignment
        and remove duplicates based on their coordinates.

        Parameters
        ----------
        assignment : AssignmentData
            Assignment data containing elements and their assigned texts

        Returns
        -------
        list[ObjectData]
            List of removed duplicate point-based objects
        """
        ...


class IDimensionCalculator(Protocol):
    """Protocol for exporting media data to a specified format."""

    def calculate_dimension(self, elements: list[ObjectData]) -> Any:
        """Calculate dimensions for a set of elements.

        This method should iterate through all elements and calculate the
        dimensions of the elements it is responsible for.

        Parameters
        ----------
        elements : list[ObjectData]
            List of elements to calculate shaft height for
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
