"""Protocol definitions for grouping and text assignment strategies.

This module defines the interfaces that allow different strategies
for grouping DXF elements and assigning texts to pipes to be
easily interchangeable following SOLID principles.
"""

from typing import Protocol, runtime_checkable

from .models import DXFText, Medium, Pipe, Shaft


@runtime_checkable
class IGroupingStrategy(Protocol):
    """Protocol for grouping DXF elements into media.

    Implementations should group pipes, shafts, and texts into
    logical media (e.g., "Abwasserleitung", "Wasserleitung").
    """

    def group_elements(
        self, pipes: list[Pipe], shafts: list[Shaft], texts: list[DXFText]
    ) -> list[Medium]:
        """Group DXF elements into media.

        Parameters
        ----------
        pipes : list[Pipe]
            List of pipes from DXF file
        shafts : list[Shaft]
            List of shafts from DXF file
        texts : list[DXFText]
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

    def assign_texts_to_pipes(self, pipes: list[Pipe], texts: list[DXFText]) -> list[Pipe]:
        """Assign texts to pipes based on spatial proximity.

        Parameters
        ----------
        pipes : list[Pipe]
            List of pipes to assign texts to
        texts : list[DXFText]
            List of available texts for assignment

        Returns
        -------
        list[Pipe]
            List of pipes with assigned texts where applicable
        """
        ...
