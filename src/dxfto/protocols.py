"""Protocol definitions for grouping and text assignment strategies.

This module defines the interfaces that allow different strategies
for grouping DXF elements and assigning texts to pipes to be
easily interchangeable following SOLID principles.
"""

from typing import Protocol, runtime_checkable

from .models import DxfText, Medium, ObjectData


@runtime_checkable
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


@runtime_checkable
class ITextAssignmentStrategy(Protocol):
    """Protocol for assigning texts to pipes.

    Implementations should assign text elements to pipes based on
    spatial proximity and validity rules.
    """

    def assign_texts_to_line_based(
        self, elements: list[ObjectData], texts: list[DxfText]
    ) -> list[ObjectData]:
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

    def assign_texts_to_point_based(
        self, elements: list[ObjectData], texts: list[DxfText]
    ) -> list[ObjectData]:
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
